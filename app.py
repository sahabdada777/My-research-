"""RESEARCHER HU - expanded academic research backend.

Provider secrets belong in Render environment variables, never in frontend files.
Long documents are generated in sections because provider token limits and hosting
request timeouts make a single 50,000-word response impractical.
"""
from __future__ import annotations

import html
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from groq import Groq
from openai import OpenAI
from google import genai
from anthropic import Anthropic
from docx import Document
from pypdf import PdfReader
from docx.shared import Inches, Pt
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

# ============================================================================
# 1. Application configuration
# ============================================================================
APP_NAME = "RESEARCHER HU"
APP_VERSION = "3.0.0"
MAX_PROMPT_CHARS = int(os.getenv("MAX_PROMPT_CHARS", "40000"))
MAX_EXPORT_CHARS = int(os.getenv("MAX_EXPORT_CHARS", "500000"))
MAX_SECTION_WORDS = int(os.getenv("MAX_SECTION_WORDS", "8000"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/tmp/researcher_hu_outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("researcher_hu")

# Set CORS_ORIGINS to the exact deployed frontend origin(s), comma-separated.
# Example: https://username.github.io,https://username.github.io/My-research-
_raw_origins = os.getenv("CORS_ORIGINS", "*")
CORS_ORIGINS = [item.strip() for item in _raw_origins.split(",") if item.strip()]

app = FastAPI(
    title=APP_NAME,
    description="AI-assisted academic research, writing and document export API.",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ============================================================================
# 2. AI provider configuration and model names
# ============================================================================
# These defaults are examples. Provider model availability can change. Override
# them in Render Environment settings without editing source code.
GROQ_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-haiku-latest")

PROVIDER_ORDER = ["groq", "gemini", "openrouter", "openai", "claude"]
PROVIDER_MODELS = {
    "groq": GROQ_MODEL,
    "gemini": GEMINI_MODEL,
    "openrouter": OPENROUTER_MODEL,
    "openai": OPENAI_MODEL,
    "claude": CLAUDE_MODEL,
}

# Per-provider output ceilings. These are deliberately conservative defaults;
# a provider/model may enforce a lower limit. They are not word-count promises.
PROVIDER_MAX_OUTPUT = {
    "groq": int(os.getenv("GROQ_MAX_OUTPUT_TOKENS", "8192")),
    "gemini": int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "8192")),
    "openrouter": int(os.getenv("OPENROUTER_MAX_OUTPUT_TOKENS", "8192")),
    "openai": int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "8192")),
    "claude": int(os.getenv("CLAUDE_MAX_OUTPUT_TOKENS", "8192")),
}

# ============================================================================
# 3. Academic modules and quality rules
# ============================================================================
MODULES: dict[str, tuple[str, str]] = {
    "general": ("General Academic Assistant", "Answer the academic question directly and explain key terms."),
    "topic_selection": ("Research Topic Selection", "Help refine a feasible, specific and researchable topic. Explain scope and feasibility."),
    "abstract": ("Abstract Writing", "Prepare a structured or unstructured abstract using only supplied study details. Do not invent findings."),
    "introduction": ("Introduction Writing", "Develop background, context, problem statement, rationale, gap, objectives and significance. Do not assert an evidence-based gap without evidence."),
    "problem_statement": ("Research Problem and Rationale", "Clarify the research problem, context, rationale, gap and contribution. Distinguish evidence from interpretation."),
    "literature": ("Review of Literature", "Organise supplied studies study-wise or thematically. Use only supplied author, year, method, sample, findings and limitations."),
    "theoretical_framework": ("Theoretical and Conceptual Framework", "Explain relevant theories and constructs. Do not claim a theory supports a relationship unless justified."),
    "objectives_hypotheses": ("Objectives, Questions and Hypotheses", "Create aligned objectives, research questions and testable hypotheses from the user's stated problem."),
    "methodology": ("Research Methodology", "Assist with design, population, sampling, sample size, instrument, variables, ethics and analysis. Distinguish planned from completed work."),
    "questionnaire": ("Questionnaire Development", "Draft clear, neutral, non-leading survey questions and response scales aligned with objectives."),
    "data_analysis": ("Data Analysis", "Analyse only supplied data. Explain test assumptions. Never fabricate observations, percentages, coefficients, p-values or tables."),
    "results": ("Results and Discussion", "Interpret only supplied findings and connect them to objectives and supplied literature."),
    "conclusion": ("Conclusion and Recommendations", "Summarise supported findings, implications, limitations and future research without adding unsupported results."),
    "peer_review": ("Critical Peer Review", "Separate genuine factual, theoretical, methodological and writing issues into major and minor revisions."),
    "proofreading": ("Academic Proofreading", "Correct grammar, spelling, clarity and academic flow while preserving meaning and claims."),
    "paraphrasing": ("Academic Rewriting", "Rewrite supplied text with original phrasing while preserving meaning. Do not help disguise plagiarism or fabricate citations."),
    "references": ("References and Citations", "Format only bibliographic information supplied by the user. Flag missing details. Never invent DOI, page range or publication data."),
    "research_paper": ("Research Paper Builder", "Draft a scholarly paper from the user's actual topic, evidence, method and findings. Flag missing evidence."),
    "thesis": ("Thesis and Dissertation Support", "Support chapter planning and drafting from user-provided research information. Do not present hypothetical work as completed research."),
    "synopsis": ("Research Synopsis Builder", "Prepare synopsis sections aligned with the topic, objectives, questions, hypotheses and feasible methodology."),
    "grant_proposal": ("Research Proposal Support", "Help prepare rationale, objectives, work plan, expected outputs and budget narrative without inventing institutional requirements."),
    "other": ("Other Academic Work", "Assist with reports, presentations, academic correspondence and related scholarly tasks."),
}

COMMON_RULES = """Write in a natural, precise and credible academic style. Vary sentence length and avoid repetitive or robotic phrasing. Use clear headings where useful. Do not fabricate numerical data, survey responses, sample sizes, statistical results, authors, article titles, journals, citations, URLs or DOIs. Do not claim a source, database, journal indexing status or fact has been verified unless reliable evidence was actually checked. Distinguish established information from assumptions and recommendations. If essential information is missing, state what is missing instead of guessing. Never present proposed methods or hypothetical examples as completed research. Return document-ready content without a conversational preamble."""

LENGTH_GUIDANCE = {
    "Short": "Be concise but answer all essential parts.",
    "Medium": "Provide a moderately detailed, well-organised answer.",
    "Detailed": "Provide a thorough, well-structured answer with explanations and useful subheadings.",
}

# ============================================================================
# 4. Request and response schemas
# ============================================================================
ProviderName = Literal["auto", "groq", "gemini", "openrouter", "openai", "claude"]
ModuleName = Literal[
    "general", "topic_selection", "abstract", "introduction", "problem_statement",
    "literature", "theoretical_framework", "objectives_hypotheses", "methodology",
    "questionnaire", "data_analysis", "results", "conclusion", "peer_review",
    "proofreading", "paraphrasing", "references", "research_paper", "thesis",
    "synopsis", "grant_proposal", "other",
]

class ChatRequest(BaseModel):
    module: ModuleName = "general"
    prompt: str = Field(min_length=2, max_length=MAX_PROMPT_CHARS)
    language: Literal["English", "Hindi", "Hinglish"] = "English"
    citation_style: Literal["APA 7", "MLA", "Chicago", "Harvard", "None"] = "APA 7"
    writing_length: Literal["Short", "Medium", "Detailed"] = "Detailed"
    provider: ProviderName = "auto"
    temperature: float = Field(default=0.35, ge=0, le=1)

class HumaniseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=30000)
    language: Literal["English", "Hindi", "Hinglish"] = "English"
    provider: ProviderName = "auto"

class ExportRequest(BaseModel):
    title: str = Field(default="Research Document", min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=MAX_EXPORT_CHARS)

class LongFormPlanRequest(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    topic: str = Field(min_length=5, max_length=MAX_PROMPT_CHARS)
    target_words: int = Field(default=50000, ge=1000, le=50000)
    language: Literal["English", "Hindi", "Hinglish"] = "English"
    citation_style: Literal["APA 7", "MLA", "Chicago", "Harvard", "None"] = "APA 7"
    document_type: Literal["thesis", "dissertation", "research_paper", "book", "report"] = "thesis"
    provider: ProviderName = "auto"
    context: str = Field(default="", max_length=MAX_PROMPT_CHARS)

class LongFormSectionRequest(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    topic: str = Field(min_length=5, max_length=MAX_PROMPT_CHARS)
    section_title: str = Field(min_length=2, max_length=300)
    section_instructions: str = Field(min_length=5, max_length=MAX_PROMPT_CHARS)
    target_words: int = Field(default=2500, ge=200, le=MAX_SECTION_WORDS)
    language: Literal["English", "Hindi", "Hinglish"] = "English"
    citation_style: Literal["APA 7", "MLA", "Chicago", "Harvard", "None"] = "APA 7"
    provider: ProviderName = "auto"
    previous_context: str = Field(default="", max_length=MAX_PROMPT_CHARS)
    source_material: str = Field(default="", max_length=MAX_PROMPT_CHARS)

# ============================================================================
# 5. Provider status, routing and prompt construction
# ============================================================================
def provider_status() -> dict[str, bool]:
    return {
        "groq": bool(GROQ_KEY),
        "gemini": bool(GEMINI_KEY),
        "openrouter": bool(OPENROUTER_KEY),
        "openai": bool(OPENAI_KEY),
        "claude": bool(ANTHROPIC_KEY),
    }


def configured_order() -> list[str]:
    status = provider_status()
    return [name for name in PROVIDER_ORDER if status.get(name)]


def get_provider_order(requested: str) -> list[str]:
    status = provider_status()
    if requested != "auto":
        if not status.get(requested, False):
            raise HTTPException(
                status_code=400,
                detail=f"{requested} is not configured. Add its API key in Render Environment Variables.",
            )
        return [requested]
    order = configured_order()
    if not order:
        raise HTTPException(status_code=503, detail="No AI provider is configured on the server.")
    return order


def language_rule(language: str) -> str:
    if language == "Hindi":
        return "Write entirely in natural academic Hindi using Devanagari script. Keep technical terms clear."
    if language == "Hinglish":
        return "Write in natural Hinglish using a simple Hindi-English mix in Roman script, unless the user requests another script."
    return "Write entirely in clear, natural academic English."

def citation_rule(style: str) -> str:
    if style == "None":
        return "Do not add citations unless source details are provided by the user."
    return f"Use {style} conventions only for source details supplied or genuinely verified. Never invent references. Mark missing bibliographic details clearly."


def build_system_prompt(req: ChatRequest) -> str:
    module_name, instructions = MODULES[req.module]
    return "\n\n".join([
        COMMON_RULES,
        f"TASK MODULE: {module_name}\n{instructions}",
        f"LANGUAGE: {language_rule(req.language)}",
        f"LENGTH: {LENGTH_GUIDANCE[req.writing_length]}",
        f"CITATION REQUIREMENT: {citation_rule(req.citation_style)}",
    ])


def build_longform_system_prompt(language: str, citation_style: str) -> str:
    return "\n\n".join([
        COMMON_RULES,
        "You are the long-form academic writing engine for RESEARCHER HU. Work only on the requested section. Maintain terminology, scope and argument continuity with the supplied context. Do not repeat previous sections. Use meaningful headings and coherent transitions. Do not pad text to reach a word target. Never fabricate research data, sources or findings.",
        f"LANGUAGE: {language_rule(language)}",
        f"CITATIONS: {citation_rule(citation_style)}",
        "If the user has not supplied empirical results, do not write invented results. Clearly identify placeholders or information still required.",
    ])

# ============================================================================
# 6. Provider-specific generation functions
# ============================================================================
def call_groq(system_prompt: str, user_prompt: str, temperature: float) -> str:
    client = Groq(api_key=GROQ_KEY, timeout=120.0, max_retries=1)
    result = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        max_completion_tokens=PROVIDER_MAX_OUTPUT["groq"],
        temperature=temperature,
    )
    return (result.choices[0].message.content or "").strip()


def call_gemini(system_prompt: str, user_prompt: str, temperature: float) -> str:
    client = genai.Client(api_key=GEMINI_KEY, http_options={"timeout": 120000})
    result = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_prompt,
        config={
            "system_instruction": system_prompt,
            "max_output_tokens": PROVIDER_MAX_OUTPUT["gemini"],
            "temperature": temperature,
        },
    )
    return (result.text or "").strip()


def call_openrouter(system_prompt: str, user_prompt: str, temperature: float) -> str:
    client = OpenAI(
        api_key=OPENROUTER_KEY,
        base_url="https://openrouter.ai/api/v1",
        timeout=120.0,
        max_retries=1,
        default_headers={
            "HTTP-Referer": os.getenv("SITE_URL", "https://researcherhu.pages.dev"),
            "X-Title": APP_NAME,
        },
    )
    result = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        max_tokens=PROVIDER_MAX_OUTPUT["openrouter"],
        temperature=temperature,
    )
    return (result.choices[0].message.content or "").strip()


def call_openai(system_prompt: str, user_prompt: str, temperature: float) -> str:
    client = OpenAI(api_key=OPENAI_KEY, timeout=120.0, max_retries=1)
    result = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        max_tokens=PROVIDER_MAX_OUTPUT["openai"],
        temperature=temperature,
    )
    return (result.choices[0].message.content or "").strip()


def call_claude(system_prompt: str, user_prompt: str, temperature: float) -> str:
    client = Anthropic(api_key=ANTHROPIC_KEY, timeout=120.0, max_retries=1)
    result = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=PROVIDER_MAX_OUTPUT["claude"],
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=temperature,
    )
    parts = [block.text for block in result.content if getattr(block, "type", None) == "text"]
    return "\n".join(parts).strip()


PROVIDER_CALLS = {
    "groq": call_groq,
    "gemini": call_gemini,
    "openrouter": call_openrouter,
    "openai": call_openai,
    "claude": call_claude,
}


def generate_with_provider(
    requested_provider: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.35,
) -> tuple[str, str, str]:
    """Generate with selected provider or configured fallback order.

    Returns response text, provider name and model name. Raw provider exceptions
    are logged by class only and are never exposed to the browser.
    """
    failures: list[str] = []
    for provider in get_provider_order(requested_provider):
        try:
            answer = PROVIDER_CALLS[provider](system_prompt, user_prompt, temperature)
            if not answer:
                raise RuntimeError("empty_response")
            logger.info("Generation succeeded provider=%s model=%s", provider, PROVIDER_MODELS[provider])
            return answer, provider, PROVIDER_MODELS[provider]
        except Exception as exc:
            logger.warning("Provider failed provider=%s error_type=%s", provider, type(exc).__name__)
            failures.append(f"{provider}:{type(exc).__name__}")
            if requested_provider != "auto":
                break
    raise HTTPException(
        status_code=502,
        detail="AI generation failed. Check provider key, quota, model availability and Render logs. " + ", ".join(failures),
    )

# ============================================================================
# 7. Core API endpoints and service information
# ============================================================================
@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html><head><meta charset='utf-8'><title>RESEARCHER HU API</title></head>"
        "<body style='font-family:Arial,sans-serif;padding:32px'>"
        "<h1>RESEARCHER HU API is running</h1>"
        "<p>Backend service is online. Open the frontend workspace to use the platform.</p>"
        "<p><a href='/health'>Health</a> | <a href='/docs'>API documentation</a></p></body></html>"
    )


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "application": APP_NAME,
        "version": APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/providers")
def providers() -> dict[str, Any]:
    return {
        "providers": provider_status(),
        "models": PROVIDER_MODELS,
        "default": "auto",
        "available": configured_order(),
        "note": "Only configuration status and model identifiers are returned. Secret values are never returned.",
    }


@app.get("/info")
def info() -> dict[str, Any]:
    return {
        "application": APP_NAME,
        "version": APP_VERSION,
        "modules": list(MODULES.keys()),
        "languages": ["English", "Hindi", "Hinglish"],
        "citation_styles": ["APA 7", "MLA", "Chicago", "Harvard", "None"],
        "providers": provider_status(),
        "models": PROVIDER_MODELS,
        "exports": ["docx", "pdf"],
        "uploads": ["docx", "pdf", "txt"],
        "humanise_word_limit": 500,
        "long_form_target_words": 50000,
        "long_form_mode": "section_by_section",
    }


@app.post("/api/humanise")
def humanise_text(req: HumaniseRequest) -> dict[str, Any]:
    """Improve clarity and natural academic flow without disguising authorship."""
    word_count = len(re.findall(r"\b[\w’'-]+\b", req.text, flags=re.UNICODE))
    if word_count > 500:
        raise HTTPException(status_code=400, detail=f"Humanise Text accepts up to 500 words per prompt. Your text has {word_count} words.")
    system = """You are RESEARCHER HU's academic language editor. Revise the supplied text so it reads naturally and clearly while preserving the author's meaning, claims, evidence, terminology, numbers, quotations and citations. Vary sentence length and structure where appropriate. Improve transitions, paragraph flow, grammar and readability. Remove unnecessary repetition and inflated wording. Retain an appropriate scholarly tone for academic content. Do not add facts, references, findings or citations. Do not intentionally introduce errors, imitate a named person, or claim to bypass AI detectors. Return only the revised text."""
    system += "\nLANGUAGE: " + language_rule(req.language)
    answer, provider, model = generate_with_provider(req.provider, system, req.text, 0.25)
    return {"status": "success", "reply": answer, "response": answer, "content": answer, "word_count": word_count, "provider": provider, "model": model}

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)) -> dict[str, Any]:
    """Extract text from DOCX, PDF or TXT uploads for editing in the browser."""
    filename = (file.filename or "").strip()
    suffix = Path(filename).suffix.lower()
    if suffix not in {".docx", ".pdf", ".txt"}:
        raise HTTPException(status_code=400, detail="Only DOCX, PDF and TXT files are supported.")
    raw = await file.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Maximum upload size is 10 MB.")
    try:
        if suffix == ".txt":
            extracted = raw.decode("utf-8-sig")
        elif suffix == ".docx":
            import io
            doc = Document(io.BytesIO(raw))
            extracted = "\n\n".join(par.text for par in doc.paragraphs if par.text.strip())
            for table in doc.tables:
                for row in table.rows:
                    extracted += "\n" + " | ".join(cell.text for cell in row.cells)
        else:
            import io
            reader = PdfReader(io.BytesIO(raw))
            extracted = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        logger.warning("Document extraction failed type=%s", type(exc).__name__)
        raise HTTPException(status_code=400, detail="The file could not be read. Please try a text-based DOCX, PDF or TXT file.")
    if not extracted.strip():
        raise HTTPException(status_code=400, detail="No readable text was found. Scanned PDFs need OCR before upload.")
    if len(extracted) > MAX_PROMPT_CHARS:
        raise HTTPException(status_code=413, detail=f"Extracted text is too long. Please upload a shorter file (maximum {MAX_PROMPT_CHARS} characters).")
    return {"filename": Path(filename).name, "text": extracted, "characters": len(extracted), "word_count": len(extracted.split())}

@app.get("/api/modules")
def list_modules() -> dict[str, Any]:
    return {
        "modules": [
            {"id": key, "name": value[0], "description": value[1]}
            for key, value in MODULES.items()
        ]
    }


@app.post("/api/chat")
@app.post("/chat")
def chat(req: ChatRequest, request: Request) -> dict[str, Any]:
    request_id = str(uuid.uuid4())
    system_prompt = build_system_prompt(req)
    answer, provider, model = generate_with_provider(
        req.provider, system_prompt, req.prompt, req.temperature
    )
    logger.info("Chat request completed request_id=%s module=%s", request_id, req.module)
    return {
        "status": "success",
        "request_id": request_id,
        "module": req.module,
        "provider": provider,
        "model": model,
        "reply": answer,
        "response": answer,
        "content": answer,
    }

# ============================================================================
# 8. Long-form research writing: 50,000-word project planning
# ============================================================================
@app.post("/api/longform/plan")
def longform_plan(req: LongFormPlanRequest) -> dict[str, Any]:
    """Create a suggested chapter plan; it does not generate 50,000 words at once."""
    system = "You are an academic project planner. Create a practical chapter outline and allocate the requested total word count. Do not invent research findings or references. Return valid JSON with keys: project_title, total_target_words, chapters (array of chapter, purpose, target_words, sections), notes."
    user = (
        f"Document type: {req.document_type}\nTitle: {req.title}\nTopic: {req.topic}\n"
        f"Target total words: {req.target_words}\nLanguage: {req.language}\n"
        f"Citation style: {req.citation_style}\nAdditional context: {req.context}\n"
        "Allocate chapter and section word targets whose sum is close to the total target. "
        "Clearly label empirical chapters that require actual user data."
    )
    answer, provider, model = generate_with_provider(req.provider, system, user, 0.25)
    return {
        "status": "success",
        "request_id": str(uuid.uuid4()),
        "provider": provider,
        "model": model,
        "target_words": req.target_words,
        "plan": answer,
        "generation_mode": "Generate each planned section separately using /api/longform/section.",
    }


@app.post("/api/longform/section")
def longform_section(req: LongFormSectionRequest) -> dict[str, Any]:
    """Generate one bounded section. Call repeatedly and assemble sections client-side.

    This endpoint intentionally does not promise 50,000 words in one HTTP request.
    A 50k project is planned once and written in multiple section requests.
    """
    system = build_longform_system_prompt(req.language, req.citation_style)
    user = "\n\n".join([
        f"DOCUMENT TITLE: {req.title}",
        f"OVERALL TOPIC: {req.topic}",
        f"SECTION TO WRITE: {req.section_title}",
        f"SECTION INSTRUCTIONS: {req.section_instructions}",
        f"TARGET LENGTH: Approximately {req.target_words} words. Treat this as a target, not a reason to pad or repeat.",
        f"PREVIOUS DOCUMENT CONTEXT: {req.previous_context or 'No previous section context supplied.'}",
        f"USER-SUPPLIED SOURCE MATERIAL: {req.source_material or 'No source material supplied. Do not invent sources or citations.'}",
        "Write only this section. Preserve continuity, avoid repeating previous sections, and identify information that must be supplied by the researcher.",
    ])
    answer, provider, model = generate_with_provider(req.provider, system, user, 0.3)
    word_count = len(re.findall(r"\b[\w'-]+\b", answer))
    return {
        "status": "success",
        "request_id": str(uuid.uuid4()),
        "provider": provider,
        "model": model,
        "section_title": req.section_title,
        "target_words": req.target_words,
        "actual_word_count": word_count,
        "content": answer,
        "continuation_required": word_count < int(req.target_words * 0.75),
        "note": "Save this section in the user's project before requesting the next section. Persistent project storage is not included in this backend yet.",
    }

# ============================================================================
# 9. Utility functions for document exports
# ============================================================================
def clean_filename(value: str, extension: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")[:60] or "research_document"
    return f"{safe}_{uuid.uuid4().hex[:8]}.{extension}"


def markdown_blocks(content: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n", content) if block.strip()]


def add_markdownish_docx(doc: Document, content: str) -> None:
    """Convert basic Markdown headings, paragraphs and lists to Word elements."""
    for block in markdown_blocks(content):
        lines = block.splitlines()
        if all(line.lstrip().startswith(("- ", "* ")) for line in lines):
            for line in lines:
                doc.add_paragraph(line.lstrip()[2:].strip(), style="List Bullet")
        elif all(re.match(r"^\d+[.)]\s+", line.strip()) for line in lines):
            for line in lines:
                doc.add_paragraph(re.sub(r"^\d+[.)]\s+", "", line.strip()), style="List Number")
        elif block.startswith("### "):
            doc.add_heading(block[4:].strip(), level=3)
        elif block.startswith("## "):
            doc.add_heading(block[3:].strip(), level=2)
        elif block.startswith("# "):
            doc.add_heading(block[2:].strip(), level=1)
        else:
            doc.add_paragraph(block)


def create_docx(title: str, content: str, destination: Path) -> None:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Inches(1)
    section.left_margin = section.right_margin = Inches(1)
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal.paragraph_format.line_spacing = 1.5
    doc.add_heading(title, level=0)
    add_markdownish_docx(doc, content)
    doc.save(destination)


def create_pdf(title: str, content: str, destination: Path) -> None:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("RhuTitle", parent=styles["Title"], fontSize=18, leading=23, spaceAfter=18)
    heading_style = ParagraphStyle("RhuHeading", parent=styles["Heading2"], fontSize=13, leading=17, spaceBefore=12, spaceAfter=7)
    body_style = ParagraphStyle("RhuBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=10.5, leading=16, alignment=TA_JUSTIFY, spaceAfter=9)
    story: list[Any] = [Paragraph(html.escape(title), title_style), Spacer(1, 8)]
    for block in markdown_blocks(content):
        if block.startswith("### "):
            story.append(Paragraph(html.escape(block[4:]), heading_style))
        elif block.startswith("## "):
            story.append(Paragraph(html.escape(block[3:]), heading_style))
        elif block.startswith("# "):
            story.append(Paragraph(html.escape(block[2:]), heading_style))
        else:
            story.append(Paragraph(html.escape(block).replace("\n", "<br/>"), body_style))
    SimpleDocTemplate(
        str(destination), pagesize=A4, rightMargin=52, leftMargin=52, topMargin=52, bottomMargin=52
    ).build(story)

# ============================================================================
# 10. Export endpoints
# ============================================================================
@app.post("/export/docx")
def export_docx(req: ExportRequest) -> FileResponse:
    path = OUTPUT_DIR / clean_filename(req.title, "docx")
    create_docx(req.title, req.content, path)
    return FileResponse(
        path,
        filename=clean_filename(req.title, "docx"),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.post("/export/pdf")
def export_pdf(req: ExportRequest) -> FileResponse:
    path = OUTPUT_DIR / clean_filename(req.title, "pdf")
    create_pdf(req.title, req.content, path)
    return FileResponse(path, filename=clean_filename(req.title, "pdf"), media_type="application/pdf")

# ============================================================================
# 11. Error handling and operational safeguards
# ============================================================================
@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled server error path=%s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Unexpected server error. Please try again later."},
    )


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# ============================================================================
# 12. Local development entry point
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "false").lower() == "true",
    )

code = r'''import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from groq import Groq
# --------------------------------------------------
# RESEARCHER HU - API CONFIGURATION
# --------------------------------------------------
APP_TITLE = "RESEARCHER HU Academic Research API"
APP_VERSION = "4.0"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
app = FastAPI(
    title=APP_TITLE,
    description="AI-powered academic research assistant",
    version=APP_VERSION,
)
# GitHub Pages frontend origin. Add more origins in Render
# environment variable CORS_ORIGINS as comma-separated URLs.
allowed_origins = ["https://sahabdada777.github.io"]
extra_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]
allowed_origins = list(dict.fromkeys(allowed_origins + extra_origins))
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
# --------------------------------------------------
# ACADEMIC SYSTEM INSTRUCTIONS
# --------------------------------------------------
SYSTEM_PROMPT = """
You are RESEARCHER HU, an AI-powered academic research assistant.
LANGUAGE:
- Support all languages.
- If the user selects Auto, All languages, or does not specify a language,
  identify the language of the user's prompt and respond in that language.
- Support Hindi, English, Hinglish and other languages.
- Follow an explicitly selected language when provided.
ACADEMIC INTEGRITY:
- Never invent authors, papers, journals, publication years, DOIs or URLs.
- Never claim a reference is verified unless its details are available and checked.
- Clearly identify uncertainty and limitations.
- Do not invent research data, survey responses, sample sizes, statistics,
  findings, p-values, regression results or participant observations.
- Use only data supplied by the user or reliable sources actually provided.
- Distinguish facts, calculations, interpretations and hypothetical examples.
- Do not fabricate citations to make an answer look complete.
ACADEMIC WRITING:
- Use a natural mix of short, medium and long sentences.
- Avoid robotic wording, repetitive phrases and unnecessary elaboration.
- Use precise, accessible language with an appropriate scholarly tone.
- Preserve the meaning of source material when editing or paraphrasing.
- Follow the requested citation style, such as APA 7, when possible.
- If source details are missing, ask for them rather than inventing references.
RESEARCH SUPPORT:
Assist with abstracts, introductions, literature reviews, research gaps,
research questions, objectives, hypotheses, methodology, sampling,
questionnaire development, statistical analysis, results and discussion,
conclusions, recommendations, peer review, paraphrasing, citations,
research papers and thesis chapters.
RESPONSE QUALITY:
- Follow the selected tool/module and requested response length.
- Give structured answers with useful headings where appropriate.
- For statistical work, explain the method and calculations.
- Never report a statistical result unless it was calculated from actual data.
- Be transparent about limitations.
"""
# --------------------------------------------------
# REQUEST SCHEMA
# --------------------------------------------------
class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=20000)
    module: str = "General Academic Research"
    language: str = "Auto-detect / All languages"
    writing_length: str = "Medium"
    citation_style: str = "APA 7"
    provider: str = "auto"
# --------------------------------------------------
# RESPONSE GENERATION
# --------------------------------------------------
def generate_reply(request: ChatRequest):
    if not GROQ_API_KEY or client is None:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY is missing in Render environment variables.",
        )
    user_message = (
        f"Research tool/module: {request.module}\n"
        f"Required language: {request.language}\n"
        f"Response length: {request.writing_length}\n"
        f"Citation style: {request.citation_style}\n"
        f"Requested provider: {request.provider}\n\n"
        f"User request:\n{request.prompt}"
    )
    length_limits = {
        "short": 1200,
        "medium": 2500,
        "detailed": 4096,
        "long": 4096,
    }
    max_tokens = length_limits.get(request.writing_length.lower(), 2500)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_completion_tokens=max_tokens,
        )
 answer = completion.choices[0].message.content or ""
        if not answer.strip():
            raise HTTPException(
                status_code=502,
                detail="The AI provider returned an empty response.",
            )
        return {
            "status": "success",
            "model": MODEL_NAME,
            "provider": "groq",
            "reply": answer,
            "response": answer,
            "content": answer,
        }
    except HTTPException:
        raise
    except Exception as exc:
        # Return a useful error without exposing API keys.
        raise HTTPException(
            status_code=502,
            detail=f"AI generation failed: {type(exc).__name__}: {str(exc)}",
        )

# --------------------------------------------------
# BASIC AND STATUS ROUTES
# --------------------------------------------------
@app.get("/")
def home():
    return {
        "name": APP_TITLE,
        "status": "active",
        "version": APP_VERSION,
        "model": MODEL_NAME,
    }
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "api_key_configured": bool(GROQ_API_KEY),
        "model": MODEL_NAME,
    }
@app.get("/info")
def info():
    return {
        "application": APP_TITLE,
        "version": APP_VERSION,
        "model": MODEL_NAME,
        "features": [
            "Multilingual academic writing",
            "Abstract and introduction writing",
            "Literature review support",
            "Research gap analysis",
            "Research methodology",
            "Statistical analysis guidance",
            "Peer review assistance",
            "Citation and referencing support",
        ],
    }
@app.get("/api/providers")
def providers():
    return {
        "active_provider": "groq",
        "configured": bool(GROQ_API_KEY),
        "model": MODEL_NAME,
        "providers": [
            {
                "id": "groq",
                "name": "Groq",
                "configured": bool(GROQ_API_KEY),
            }
        ],
    }
# --------------------------------------------------
# CHAT ROUTES
# --------------------------------------------------
@app.post("/chat")
def chat(request: ChatRequest):
    return generate_reply(request)
@app.post("/api/chat")
def api_chat(request: ChatRequest):
    return generate_reply(request)
@app.get("/chat")
def chat_get(prompt: str):
    request = ChatRequest(prompt=prompt)
    return generate_reply(request)
'''
path='/mnt/data/researcher_hu_app_clean.py'
open(path,'w',encoding='utf-8').write(code)
import ast
ast.parse(code)
len(code.splitlines()), path

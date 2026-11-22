from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from groq import Groq
import os

# ==========================================
# 1. APPLICATION CONFIGURATION
# ==========================================

app = FastAPI(
    title="My Academic Research Assistant",
    description="AI-powered academic research and analysis API",
    version="3.0"
)

# ==========================================
# 2. API CONFIGURATION
# ==========================================

api_key = os.getenv("GROQ_API_KEY")

MODEL = "openai/gpt-oss-120b"

client = Groq(api_key=api_key) if api_key else None


# ==========================================
# 3. ACADEMIC RESEARCH SYSTEM PROMPT
# ==========================================

SYSTEM_PROMPT = """
You are an advanced academic research assistant
specialized in PhD-level research and scholarly writing.

Your highest priorities are accuracy, authenticity,
academic integrity and evidence-based reasoning.

==========================================
A. RESEARCH ACCURACY
==========================================

1. Provide factually accurate and evidence-based
academic information.

2. Never invent research papers, authors, journal
names, publication years, DOIs or references.

3. Never present unverified information as fact.

4. Clearly distinguish verified information,
interpretations, assumptions and limitations.

5. Never claim to have accessed a research paper,
database or website unless its content was actually
provided or retrieved.

6. Do not create unsupported research claims.

==========================================
B. REAL DATA AND NUMERICAL INTEGRITY
==========================================

1. NEVER fabricate, invent, assume or generate
fake numerical data.

2. Never create fictional:
   - Sample sizes
   - Survey responses
   - Percentages
   - Frequencies
   - Mean and median values
   - Standard deviations
   - Correlation coefficients
   - Regression coefficients
   - P-values
   - Confidence intervals
   - Statistical test results
   - Research findings

3. Use numerical data ONLY when:
   - It is supplied by the user.
   - It comes from an authentic and verifiable source.
   - It is calculated correctly from actual data.

4. Never fill missing data with invented values.

5. Never manipulate original data to achieve
a desired or predetermined research result.

6. Never create fictional questionnaire responses
or participant observations.

7. If actual numerical data is unavailable, clearly
state that reliable data could not be verified.

8. Never present hypothetical examples as actual
research findings.

9. Show formulas and calculation procedures when
performing statistical analysis.

10. Cross-check calculations before reporting results.

11. Preserve the original sample size, study period,
observations and statistical findings.

12. Clearly distinguish:
   - Primary data
   - Secondary data
   - Calculated results
   - Estimates
   - Hypothetical examples

13. If two authentic sources report conflicting
figures, disclose the discrepancy.

14. Never create false precision or unsupported
decimal places.

15. Data integrity must always take priority over
completing an answer.

==========================================
C. AUTHENTIC REFERENCES AND CITATIONS
==========================================

1. Never generate fictional academic references.

2. Never invent DOI numbers or URLs.

3. Never attribute a statement to an author without
a verifiable source.

4. Use authentic academic publications whenever
their details are available.

5. Prefer peer-reviewed journals, academic books,
official reports and credible institutional sources.

6. Verify publication details before presenting
references as verified.

7. Follow APA 7th edition when requested.

8. If a reference cannot be verified, clearly
mention that its authenticity is unconfirmed.

==========================================
D. ACADEMIC WRITING STYLE
==========================================

1. Use a natural combination of short, medium
and long sentences.

2. Maintain variation in sentence structure.

3. Avoid repetitive sentence openings and
mechanical paragraph construction.

4. Avoid robotic, generic and unnecessarily
formal language.

5. Use simple, precise and meaningful vocabulary.

6. Maintain a scholarly tone without making
the writing unnecessarily complicated.

7. Avoid repeating words, phrases and expressions.

8. Maintain natural transitions between sentences
and paragraphs.

9. Use punctuation only where necessary.

10. Avoid unnecessary elaboration and repetition.

11. Maintain a natural human writing rhythm.

12. Writing should be polished but not excessively
over-polished or artificial.

13. Preserve the original meaning and argument
when editing academic content.

==========================================
E. RESEARCH AND ANALYTICAL CAPABILITIES
==========================================

Assist with:

1. Literature Review (ROL)
2. Systematic Literature Review (SLR)
3. Research Gap Identification
4. Research Problem Formulation
5. Research Objectives and Hypotheses
6. Research Methodology
7. Sampling Techniques
8. Questionnaire Development
9. Statistical Analysis
10. Data Interpretation
11. Critical Evaluation of Research Papers
12. Research Paper Writing
13. Thesis Chapter Development
14. Academic Referencing
15. Research Findings and Discussion

==========================================
F. STATISTICAL ANALYSIS RULES
==========================================

1. Use only actual datasets supplied by the user
or verified data sources.

2. Do not manufacture observations.

3. Explain the statistical method used.

4. Show relevant formulas where appropriate.

5. Never report a statistical test result without
actually calculating it from available data.

6. Identify missing variables and insufficient data.

7. Explain the limitations of statistical analysis.

8. Do not claim statistical significance without
a valid statistical test.

==========================================
G. CRITICAL RESEARCH EVALUATION
==========================================

When reviewing a research paper:

1. Evaluate the research objectives.
2. Examine the literature review.
3. Assess the research methodology.
4. Check sampling and sample size justification.
5. Examine data analysis and interpretation.
6. Identify inconsistencies and unsupported claims.
7. Evaluate references and citations.
8. Identify actual research limitations.
9. Provide specific and practical improvements.

Do not invent shortcomings that are not present
in the supplied research material.

==========================================
H. FINAL RESPONSE RULE
==========================================

Prioritize accuracy over confidence.

If information is missing, ask for it.

If data cannot be verified, disclose it.

If a calculation cannot be performed, explain why.

Never sacrifice academic integrity to produce
a complete-looking answer.

Always provide clear, logical and evidence-conscious
academic responses.
"""


# ==========================================
# 4. REQUEST MODEL
# ==========================================

class ChatRequest(BaseModel):

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=20000
    )


# ==========================================
# 5. AI RESPONSE FUNCTION
# ==========================================

def generate_reply(prompt: str):

    if not api_key or not client:

        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is not configured."
        )

    try:

        chat_completion = client.chat.completions.create(

            model=MODEL,

            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            reasoning_effort="high",

            max_completion_tokens=4096
        )

        reply = chat_completion.choices[0].message.content

        return {
            "status": "success",
            "model": MODEL,
            "reply": reply
        }

    except Exception as e:

        raise HTTPException(
            status_code=502,
            detail=f"AI model request failed: {str(e)}"
        )


# ==========================================
# 6. HOME ENDPOINT
# ==========================================

@app.get("/")
def home():

    return {
        "message": "My Academic Research Assistant API is running!",
        "status": "active",
        "model": MODEL,
        "version": "3.0"
    }


# ==========================================
# 7. GET CHAT ENDPOINT
# ==========================================

@app.get("/chat")
def chat(prompt: str):

    return generate_reply(prompt)


# ==========================================
# 8. POST CHAT ENDPOINT
# ==========================================

@app.post("/chat")
def chat_post(request: ChatRequest):

    return generate_reply(request.prompt)


# ==========================================
# 9. HEALTH CHECK ENDPOINT
# ==========================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "api_key_configured": bool(api_key),
        "model": MODEL
    }


# ==========================================
# 10. API INFORMATION
# ==========================================

@app.get("/info")
def info():

    return {
        "application": "Academic Research Assistant",
        "model": MODEL,
        "features": [
            "Academic Research",
            "Literature Review",
            "Research Gap Analysis",
            "Research Methodology",
            "Statistical Analysis",
            "Real Data Integrity",
            "Citation Integrity",
            "APA 7 Referencing",
            "Academic Writing"
        ]
    }

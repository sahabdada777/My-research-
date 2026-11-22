            "content": reply
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
    return generate_reply(
        request.prompt,
        request.module,
        request.language,
        request.writing_length,
        request.citation_style,
    )


# Current frontend uses /api/chat. Keep /chat above for backward compatibility.
@app.post("/api/chat")
def api_chat(request: ChatRequest):
    return chat_post(request)


@app.get("/api/providers")
def api_providers():
    return {
        "active_provider": "groq",
        "configured": bool(api_key),
        "model": MODEL,
        "providers": [{"id": "groq", "name": "Groq", "configured": bool(api_key)}],
    }


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

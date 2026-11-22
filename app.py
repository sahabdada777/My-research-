            raise RuntimeError("Groq package is not installed")
        groq_client = Groq(api_key=GROQ_API_KEY)
        result = groq_client.chat.completions.create(
            model=GROQ_MODEL, messages=messages, max_completion_tokens=max_tokens
        )
        return result.choices[0].message.content or "", GROQ_MODEL
    if provider == "openrouter":
        text = await call_openai_compatible("https://openrouter.ai/api/v1/chat/completions", OPENROUTER_API_KEY, OPENROUTER_MODEL, messages, provider)
        return text, OPENROUTER_MODEL
    if provider == "openai":
        text = await call_openai_compatible("https://api.openai.com/v1/chat/completions", OPENAI_API_KEY, OPENAI_MODEL, messages, provider)
        return text, OPENAI_MODEL
    if provider == "gemini":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        contents = [{"role": "user", "parts": [{"text": messages[0]["content"] + "\n\n" + messages[1]["content"]}]}]
        payload = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens}}
        async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=15.0)) as client_http:
            response = await client_http.post(url, json=payload)
        if response.status_code >= 400:
            raise RuntimeError(f"Gemini HTTP {response.status_code}: {response.text[:700]}")
        data = response.json()
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        return "\n".join(p.get("text", "") for p in parts), GEMINI_MODEL
    if provider == "claude":
        payload = {"model": CLAUDE_MODEL, "max_tokens": max_tokens, "system": messages[0]["content"], "messages": [{"role": "user", "content": messages[1]["content"]}]}
        headers = {"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=15.0)) as client_http:
            response = await client_http.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        if response.status_code >= 400:
            raise RuntimeError(f"Claude HTTP {response.status_code}: {response.text[:700]}")
        data = response.json()
        return "\n".join(x.get("text", "") for x in data.get("content", []) if x.get("type") == "text"), CLAUDE_MODEL
    raise RuntimeError(f"Unsupported provider: {provider}")

@app.get("/")
async def home():
    return {"name": APP_NAME, "status": "active", "version": APP_VERSION}

@app.get("/health")
async def health():
    return {"status": "healthy", "version": APP_VERSION, "configured_providers": [p for p, key in [("groq", GROQ_API_KEY), ("openrouter", OPENROUTER_API_KEY), ("gemini", GEMINI_API_KEY), ("openai", OPENAI_API_KEY), ("claude", ANTHROPIC_API_KEY)] if key]}

@app.get("/api/providers")
async def providers():
    return {"providers": [
        {"id": "groq", "name": "Groq", "configured": bool(GROQ_API_KEY), "model": GROQ_MODEL},
        {"id": "gemini", "name": "Gemini", "configured": bool(GEMINI_API_KEY), "model": GEMINI_MODEL},
        {"id": "openrouter", "name": "OpenRouter", "configured": bool(OPENROUTER_API_KEY), "model": OPENROUTER_MODEL},
        {"id": "openai", "name": "OpenAI", "configured": bool(OPENAI_API_KEY), "model": OPENAI_MODEL},
        {"id": "claude", "name": "Claude", "configured": bool(ANTHROPIC_API_KEY), "model": CLAUDE_MODEL},
    ], "fallback_order": ["groq", "gemini", "openrouter", "openai", "claude"]}

@app.get("/info")
async def info():
    return {"application": APP_NAME, "version": APP_VERSION, "features": ["Multilingual research writing", "Literature review assistance", "Research methodology", "Peer review", "Provider selection and fallback"]}

@app.post("/chat")
@app.post("/api/chat")
async def chat(req: ChatRequest):
    messages = build_messages(req)
    try:
        order = provider_order(req.provider)
    except HTTPException:
        raise
    if not order:
        raise HTTPException(status_code=503, detail="No AI provider is configured. Add provider API keys in Render Environment.")
    errors = []
    for provider in order:
        try:
            answer, model = await call_provider(provider, messages, req)
            if not answer.strip():
                raise RuntimeError("Provider returned an empty response")
            return {"status": "success", "provider": provider, "model": model, "reply": answer, "response": answer, "content": answer}
        except Exception as exc:
            logger.exception("Provider %s failed", provider)
            errors.append(f"{provider}: {type(exc).__name__}: {str(exc)[:350]}")
            if req.provider.lower() != "auto":
                break
    raise HTTPException(status_code=502, detail="All selected AI requests failed. " + " | ".join(errors))

@app.get("/chat")
async def chat_get(prompt: str, provider: str = "auto", language: str = "Auto"):
    req = ChatRequest(prompt=prompt, provider=provider, language=language)
    return await chat(req)

@app.post("/export/docx")
async def export_docx(req: ExportRequest):
    if Document is None:
        raise HTTPException(status_code=503, detail="python-docx is not installed")
    doc = Document()
    doc.add_heading(req.title, 0)
    for paragraph in req.content.split("\n"):
        doc.add_paragraph(paragraph)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": "attachment; filename=researcher-hu.docx"})

@app.post("/export/pdf")
async def export_pdf(req: ExportRequest):
    if canvas is None:
        raise HTTPException(status_code=503, detail="reportlab is not installed")
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(45, y, req.title[:90])
    y -= 35
    pdf.setFont("Helvetica", 10)
    for line in req.content.splitlines():
        if y < 55:
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica", 10)
        pdf.drawString(45, y, line[:110])
        y -= 14
    pdf.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=researcher-hu.pdf"})


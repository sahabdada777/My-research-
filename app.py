                "request_id": request_id,
                "module": req.module,
                "provider": provider,
                "model": model_name,
                "reply": answer,
            }
        except Exception as exc:  # do not return raw exception details or secrets to browser
            logger.warning("AI request %s failed for provider=%s: %s", request_id, provider, type(exc).__name__)
            failures.append(f"{provider} ({type(exc).__name__})")

    if req.provider != "auto":
        raise HTTPException(status_code=502, detail=f"The selected AI provider failed. Reference: {request_id}")
    raise HTTPException(
        status_code=502,
        detail="All configured AI providers failed: " + ", ".join(failures) + f". Reference: {request_id}",
    )

# ---------------------------------------------------------------------------
# Document exports
# ---------------------------------------------------------------------------
def clean_filename(value: str, extension: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")[:60] or "research_document"
    return f"{safe}_{uuid.uuid4().hex[:8]}.{extension}"


def add_markdownish_docx(doc: Document, content: str) -> None:
    """Simple, safe conversion for headings, paragraphs and bullet lines."""
    for raw_block in re.split(r"\n\s*\n", content):
        block = raw_block.strip()
        if not block:
            continue
        lines = block.splitlines()
        if all(line.lstrip().startswith(("- ", "* ")) for line in lines):
            for line in lines:
                doc.add_paragraph(line.lstrip()[2:].strip(), style="List Bullet")
        elif block.startswith("### "):
            doc.add_heading(block[4:].strip(), level=3)
        elif block.startswith("## "):
            doc.add_heading(block[3:].strip(), level=2)
        elif block.startswith("# "):
            doc.add_heading(block[2:].strip(), level=1)
        else:
            doc.add_paragraph(block)

@app.post("/export/docx")
def export_docx(req: ExportRequest) -> FileResponse:
    path = OUTPUT_DIR / clean_filename(req.title, "docx")
    doc = Document()
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Inches(1)
    section.left_margin = section.right_margin = Inches(1)
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal.paragraph_format.line_spacing = 1.5
    doc.add_heading(req.title, level=0)
    add_markdownish_docx(doc, req.content)
    doc.save(path)
    return FileResponse(
        path,
        filename=clean_filename(req.title, "docx"),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

@app.post("/export/pdf")
def export_pdf(req: ExportRequest) -> FileResponse:
    path = OUTPUT_DIR / clean_filename(req.title, "pdf")
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("RHUTitle", parent=styles["Title"], fontSize=18, leading=23, spaceAfter=18)
    heading_style = ParagraphStyle("RHUHeading", parent=styles["Heading2"], fontSize=13, leading=17, spaceBefore=12, spaceAfter=7)
    body_style = ParagraphStyle(
        "RHUBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=10.5,
        leading=16, alignment=TA_JUSTIFY, spaceAfter=9,
    )
    story = [Paragraph(html.escape(req.title), title_style), Spacer(1, 8)]
    for raw_block in re.split(r"\n\s*\n", req.content):
        block = raw_block.strip()
        if not block:
            continue
        if block.startswith("### "):
            story.append(Paragraph(html.escape(block[4:]), heading_style))
        elif block.startswith("## "):
            story.append(Paragraph(html.escape(block[3:]), heading_style))
        elif block.startswith("# "):
            story.append(Paragraph(html.escape(block[2:]), heading_style))
        else:
            safe_text = html.escape(block).replace("\n", "<br/>")
            story.append(Paragraph(safe_text, body_style))
    SimpleDocTemplate(
        str(path), pagesize=A4, rightMargin=52, leftMargin=52, topMargin=52, bottomMargin=52
    ).build(story)
    return FileResponse(path, filename=clean_filename(req.title, "pdf"), media_type="application/pdf")

# Friendly validation response for malformed JSON and unexpected server errors.
@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error on %s", request.url.path)
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"detail": "Unexpected server error. Please try again later."})

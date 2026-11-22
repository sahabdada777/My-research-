# RESEARCHER HU deployment package

This package contains the matched frontend and FastAPI backend.

## Render backend
- Root directory: repository root
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Add provider keys in Render Environment Variables: `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY` (optional: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). Never put these keys in frontend files.
- `CORS_ORIGINS` may be set to `https://sahabdada777.github.io`. If the GitHub Pages URL changes, update this to the site's origin only, without a path.

## GitHub Pages frontend
- Publish the contents of `frontend/` at the GitHub Pages publishing root.
- The `config.js` file currently points to `https://my-research-ctbl.onrender.com`.
- Supabase values are intentionally blank. Login/signup will not work until the Supabase URL and public publishable/anon key are entered in `frontend/config.js`.

## Tests and limits
- Backend syntax is checked before deployment.
- Test `/health`, `/api/providers`, and `/docs` after deploying.
- AI provider keys, quotas, model access, and live generation must be verified on Render. They cannot be confirmed by a local syntax check.
- Long-form writing is section-by-section. A single 50,000-word response is not supported.
- PDF export currently uses ReportLab's standard font and may not render Hindi text correctly. DOCX is preferable for Hindi content.
- Supabase authentication is not yet enforced on backend API routes. Do not treat this package as production-secure or expose private research data until authentication, authorization, storage and database policies are implemented and tested.

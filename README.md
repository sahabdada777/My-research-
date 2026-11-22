# RESEARCHER HU — Complete Starter v2

**Tagline:** Research Smarter. Discover More.

This package is a refreshed starter for the existing `My-research-` GitHub project. It includes a FastAPI backend, a blue responsive website, task-specific AI modules, a configurable model router, and a Supabase Auth frontend connection point.

## Included structure

```text
researcher-hu-complete-starter/
├── app.py
├── requirements.txt
├── render.yaml
├── .env.example
├── .gitignore
├── README.md
└── frontend/
    ├── index.html
    ├── styles.css
    ├── script.js
    └── config.js
```

## Important before uploading

- This is a **new starter package**, not a verified replacement for the current live backend.
- Download and keep a backup of the existing GitHub repository first.
- Do not overwrite the current `app.py` until the existing endpoints and Render deployment have been compared.
- The frontend is a static website. The AI workspace calls the FastAPI `/api/chat` endpoint.
- Login/signup uses Supabase Auth after you create a Supabase project and add its Project URL and public anon key to `frontend/config.js`.
- The Supabase login is a frontend authentication starter. Before production, protect backend API endpoints by validating Supabase access tokens and configure database Row Level Security. Do not store private provider keys in frontend files.
- The task router is implemented, but all routes use the configured Groq model by default. It does not mean multiple independent AI providers have already been connected.
- The current starter does not yet include persistent user projects, file uploads, vector search, payment, or long-running 50,000-word generation.

## 1. Render backend setup

Use the existing Render service only after comparing this version with the current deployed app.

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

Set these environment variables in Render:

- `GROQ_API_KEY` — your private Groq key
- `GROQ_MODEL` — `openai/gpt-oss-120b` if this model is enabled for your Groq account

Optional task routes:

- `MODEL_WRITING`
- `MODEL_REASONING`
- `MODEL_LITERATURE`
- `MODEL_DATA`
- `MODEL_REVIEW`
- `MODEL_VERIFICATION`
- `MODEL_FAST`

At first, each route can use the same available Groq model. Use a different model ID only after confirming that your provider account supports it.

Check the API:
- `/health`
- `/api/modules`
- `/docs`

## 2. Supabase login/signup

1. Create a Supabase project.
2. Open Project Settings → API.
3. Copy the Project URL and the public `anon` key.
4. Put those two public values in `frontend/config.js`.
5. Never put a Supabase `service_role` key or Groq key in frontend files.
6. Configure the allowed site URL and redirect URLs in Supabase Authentication settings.

## 3. Frontend setup

Edit `frontend/config.js`:

```js
window.RESEARCHER_HU_CONFIG = {
  API_BASE_URL: "https://YOUR-RENDER-SERVICE.onrender.com",
  SUPABASE_URL: "YOUR_SUPABASE_PROJECT_URL",
  SUPABASE_ANON_KEY: "YOUR_SUPABASE_ANON_KEY"
};
```

For a static host, publish the contents of the `frontend` folder. The frontend must use the actual Render API URL and Supabase project values.

## 4. Model routing

The backend has task routes for writing, reasoning, literature, data, review, verification and fast responses. The routes are configurable independently with environment variables. By default, all routes use `GROQ_MODEL`; add other providers only after their credentials, model IDs, error handling and usage limits have been tested.

## Academic integrity

The prompts instruct the system not to invent studies, citations, DOI links, sample sizes, data or findings. Users must still verify AI-generated material against original sources.

from fastapi import FastAPI
import os
from groq import Groq

app = FastAPI()

# API Key Render ke Environment Variables se uthayega
api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key)

@app.get("/")
def home():
    return {"message": "Bhai, API chalu hai!"}

@app.get("/chat")
def chat(prompt: str):
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
        )
        return {"reply": chat_completion.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}

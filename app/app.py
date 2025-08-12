import os
import requests
import openai
from fastapi import FastAPI, File, Query
from pypdf import PdfReader
from io import BytesIO

LLM_URL = os.getenv("LLM_URL")
LLM_ID = os.getenv("LLM_ID")

try:
    health_check = requests.get(LLM_URL, timeout = 5)
    print(f"INFO:\tPing to {LLM_URL} returned status: {health_check.status_code}")
except Exception as e:
    print(f"Error pinging {LLM_URL}: {e}")

app = FastAPI(title="LLM Wrapper")

@app.post("/cover-letter")
async def cover_letter(file: bytes = File(..., description="Resume (*.pdf) >25MB")):
    # size check (keeps it small and non-streaming)
    if len(file) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    # quick PDF signature check
    if not file.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Not a valid PDF")

    reader = PdfReader(BytesIO(file))
    number_of_pages = len(reader.pages)
    page = reader.pages[0]
    return {
        "pages": number_of_pages,
        "first_page_text": text
    }

@app.get("/complete")
def complete(
    prompt: str = Query(..., description="User's prompt"),
    system: str | None = Query(None, description="Optional system prompt"),
    temperature: float = Query(0.7, description="Sampling temperature"),
    max_tokens: int = Query(512, description="Maximum tokens to generate"),
):
    client = openai.OpenAI(
        base_url = LLM_URL,
        api_key = "docker"
    )

    completion = client.chat.completions.create(
        model=LLM_ID.lower(), 
        messages=[
            {"role": "system", "content": system or "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ]
    )

    return completion.choices[0].message.content
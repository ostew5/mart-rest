import os
import requests
from fastapi import FastAPI, Query

LLM_URL = os.getenv("LLM_URL")
LLM_ID = os.getenv("LLM_ID")

try:
    health_check = requests.get(LLM_URL, timeout = 5)
    print(f"Ping to {LLM_URL} returned status: {health_check.status_code}")
except Exception as e:
    print(f"Error pinging {LLM_URL}: {e}")

app = FastAPI(title="LLM Wrapper")

@app.get("/models")
def models():
    r = requests.get(f"{LLM_URL}models", timeout=600)
    r.raise_for_status()
    return r.json()

@app.get("/complete")
def complete(
    prompt: str = Query(..., description="User's prompt"),
    system: str | None = Query(None, description="Optional system prompt"),
    temperature: float = Query(0.7, description="Sampling temperature"),
    max_tokens: int = Query(512, description="Maximum tokens to generate"),
):
    payload = {
        "model": LLM_ID,
        "messages": [
            {"role": "system", "content": system or "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        r = requests.post(f"{LLM_URL}chat/completions", json=payload, timeout=600)
        r.raise_for_status()
        data = r.json()
        return {"completion": data["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"internal error": {"exception" : f"{e}", "payload" : payload}}
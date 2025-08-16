import os
import requests
import openai
from fastapi import FastAPI, File, Query, HTTPException
import json
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader, select_autoescape
import re
from fastapi.responses import StreamingResponse
from io import BytesIO

from pyapp.make_prompt import make_prompt
from pyapp.indexing import get_pdf_content, get_job_listing_details, index_resume, retrieve

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

EMBEDDER_URL = os.getenv("EMBEDDER_URL")

app = FastAPI(title="LLM Wrapper")

def bullets_to_html(text: str) -> str:
    if not text:
        return ""
    lines = text.splitlines()
    out = []
    in_list = False
    for line in lines:
        if re.match(r'^\s*([*\-•])\s+', line):
            if not in_list:
                out.append("<ul>")
                in_list = True
            item = re.sub(r'^\s*([*\-•])\s+', '', line)
            out.append(f"<li>{item}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            if line.strip():
                out.append(f"<p>{line}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)

env = Environment(
    loader=FileSystemLoader("pyapp/templates"),
    autoescape=select_autoescape(["html", "xml"])
)
env.filters["bullets"] = bullets_to_html

@app.on_event("startup")
async def initialise():
    print("INFO:\t\tInitialising app...")

    print(f"INFO:\t\tChecking Embedder connection...")
    try:
        health_check = requests.get(EMBEDDER_URL, timeout = 5)
        print(f"INFO:\t\tPing to {EMBEDDER_URL} returned status: {health_check.status_code}")
    except Exception as e:
        print(f"ERROR:\t\tError pinging {EMBEDDER_URL}: {e}")

    print("INFO:\t\tSetting up OpenAI client for Embedder connection...")
    embedder = openai.OpenAI(
        base_url = EMBEDDER_URL,
        api_key = "docker"
    )

    print("INFO:\t\tSetting up app.state...")
    app.state.embedder = embedder

    print("INFO:\t\tApp initialisation complete.")

@app.post("/generate-cover-letter")
async def generate_cover_letter(
    job_listing_url: str = Query(..., description="URL of the LinkedIn job listing"),
    resume: bytes = File(..., description="Resume in PDF format")
):
    # size check (require pdf to be less than 25MB)
    if len(resume) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    # quick PDF signature check
    if not resume.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Not a valid PDF")

    resume_content = get_pdf_content(resume)
    
    job_details = get_job_listing_details(job_listing_url)

    index, chunks = index_resume(app, resume_content)

    job_details_retrieved = retrieve(app, index, chunks, job_details['description'], k=8)
    applicant_name_retrieved = retrieve(app, index, chunks, "name", k=3)
    applicant_cont_retrieved = retrieve(app, index, chunks, "contact details", k=3)
    applicant_loca_retrieved = retrieve(app, index, chunks, "location", k=3)

    system, prompt = make_prompt(
        job_details['title'],
        job_details['company'],
        job_details['location'],
        job_details['description'],
        job_details_retrieved,
        applicant_name_retrieved + applicant_cont_retrieved + applicant_loca_retrieved
    )

    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }

    payload = {
        "system_instruction": {
            "parts": [
                {
                    "text": system
                }
            ]
        },
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "letterhead": { "type": "STRING" },
                    "date": { "type": "STRING" },
                    "inside_address": { "type": "STRING" },
                    "attention_line": { "type": "STRING" },
                    "salutation": { "type": "STRING" },
                    "letterbody": { "type": "STRING" },
                    "closing": { "type": "STRING" },
                    "signature": { "type": "STRING" }
                },
                "propertyOrdering": [
                    "letterhead", 
                    "date", 
                    "inside_address", 
                    "attention_line", 
                    "salutation", 
                    "letterbody", 
                    "closing", 
                    "signature"
                ]
                }
            }
        }
    }

    response = requests.post(GEMINI_API_URL, headers=headers, json=payload)

    text = json.loads(response.text).get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

    print(f"INFO:\t\tReceived response: {text}")

    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())

    payload = json.loads(text)
    obj = payload[0] if isinstance(payload, list) else payload
    
    FIELDS = [
        "letterhead", "date", "inside_address", "attention_line",
        "salutation", "letterbody", "closing", "signature"
    ]

    ctx = {k: obj.get(k, "") for k in FIELDS}

    print(f"INFO:\t\tGenerated cover letter context: {ctx}")

    try:
        tpl = env.get_template("letter.html")
        html = tpl.render(**ctx)
        pdf_io = BytesIO()
        print(f"INFO:\t\tRendering HTML to PDF: {html}...")
        HTML(string=html, base_url=".").write_pdf(pdf_io)
        pdf_io.seek(0)
        return StreamingResponse(
            pdf_io,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="letter.pdf"'},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create PDF: {e}")

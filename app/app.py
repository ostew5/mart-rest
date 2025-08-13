import os
import requests
import openai
from fastapi import FastAPI, File, Query
from pypdf import PdfReader
from io import BytesIO
from bs4 import BeautifulSoup
import json
import re
import faiss, numpy as np
from datetime import date

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

LLM_URL = os.getenv("LLM_URL")
LLM_ID = os.getenv("LLM_ID")

EMBEDDER_URL = os.getenv("EMBEDDER_URL")
EMBEDDER_ID = os.getenv("EMBEDDER_ID")

app = FastAPI(title="LLM Wrapper")

@app.on_event("startup")
async def initialise():
    print("INFO:\t\tInitialising app...")
    print(f"INFO:\t\tChecking LLM connection...")
    try:
        health_check = requests.get(LLM_URL, timeout = 5)
        print(f"INFO:\t\tPing to {LLM_URL} returned status: {health_check.status_code}")
    except Exception as e:
        print(f"ERROR:\t\tError pinging {LLM_URL}: {e}")

    print("INFO:\t\tSetting up OpenAI client for LLM connection...")
    llm = openai.OpenAI(
        base_url = LLM_URL,
        api_key = "docker"
    )

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
    app.state.llm = llm
    app.state.embedder = embedder

    print("INFO:\t\tApp initialisation complete.")

def get_pdf_content(file: bytes):
    reader = PdfReader(BytesIO(file))
    number_of_pages = len(reader.pages)
    text = ""
    for page in reader.pages:
	    text += page.extract_text()
    return text

def get_job_listing_details(job_listing_url: str):
    job_listing = requests.get(job_listing_url, timeout = 5)

    if job_listing.status_code != 200:
        raise HTTPException(status_code=404, detail="Job listing not found")

    with open("job-listing-selectors.json", "r") as f:
        selectors = json.load(f)

    print(f"INFO:\t\tLoaded selectors: {selectors}")

    if not selectors:
        raise HTTPException(status_code=500, detail="Could not load job listing selectors")

    soup = BeautifulSoup(job_listing.text, "html.parser")
    
    result = {}

    for key, selector_list in selectors.items():
        value = None
        for selector in selector_list:
            el = soup.select_one(selector)
            if el and el.get_text(strip=True):
                value = el.get_text(strip=True)
                break
        result[key] = value

    return result

def mark_guarded_newlines_manual(text: str) -> str:
    result = []
    last_nl_pos = -1  # position of last newline (or -1 for start)
    
    for i, ch in enumerate(text):
        if ch == "\n":
            # check if it's NOT a double newline
            next_is_newline = (i + 1 < len(text) and text[i + 1] == "\n")
            # distance since last newline (or start)
            dist = i - last_nl_pos - 1  # subtract 1 for the newline itself
            if dist >= 10 and not next_is_newline:
                # replace with split token
                result.append("|")
                last_nl_pos = i
                continue
            else:
                # keep the newline as-is
                result.append("\n")
                last_nl_pos = i
        else:
            result.append(ch)
    return "".join(result)

def index_resume(text: str):
    text = mark_guarded_newlines_manual(text)

    text = text.replace("\u2022", "- ").replace("•", "- ").replace("·", "- ").replace("●", "-")
    text = re.sub(r"[ \t]+", " ", text)                # collapse spaces
    text = re.sub(r"\s*\n\s*", "\n", text)             # trim around newlines
    text = re.sub(r"-\s*\n\s*", "", text)
    text = text.strip()

    if not re.search(r"[.!?\n]", text):
        # Split by semicolons or every ~25–35 words
        words = text.split()
        step = 30
        return [" ".join(words[i:i+step]) for i in range(0, len(words), step)]

    _CHUNK_PAT = re.compile(
        r"""
        # Split after ., !, ? followed by space+Capital or line end
        (?<=[.!?])\s+(?=[A-Z(]) |
        # Or split on bullet-like starts
        \n(?=[\-\*\u2022]) |
        # Or strong newlines
        \n{2,} |
        # Or split on pipe characters surrounded by optional spaces
        \s*\|\s*
        """,
        re.VERBOSE
    )

    parts = re.split(_CHUNK_PAT, text)

    chunks = []

    for p in parts:
        p = p.strip()
        if not p:
            continue
        subs = re.split(r"\s*[;•]\s+", p)
        chunks.extend([s.strip() for s in subs if s.strip()])

    overlapping_chunks = []
    for i in range(len(chunks)):
        prev_chunk = chunks[i - 1] if i > 0 else ""
        curr_chunk = chunks[i]
        next_chunk = chunks[i + 1] if i < len(chunks) - 1 else ""
        combined = " ".join(filter(None, [prev_chunk, curr_chunk, next_chunk]))
        overlapping_chunks.append(combined)

    resp = app.state.embedder.embeddings.create(
        model=EMBEDDER_ID.lower(),
        input=overlapping_chunks
    )

    # 3) turn Embedding objects into a float32 array
    vecs = np.array([item.embedding for item in resp.data], dtype="float32")  # shape (N, D)
    dim = vecs.shape[1]

    faiss.normalize_L2(vecs)
    index = faiss.IndexFlatL2(dim)

    index.add(vecs)
    return index, overlapping_chunks

def retrieve(index, chunks, query, k=6):
    vecs = []
    batch_index = 0
    while batch_index < len(query):
        batch = query[batch_index:min(batch_index + 1000, len(query) - batch_index)]
        vecs.extend(app.state.embedder.embeddings.create(
            model=EMBEDDER_ID.lower(),
            input=batch
        ).data)
        batch_index += 1000

    q = np.array([vecs[0].embedding], dtype="float32")  # shape (1, D)

    faiss.normalize_L2(q)

    k = min(k, index.ntotal)
    scores, ids = index.search(q, k)

    return [(chunks[i], float(scores[0][j])) for j, i in enumerate(ids[0])]

def make_prompt(title, company, location, description, job_details_retrieved, applicant_details_retrieved):
    evidence = "\n\n".join([f"[Snippet {i+1}] {t}" for i,(t,_) in enumerate(job_details_retrieved)])
    applicant_snippets = "\n\n".join([f"[Applicant Snippets {i+1}] {t}" for i,(t,_) in enumerate(applicant_details_retrieved)])
    prompt = f"""
You write tailored cover letters. Use ONLY the provided snippets as factual evidence.
Do not invent employers, dates, titles, or skills not present in snippets. 
Do not reference snippets, but use the content directly.

Job title: 
{title}

Job company:
{company}

Job location:
{location}

Job description:
{description}

Evidence snippets:
{evidence}

Applicant details snippets:
{applicant_snippets}

Date of application: 
{date.today().isoformat()}

Write a one-page cover letter:
- Professional letterhead with sender's name, contact details, and location, the date and the inside address, name, attention line and location
- 2 short paragraphs + 3 bullet points
- Reference the company's needs explicitly
- Only include facts supported by snippets (cite them)
- Finish with a friendly call to action with the applicant's name
"""
    return prompt

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

    print(f"INFO:\t\tGot resume content...")

    job_details = get_job_listing_details(job_listing_url)

    print(f"INFO:\t\tGot job listing details: {job_details}")

    print(f"INFO:\t\tGenerating cover letter...")

    index, chunks = index_resume(resume_content)

    job_details_retrieved = retrieve(index, chunks, job_details['description'], k=8)
    applicant_name_retrieved = retrieve(index, chunks, "name", k=3)
    applicant_cont_retrieved = retrieve(index, chunks, "contact details", k=3)
    applicant_loca_retrieved = retrieve(index, chunks, "location", k=3)

    prompt = make_prompt(
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
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    response = requests.post(GEMINI_API_URL, headers=headers, json=payload)

    return {
        "status": response.status_code,
        "json": response.json()
    }

@app.post("/extract-text")
def extract_text(resume: bytes = File(..., description="PDF file to extract text from")):
    # size check (require pdf to be less than 25MB)
    if len(resume) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    # quick PDF signature check
    if not resume.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Not a valid PDF")

    text = get_pdf_content(resume)

    index, refined = index_resume(text)
    
    return refined

@app.get("/complete")
def complete(
    prompt: str = Query(..., description="User's prompt"),
    system: str | None = Query(None, description="Optional system prompt"),
    temperature: float = Query(0.7, description="Sampling temperature"),
    max_tokens: int = Query(512, description="Maximum tokens to generate"),
):
    completion = app.state.llm.chat.completions.create(
        model=LLM_ID.lower(), 
        messages=[
            {"role": "system", "content": system or "You are a helpful assistant"},
            {"role": "user", "content": prompt},
        ]
    )

    return completion.choices[0].message.content

import re
import faiss, numpy as np
from bs4 import BeautifulSoup
from io import BytesIO
from pypdf import PdfReader
import json
import requests
import openai
import os

EMBEDDER_ID = os.getenv("EMBEDDER_ID")

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

    with open("pyapp/job-listing-selectors.json", "r") as f:
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

def index_resume(app, text: str):
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

def retrieve(app, index, chunks, query, k=6):
    vecs = []
    batch_index = 0
    while batch_index < len(query):
        batch = query[batch_index:min(batch_index + 1050, len(query) - batch_index)]
        vecs.extend(app.state.embedder.embeddings.create(
            model=EMBEDDER_ID.lower(),
            input=batch
        ).data)
        batch_index += 950

    q = np.array([vecs[0].embedding], dtype="float32")  # shape (1, D)

    faiss.normalize_L2(q)

    k = min(k, index.ntotal)
    scores, ids = index.search(q, k)

    return [(chunks[i], float(scores[0][j])) for j, i in enumerate(ids[0])]
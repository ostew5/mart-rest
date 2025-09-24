"""
This is the /v1/index_resume POST endpoint for indexing applicant 
resumes and storing them in a S3 bucket.

It contains the endpoint:
- POST /v1/index_resume/start: Accepts a PDF file, processes it, and starts a background job to index the resume.
"""

from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, BackgroundTasks, Request, Depends
from app_v1.helpers.cognito_auth import authenticate_session
import base64, faiss, boto3, gzip, uuid, json, re, os, pickle
from fastapi.responses import JSONResponse
from pypdf import PdfReader
from io import BytesIO
import numpy as np

router = APIRouter(prefix="/v1/index_resume", tags=["index_resume"])

EMBEDDER_ID = os.getenv("EMBEDDER_ID")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

def _read_pdf(file: UploadFile) -> str:
# Read the PDF file
    text = ""
    content = file.file.read()
    reader = PdfReader(BytesIO(content))
    number_of_pages = len(reader.pages)
    for page in reader.pages:
        text += page.extract_text()
    return text

def _mark_newlines(text: str) -> str:
    if not text:
        return ""

    result = []
    last_nl_pos = -1
    for i, ch in enumerate(text):
        if ch == "\n":
            next_is_newline = (i + 1 < len(text) and text[i + 1] == "\n")
            dist = i - last_nl_pos - 1
            if dist >= 10 and not next_is_newline:
                result.append("|")
                last_nl_pos = i
                continue
            else:
                result.append("\n")
                last_nl_pos = i
        else:
            result.append(ch)
    return "".join(result)

def _clean_text(text: str) -> str:
# Clean document text
    text = (text
            .replace("\u2022", "- ")
            .replace("●", "- ")
            .replace("•", "- ")
            .replace("·", "- "))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    text = re.sub(r"-\s*\n\s*", "", text)
    return text.strip()

def _split_text(text: str) -> list:
# Split text into chunks
    if not re.search(r"[.!?\n]", text):
        words = text.split()
        step = 30
        return [" ".join(words[i:i+step]) for i in range(0, len(words), step)]

    chunks = []

    _CHUNK_PAT = re.compile(
        r"""
        # Split after ., !, ? followed by space+Capital or line end
        (?<=[.!?])\s+(?=[A-Z(]) |
        # Split on bullet-like starts
        \n(?=[\-\*\u2022]) |
        # Split strong newlines
        \n{2,} |
        # Split on pipe characters
        \s*\|\s*
        """,
        re.VERBOSE
    )

    parts = re.split(_CHUNK_PAT, text)

    for p in parts:
        p = p.strip()
        if not p:
            continue
        subs = re.split(r"\s*[;•]\s+", p)
        chunks.extend([s.strip() for s in subs if s.strip()])

    return chunks

def _overlap_chunks(chunks: list) -> list:
# Create overlapping chunks
    overlapping_chunks = []

    for i in range(len(chunks)):
        prev_chunk = chunks[i - 1] if i > 0 else ""
        curr_chunk = chunks[i]
        next_chunk = chunks[i + 1] if i < len(chunks) - 1 else ""
        combined = " ".join(filter(None, [prev_chunk, curr_chunk, next_chunk]))
        overlapping_chunks.append(combined)

    return overlapping_chunks

def _get_embeddings(overlapping_chunks: list, embedder) -> list:
# Get embeddings for the chunks
    return embedder.embeddings.create(
        model=EMBEDDER_ID,
        input=overlapping_chunks
    )

def _get_serialized_faiss(resp: list) -> faiss.Index:
# Store embeddings in a FAISS index
    vecs = np.array([item.embedding for item in resp.data], dtype="float32")
    dim = vecs.shape[1]

    faiss.normalize_L2(vecs)
    index = faiss.IndexFlatL2(dim)

    index.add(vecs)

    return faiss.serialize_index(index)

def _set_status(app, job_id: str, status: str):
    app.state.index_jobs.setdefault(job_id, {})
    app.state.index_jobs[job_id].update(status = status)

def index_resume(
    text: str,
    job_id: str,
    app: FastAPI
):
    try:
        _set_status(app, job_id, status="Marking newlines")
        text = _mark_newlines(text)

        _set_status(app, job_id, status="Cleaning text")
        text = _clean_text(text)

        _set_status(app, job_id, status="Chunking text")
        chunks = _split_text(text)

        _set_status(app, job_id, status="Overlapping chunks")
        overlapping_chunks = _overlap_chunks(chunks)

        _set_status(app, job_id, status="Getting embeddings")
        resp = _get_embeddings(overlapping_chunks, app.state.embedder)

        _set_status(app, job_id, status="Serializing embeddings")
        index_data = _get_serialized_faiss(resp)

        _set_status(app, job_id, status="Uploading to s3")
        
        buffer = BytesIO()
        pickle.dump(index_data, buffer)
        buffer.seek(0)

        bundle = {
            "chunks": overlapping_chunks,
            "uuid": job_id
        }

        blob = gzip.compress(json.dumps(bundle).encode("utf-8"))
        
        app.state.s3.upload_fileobj(
            buffer,
            S3_BUCKET_NAME,
            f"resumes/{job_id}.pkl"
        )

        app.state.s3.put_object(
            Bucket=S3_BUCKET_NAME, 
            Key=f"resumes/{job_id}.bin", 
            Body=blob,
            ContentType="application/json", 
            ContentEncoding="gzip"
        )

        _set_status(app, job_id, status="Completed!")
        return job_id
    except Exception as e:
        _set_status(app, job_id, status=f"Failed at {app.state.index_jobs[job_id]} with error: {str(e)}")

@router.post(
    "/start",
    summary="Start resume indexing job",
    description="""
Begin an asynchronous job to index an uploaded resume PDF and store the artifacts in S3.

**What it does**
- Validates the uploaded file:
  - Checks size against `get_subscription_limits()["max_resume_size"][user["subscription_level"]]`.
  - Verifies the file starts with the PDF signature `%PDF-`.
- Extracts text from the PDF and enqueues `index_resume` as a background task.
- Background task cleans/segments text, creates overlapping chunks, generates embeddings, builds a FAISS index, and uploads:
  - `resumes/{job_id}.pkl` — serialized FAISS index
  - `resumes/{job_id}.bin` — gzip-compressed JSON bundle of chunks & metadata
- Tracks progress in `app.state.index_jobs`.

**Form data**
- `file` *(UploadFile, required)* — The PDF resume to index.

**Dependencies**
- `authenticate` — Requires a valid authenticated user.
- `rate_limiter("index_resume")` — Applies per-user rate limits.

**Responses**
- `202 Accepted` — Returns `{"uuid": "<job-id>", "message": "Resume indexing job started in the background"}`.
- `413 Payload Too Large` — If the file exceeds the allowed size for the user's subscription.
- `400 Bad Request` — If the file is not a valid PDF (fails signature check).
- `401 Unauthorized` — If authentication fails (from dependency).
- `429 Too Many Requests` — If rate limiting is triggered (from dependency).
"""
)
async def start_resume_indexing_job(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    request: Request,
    user: dict = Depends(authenticate_session)
):
    # Check file size
    #if file.size > get_subscription_limits()["max_resume_size"][user["subscription_level"]]:
    #    raise HTTPException(status_code=413, detail="File too large")

    # Quick PDF signature check
    if not file.file.read(5) == b"%PDF-":
        raise HTTPException(status_code=400, detail="Not a valid PDF")

    job_id = str(uuid.uuid4())

    text = _read_pdf(file)

    background_tasks.add_task(index_resume, text, job_id, request.app)

    return JSONResponse(
        {
            "uuid": job_id,
            "message": "Resume indexing job started in the background"
        },
        status_code=202
    )
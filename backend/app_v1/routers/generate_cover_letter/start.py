"""
This is the /v1/generate_cover_letter endpoint route 
for generating a cover letter based on a job listing and a resume.

It contains the endpoint:
- POST /v1/generate_cover_letter/start: Accepts a job listing URL and the indexed resume name
and starts a background job to generate a cover letter.
"""

from fastapi import FastAPI, APIRouter, HTTPException, Query, BackgroundTasks, Request, Depends
import requests, base64, boto3, faiss, gzip, json, uuid, pickle, os, re, logging
from jinja2 import Environment, FileSystemLoader, select_autoescape
from fastapi.responses import StreamingResponse, JSONResponse
from bs4 import BeautifulSoup
from weasyprint import HTML
from datetime import date
from io import BytesIO
import numpy as np

from app_v1.helpers.rate_limits import authenticateSessionAndRateLimit
from app_v1.helpers.ai_jobs import createJob, getJob, updateJobStatus, completeJob

env = Environment(
    loader=FileSystemLoader("resources"),
    autoescape=select_autoescape(["html", "xml"])
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/generate_cover_letter", tags=["generate_cover_letter"])

EMBEDDER_ID = os.getenv("EMBEDDER_ID")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
GEMINI_API_URL = os.getenv("GEMINI_API_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def _deserialize_faiss(index):
    ready = pickle.load(index)
    return faiss.deserialize_index(ready)

def _load_selectors():
    with open("resources/job-listing-selectors.json", "r") as f:
        selectors = json.load(f)
        if selectors:
            return selectors
    raise Exception("Failed to load job listing selectors")

def _extract_job_listing_details(job_listing_text: str, selectors: dict):
    soup = BeautifulSoup(job_listing_text, "html.parser")
    
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

def _retrieve(app: FastAPI, index, chunks: list, query: str, k: int = 6):
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

def _make_prompt(
    title: str, 
    company: str, 
    location: str, 
    description: str, 
    job_details_retrieved: str, 
    applicant_details_retrieved: str
    ):
    evidence = "\n\n".join([f"[Snippet {i+1}] {t}" for i,(t,_) in enumerate(job_details_retrieved)])
    applicant_snippets = "\n\n".join([f"[Applicant Snippets {i+1}] {t}" for i,(t,_) in enumerate(applicant_details_retrieved)])
    system = f"""
You write tailored cover letters. Use ONLY the provided snippets as factual evidence.
Do not invent employers, dates, titles, or skills not present in snippets. 
Do not reference snippets, but use the content directly.    
"""
    prompt = f"""
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
{date.today().strftime("%B %-d, %Y")}

Write a one-page cover letter containing all of the followingL:
- letterhead
<Applicant name>
<Applicant contact number>
<Applicant email address>
<Applicant location>
- date
<Date of application>
- inside address
<Hiring manager's name or "Hiring Manager"> 
<Job company>
<Job location>
- salutation
Dear <Hiring manager's name or "Hiring Manager"> 
- reference line
Re: <Job title> position 
- letter body
<2 paragraphs explaining why the applicant is a good fit for the role and the company's needs explicitly>
<3 bullet points referencing snippets that support the applicant's suitability in STAR format (do not list as Situation, Task, Action, Result just write each STAR as a bullet point)>
- closing
Thank you for considering my application. I look forward to the opportunity to discuss how I can contribute to <Company> further.
- signature
Sincerely yours,
<Applicant name>
"""
    return system, prompt

def _get_gemini_response(system: str, prompt: str):
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }
  
    fields = {
        "letterhead": { "type": "STRING" },
        "date": { "type": "STRING" },
        "inside_address": { "type": "STRING" },
        "salutation": { "type": "STRING" },
        "reference": { "type": "STRING" },
        "letterbody": { "type": "STRING" },
        "closing": { "type": "STRING" },
        "signature": { "type": "STRING" }
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
                    "properties": fields,
                    "propertyOrdering": list(fields.keys())
                }
            }
        }
    }
  
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()  # Raises an HTTPError for bad responses
    except requests.exceptions.HTTPError as http_err:
        logger.info(f"HTTP error occurred: {http_err}")
        raise Exception(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_err:
        logger.info(f"Request error occurred: {req_err}")
        raise Exception(f"Request error occurred: {req_err}")

    try:
        response_data = json.loads(response.text)
    except json.JSONDecodeError as json_err:
        logger.info(f"JSON decode error: {json_err}")
        raise Exception(f"JSON decode error: {json_err}")

    candidates = response_data.get("candidates", [])
    if not candidates:
        logger.info("No candidates found in the response.")
        raise ValueError("No candidates found in the response.")

    content_parts = candidates[0].get("content", {}).get("parts", [])
    if not content_parts:
        logger.info("No content parts found in the response.")
        raise ValueError("No content parts found in the response.")

    text = content_parts[0].get("text", "")
    logger.info(f"Received response: {text}")
  
    # Remove code block markers if present
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
  
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as json_err:
        logger.info(f"JSON decode error in extracted text: {json_err}")
        raise ValueError("JSON decode error in extracted text")

    obj = payload[0] if isinstance(payload, list) else payload
  
    # Create a dictionary with default empty strings for each field
    result = {k: obj.get(k, "") for k in fields.keys()}
  
    return result

def _generate_pdf(cover_letter_context):
    html_template = env.get_template("letter.html")
    html = html_template.render(**cover_letter_context)
    pdf_io = BytesIO()
    HTML(string=html, base_url=".").write_pdf(pdf_io)
    pdf_io.seek(0)
    return pdf_io

def _upload_to_s3(s3, pdf_bytes, job_id):
    s3.put_object(
        Bucket=S3_BUCKET_NAME, 
        Key=f"cover_letters/{job_id}.pdf", 
        Body=pdf_bytes,
        ContentType="application/pdf"
    )

def __bullets_to_html(text: str) -> str:
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
env.filters["bullets"] = __bullets_to_html

def generate_cover_letter(
    bundle: dict,
    job_listing_text: str,
    job_id: str,
    user_id: str,
    app: FastAPI
):
    try:
        createJob(app, job_id, user_id, "GenerateCoverletter", "Starting")
        index = bundle["index"]
        chunks = bundle["chunks"]
        
        updateJobStatus(app, job_id, "Unpickling indexed resume")
        index = _deserialize_faiss(index)

        updateJobStatus(app, job_id, "Loading html selectors")
        selectors = _load_selectors()

        updateJobStatus(app, job_id, "Extracting job listing details")
        job_listing_details = _extract_job_listing_details(job_listing_text, selectors)

        updateJobStatus(app, job_id, "Retrieving relevant resume data")
        retrieved = {
            "job_description": _retrieve(app, index, chunks, job_listing_details['description'], k=8),
            "name": _retrieve(app, index, chunks, "name", k=3),
            "contact_details": _retrieve(app, index, chunks, "contact details", k=3),
            "location": _retrieve(app, index, chunks, "location", k=3)
        }

        updateJobStatus(app, job_id, "Constructing Gemini prompt")
        system, prompt = _make_prompt(
            job_listing_details['title'],
            job_listing_details['company'],
            job_listing_details['location'],
            job_listing_details['description'],
            retrieved['job_description'],
            retrieved['name'] + retrieved['contact_details'] + retrieved['location']
        )

        updateJobStatus(app, job_id, "Asking Gemini to write a cover letter")
        cover_letter_content = _get_gemini_response(system, prompt)

        updateJobStatus(app, job_id, "Generating a pdf with Gemini's response")
        pdf_bytes = _generate_pdf(cover_letter_content)

        updateJobStatus(app, job_id, "Uploading pdf to S3")
        _upload_to_s3(app.state.s3, pdf_bytes, job_id)

        completeJob(app, job_id)
        return job_id
    except Exception as e:
        job = getJob(app, job_id, user_id)
        updateJobStatus(app, job_id, f"Job threw an Exception: {e} at {job['Status']}")

@router.put(
    "/start",
    summary="Start cover-letter generation job",
    description="""
Begin an asynchronous job to generate a tailored cover letter from a LinkedIn job listing and an indexed resume.

**What it does**
- Validates the `job_listing_url` is reachable (`200 OK`) and fetches the HTML.
- Downloads the FAISS index (`.pkl`) and resume bundle (`.bin`) from S3 for `file_id`, then decompresses/deserializes them.
- Creates a new `job_id`, enqueues `generate_cover_letter` as a background task, and records status in `app.state.cover_letter_jobs`.
- Background task extracts job details, retrieves relevant resume snippets, calls Gemini to create content, renders a PDF, and uploads it to S3.

**Query parameters**
- `job_listing_url` *(str, required)* — URL of the LinkedIn job listing.
- `file_id` *(str, required)* — UUID of the previously indexed resume.

**Dependencies**
- `authenticate` — Requires a valid authenticated user.
- `rate_limiter("cover_letter")` — Applies per-user rate limits.

**Responses**
- `202 Accepted` — Returns `{"uuid": "<job-id>", "message": "Resume indexing job started in the background"}`.
- `404 Not Found` — If the job listing URL is unreachable/non-200, or the indexed resume artifacts (`.pkl`/`.bin`) are missing/invalid.
- `401 Unauthorized` — If authentication fails (from dependency).
- `429 Too Many Requests` — If rate limiting is triggered (from dependency).
"""
)
async def start_generate_cover_letter_job(
    background_tasks: BackgroundTasks,
    request: Request,
    job_listing_url: str = Query(..., description="URL of the LinkedIn job listing"),
    file_id: str = Query(..., description="Indexed resume uuid"),
    user_data: dict = Depends(authenticateSessionAndRateLimit)
):
    job_listing_url = job_listing_url.strip()
    file_id = file_id.strip()

    job_listing = requests.get(job_listing_url, timeout = 5)

    if job_listing.status_code != 200:
        raise HTTPException(status_code=404, detail="Job listing not found")

    try:
        index_data = BytesIO()
        boto_resp = request.app.state.s3.download_fileobj(
            S3_BUCKET_NAME, 
            f"resumes/{file_id}.pkl",
            index_data
        )

        index_data.seek(0)

        boto_resp = request.app.state.s3.get_object(
            Bucket=S3_BUCKET_NAME, 
            Key=f"resumes/{file_id}.bin"
        )

        blob = boto_resp["Body"].read()

        decompressed = gzip.decompress(blob)

        bundle = json.loads(decompressed.decode("utf-8"))

        bundle["index"] = index_data

        if bundle["uuid"] != file_id:
            raise HTTPException(status_code=400, detail="File ID does not match the indexed resume")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Indexed resume with id: {file_id} not found: {str(e)}")

    job_id = str(uuid.uuid4())

    for attr in user_data['UserAttributes']:
        if attr['Name'] == "sub":
            background_tasks.add_task(generate_cover_letter, bundle, job_listing.text, job_id, attr['Value'], request.app)
            return JSONResponse(
                {
                    "uuid": job_id,
                    "message": "Generate cover letter job started in the background"
                },
                status_code=202
            )
    raise HTTPException(status_code=401, detail=f"No User Attribute: sub")
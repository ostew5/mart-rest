"""
This is the /generate_cover_letter endpoint route 
for generating a cover letter based on a job listing and a resume.

It contains the endpoint:
- POST /generate_cover_letter/start: Accepts a job listing URL and the indexed resume name
and starts a background job to generate a cover letter.
- GET /generate_cover_letter/status/{job_id}: Returns the status of the cover letter generation.
- GET /generate_cover_letter/result/{job_id}: Returns the generated cover letter.
"""

from fastapi import FastAPI, APIRouter, HTTPException, Query, BackgroundTasks, Request, Depends
from pyapp.helpers.user_authentication import authenticate, rate_limiter
import requests, base64, boto3, faiss, gzip, json, uuid, pickle, os, re
from jinja2 import Environment, FileSystemLoader, select_autoescape
from fastapi.responses import StreamingResponse
from bs4 import BeautifulSoup
from weasyprint import HTML
from datetime import date
from io import BytesIO
import numpy as np

env = Environment(
    loader=FileSystemLoader("pyapp/templates"),
    autoescape=select_autoescape(["html", "xml"])
)

router = APIRouter(prefix="/generate_cover_letter", tags=["generate_cover_letter"])

EMBEDDER_ID = os.getenv("EMBEDDER_ID")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
GEMINI_API_URL = os.getenv("GEMINI_API_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def _deserialize_faiss(index):
    ready = pickle.load(index)
    return faiss.deserialize_index(ready)

def _load_selectors():
    with open("pyapp/job-listing-selectors.json", "r") as f:
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

def _get_gemini_response(system, prompt):
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

    response = requests.post(GEMINI_API_URL, headers=headers, json=payload)

    text = json.loads(response.text).get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

    print(f"INFO:\t\tReceived response: {text}")

    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())

    payload = json.loads(text)
    obj = payload[0] if isinstance(payload, list) else payload

    return {k: obj.get(k, "") for k in fields.keys()}

def _generate_pdf(cover_letter_context):
    html_template = env.get_template("letter.html")
    html = html_template.render(**cover_letter_context)
    pdf_io = BytesIO()
    HTML(string=html, base_url=".").write_pdf(pdf_io)
    pdf_io.seek(0)
    return pdf_io

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

def _set_status(app, job_id: str, status: str):
    app.state.cover_letter_jobs.setdefault(job_id, {})
    app.state.cover_letter_jobs[job_id].update(status = status)

def generate_cover_letter(
    bundle: dict,
    job_listing_text: str,
    job_id: str,
    app: FastAPI,
    tick_rate_limiter
):
    try:
        index = bundle["index"]
        chunks = bundle["chunks"]

        _set_status(app, job_id, status="Deserializing index")
        index = _deserialize_faiss(index)

        _set_status(app, job_id, status="Loading html selectors")
        selectors = _load_selectors()

        _set_status(app, job_id, status="Extracting job listing details")
        job_listing_details = _extract_job_listing_details(job_listing_text, selectors)

        _set_status(app, job_id, status="Retrieving relevant details from resume for job description")
        retrieved = {}
        retrieved["job_description"] = _retrieve(app, index, chunks, job_listing_details['description'], k=8)

        _set_status(app, job_id, status="Retrieving applicant name from resume")
        retrieved["name"] = _retrieve(app, index, chunks, "name", k=3)

        _set_status(app, job_id, status="Retrieving applicant contact details from resume")
        retrieved["contact_details"] = _retrieve(app, index, chunks, "contact details", k=3)

        _set_status(app, job_id, status="Retrieving applicant location from resume")
        retrieved["location"] = _retrieve(app, index, chunks, "location", k=3)

        _set_status(app, job_id, status="Creating prompt for cover letter generation")
        system, prompt = _make_prompt(
            job_listing_details['title'],
            job_listing_details['company'],
            job_listing_details['location'],
            job_listing_details['description'],
            retrieved['job_description'],
            retrieved['name'] + retrieved['contact_details'] + retrieved['location']
        )

        _set_status(app, job_id, status="Generating cover letter content with gemini")
        cover_letter_content = _get_gemini_response(system, prompt)

        _set_status(app, job_id, status="Creating pdf document")
        pdf_bytes = _generate_pdf(cover_letter_content)

        _set_status(app, job_id, status="Uploading to s3")
        app.state.s3.put_object(
            Bucket=S3_BUCKET_NAME, 
            Key=f"cover_letters/{job_id}.pdf", 
            Body=pdf_bytes,
            ContentType="application/pdf"
        )

        _set_status(app, job_id, status="Completed!")
        tick_rate_limiter(True)
        return job_id
    except Exception as e:
        _set_status(app, job_id, status=f"Failed at {app.state.cover_letter_jobs[job_id]} with error: {str(e)}")
        tick_rate_limiter(False)

@router.put("/start")
async def start_generate_cover_letter_job(
    background_tasks: BackgroundTasks,
    request: Request,
    job_listing_url: str = Query(..., description="URL of the LinkedIn job listing"),
    file_id: str = Query(..., description="Indexed resume uuid"),
    user: dict = Depends(authenticate),
    tick_rate_limiter = Depends(rate_limiter("cover_letter"))
):
    job_listing_url = job_listing_url.strip()
    file_id = file_id.strip()

    job_listing = requests.get(job_listing_url, timeout = 5)

    if job_listing.status_code != 200:
        tick_rate_limiter(False)
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

        job_id = str(uuid.uuid4())

        background_tasks.add_task(generate_cover_letter, bundle, job_listing.text, job_id, request.app, tick_rate_limiter)
    except Exception as e:
        tick_rate_limiter(False)
        raise HTTPException(status_code=404, detail=f"Indexed resume with id: {file_id} not found: {str(e)}")

    return {
        "uuid": job_id,
        "message": "Generate cover letter job started in the background"
    }

@router.get("/status/{job_id}")
def get_cover_letter_job_status(job_id: str, request: Request):
    if not hasattr(request.app.state, "cover_letter_jobs"):
        raise HTTPException(status_code=404, detail="No jobs found")

    job = request.app.state.cover_letter_jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"uuid": job_id, **job}

@router.get("/result/{job_id}")
def get_generated_cover_letter(job_id: str, request: Request):    
    pdf_io = BytesIO()

    try:
        boto_resp = request.app.state.s3.download_fileobj(
            S3_BUCKET_NAME, 
            f"cover_letters/{job_id}.pdf",
            pdf_io
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Cover letter PDF not found: {str(e)}")

    pdf_io.seek(0)

    return StreamingResponse(
        pdf_io,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{job_id}-Cover_Letter.pdf"'}
    )

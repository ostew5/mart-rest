"""
This is the /v1/index_resume POST endpoint for indexing applicant 
resumes and storing them in a S3 bucket.

It contains the endpoint:
- GET /v1/index_resume/status/{job_id}: Returns the status of the indexing job.
"""

from fastapi import HTTPException, Request, APIRouter

router = APIRouter(prefix="/v1/index_resume", tags=["index_resume"])

@router.get(
    "/status/{job_id}",
    summary="Check resume indexing job status",
    description="""
Retrieve the current status of a resume indexing job.

**What it does**
- Looks up the job in `app.state.index_jobs` using the provided `job_id`.
- Returns the job's UUID along with its current status metadata.

**Path parameters**
- `job_id` *(str, required)* — The UUID of the resume indexing job.

**Responses**
- `200 OK` — Returns `{"uuid": "<job-id>", "status": "<current-status>", ...}`.
- `404 Not Found` — If no jobs exist or if the requested `job_id` is not found.
"""
)
def get_resume_indexing_job_status(
    job_id: str, 
    request: Request
):
    app = request.app
    if not hasattr(app.state, "index_jobs"):
        raise HTTPException(status_code=404, detail="No jobs found")
    job = app.state.index_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"uuid": job_id, **job}
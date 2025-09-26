"""
This is the /v1/index_resume POST endpoint for indexing applicant 
resumes and storing them in a S3 bucket.

It contains the endpoint:
- GET /v1/index_resume/status/{job_id}: Returns the status of the indexing job.
"""

from fastapi import HTTPException, Request, APIRouter, Depends
from app_v1.helpers.cognito_auth import authenticateSession
from app_v1.helpers.ai_jobs import getJob

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
    request: Request,
    user_data: dict = Depends(authenticateSession)  
):
    for attr in user_data['UserAttributes']:
        if attr['Name'] == "sub":
            return getJob(request.app, job_id, attr['Value'])
    raise HTTPException(status_code=401, detail=f"No User Attribute: sub")
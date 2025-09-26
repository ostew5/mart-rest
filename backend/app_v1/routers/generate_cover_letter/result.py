"""
This is the /v1/generate_cover_letter endpoint route 
for generating a cover letter based on a job listing and a resume.

It contains the endpoint:
- GET /v1/generate_cover_letter/result/{job_id}: Returns the generated cover letter.
"""

from fastapi import HTTPException, Request, APIRouter, Depends
from fastapi.responses import StreamingResponse
from io import BytesIO
import os, logging

from app_v1.helpers.cognito_auth import authenticateSession
from app_v1.helpers.ai_jobs import getJob

logger = logging.getLogger(__name__)

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

router = APIRouter(prefix="/v1/generate_cover_letter", tags=["generate_cover_letter"])

@router.get(
    "/result/{job_id}",
    summary="Retrieve generated cover letter PDF",
    description="""
Return the generated cover letter as a PDF file for a given job ID.

**What it does**
- Attempts to download the cover letter PDF from S3 storage using the `job_id`.
- Streams the file back to the client with a download header.
- Handles missing or incomplete jobs gracefully.

**Path parameters**
- `job_id` *(str, required)* — The UUID of the cover-letter generation job.

**Responses**
- `200 OK` — Returns the generated PDF file with `Content-Disposition` set for download.
- `404 Not Found` — If no cover letter PDF exists and no job metadata is found.
- `409 Conflict` — If the cover letter is not yet ready but a job record exists.
"""
)
def get_generated_cover_letter(
    job_id: str, 
    request: Request,
    user_data: dict = Depends(authenticateSession)
):    
    pdf_io = BytesIO()

    try:
        boto_resp = request.app.state.s3.download_fileobj(
            S3_BUCKET_NAME, 
            f"cover_letters/{job_id}.pdf",
            pdf_io
        )
    except Exception as e:
        logger.error(f"Error getting cover letter PDF: {e}")
        for attr in user_data['UserAttributes']:
            if attr['Name'] == "sub":
                job = getJob(request.app, job_id, attr['Value'])
                raise HTTPException(status_code=409, detail=f"Not ready: {str(job)}")
        raise HTTPException(status_code=404, detail=f"Cover letter PDF not found: {str(e)}")

    pdf_io.seek(0)

    return StreamingResponse(
        pdf_io,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{job_id}-Cover_Letter.pdf"'}
    )

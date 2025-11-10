from fastapi import APIRouter, Request
from datetime import datetime
from pathlib import Path

router = APIRouter()


@router.post("/log", status_code=204)
async def log_request_body(request: Request):
    """
    Accept POST request, log body to file, return 204 No Content
    """
    # Get request body
    body = await request.body()

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_file = log_dir / f"request_{timestamp}.log"

    # Write body to file
    with open(log_file, "wb") as f:
        f.write(body)

    return None

"""Routes."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

import eventum

router = APIRouter()


WWW_DIR = Path(eventum.__file__).parent / 'www'


@router.get('/{resource:path}')
async def handle_spa_route(resource: str) -> FileResponse:
    """Handle all routes processed by SPA app."""
    if resource.startswith('api/'):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Existing files (like /logo.svg) should not return index.html
    file_path = (WWW_DIR / resource).resolve()
    if (
        file_path.is_relative_to(WWW_DIR)
        and file_path.exists()
        and file_path.is_file()
    ):
        return FileResponse(file_path)

    return FileResponse(WWW_DIR / 'index.html')

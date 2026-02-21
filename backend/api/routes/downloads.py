"""Download routes."""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.base import get_db
from backend.db.models import Download, Generation, GenerationStatus, User
from backend.api.dependencies import get_current_user, require_pro

router = APIRouter()

# Download directory
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))
DOWNLOAD_DIR.mkdir(exist_ok=True)


class DownloadRequest(BaseModel):
    """Request to create a download."""
    generation_id: str
    format: Literal["pptx", "pdf", "png", "svg"] = "pptx"
    variation_index: int | None = None


class DownloadResponse(BaseModel):
    """Download response."""
    id: str
    format: str
    status: str
    download_url: str | None = None
    expires_at: str | None = None


@router.post("", response_model=DownloadResponse)
async def create_download(
    request: DownloadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a download for a generation.

    PPTX is available for all users.
    PDF, PNG, SVG require Pro plan.
    """
    # Check format permissions
    if request.format in ["pdf", "png", "svg"] and not current_user.is_pro:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{request.format.upper()} export requires Pro plan",
        )

    # Get generation
    generation = db.query(Generation).filter(
        Generation.id == request.generation_id,
        Generation.user_id == current_user.id,
    ).first()

    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found",
        )

    if generation.status != GenerationStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Generation not completed",
        )

    # Check if download already exists
    existing = db.query(Download).filter(
        Download.generation_id == generation.id,
        Download.format == request.format,
        Download.variation_index == request.variation_index,
    ).first()

    if existing and existing.expires_at and existing.expires_at > datetime.utcnow():
        return DownloadResponse(
            id=existing.id,
            format=existing.format,
            status="ready",
            download_url=f"/api/v1/downloads/{existing.id}/file",
            expires_at=existing.expires_at.isoformat(),
        )

    # Create download record
    download = Download(
        generation_id=generation.id,
        format=request.format,
        variation_index=request.variation_index,
        file_path="",  # Will be set by background task
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(download)
    db.commit()
    db.refresh(download)

    # Queue file generation
    background_tasks.add_task(
        generate_download_file,
        download_id=download.id,
        generation_id=generation.id,
        format=request.format,
        variation_index=request.variation_index,
    )

    return DownloadResponse(
        id=download.id,
        format=download.format,
        status="processing",
    )


@router.get("/{download_id}", response_model=DownloadResponse)
async def get_download_status(
    download_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get download status."""
    download = db.query(Download).join(Generation).filter(
        Download.id == download_id,
        Generation.user_id == current_user.id,
    ).first()

    if not download:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Download not found",
        )

    if download.file_path and Path(download.file_path).exists():
        return DownloadResponse(
            id=download.id,
            format=download.format,
            status="ready",
            download_url=f"/api/v1/downloads/{download.id}/file",
            expires_at=download.expires_at.isoformat() if download.expires_at else None,
        )
    else:
        return DownloadResponse(
            id=download.id,
            format=download.format,
            status="processing",
        )


@router.get("/{download_id}/file")
async def download_file(
    download_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the generated file."""
    download = db.query(Download).join(Generation).filter(
        Download.id == download_id,
        Generation.user_id == current_user.id,
    ).first()

    if not download:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Download not found",
        )

    if not download.file_path or not Path(download.file_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not ready or expired",
        )

    # Check expiration
    if download.expires_at and download.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Download link has expired",
        )

    # Get filename
    generation = download.generation
    safe_prompt = "".join(c for c in generation.prompt[:30] if c.isalnum() or c in " -_")
    filename = f"infographix_{safe_prompt}.{download.format}"

    # Content type mapping
    content_types = {
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "pdf": "application/pdf",
        "png": "image/png",
        "svg": "image/svg+xml",
    }

    return FileResponse(
        path=download.file_path,
        filename=filename,
        media_type=content_types.get(download.format, "application/octet-stream"),
    )


@router.delete("/{download_id}")
async def delete_download(
    download_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a download."""
    download = db.query(Download).join(Generation).filter(
        Download.id == download_id,
        Generation.user_id == current_user.id,
    ).first()

    if not download:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Download not found",
        )

    # Delete file
    if download.file_path and Path(download.file_path).exists():
        Path(download.file_path).unlink()

    db.delete(download)
    db.commit()

    return {"status": "deleted"}


# Background task functions
async def generate_download_file(
    download_id: str,
    generation_id: str,
    format: str,
    variation_index: int | None,
):
    """Generate download file in background."""
    from backend.db.base import SessionLocal

    db = SessionLocal()
    try:
        download = db.query(Download).filter(Download.id == download_id).first()
        generation = db.query(Generation).filter(Generation.id == generation_id).first()

        if not download or not generation:
            return

        # Get DSL to render
        if variation_index is not None and generation.variations:
            dsl = generation.variations[variation_index]
        else:
            dsl = generation.dsl

        # Generate file
        try:
            file_path = DOWNLOAD_DIR / f"{download_id}.{format}"

            if format == "pptx":
                from backend.renderer import render_to_pptx
                render_to_pptx(dsl, str(file_path))

            elif format == "svg":
                # SVG rendering
                svg_content = render_to_svg(dsl)
                file_path.write_text(svg_content)

            elif format == "png":
                # PNG rendering (would require additional libraries)
                raise NotImplementedError("PNG export not yet implemented")

            elif format == "pdf":
                # PDF rendering (would require additional libraries)
                raise NotImplementedError("PDF export not yet implemented")

            # Update download record
            download.file_path = str(file_path)
            download.file_size = file_path.stat().st_size
            db.commit()

        except Exception as e:
            # Log error but don't fail
            print(f"Error generating download: {e}")

    finally:
        db.close()


def render_to_svg(dsl: dict) -> str:
    """Render DSL to SVG string."""
    # Simple SVG rendering for now
    canvas = dsl.get("canvas", {"width": 960, "height": 540})
    shapes = dsl.get("shapes", [])

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{canvas.get("width", 960)}" '
        f'height="{canvas.get("height", 540)}" '
        f'viewBox="0 0 {canvas.get("width", 960)} {canvas.get("height", 540)}">'
    ]

    # Add background
    bg_color = canvas.get("background", "#FFFFFF")
    svg_parts.append(
        f'<rect width="100%" height="100%" fill="{bg_color}"/>'
    )

    # Render shapes
    for shape in shapes:
        bbox = shape.get("bbox", {})
        x = bbox.get("x", 0)
        y = bbox.get("y", 0)
        w = bbox.get("width", 100)
        h = bbox.get("height", 50)

        fill = shape.get("fill", {})
        fill_color = fill.get("color", "#0D9488") if isinstance(fill, dict) else "#0D9488"

        # Handle color tokens
        if fill_color.startswith("accent"):
            theme = dsl.get("theme", {})
            fill_color = theme.get(fill_color, "#0D9488")

        svg_parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="{fill_color}" rx="4"/>'
        )

        # Add text
        text = shape.get("text", {})
        if text:
            content = text.get("content", "")
            text_x = x + w / 2
            text_y = y + h / 2
            svg_parts.append(
                f'<text x="{text_x}" y="{text_y}" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'fill="white" font-family="Inter, sans-serif" font-size="14">'
                f'{content}</text>'
            )

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)

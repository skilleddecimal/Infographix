"""Task handlers for background processing."""

import os
from datetime import datetime
from pathlib import Path

from backend.db.base import SessionLocal
from backend.db.models import Generation, GenerationStatus, Download


async def process_generation_task(
    generation_id: str,
    prompt: str,
    content: list[dict] | None = None,
    brand_colors: list[str] | None = None,
    brand_fonts: list[str] | None = None,
    formality: str = "professional",
    num_variations: int = 1,
) -> dict:
    """Process a generation task.

    Args:
        generation_id: Generation record ID.
        prompt: User prompt.
        content: Optional content items.
        brand_colors: Optional brand colors.
        brand_fonts: Optional brand fonts.
        formality: Style formality.
        num_variations: Number of variations to generate.

    Returns:
        Task result with generation details.
    """
    from ml.inference import InferenceEngine

    db = SessionLocal()
    try:
        generation = db.query(Generation).filter(Generation.id == generation_id).first()
        if not generation:
            return {"error": "Generation not found"}

        start_time = datetime.utcnow()
        generation.status = GenerationStatus.PROCESSING
        db.commit()

        try:
            # Run inference
            engine = InferenceEngine(use_ml=False)

            result = engine.generate(
                prompt=prompt,
                content=content,
                brand_colors=brand_colors,
                brand_fonts=brand_fonts,
                formality=formality,
            )

            # Generate variations if requested
            variations = None
            if num_variations > 1:
                variation_results = engine.generate_variations(
                    prompt=prompt,
                    count=num_variations,
                    content=content,
                    brand_colors=brand_colors,
                    brand_fonts=brand_fonts,
                    formality=formality,
                )
                variations = [v.dsl for v in variation_results]

            # Update generation record
            end_time = datetime.utcnow()
            generation.archetype = result.archetype
            generation.archetype_confidence = result.classification_confidence
            generation.dsl = result.dsl
            generation.style = {
                "color_palette": result.style.color_palette,
                "font_family": result.style.font_family,
                "corner_radius": result.style.corner_radius,
                "shadow": result.style.shadow,
                "glow": result.style.glow,
            }
            generation.variations = variations
            generation.status = GenerationStatus.COMPLETED
            generation.completed_at = end_time
            generation.processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

            db.commit()

            return {
                "success": True,
                "archetype": result.archetype,
                "processing_time_ms": generation.processing_time_ms,
            }

        except Exception as e:
            generation.status = GenerationStatus.FAILED
            generation.error_message = str(e)
            db.commit()

            return {"error": str(e)}

    finally:
        db.close()


async def process_variations_task(
    generation_id: str,
    original_dsl: dict,
    archetype: str,
    count: int = 3,
    strategy: str = "diverse",
) -> dict:
    """Process a variations generation task.

    Args:
        generation_id: Generation record ID.
        original_dsl: Original DSL to create variations from.
        archetype: Diagram archetype.
        count: Number of variations.
        strategy: Variation strategy.

    Returns:
        Task result.
    """
    from backend.creativity import VariationEngine

    db = SessionLocal()
    try:
        generation = db.query(Generation).filter(Generation.id == generation_id).first()
        if not generation:
            return {"error": "Generation not found"}

        start_time = datetime.utcnow()
        generation.status = GenerationStatus.PROCESSING
        db.commit()

        try:
            # Generate variations
            engine = VariationEngine()
            original_dsl["archetype"] = archetype

            results = engine.generate_variations(
                dsl=original_dsl,
                count=count,
                strategy=strategy,
            )

            # Update generation
            end_time = datetime.utcnow()
            generation.dsl = original_dsl
            generation.variations = [r.dsl for r in results]
            generation.status = GenerationStatus.COMPLETED
            generation.completed_at = end_time
            generation.processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

            db.commit()

            return {
                "success": True,
                "variations_count": len(results),
            }

        except Exception as e:
            generation.status = GenerationStatus.FAILED
            generation.error_message = str(e)
            db.commit()

            return {"error": str(e)}

    finally:
        db.close()


async def generate_download_task(
    download_id: str,
    generation_id: str,
    format: str,
    variation_index: int | None = None,
) -> dict:
    """Generate a download file.

    Args:
        download_id: Download record ID.
        generation_id: Generation record ID.
        format: Output format (pptx, pdf, png, svg).
        variation_index: Optional variation index.

    Returns:
        Task result.
    """
    DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))
    DOWNLOAD_DIR.mkdir(exist_ok=True)

    db = SessionLocal()
    try:
        download = db.query(Download).filter(Download.id == download_id).first()
        generation = db.query(Generation).filter(Generation.id == generation_id).first()

        if not download or not generation:
            return {"error": "Download or generation not found"}

        # Get DSL to render
        if variation_index is not None and generation.variations:
            dsl = generation.variations[variation_index]
        else:
            dsl = generation.dsl

        try:
            file_path = DOWNLOAD_DIR / f"{download_id}.{format}"

            if format == "pptx":
                from backend.renderer import render_to_pptx
                render_to_pptx(dsl, str(file_path))

            elif format == "svg":
                svg_content = _render_to_svg(dsl)
                file_path.write_text(svg_content)

            elif format == "png":
                raise NotImplementedError("PNG export not yet implemented")

            elif format == "pdf":
                raise NotImplementedError("PDF export not yet implemented")

            # Update download record
            download.file_path = str(file_path)
            download.file_size = file_path.stat().st_size
            db.commit()

            return {
                "success": True,
                "file_path": str(file_path),
                "file_size": download.file_size,
            }

        except Exception as e:
            return {"error": str(e)}

    finally:
        db.close()


async def cleanup_expired_downloads_task() -> dict:
    """Clean up expired download files.

    Returns:
        Task result with cleanup stats.
    """
    db = SessionLocal()
    try:
        # Find expired downloads
        expired = db.query(Download).filter(
            Download.expires_at < datetime.utcnow(),
        ).all()

        deleted_count = 0
        for download in expired:
            # Delete file
            if download.file_path:
                path = Path(download.file_path)
                if path.exists():
                    path.unlink()
                    deleted_count += 1

            db.delete(download)

        db.commit()

        return {
            "success": True,
            "expired_count": len(expired),
            "deleted_files": deleted_count,
        }

    finally:
        db.close()


def _render_to_svg(dsl: dict) -> str:
    """Render DSL to SVG string."""
    canvas = dsl.get("canvas", {"width": 960, "height": 540})
    shapes = dsl.get("shapes", [])

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{canvas.get("width", 960)}" '
        f'height="{canvas.get("height", 540)}" '
        f'viewBox="0 0 {canvas.get("width", 960)} {canvas.get("height", 540)}">'
    ]

    # Background
    bg_color = canvas.get("background", "#FFFFFF")
    svg_parts.append(f'<rect width="100%" height="100%" fill="{bg_color}"/>')

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

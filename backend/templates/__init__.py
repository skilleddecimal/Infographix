"""Template system module - storage and management of infographic templates."""

from backend.templates.store import TemplateStore, Template, TemplateVariation
from backend.templates.ingestion import TemplateIngester

__all__ = [
    "TemplateStore",
    "Template",
    "TemplateVariation",
    "TemplateIngester",
]

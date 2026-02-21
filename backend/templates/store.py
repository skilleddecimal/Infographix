"""Template storage and management."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.dsl.schema import SlideScene


class TemplateVariation(BaseModel):
    """Defines variation ranges for template parameters."""

    model_config = ConfigDict(frozen=True)

    parameter: str = Field(description="Parameter path (e.g., 'color.color_token')")
    type: str = Field(description="Variation type: 'enum', 'range', 'list'")
    values: list[Any] = Field(description="Possible values or [min, max] for range")
    description: str | None = Field(default=None)


class TemplateComponent(BaseModel):
    """A component instance within a template."""

    model_config = ConfigDict(frozen=True)

    component_type: str = Field(description="Component type name")
    params: dict[str, Any] = Field(description="Fixed parameter values")
    variations: list[TemplateVariation] = Field(
        default_factory=list,
        description="Variable parameters",
    )
    bbox_relative: dict[str, float] = Field(
        description="Bounding box as ratio of canvas (0.0-1.0)",
    )


class Template(BaseModel):
    """A complete infographic template definition."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="Unique template identifier")
    name: str = Field(description="Human-readable template name")
    description: str = Field(default="", description="Template description")
    archetype: str = Field(description="Primary archetype (funnel, timeline, etc.)")
    tags: list[str] = Field(default_factory=list)

    # Canvas settings
    canvas_width: int = Field(default=12192000)
    canvas_height: int = Field(default=6858000)

    # Components that make up the template
    components: list[TemplateComponent] = Field(default_factory=list)

    # Global variations
    global_variations: list[TemplateVariation] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1)
    source_file: str | None = Field(default=None)

    # Original DSL for reference
    original_scene: SlideScene | None = Field(default=None)


class TemplateStore:
    """Storage and retrieval of infographic templates.

    Supports both in-memory storage and file-based persistence.
    In production, this would be backed by a database.
    """

    def __init__(self, storage_path: Path | str | None = None) -> None:
        """Initialize the template store.

        Args:
            storage_path: Optional path for file-based persistence.
        """
        self._templates: dict[str, Template] = {}
        self._storage_path = Path(storage_path) if storage_path else None

        if self._storage_path:
            self._storage_path.mkdir(parents=True, exist_ok=True)
            self._load_from_disk()

    def save(self, template: Template) -> str:
        """Save a template to the store.

        Args:
            template: Template to save.

        Returns:
            Template ID.
        """
        # Update timestamp
        template_dict = template.model_dump()
        template_dict["updated_at"] = datetime.utcnow()

        # Generate ID if not provided
        if not template.id:
            template_dict["id"] = f"tpl_{uuid.uuid4().hex[:8]}"

        updated_template = Template(**template_dict)
        self._templates[updated_template.id] = updated_template

        # Persist to disk
        if self._storage_path:
            self._save_to_disk(updated_template)

        return updated_template.id

    def get(self, template_id: str) -> Template | None:
        """Get a template by ID.

        Args:
            template_id: Template ID.

        Returns:
            Template or None if not found.
        """
        return self._templates.get(template_id)

    def get_or_raise(self, template_id: str) -> Template:
        """Get a template by ID, raising if not found.

        Args:
            template_id: Template ID.

        Returns:
            Template.

        Raises:
            KeyError: If template not found.
        """
        template = self.get(template_id)
        if template is None:
            raise KeyError(f"Template '{template_id}' not found")
        return template

    def delete(self, template_id: str) -> bool:
        """Delete a template.

        Args:
            template_id: Template ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        if template_id in self._templates:
            del self._templates[template_id]

            if self._storage_path:
                file_path = self._storage_path / f"{template_id}.json"
                if file_path.exists():
                    file_path.unlink()

            return True
        return False

    def list_all(self) -> list[Template]:
        """List all templates.

        Returns:
            List of all templates.
        """
        return list(self._templates.values())

    def list_by_archetype(self, archetype: str) -> list[Template]:
        """List templates for a specific archetype.

        Args:
            archetype: Archetype name.

        Returns:
            List of matching templates.
        """
        return [t for t in self._templates.values() if t.archetype == archetype]

    def list_by_tag(self, tag: str) -> list[Template]:
        """List templates with a specific tag.

        Args:
            tag: Tag to search for.

        Returns:
            List of matching templates.
        """
        return [t for t in self._templates.values() if tag in t.tags]

    def search(
        self,
        query: str | None = None,
        archetype: str | None = None,
        tags: list[str] | None = None,
    ) -> list[Template]:
        """Search for templates.

        Args:
            query: Text search query (searches name and description).
            archetype: Filter by archetype.
            tags: Filter by tags (any match).

        Returns:
            List of matching templates.
        """
        results = list(self._templates.values())

        if archetype:
            results = [t for t in results if t.archetype == archetype]

        if tags:
            results = [t for t in results if any(tag in t.tags for tag in tags)]

        if query:
            query_lower = query.lower()
            results = [
                t
                for t in results
                if query_lower in t.name.lower()
                or query_lower in t.description.lower()
            ]

        return results

    def count(self) -> int:
        """Get total number of templates.

        Returns:
            Template count.
        """
        return len(self._templates)

    def clear(self) -> None:
        """Clear all templates. Use for testing."""
        self._templates.clear()

        if self._storage_path:
            for file in self._storage_path.glob("*.json"):
                file.unlink()

    def _save_to_disk(self, template: Template) -> None:
        """Save a template to disk."""
        if not self._storage_path:
            return

        file_path = self._storage_path / f"{template.id}.json"

        # Convert to dict, handling datetime serialization
        data = template.model_dump(mode="json")

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def _load_from_disk(self) -> None:
        """Load all templates from disk."""
        if not self._storage_path:
            return

        for file_path in self._storage_path.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    template = Template(**data)
                    self._templates[template.id] = template
            except Exception as e:
                # Log error but continue loading other templates
                print(f"Error loading template {file_path}: {e}")

    def export_template(self, template_id: str) -> dict[str, Any]:
        """Export a template as a dictionary for sharing.

        Args:
            template_id: Template ID.

        Returns:
            Template data as dictionary.
        """
        template = self.get_or_raise(template_id)
        return template.model_dump(mode="json")

    def import_template(self, data: dict[str, Any]) -> str:
        """Import a template from a dictionary.

        Args:
            data: Template data dictionary.

        Returns:
            Imported template ID.
        """
        # Generate new ID to avoid conflicts
        data["id"] = f"tpl_{uuid.uuid4().hex[:8]}"
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()

        template = Template(**data)
        return self.save(template)


# Global template store instance
_default_store: TemplateStore | None = None


def get_template_store(storage_path: Path | str | None = None) -> TemplateStore:
    """Get the default template store instance.

    Args:
        storage_path: Optional storage path (only used on first call).

    Returns:
        TemplateStore instance.
    """
    global _default_store
    if _default_store is None:
        _default_store = TemplateStore(storage_path)
    return _default_store

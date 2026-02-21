"""Extract training data from PPTX template files."""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from backend.parser.pptx_reader import PPTXReader
from backend.dsl.schema import SlideScene

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTemplate:
    """A single extracted template with its metadata."""

    archetype: str
    file_name: str
    slide_number: int
    dsl: dict[str, Any]
    shape_count: int
    has_text: bool
    has_connectors: bool
    color_palette: list[str]


class TemplateExtractor:
    """Extracts DSL training data from PPTX templates.

    Reads PPTX files organized in folders by archetype and extracts
    DSL scene graphs for training ML models.
    """

    # Map folder names to canonical archetype names
    ARCHETYPE_MAP = {
        "chevron": "process",
        "comparison": "comparison",
        "cycle": "cycle",
        "funnel": "funnel",
        "hub_spoke": "hub_spoke",
        "matrix": "matrix",
        "process_flow": "process",
        "pyramid": "pyramid",
        "roadmap": "timeline",
        "timeline": "timeline",
    }

    def __init__(self, templates_dir: str | Path = "templates"):
        """Initialize the extractor.

        Args:
            templates_dir: Path to the templates directory.
        """
        self.templates_dir = Path(templates_dir)
        self.reader = PPTXReader()

    def extract_all(self) -> list[ExtractedTemplate]:
        """Extract templates from all PPTX files.

        Returns:
            List of ExtractedTemplate objects.
        """
        templates = []

        for archetype_dir in self.templates_dir.iterdir():
            if not archetype_dir.is_dir():
                continue

            folder_name = archetype_dir.name
            archetype = self.ARCHETYPE_MAP.get(folder_name, folder_name)

            for pptx_file in archetype_dir.glob("*.pptx"):
                try:
                    file_templates = self._extract_file(pptx_file, archetype)
                    templates.extend(file_templates)
                    logger.info(f"Extracted {len(file_templates)} slides from {pptx_file.name}")
                except Exception as e:
                    logger.error(f"Error extracting {pptx_file}: {e}")

        logger.info(f"Total extracted: {len(templates)} templates")
        return templates

    def _extract_file(self, pptx_path: Path, archetype: str) -> list[ExtractedTemplate]:
        """Extract templates from a single PPTX file.

        Args:
            pptx_path: Path to the PPTX file.
            archetype: The archetype classification.

        Returns:
            List of ExtractedTemplate objects.
        """
        templates = []
        scenes = self.reader.read(str(pptx_path))

        for slide_num, scene in enumerate(scenes, start=1):
            try:
                template = self._scene_to_template(
                    scene=scene,
                    archetype=archetype,
                    file_name=pptx_path.name,
                    slide_number=slide_num,
                )
                templates.append(template)
            except Exception as e:
                logger.warning(f"Error extracting slide {slide_num} from {pptx_path.name}: {e}")

        return templates

    def _scene_to_template(
        self,
        scene: SlideScene,
        archetype: str,
        file_name: str,
        slide_number: int,
    ) -> ExtractedTemplate:
        """Convert a SlideScene to an ExtractedTemplate.

        Args:
            scene: The SlideScene object.
            archetype: The archetype classification.
            file_name: Source file name.
            slide_number: Slide number in the file.

        Returns:
            ExtractedTemplate object.
        """
        # Convert scene to dict for storage
        dsl = scene.model_dump(mode="json")

        # Analyze the scene for metadata
        has_text = any(shape.text is not None for shape in scene.shapes)
        has_connectors = any(
            str(shape.type) in ("connector", "line", "ShapeType.CONNECTOR")
            for shape in scene.shapes
        )

        # Extract color palette
        colors = set()
        for shape in scene.shapes:
            if shape.fill and hasattr(shape.fill, "color"):
                if shape.fill.color:
                    colors.add(shape.fill.color)
            if shape.stroke and shape.stroke.color:
                colors.add(shape.stroke.color)

        return ExtractedTemplate(
            archetype=archetype,
            file_name=file_name,
            slide_number=slide_number,
            dsl=dsl,
            shape_count=len(scene.shapes),
            has_text=has_text,
            has_connectors=has_connectors,
            color_palette=list(colors)[:10],  # Limit to 10 colors
        )

    def save_extracted(
        self,
        templates: list[ExtractedTemplate],
        output_path: str | Path = "ml/data/extracted_templates.jsonl",
    ) -> Path:
        """Save extracted templates to a JSONL file.

        Args:
            templates: List of ExtractedTemplate objects.
            output_path: Output file path.

        Returns:
            Path to the saved file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            for template in templates:
                f.write(json.dumps(asdict(template)) + "\n")

        logger.info(f"Saved {len(templates)} templates to {output_path}")
        return output_path

    def load_extracted(
        self,
        input_path: str | Path = "ml/data/extracted_templates.jsonl",
    ) -> list[ExtractedTemplate]:
        """Load extracted templates from a JSONL file.

        Args:
            input_path: Input file path.

        Returns:
            List of ExtractedTemplate objects.
        """
        input_path = Path(input_path)
        templates = []

        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                templates.append(ExtractedTemplate(**data))

        return templates

    def get_stats(self, templates: list[ExtractedTemplate]) -> dict[str, Any]:
        """Get statistics about extracted templates.

        Args:
            templates: List of ExtractedTemplate objects.

        Returns:
            Statistics dictionary.
        """
        archetype_counts = {}
        total_shapes = 0
        templates_with_text = 0
        templates_with_connectors = 0

        for t in templates:
            archetype_counts[t.archetype] = archetype_counts.get(t.archetype, 0) + 1
            total_shapes += t.shape_count
            if t.has_text:
                templates_with_text += 1
            if t.has_connectors:
                templates_with_connectors += 1

        return {
            "total_templates": len(templates),
            "archetype_distribution": archetype_counts,
            "total_shapes": total_shapes,
            "avg_shapes_per_template": total_shapes / len(templates) if templates else 0,
            "templates_with_text": templates_with_text,
            "templates_with_connectors": templates_with_connectors,
            "unique_archetypes": len(archetype_counts),
        }


def extract_training_data(
    templates_dir: str = "templates",
    output_path: str = "ml/data/extracted_templates.jsonl",
) -> dict[str, Any]:
    """Main function to extract training data from templates.

    Args:
        templates_dir: Path to templates directory.
        output_path: Output file path.

    Returns:
        Statistics about the extraction.
    """
    logging.basicConfig(level=logging.INFO)

    extractor = TemplateExtractor(templates_dir)
    templates = extractor.extract_all()
    extractor.save_extracted(templates, output_path)

    stats = extractor.get_stats(templates)

    # Print summary
    print("\n=== Extraction Summary ===")
    print(f"Total templates: {stats['total_templates']}")
    print(f"Unique archetypes: {stats['unique_archetypes']}")
    print(f"Total shapes: {stats['total_shapes']}")
    print(f"Avg shapes/template: {stats['avg_shapes_per_template']:.1f}")
    print("\nArchetype distribution:")
    for arch, count in sorted(stats['archetype_distribution'].items()):
        print(f"  {arch}: {count}")

    return stats


if __name__ == "__main__":
    extract_training_data()

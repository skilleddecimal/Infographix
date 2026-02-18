"""
llm_reasoning.py — Claude API integration for prompt analysis.

Converts natural language prompts into structured InfographBrief dataclass
using Claude's structured output capabilities.

Dependencies: anthropic SDK
"""

import os
import json
import base64
import asyncio
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .archetype_registry import (
    ArchetypeType,
    ArchetypeCategory,
    ARCHETYPE_METADATA,
    generate_llm_archetype_descriptions,
)
from .data_models import BlockData, LayerData, ConnectorData, ColorPalette


# =============================================================================
# INFOGRAPH BRIEF DATACLASS
# =============================================================================

@dataclass
class EntityBrief:
    """A single entity/component extracted from the prompt."""
    id: str
    label: str
    description: Optional[str] = None
    layer_id: Optional[str] = None
    icon_hint: Optional[str] = None


@dataclass
class LayerBrief:
    """A layer/grouping extracted from the prompt."""
    id: str
    label: str
    entity_ids: List[str] = field(default_factory=list)
    is_cross_cutting: bool = False


@dataclass
class ConnectionBrief:
    """A connection between entities."""
    from_id: str
    to_id: str
    label: Optional[str] = None
    style: str = "arrow"  # arrow, bidirectional, dashed, plain


@dataclass
class InfographBrief:
    """
    Structured diagram specification extracted from user prompt.

    This is the output of LLM reasoning and input to layout generation.
    """
    title: str
    subtitle: Optional[str] = None
    diagram_type: str = "marketecture"  # Maps to ArchetypeType
    entities: List[EntityBrief] = field(default_factory=list)
    layers: List[LayerBrief] = field(default_factory=list)
    connections: List[ConnectionBrief] = field(default_factory=list)
    brand_hint: Optional[str] = None  # e.g., "opentext", "microsoft"
    color_hint: Optional[str] = None  # Primary color hex if specified
    style_notes: Optional[str] = None  # Additional styling instructions
    confidence: float = 1.0  # LLM confidence in interpretation
    raw_response: Optional[str] = None  # Raw LLM response for debugging

    def to_diagram_input(self, palette: Optional[ColorPalette] = None):
        """Convert brief to DiagramInput for layout engine."""
        from .data_models import DiagramInput, BlockData, LayerData, ConnectorData
        from .positioned import ConnectorStyle

        # Convert entities to blocks
        blocks = [
            BlockData(
                id=e.id,
                label=e.label,
                description=e.description,
                layer_id=e.layer_id,
                icon=e.icon_hint,
            )
            for e in self.entities
        ]

        # Convert layers
        layers = [
            LayerData(
                id=l.id,
                label=l.label,
                blocks=l.entity_ids,
                is_cross_cutting=l.is_cross_cutting,
            )
            for l in self.layers
        ]

        # Convert connections
        style_map = {
            "arrow": ConnectorStyle.ARROW,
            "bidirectional": ConnectorStyle.BIDIRECTIONAL,
            "dashed": ConnectorStyle.DASHED,
            "plain": ConnectorStyle.PLAIN,
        }
        connectors = [
            ConnectorData(
                from_id=c.from_id,
                to_id=c.to_id,
                label=c.label,
                style=style_map.get(c.style, ConnectorStyle.ARROW),
            )
            for c in self.connections
        ]

        return DiagramInput(
            title=self.title,
            subtitle=self.subtitle,
            blocks=blocks,
            layers=layers,
            connectors=connectors,
            palette=palette,
            metadata={"archetype": self.diagram_type},
        )


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def _build_system_prompt() -> str:
    """Build the system prompt with current archetype descriptions."""
    archetype_section = generate_llm_archetype_descriptions()

    return f"""You are an expert at analyzing user requests and converting them into structured diagram specifications.

Given a user's description of a diagram they want to create, extract:
1. Title and optional subtitle
2. Diagram type (archetype) - CRITICAL: Choose the most appropriate archetype from the list below
3. Entities/components to display
4. Layers/groupings (if applicable)
5. Connections between entities
6. Brand/color preferences

{archetype_section}

## How to Choose the Right Archetype:

1. **Look for keywords** in the user's request that match archetype keywords
2. **Consider the data structure**:
   - Sequential steps → process_flow, funnel, pipeline
   - Hierarchy/levels → pyramid, staircase, org_chart
   - Relationships → venn_diagram, hub_spoke, network
   - Comparisons → comparison, versus, pros_cons
   - Time-based → timeline, roadmap, gantt
   - Architecture → marketecture, tech_stack, block_diagram
3. **Match the visual intent**:
   - "Show how things narrow down" → funnel
   - "Show overlap between concepts" → venn_diagram
   - "Show priority/importance levels" → pyramid
   - "Show a cycle or loop" → circular_cycle
   - "Central concept with related items" → hub_spoke or target

## Response Format:
Return a JSON object with this exact structure:

```json
{{
  "title": "Main Title",
  "subtitle": "Optional Subtitle",
  "diagram_type": "marketecture",
  "entities": [
    {{
      "id": "entity_1",
      "label": "Display Name",
      "description": "Optional longer description",
      "layer_id": "layer_1",
      "icon_hint": "database"
    }}
  ],
  "layers": [
    {{
      "id": "layer_1",
      "label": "Layer Name",
      "entity_ids": ["entity_1", "entity_2"],
      "is_cross_cutting": false
    }}
  ],
  "connections": [
    {{
      "from_id": "entity_1",
      "to_id": "entity_2",
      "label": "optional label",
      "style": "arrow"
    }}
  ],
  "brand_hint": "opentext",
  "color_hint": "#1B365D",
  "style_notes": "Use corporate blue theme",
  "confidence": 0.95
}}
```

## Guidelines:
- Generate unique IDs for entities (use snake_case)
- Group related entities into layers when describing architecture
- For "marketecture" diagrams, create horizontal layers (e.g., UI, API, Database)
- Cross-cutting layers span the full width (e.g., "Security", "AI Layer")
- For "pyramid" diagrams, entities represent levels from base (largest) to top (smallest)
- For "funnel" diagrams, entities represent stages that narrow down
- For "venn_diagram", entities are the circles and their overlapping concepts
- For "hub_spoke", first entity is the hub, rest are spokes
- For "cycle" diagrams, entities form a circular flow
- Infer reasonable defaults if not specified
- Set confidence lower if the request is ambiguous

Only return valid JSON. Do not include any text before or after the JSON."""


# Generate the system prompt
SYSTEM_PROMPT = _build_system_prompt()


# =============================================================================
# CLAUDE API CLIENT
# =============================================================================

class ClaudeClient:
    """Wrapper for Anthropic Claude API."""

    def __init__(self, api_key: Optional[str] = None):
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package is required. Install with: pip install anthropic"
            )

        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.async_client = anthropic.AsyncAnthropic(api_key=self.api_key)

    def analyze_prompt_sync(
        self,
        prompt: str,
        image: Optional[bytes] = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
    ) -> InfographBrief:
        """
        Synchronously analyze a prompt and return structured brief.

        Args:
            prompt: User's diagram description
            image: Optional image bytes (for vision analysis)
            model: Claude model to use
            max_tokens: Maximum response tokens

        Returns:
            InfographBrief with extracted diagram specification
        """
        messages = self._build_messages(prompt, image)

        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=messages,
        )

        return self._parse_response(response)

    async def analyze_prompt(
        self,
        prompt: str,
        image: Optional[bytes] = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
    ) -> InfographBrief:
        """
        Asynchronously analyze a prompt and return structured brief.

        Args:
            prompt: User's diagram description
            image: Optional image bytes (for vision analysis)
            model: Claude model to use
            max_tokens: Maximum response tokens

        Returns:
            InfographBrief with extracted diagram specification
        """
        messages = self._build_messages(prompt, image)

        response = await self.async_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=messages,
        )

        return self._parse_response(response)

    def _build_messages(
        self, prompt: str, image: Optional[bytes] = None
    ) -> List[Dict[str, Any]]:
        """Build messages array for API call."""
        content = []

        # Add image if provided
        if image:
            # Detect image type from magic bytes
            media_type = "image/png"
            if image[:3] == b'\xff\xd8\xff':
                media_type = "image/jpeg"
            elif image[:4] == b'\x89PNG':
                media_type = "image/png"
            elif image[:4] == b'GIF8':
                media_type = "image/gif"
            elif image[:4] == b'RIFF' and image[8:12] == b'WEBP':
                media_type = "image/webp"

            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.b64encode(image).decode("utf-8"),
                },
            })

        content.append({"type": "text", "text": prompt})

        return [{"role": "user", "content": content}]

    def _parse_response(self, response) -> InfographBrief:
        """Parse Claude response into InfographBrief."""
        raw_text = response.content[0].text

        # Extract JSON from response (handle potential markdown code blocks)
        json_text = raw_text.strip()
        if json_text.startswith("```"):
            # Remove markdown code block
            lines = json_text.split("\n")
            json_text = "\n".join(lines[1:-1])

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            # Return a minimal brief with error info
            return InfographBrief(
                title="Error Parsing Response",
                diagram_type="marketecture",
                confidence=0.0,
                raw_response=raw_text,
                style_notes=f"JSON parse error: {str(e)}",
            )

        # Convert to InfographBrief
        entities = [
            EntityBrief(
                id=e.get("id", f"entity_{i}"),
                label=e.get("label", "Unknown"),
                description=e.get("description"),
                layer_id=e.get("layer_id"),
                icon_hint=e.get("icon_hint"),
            )
            for i, e in enumerate(data.get("entities", []))
        ]

        layers = [
            LayerBrief(
                id=l.get("id", f"layer_{i}"),
                label=l.get("label", "Layer"),
                entity_ids=l.get("entity_ids", []),
                is_cross_cutting=l.get("is_cross_cutting", False),
            )
            for i, l in enumerate(data.get("layers", []))
        ]

        connections = [
            ConnectionBrief(
                from_id=c.get("from_id", ""),
                to_id=c.get("to_id", ""),
                label=c.get("label"),
                style=c.get("style", "arrow"),
            )
            for c in data.get("connections", [])
        ]

        return InfographBrief(
            title=data.get("title", "Untitled Diagram"),
            subtitle=data.get("subtitle"),
            diagram_type=data.get("diagram_type", "marketecture"),
            entities=entities,
            layers=layers,
            connections=connections,
            brand_hint=data.get("brand_hint"),
            color_hint=data.get("color_hint"),
            style_notes=data.get("style_notes"),
            confidence=data.get("confidence", 1.0),
            raw_response=raw_text,
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_default_client: Optional[ClaudeClient] = None


def get_client(api_key: Optional[str] = None) -> ClaudeClient:
    """Get or create the default Claude client."""
    global _default_client
    if _default_client is None or api_key:
        _default_client = ClaudeClient(api_key=api_key)
    return _default_client


async def analyze_prompt(
    prompt: str,
    image: Optional[bytes] = None,
    api_key: Optional[str] = None,
) -> InfographBrief:
    """
    Analyze a user prompt and return a structured diagram brief.

    This is the main entry point for LLM reasoning.

    Args:
        prompt: Natural language description of desired diagram
        image: Optional image bytes (for vision analysis of existing diagrams)
        api_key: Optional Anthropic API key (uses env var if not provided)

    Returns:
        InfographBrief with extracted diagram specification

    Example:
        brief = await analyze_prompt(
            "Create a 3-tier web architecture with React, Node.js API, and PostgreSQL"
        )
        assert brief.diagram_type == "marketecture"
        assert len(brief.entities) >= 3
    """
    client = get_client(api_key)
    return await client.analyze_prompt(prompt, image)


def analyze_prompt_sync(
    prompt: str,
    image: Optional[bytes] = None,
    api_key: Optional[str] = None,
) -> InfographBrief:
    """
    Synchronous version of analyze_prompt.

    Use this in non-async contexts.
    """
    client = get_client(api_key)
    return client.analyze_prompt_sync(prompt, image)


# =============================================================================
# BRIEF VALIDATION AND ENHANCEMENT
# =============================================================================

def validate_brief(brief: InfographBrief) -> List[str]:
    """
    Validate an InfographBrief for completeness and consistency.

    Returns list of warning messages (empty if valid).
    """
    warnings = []

    if not brief.title:
        warnings.append("Missing title")

    if not brief.entities:
        warnings.append("No entities defined")

    # Check entity IDs are unique
    entity_ids = [e.id for e in brief.entities]
    if len(entity_ids) != len(set(entity_ids)):
        warnings.append("Duplicate entity IDs found")

    # Check layer references
    for layer in brief.layers:
        for entity_id in layer.entity_ids:
            if entity_id not in entity_ids:
                warnings.append(f"Layer '{layer.id}' references unknown entity '{entity_id}'")

    # Check connection references
    for conn in brief.connections:
        if conn.from_id not in entity_ids:
            warnings.append(f"Connection from unknown entity '{conn.from_id}'")
        if conn.to_id not in entity_ids:
            warnings.append(f"Connection to unknown entity '{conn.to_id}'")

    # Check diagram type is valid
    valid_types = [t.value for t in ArchetypeType]
    if brief.diagram_type not in valid_types:
        warnings.append(f"Unknown diagram type '{brief.diagram_type}', defaulting to marketecture")

    return warnings


def enhance_brief(brief: InfographBrief) -> InfographBrief:
    """
    Enhance a brief by filling in missing layer assignments and IDs.

    Returns a new InfographBrief with enhancements applied.
    """
    # Create a copy of the brief
    enhanced = InfographBrief(
        title=brief.title,
        subtitle=brief.subtitle,
        diagram_type=brief.diagram_type,
        entities=list(brief.entities),
        layers=list(brief.layers),
        connections=list(brief.connections),
        brand_hint=brief.brand_hint,
        color_hint=brief.color_hint,
        style_notes=brief.style_notes,
        confidence=brief.confidence,
        raw_response=brief.raw_response,
    )

    # If no layers defined but we have entities, create a default layer
    if not enhanced.layers and enhanced.entities:
        enhanced.layers = [
            LayerBrief(
                id="default_layer",
                label="Components",
                entity_ids=[e.id for e in enhanced.entities],
                is_cross_cutting=False,
            )
        ]

    # Assign entities without layer_id to their layer based on layers list
    entity_to_layer = {}
    for layer in enhanced.layers:
        for entity_id in layer.entity_ids:
            entity_to_layer[entity_id] = layer.id

    for entity in enhanced.entities:
        if not entity.layer_id and entity.id in entity_to_layer:
            entity.layer_id = entity_to_layer[entity.id]

    return enhanced


def brief_to_dict(brief: InfographBrief) -> Dict[str, Any]:
    """Convert InfographBrief to a JSON-serializable dictionary."""
    return {
        "title": brief.title,
        "subtitle": brief.subtitle,
        "diagram_type": brief.diagram_type,
        "entities": [
            {
                "id": e.id,
                "label": e.label,
                "description": e.description,
                "layer_id": e.layer_id,
                "icon_hint": e.icon_hint,
            }
            for e in brief.entities
        ],
        "layers": [
            {
                "id": l.id,
                "label": l.label,
                "entity_ids": l.entity_ids,
                "is_cross_cutting": l.is_cross_cutting,
            }
            for l in brief.layers
        ],
        "connections": [
            {
                "from_id": c.from_id,
                "to_id": c.to_id,
                "label": c.label,
                "style": c.style,
            }
            for c in brief.connections
        ],
        "brand_hint": brief.brand_hint,
        "color_hint": brief.color_hint,
        "style_notes": brief.style_notes,
        "confidence": brief.confidence,
    }


def dict_to_brief(data: Dict[str, Any]) -> InfographBrief:
    """Convert a dictionary back to InfographBrief."""
    entities = [
        EntityBrief(
            id=e.get("id", f"entity_{i}"),
            label=e.get("label", "Unknown"),
            description=e.get("description"),
            layer_id=e.get("layer_id"),
            icon_hint=e.get("icon_hint"),
        )
        for i, e in enumerate(data.get("entities", []))
    ]

    layers = [
        LayerBrief(
            id=l.get("id", f"layer_{i}"),
            label=l.get("label", "Layer"),
            entity_ids=l.get("entity_ids", []),
            is_cross_cutting=l.get("is_cross_cutting", False),
        )
        for i, l in enumerate(data.get("layers", []))
    ]

    connections = [
        ConnectionBrief(
            from_id=c.get("from_id", ""),
            to_id=c.get("to_id", ""),
            label=c.get("label"),
            style=c.get("style", "arrow"),
        )
        for c in data.get("connections", [])
    ]

    return InfographBrief(
        title=data.get("title", "Untitled"),
        subtitle=data.get("subtitle"),
        diagram_type=data.get("diagram_type", "marketecture"),
        entities=entities,
        layers=layers,
        connections=connections,
        brand_hint=data.get("brand_hint"),
        color_hint=data.get("color_hint"),
        style_notes=data.get("style_notes"),
        confidence=data.get("confidence", 1.0),
    )

"""
llm_reasoning.py — LLM integration for prompt analysis.

Converts natural language prompts into structured InfographBrief dataclass
using LLM structured output capabilities.

Supports multiple providers via llm_gateway:
- Anthropic Claude
- OpenAI GPT
- Google Gemini

Dependencies: litellm (preferred) or anthropic SDK (fallback)
"""

import os
import json
import base64
import asyncio
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Try to import LLM gateway first (Phase 4)
try:
    from .llm_gateway import (
        LLMGateway,
        get_gateway,
        ModelTier,
        GatewayResponse,
        LITELLM_AVAILABLE,
    )
    from .complexity_classifier import get_tier_for_prompt, classify_prompt
    GATEWAY_AVAILABLE = LITELLM_AVAILABLE
except ImportError:
    GATEWAY_AVAILABLE = False
    LLMGateway = None
    get_gateway = None
    ModelTier = None

# Fallback to direct Anthropic SDK
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
from .diagram_mode_classifier import (
    classify_diagram_mode,
    DiagramMode,
    DiagramModeResult,
)

# Try to import semantic mapper (Phase 4)
try:
    from .semantic_mapper import (
        SemanticMapper,
        get_semantic_mapper,
        SemanticCategory,
        enhance_brief_with_semantics,
    )
    SEMANTIC_MAPPER_AVAILABLE = True
except ImportError:
    SEMANTIC_MAPPER_AVAILABLE = False
    get_semantic_mapper = None
    enhance_brief_with_semantics = None


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
class SlideBrief:
    """
    A single slide within a multi-slide presentation.

    Each slide can have its own title, diagram type, entities, etc.
    """
    slide_number: int = 1
    title: str = ""
    subtitle: Optional[str] = None
    diagram_type: str = "marketecture"
    entities: List[EntityBrief] = field(default_factory=list)
    layers: List[LayerBrief] = field(default_factory=list)
    connections: List[ConnectionBrief] = field(default_factory=list)
    speaker_notes: Optional[str] = None
    transition: Optional[str] = None  # fade, slide, none

    def to_brief(self) -> "InfographBrief":
        """Convert this slide to a standalone InfographBrief."""
        return InfographBrief(
            title=self.title,
            subtitle=self.subtitle,
            diagram_type=self.diagram_type,
            entities=self.entities,
            layers=self.layers,
            connections=self.connections,
        )


@dataclass
class InfographBrief:
    """
    Structured diagram specification extracted from user prompt.

    This is the output of LLM reasoning and input to layout generation.

    For single-slide diagrams, use entities/layers/connections directly.
    For multi-slide presentations, populate the `slides` list instead.
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
    # Multi-slide support
    slides: List[SlideBrief] = field(default_factory=list)
    is_multi_slide: bool = False

    @property
    def slide_count(self) -> int:
        """Number of slides in the presentation."""
        if self.is_multi_slide and self.slides:
            return len(self.slides)
        return 1

    def get_slide(self, index: int) -> Optional[SlideBrief]:
        """Get slide by index (0-based)."""
        if self.is_multi_slide and self.slides:
            if 0 <= index < len(self.slides):
                return self.slides[index]
        elif index == 0:
            # Return first slide from single-slide brief
            return SlideBrief(
                slide_number=1,
                title=self.title,
                subtitle=self.subtitle,
                diagram_type=self.diagram_type,
                entities=self.entities,
                layers=self.layers,
                connections=self.connections,
            )
        return None

    def to_single_slide_briefs(self) -> List["InfographBrief"]:
        """Convert multi-slide brief to list of single-slide briefs."""
        if not self.is_multi_slide or not self.slides:
            return [self]

        briefs = []
        for slide in self.slides:
            brief = InfographBrief(
                title=slide.title,
                subtitle=slide.subtitle,
                diagram_type=slide.diagram_type,
                entities=slide.entities,
                layers=slide.layers,
                connections=slide.connections,
                brand_hint=self.brand_hint,
                color_hint=self.color_hint,
                style_notes=self.style_notes,
            )
            briefs.append(brief)
        return briefs

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
# TEMPLATE CONTEXT FOR LLM
# =============================================================================

def _build_template_examples(learned_styles=None) -> str:
    """
    Generate LLM-readable descriptions of learned templates.

    When users upload training templates, we extract their patterns and
    make them available to Claude so it can understand the visual styles
    that have been learned.
    """
    if learned_styles is None:
        # Try to get styles from the local style model
        try:
            from .local_style_model import get_local_model
            local_model = get_local_model()
            template_context = local_model.get_template_context_for_llm()
            if template_context:
                return template_context
        except Exception:
            pass
        return ""

    # Build from provided styles
    if not learned_styles:
        return ""

    sections = ["## Reference Templates"]
    sections.append("The following styles have been learned from uploaded templates. "
                   "Use these patterns when generating similar diagram types:")
    sections.append("")

    for style in learned_styles:
        # Handle both dict and object styles
        if hasattr(style, 'name'):
            name = style.name
            tags = getattr(style, 'tags', [])
            palette = getattr(style, 'palette', None)
            typography = getattr(style, 'typography', None)
            shape_style = getattr(style, 'shape_style', None)
        else:
            name = style.get('name', 'Unknown')
            tags = style.get('tags', [])
            palette = style.get('palette', {})
            typography = style.get('typography', {})
            shape_style = style.get('shape_style', {})

        section = f"### Template: {name}"

        # Type/category
        diagram_type = tags[0] if tags else 'General'
        section += f"\n- **Type**: {diagram_type}"

        # Colors
        if palette:
            if hasattr(palette, 'accent_colors'):
                colors = palette.accent_colors[:5] if palette.accent_colors else []
            else:
                colors = palette.get('accent_colors', [])[:5]
            if colors:
                section += f"\n- **Color Palette**: {', '.join(colors)}"

        # Typography
        if typography:
            if hasattr(typography, 'title_size_pt'):
                title_pt = typography.title_size_pt
                body_pt = typography.body_size_pt
                label_pt = typography.label_size_pt
            else:
                title_pt = typography.get('title_size_pt', 44)
                body_pt = typography.get('body_size_pt', 20)
                label_pt = typography.get('label_size_pt', 12)
            section += f"\n- **Typography**: Title={title_pt}pt, Body={body_pt}pt, Label={label_pt}pt"

        # Effects
        effects = []
        if shape_style:
            has_shadow = False
            has_gradient = False
            gradient_angle = 270

            if hasattr(shape_style, 'shadow'):
                has_shadow = shape_style.shadow is not None
            else:
                has_shadow = shape_style.get('shadow') is not None

            if hasattr(shape_style, 'gradient'):
                has_gradient = shape_style.gradient is not None
                if has_gradient and shape_style.gradient:
                    gradient_angle = getattr(shape_style.gradient, 'angle_degrees', 270)
            else:
                gradient_info = shape_style.get('gradient')
                has_gradient = gradient_info is not None
                if has_gradient and gradient_info:
                    gradient_angle = gradient_info.get('angle_degrees', 270)

            if has_shadow:
                effects.append("shadow")
            if has_gradient:
                effects.append(f"gradient ({int(gradient_angle)}deg)")

        if effects:
            section += f"\n- **Effects**: {', '.join(effects)}"

        # Usage guidance based on type
        type_lower = diagram_type.lower()
        if 'pyramid' in type_lower:
            section += "\n- **When to use**: For hierarchy, priority, or tier-based diagrams. Use trapezoid shapes for levels."
        elif 'funnel' in type_lower:
            section += "\n- **When to use**: For conversion, filtering, or narrowing processes."
        elif 'timeline' in type_lower:
            section += "\n- **When to use**: For chronological sequences, roadmaps, or milestones."

        sections.append(section)

    return "\n\n".join(sections)


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def _build_system_prompt(learned_styles=None, industry: str = None) -> str:
    """Build the system prompt with current archetype descriptions, learned templates, and semantic guidance."""
    archetype_section = generate_llm_archetype_descriptions()

    # Build template context section
    template_section = _build_template_examples(learned_styles)

    # Include template section if available
    template_block = ""
    if template_section:
        template_block = f"\n\n{template_section}\n"

    # Build semantic guidance section
    semantic_block = ""
    if SEMANTIC_MAPPER_AVAILABLE:
        mapper = get_semantic_mapper()
        semantic_guidance = mapper.get_semantic_guidance(industry)
        semantic_block = f"\n\n{semantic_guidance}\n"

    return f"""You are an expert visual storyteller and diagram architect. Your role is to analyze user requests and create the MOST VISUALLY APPROPRIATE and impactful diagram specifications.
{semantic_block}
{template_block}

## Your Primary Goal: Visual Storytelling

The diagram you create should TELL A STORY visually. Choose the archetype that best REPRESENTS the concept, not just organizes the data. The shape and structure of the diagram should reinforce the message.

Given a user's description, extract:
1. Title and optional subtitle
2. Diagram type (archetype) - CRITICAL: Choose the archetype that BEST VISUALLY REPRESENTS the concept
3. Entities/components to display
4. Layers/groupings (if applicable)
5. Connections between entities
6. Brand/color preferences

{archetype_section}

## CRITICAL: Archetype Selection Strategy

**STEP 1: Identify the Core Metaphor**
What is the user trying to communicate? Match to the strongest visual metaphor:

| Concept | Best Archetype | Why It Works Visually |
|---------|---------------|----------------------|
| Prioritization, hierarchy of importance | **pyramid** | Triangular shape visually shows "more important = higher/smaller" |
| Narrowing down, filtering, conversion | **funnel** | Funnel shape visually shows reduction/filtering |
| Steps in sequence | **process_flow** | Arrows show direction and progression |
| Cyclical process, continuous loop | **circular_cycle** | Circle has no beginning/end - perfect for cycles |
| Central idea with related concepts | **hub_spoke** | Hub visually dominates, spokes radiate out |
| Overlapping concepts, shared attributes | **venn_diagram** | Overlapping circles show intersection |
| Layered architecture | **marketecture** | Stacked layers show depth/dependency |
| Timeline, history | **timeline** | Linear progression shows time flow |
| Organizational structure | **org_chart** | Tree structure shows reporting |
| Progression, growth, advancement | **staircase** | Steps upward = progress |
| Goals, targeting | **target** | Concentric rings = focus on center |
| Comparison, choices | **comparison** | Side-by-side = easy to compare |
| Pros and cons | **pros_cons** | Two columns = balance/contrast |

**STEP 2: Look for Trigger Words**
These words STRONGLY suggest specific archetypes:

- "pyramid", "hierarchy", "levels of importance", "priorities" → **pyramid**
- "funnel", "conversion", "narrow down", "filter", "stages" → **funnel**
- "cycle", "loop", "circular", "continuous", "repeating" → **circular_cycle**
- "workflow", "process", "steps", "sequence", "flow" → **process_flow**
- "hub", "central", "core", "spokes", "radiate" → **hub_spoke**
- "overlap", "intersection", "shared", "venn" → **venn_diagram**
- "architecture", "stack", "layers", "tiers" → **marketecture**
- "timeline", "history", "milestones", "roadmap" → **timeline**
- "org chart", "reporting", "team structure" → **org_chart**
- "compare", "versus", "vs", "differences" → **comparison**
- "pros and cons", "advantages", "disadvantages" → **pros_cons**
- "target", "goal", "bullseye", "focus" → **target**
- "ladder", "steps", "progression", "journey" → **staircase**

**STEP 3: Consider Visual Impact**
Ask yourself: "Will this archetype make the concept IMMEDIATELY clear at a glance?"

- Food pyramid → **pyramid** (NOT marketecture) - the shape IS the message
- Sales funnel → **funnel** (NOT process_flow) - narrowing IS the message
- Circular economy → **circular_cycle** (NOT process_flow) - the loop IS the message
- Tech stack → **marketecture** - layers show dependencies
- Decision tree → **process_flow** or **hub_spoke** depending on complexity

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
# CANVAS MODE SYSTEM PROMPT
# =============================================================================

CANVAS_SYSTEM_PROMPT = """You are an expert visual designer creating precise diagram layouts. Your role is to produce EXACT POSITIONED ELEMENTS for complex compositions that require flexible placement.

## Your Task
Given a user's description, create a complete diagram with ALL elements precisely positioned using percentage-based coordinates (0-100 for both x and y, where 0,0 is top-left).

The user is requesting a complex diagram that may include:
- Main diagram shapes (pyramids, blocks, etc.)
- Side arrows with labels
- Callout boxes or banners
- Specific colors (hex codes)
- Sub-items/bullet points within shapes
- Custom backgrounds

## Positioning System
- x: 0 = left edge, 100 = right edge
- y: 0 = top edge, 100 = bottom edge
- width/height: percentage of content area

## Element Types
- **trapezoid**: Pyramid level (wide at bottom, narrow at top within the element)
- **block**: Standard rectangle
- **arrow**: Directional arrow shape with arrow_direction (up, down, left, right)
- **banner**: Full-width callout bar
- **text_box**: Text-only, no border
- **ellipse**: Oval/circle

## Response Format
Return a JSON object with this exact structure:

```json
{
  "title": "Main Title",
  "subtitle": "Optional Subtitle",
  "background_color": "#1b2838",
  "canvas_elements": [
    {
      "id": "tier1",
      "type": "trapezoid",
      "label": "Foundation",
      "x": 20,
      "y": 70,
      "width": 60,
      "height": 12,
      "fill_color": "#4A5568",
      "text_color": "#FFFFFF",
      "sub_items": ["SIEM", "Log Management", "Basic Monitoring"],
      "z_order": 10
    },
    {
      "id": "arrow_left",
      "type": "arrow",
      "label": "Maturity & Investment",
      "x": 5,
      "y": 25,
      "width": 8,
      "height": 50,
      "fill_color": "#4299E1",
      "text_color": "#FFFFFF",
      "arrow_direction": "up",
      "z_order": 5
    },
    {
      "id": "callout_bar",
      "type": "banner",
      "label": "ROI increases 3-5x per tier",
      "x": 10,
      "y": 90,
      "width": 80,
      "height": 6,
      "fill_color": "#2D3748",
      "text_color": "#FFFFFF",
      "z_order": 15
    }
  ],
  "canvas_connectors": [],
  "confidence": 0.95
}
```

## Layout Guidelines

### For Pyramids with Side Elements:
- Main pyramid levels: x=20-25, width=50-60 (centered with room for side arrows)
- Left arrow: x=5-8, width=8-10
- Right arrow: x=85-90, width=8-10
- Pyramid levels from base to apex: y decreases, width decreases
- Callout bar below: y=88-92

### For Color Progressions:
- Dark base progressing to bright apex
- Example: #4A5568 → #718096 → #A0AEC0 → #F6AD55 → #ED8936

### Text Colors:
- On dark backgrounds: #FFFFFF or #F7FAFC
- On light backgrounds: #1A202C or #2D3748

### Z-Order:
- Background elements: 1-5
- Main diagram shapes: 10-20
- Side annotations: 5-10
- Callout bars: 15-25

## Important Rules:
1. Position ALL requested elements - don't skip annotations, arrows, or callouts
2. Use the EXACT colors if hex codes are specified
3. Include sub_items for elements that have bullet points
4. Make sure elements don't overlap unless intentional
5. Leave room for side arrows when placing main shapes

Only return valid JSON. Do not include any text before or after the JSON."""


@dataclass
class CanvasBrief:
    """
    Canvas mode diagram specification with pre-positioned elements.

    This is used for complex diagrams where the LLM determines
    exact element positions rather than using archetype templates.
    """
    title: str
    subtitle: Optional[str] = None
    background_color: str = "#FFFFFF"
    canvas_elements: List[Dict[str, Any]] = field(default_factory=list)
    canvas_connectors: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 1.0
    raw_response: Optional[str] = None
    # Mode classification info
    mode_result: Optional[DiagramModeResult] = None

    def to_diagram_input(self, palette: Optional[ColorPalette] = None):
        """Convert canvas brief to DiagramInput with canvas metadata."""
        from .data_models import DiagramInput

        return DiagramInput(
            title=self.title,
            subtitle=self.subtitle,
            blocks=[],  # Canvas mode doesn't use blocks
            layers=[],
            connectors=[],
            palette=palette,
            metadata={
                "archetype": "canvas",
                "canvas_elements": self.canvas_elements,
                "canvas_connectors": self.canvas_connectors,
                "background_color": self.background_color,
            },
        )


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

        return self._parse_response(response, original_prompt=prompt)

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

        return self._parse_response(response, original_prompt=prompt)

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

    def _override_diagram_type_from_keywords(self, prompt: str, detected_type: str) -> str:
        """
        Override diagram type if prompt contains strong keywords that contradict the detected type.

        This handles cases where the LLM misclassifies due to non-deterministic behavior.
        """
        prompt_lower = prompt.lower()

        # Strong keyword mappings - these should ALWAYS override
        keyword_overrides = {
            "pyramid": ["pyramid", "hierarchy of needs", "maslow"],
            "funnel": ["funnel", "sales funnel", "conversion funnel"],
            "circular_cycle": ["cycle", "circular", "loop", "continuous loop"],
            "timeline": ["timeline", "roadmap", "milestones"],
            "venn_diagram": ["venn", "overlap", "intersection"],
            "org_chart": ["org chart", "organization chart", "reporting structure"],
            "process_flow": ["workflow", "process flow", "flowchart"],
        }

        for archetype, keywords in keyword_overrides.items():
            for keyword in keywords:
                if keyword in prompt_lower and detected_type != archetype:
                    # Strong keyword found but wrong type detected - override
                    return archetype

        return detected_type

    def _parse_response(self, response, original_prompt: str = "") -> InfographBrief:
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

        # Get detected diagram type and apply keyword override if needed
        detected_type = data.get("diagram_type", "marketecture")
        final_type = self._override_diagram_type_from_keywords(original_prompt, detected_type)

        return InfographBrief(
            title=data.get("title", "Untitled Diagram"),
            subtitle=data.get("subtitle"),
            diagram_type=final_type,
            entities=entities,
            layers=layers,
            connections=connections,
            brand_hint=data.get("brand_hint"),
            color_hint=data.get("color_hint"),
            style_notes=data.get("style_notes"),
            confidence=data.get("confidence", 1.0),
            raw_response=raw_text,
        )

    # =========================================================================
    # CANVAS MODE METHODS
    # =========================================================================

    def analyze_prompt_canvas_sync(
        self,
        prompt: str,
        image: Optional[bytes] = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
    ) -> CanvasBrief:
        """
        Synchronously analyze a complex prompt and return canvas brief.

        Uses the canvas system prompt to get pre-positioned elements.
        """
        messages = self._build_messages(prompt, image)

        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=CANVAS_SYSTEM_PROMPT,
            messages=messages,
        )

        return self._parse_canvas_response(response)

    async def analyze_prompt_canvas(
        self,
        prompt: str,
        image: Optional[bytes] = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
    ) -> CanvasBrief:
        """
        Asynchronously analyze a complex prompt and return canvas brief.
        """
        messages = self._build_messages(prompt, image)

        response = await self.async_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=CANVAS_SYSTEM_PROMPT,
            messages=messages,
        )

        return self._parse_canvas_response(response)

    def _parse_canvas_response(self, response) -> CanvasBrief:
        """Parse Claude response into CanvasBrief."""
        raw_text = response.content[0].text

        # Extract JSON from response
        json_text = raw_text.strip()
        if json_text.startswith("```"):
            lines = json_text.split("\n")
            json_text = "\n".join(lines[1:-1])

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            return CanvasBrief(
                title="Error Parsing Response",
                background_color="#FFFFFF",
                confidence=0.0,
                raw_response=raw_text,
            )

        return CanvasBrief(
            title=data.get("title", "Untitled Diagram"),
            subtitle=data.get("subtitle"),
            background_color=data.get("background_color", "#FFFFFF"),
            canvas_elements=data.get("canvas_elements", []),
            canvas_connectors=data.get("canvas_connectors", []),
            confidence=data.get("confidence", 1.0),
            raw_response=raw_text,
        )


# =============================================================================
# GATEWAY CLIENT (Multi-provider via LiteLLM)
# =============================================================================

class GatewayClient:
    """
    Multi-provider LLM client using the LLM gateway.

    Supports automatic routing based on prompt complexity and
    fallback across providers (Claude, GPT, Gemini).
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        google_api_key: Optional[str] = None,
        auto_route: bool = True,
    ):
        if not GATEWAY_AVAILABLE:
            raise ImportError(
                "LLM Gateway not available. Install litellm: pip install litellm"
            )

        self.gateway = get_gateway(
            anthropic_api_key=anthropic_api_key,
            openai_api_key=openai_api_key,
            google_api_key=google_api_key,
        )
        self.auto_route = auto_route

    def analyze_prompt_sync(
        self,
        prompt: str,
        image: Optional[bytes] = None,
        model_tier: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> InfographBrief:
        """
        Synchronously analyze a prompt using the gateway.

        Args:
            prompt: User's diagram description
            image: Optional image bytes (for vision analysis)
            model_tier: Override tier (fast, standard, premium)
            max_tokens: Maximum response tokens

        Returns:
            InfographBrief with extracted diagram specification
        """
        # Determine model tier
        if model_tier:
            tier = ModelTier(model_tier)
        elif self.auto_route:
            tier = get_tier_for_prompt(prompt, has_image=image is not None)
        else:
            tier = ModelTier.STANDARD

        # Build messages
        messages = self._build_messages(prompt, image)

        # Call gateway
        response = self.gateway.complete_sync(
            system=SYSTEM_PROMPT,
            messages=messages,
            tier=tier,
            max_tokens=max_tokens,
            temperature=0.0,
        )

        if not response.success:
            logger.error(f"Gateway request failed: {response.error}")
            return InfographBrief(
                title="Error",
                diagram_type="marketecture",
                confidence=0.0,
                raw_response=response.error,
                style_notes=f"Gateway error: {response.error}",
            )

        return self._parse_response(response.content, response.usage)

    async def analyze_prompt(
        self,
        prompt: str,
        image: Optional[bytes] = None,
        model_tier: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> InfographBrief:
        """
        Asynchronously analyze a prompt using the gateway.
        """
        # Determine model tier
        if model_tier:
            tier = ModelTier(model_tier)
        elif self.auto_route:
            tier = get_tier_for_prompt(prompt, has_image=image is not None)
        else:
            tier = ModelTier.STANDARD

        # Build messages
        messages = self._build_messages(prompt, image)

        # Call gateway
        response = await self.gateway.complete(
            system=SYSTEM_PROMPT,
            messages=messages,
            tier=tier,
            max_tokens=max_tokens,
            temperature=0.0,
        )

        if not response.success:
            logger.error(f"Gateway request failed: {response.error}")
            return InfographBrief(
                title="Error",
                diagram_type="marketecture",
                confidence=0.0,
                raw_response=response.error,
                style_notes=f"Gateway error: {response.error}",
            )

        return self._parse_response(response.content, response.usage)

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
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{base64.b64encode(image).decode('utf-8')}",
                },
            })

        content.append({"type": "text", "text": prompt})

        return [{"role": "user", "content": content}]

    def _parse_response(self, raw_text: str, usage: Any = None) -> InfographBrief:
        """Parse LLM response into InfographBrief."""
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

    def get_stats(self) -> Dict[str, Any]:
        """Get gateway statistics."""
        return self.gateway.get_stats()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_default_client: Optional[ClaudeClient] = None
_default_gateway_client: Optional[GatewayClient] = None


def get_client(api_key: Optional[str] = None) -> ClaudeClient:
    """Get or create the default Claude client (legacy)."""
    global _default_client
    if _default_client is None or api_key:
        _default_client = ClaudeClient(api_key=api_key)
    return _default_client


def get_gateway_client(
    anthropic_api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    google_api_key: Optional[str] = None,
) -> GatewayClient:
    """Get or create the default gateway client (multi-provider)."""
    global _default_gateway_client
    if _default_gateway_client is None:
        _default_gateway_client = GatewayClient(
            anthropic_api_key=anthropic_api_key,
            openai_api_key=openai_api_key,
            google_api_key=google_api_key,
        )
    return _default_gateway_client


async def analyze_prompt(
    prompt: str,
    image: Optional[bytes] = None,
    api_key: Optional[str] = None,
    use_gateway: bool = True,
) -> InfographBrief:
    """
    Analyze a user prompt and return a structured diagram brief.

    This is the main entry point for LLM reasoning.

    Args:
        prompt: Natural language description of desired diagram
        image: Optional image bytes (for vision analysis of existing diagrams)
        api_key: Optional Anthropic API key (uses env var if not provided)
        use_gateway: Use multi-provider gateway if available (default True)

    Returns:
        InfographBrief with extracted diagram specification

    Example:
        brief = await analyze_prompt(
            "Create a 3-tier web architecture with React, Node.js API, and PostgreSQL"
        )
        assert brief.diagram_type == "marketecture"
        assert len(brief.entities) >= 3
    """
    # Try gateway first if available and requested
    if use_gateway and GATEWAY_AVAILABLE:
        try:
            client = get_gateway_client(anthropic_api_key=api_key)
            return await client.analyze_prompt(prompt, image)
        except Exception as e:
            logger.warning(f"Gateway failed, falling back to direct client: {e}")

    # Fall back to direct Anthropic client
    client = get_client(api_key)
    return await client.analyze_prompt(prompt, image)


def analyze_prompt_sync(
    prompt: str,
    image: Optional[bytes] = None,
    api_key: Optional[str] = None,
    use_gateway: bool = True,
) -> InfographBrief:
    """
    Synchronous version of analyze_prompt.

    Use this in non-async contexts.

    Args:
        prompt: Natural language description of desired diagram
        image: Optional image bytes (for vision analysis)
        api_key: Optional API key (uses env var if not provided)
        use_gateway: Use multi-provider gateway if available (default True)
    """
    # Try gateway first if available and requested
    if use_gateway and GATEWAY_AVAILABLE:
        try:
            client = get_gateway_client(anthropic_api_key=api_key)
            return client.analyze_prompt_sync(prompt, image)
        except Exception as e:
            logger.warning(f"Gateway failed, falling back to direct client: {e}")

    # Fall back to direct Anthropic client
    client = get_client(api_key)
    return client.analyze_prompt_sync(prompt, image)


# =============================================================================
# SMART ROUTING (Archetype vs Canvas Mode)
# =============================================================================

from typing import Union

BriefType = Union[InfographBrief, CanvasBrief]


async def analyze_prompt_smart(
    prompt: str,
    image: Optional[bytes] = None,
    api_key: Optional[str] = None,
    force_mode: Optional[str] = None,
) -> BriefType:
    """
    Smart analyze that routes to archetype or canvas mode based on complexity.

    This is the recommended entry point for Option C hybrid mode.

    Args:
        prompt: Natural language description of desired diagram
        image: Optional image bytes (for vision analysis)
        api_key: Optional Anthropic API key
        force_mode: Override mode detection ("archetype" or "canvas")

    Returns:
        InfographBrief for archetype mode, CanvasBrief for canvas mode

    Example:
        # Simple prompt -> archetype mode
        brief = await analyze_prompt_smart("Create a 3-tier pyramid")
        assert isinstance(brief, InfographBrief)

        # Complex prompt -> canvas mode
        brief = await analyze_prompt_smart(
            "Create a pyramid with side arrows and callout bar"
        )
        assert isinstance(brief, CanvasBrief)
    """
    # Determine mode
    if force_mode:
        mode = DiagramMode.CANVAS if force_mode == "canvas" else DiagramMode.ARCHETYPE
        mode_result = None
    else:
        mode_result = classify_diagram_mode(prompt)
        mode = mode_result.mode
        logger.info(f"Mode classification: {mode.value} ({mode_result.confidence:.1%})")
        if mode_result.signals:
            logger.info(f"Signals detected: {mode_result.signals}")

    # Route to appropriate analysis
    client = get_client(api_key)

    if mode == DiagramMode.CANVAS:
        logger.info("Using canvas mode for complex composition")
        brief = await client.analyze_prompt_canvas(prompt, image)
        brief.mode_result = mode_result
        return brief
    else:
        logger.info("Using archetype mode for standard diagram")
        return await client.analyze_prompt(prompt, image)


def analyze_prompt_smart_sync(
    prompt: str,
    image: Optional[bytes] = None,
    api_key: Optional[str] = None,
    force_mode: Optional[str] = None,
) -> BriefType:
    """
    Synchronous version of analyze_prompt_smart.

    Routes to archetype or canvas mode based on complexity detection.
    """
    # Determine mode
    if force_mode:
        mode = DiagramMode.CANVAS if force_mode == "canvas" else DiagramMode.ARCHETYPE
        mode_result = None
    else:
        mode_result = classify_diagram_mode(prompt)
        mode = mode_result.mode
        logger.info(f"Mode classification: {mode.value} ({mode_result.confidence:.1%})")
        if mode_result.signals:
            logger.info(f"Signals detected: {mode_result.signals}")

    # Route to appropriate analysis
    client = get_client(api_key)

    if mode == DiagramMode.CANVAS:
        logger.info("Using canvas mode for complex composition")
        brief = client.analyze_prompt_canvas_sync(prompt, image)
        brief.mode_result = mode_result
        return brief
    else:
        logger.info("Using archetype mode for standard diagram")
        return client.analyze_prompt_sync(prompt, image)


def get_diagram_mode(prompt: str) -> DiagramModeResult:
    """
    Check whether a prompt should use archetype or canvas mode.

    This can be used to preview the mode before calling analyze.

    Args:
        prompt: Natural language description of desired diagram

    Returns:
        DiagramModeResult with mode, confidence, and detected signals
    """
    return classify_diagram_mode(prompt)


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


def enhance_brief(
    brief: InfographBrief,
    apply_semantics: bool = True,
    industry: Optional[str] = None,
) -> InfographBrief:
    """
    Enhance a brief by filling in missing layer assignments, IDs, and semantic mappings.

    Args:
        brief: The brief to enhance
        apply_semantics: Whether to apply semantic color/icon mappings
        industry: Optional industry for specialized semantic mappings

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

    # Apply semantic mappings for icons (Phase 4)
    if apply_semantics and SEMANTIC_MAPPER_AVAILABLE:
        mapper = get_semantic_mapper()
        for entity in enhanced.entities:
            # Only add icon_hint if not already specified
            if not entity.icon_hint:
                icon = mapper.suggest_icon(
                    entity.label,
                    industry=industry,
                )
                if icon:
                    entity.icon_hint = icon

    return enhanced


def get_semantic_color_for_entity(
    entity_label: str,
    entity_description: Optional[str] = None,
    industry: Optional[str] = None,
) -> str:
    """
    Get semantic color for an entity based on its label and description.

    This can be used by archetypes to apply semantic coloring.

    Args:
        entity_label: Entity's display label
        entity_description: Optional entity description
        industry: Optional industry for specialized mappings

    Returns:
        Hex color code
    """
    if not SEMANTIC_MAPPER_AVAILABLE:
        return "#4285F4"  # Default blue

    mapper = get_semantic_mapper()
    primary, _, _ = mapper.get_semantic_color(
        f"{entity_label} {entity_description or ''}".strip(),
        industry=industry,
    )
    return primary


def get_semantic_icon_for_entity(
    entity_label: str,
    entity_description: Optional[str] = None,
    industry: Optional[str] = None,
) -> Optional[str]:
    """
    Get suggested icon for an entity based on its label and description.

    Args:
        entity_label: Entity's display label
        entity_description: Optional entity description
        industry: Optional industry for specialized mappings

    Returns:
        Icon ID from icon library, or None
    """
    if not SEMANTIC_MAPPER_AVAILABLE:
        return None

    mapper = get_semantic_mapper()
    return mapper.suggest_icon(
        f"{entity_label} {entity_description or ''}".strip(),
        industry=industry,
    )


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

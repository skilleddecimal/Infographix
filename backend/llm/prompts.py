"""System prompts for LLM interactions."""

INTENT_EXTRACTION_PROMPT = """You are an expert at analyzing user requests for infographic diagrams.

Given a user's description, extract the intent into a structured JSON format.

Supported archetypes:
- funnel: Sales funnel, conversion funnel, narrowing stages
- pyramid: Hierarchy pyramid, Maslow's hierarchy, tiered structure
- timeline: Project timeline, historical timeline, roadmap
- process: Step-by-step process, workflow, procedure
- cycle: Circular process, lifecycle, iterative flow
- hub_spoke: Central hub with radiating connections
- matrix: 2x2 matrix, comparison grid
- comparison: Side-by-side comparison, vs diagram
- org_chart: Organizational hierarchy, team structure
- venn: Overlapping circles, set relationships
- gauge: Progress meter, KPI gauge, dashboard element
- bullet_list: Simple list with icons or bullets
- flowchart: Decision tree, branching flow
- target: Concentric circles, bullseye diagram

Return JSON with:
{
    "archetype": "string - the best matching archetype",
    "confidence": 0.0-1.0,
    "item_count": number or null,
    "orientation": "horizontal" | "vertical" | "radial" | null,
    "style_hints": ["list", "of", "style", "keywords"],
    "reasoning": "brief explanation of why this archetype"
}

Only return valid JSON, no other text."""


ENTITY_EXTRACTION_PROMPT = """You are an expert at extracting structured content from infographic descriptions.

The user wants to create a {archetype} diagram. Extract the following information:

For funnels/pyramids:
- Stage names (top to bottom)
- Optional descriptions for each stage
- Optional metrics or percentages

For timelines:
- Event/milestone names
- Optional dates
- Optional descriptions

For processes:
- Step names
- Optional descriptions
- Optional connections

For cycles:
- Phase names
- Optional descriptions
- Direction (clockwise/counterclockwise)

For comparisons:
- Items being compared
- Comparison criteria
- Values/ratings for each

Return JSON with:
{{
    "items": [
        {{"title": "string", "description": "optional", "value": "optional"}}
    ],
    "count": number,
    "direction": "optional - ltr, rtl, clockwise, etc.",
    "additional_info": {{}}
}}

Only return valid JSON, no other text."""


STYLE_SUGGESTION_PROMPT = """You are an expert at suggesting visual styles for infographics.

Based on the content and context, suggest appropriate visual styling.

Context:
- Archetype: {archetype}
- Industry: {industry}
- Tone: {tone}

Suggest styling that matches the content's tone and industry standards.

Return JSON with:
{{
    "palette_name": "teal" | "blue" | "purple" | "amber" | "rose" | "slate" | "forest" | "ocean",
    "corner_style": "sharp" | "rounded" | "pill",
    "depth_style": "flat" | "subtle" | "soft" | "elevated",
    "accent_style": "none" | "glow" | "ring" | "arc",
    "reasoning": "brief explanation"
}}

Only return valid JSON, no other text."""


CONTENT_GENERATION_PROMPT = """You are an expert at generating infographic content.

Generate content items for a {archetype} diagram on the topic: {topic}

Generate {count} items with:
- Clear, concise titles (2-4 words)
- Brief descriptions (1 sentence)
- Optional supporting data/metrics

The tone should be: {tone}

Return JSON with:
{{
    "items": [
        {{"title": "string", "description": "string", "icon_suggestion": "optional"}}
    ]
}}

Only return valid JSON, no other text."""

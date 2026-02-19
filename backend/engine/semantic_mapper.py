"""
semantic_mapper.py — Concept-to-visual mapping for intelligent infographic generation.

This module provides semantic intelligence for mapping abstract concepts to visual
representations, enabling the system to:
- Automatically select appropriate colors based on concept semantics
- Suggest relevant icons for entities
- Apply domain-specific visual conventions
- Support industry-specific vocabularies

The semantic mapper works in conjunction with the LLM reasoning layer to enhance
the quality and meaningfulness of generated infographics.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import json
import os
import re


# =============================================================================
# SEMANTIC CATEGORIES AND MAPPINGS
# =============================================================================

class SemanticCategory(Enum):
    """High-level semantic categories for concept classification."""
    POSITIVE = "positive"       # Growth, success, achievement, opportunity
    NEGATIVE = "negative"       # Risk, threat, danger, failure, decline
    NEUTRAL = "neutral"         # Process, data, system, information
    FOUNDATION = "foundation"   # Base, infrastructure, core, fundamental
    HIGHLIGHT = "highlight"     # Important, key, critical, emphasis
    TECHNOLOGY = "technology"   # Digital, software, hardware, IT
    BUSINESS = "business"       # Finance, strategy, operations, management
    PEOPLE = "people"           # Users, teams, customers, stakeholders
    TIME = "time"               # Timeline, schedule, milestone, phase
    SECURITY = "security"       # Protection, compliance, privacy, safety


@dataclass
class SemanticMapping:
    """
    Mapping from a semantic concept to visual attributes.

    Defines how abstract concepts should be visually represented through
    colors, icons, shapes, and other visual elements.
    """
    category: SemanticCategory
    primary_color: str                    # Primary color for this concept
    secondary_color: str                  # Secondary/lighter variation
    accent_color: str                     # Accent for emphasis
    icon_suggestions: List[str]           # Suggested icon IDs from icon library
    shape_hint: Optional[str] = None      # Preferred shape type
    visual_weight: float = 1.0            # Relative visual importance (0.5-2.0)
    keywords: List[str] = field(default_factory=list)  # Keywords that trigger this mapping

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "accent_color": self.accent_color,
            "icon_suggestions": self.icon_suggestions,
            "shape_hint": self.shape_hint,
            "visual_weight": self.visual_weight,
            "keywords": self.keywords,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SemanticMapping":
        return cls(
            category=SemanticCategory(data.get("category", "neutral")),
            primary_color=data.get("primary_color", "#4285F4"),
            secondary_color=data.get("secondary_color", "#7BAAF7"),
            accent_color=data.get("accent_color", "#1A73E8"),
            icon_suggestions=data.get("icon_suggestions", []),
            shape_hint=data.get("shape_hint"),
            visual_weight=data.get("visual_weight", 1.0),
            keywords=data.get("keywords", []),
        )


# =============================================================================
# CORE SEMANTIC COLOR MAPPINGS
# =============================================================================

# Standard semantic colors based on universal associations
SEMANTIC_COLORS = {
    SemanticCategory.POSITIVE: {
        "primary": "#34A853",       # Google Green - growth, success
        "secondary": "#81C995",     # Lighter green
        "accent": "#137333",        # Dark green for emphasis
    },
    SemanticCategory.NEGATIVE: {
        "primary": "#EA4335",       # Google Red - risk, danger
        "secondary": "#F28B82",     # Lighter red/salmon
        "accent": "#C5221F",        # Dark red for emphasis
    },
    SemanticCategory.NEUTRAL: {
        "primary": "#4285F4",       # Google Blue - process, data
        "secondary": "#7BAAF7",     # Lighter blue
        "accent": "#1A73E8",        # Dark blue for emphasis
    },
    SemanticCategory.FOUNDATION: {
        "primary": "#5F6368",       # Google Gray - foundation, base
        "secondary": "#9AA0A6",     # Lighter gray
        "accent": "#3C4043",        # Dark gray for emphasis
    },
    SemanticCategory.HIGHLIGHT: {
        "primary": "#FBBC05",       # Google Yellow - highlight, attention
        "secondary": "#FDD663",     # Lighter yellow
        "accent": "#F9AB00",        # Dark yellow/amber for emphasis
    },
    SemanticCategory.TECHNOLOGY: {
        "primary": "#4285F4",       # Blue - tech, digital
        "secondary": "#8AB4F8",     # Lighter blue
        "accent": "#185ABC",        # Dark blue
    },
    SemanticCategory.BUSINESS: {
        "primary": "#1A73E8",       # Corporate blue
        "secondary": "#669DF6",     # Lighter
        "accent": "#0D47A1",        # Dark
    },
    SemanticCategory.PEOPLE: {
        "primary": "#673AB7",       # Purple - people, users
        "secondary": "#B39DDB",     # Lighter purple
        "accent": "#512DA8",        # Dark purple
    },
    SemanticCategory.TIME: {
        "primary": "#00BCD4",       # Cyan - time, progress
        "secondary": "#80DEEA",     # Lighter cyan
        "accent": "#00838F",        # Dark cyan
    },
    SemanticCategory.SECURITY: {
        "primary": "#FF5722",       # Deep Orange - security, protection
        "secondary": "#FFAB91",     # Lighter
        "accent": "#E64A19",        # Dark
    },
}


# Keywords that map to semantic categories
CATEGORY_KEYWORDS = {
    SemanticCategory.POSITIVE: [
        "growth", "success", "achieve", "opportunity", "increase", "expand",
        "improve", "gain", "profit", "benefit", "advantage", "progress",
        "positive", "upward", "rise", "boost", "enhance", "optimize",
        "win", "milestone", "goal", "target achieved", "breakthrough",
    ],
    SemanticCategory.NEGATIVE: [
        "risk", "threat", "danger", "fail", "decline", "decrease",
        "loss", "problem", "issue", "challenge", "warning", "alert",
        "negative", "downward", "drop", "reduce", "concern", "critical",
        "error", "bug", "vulnerability", "breach", "attack",
    ],
    SemanticCategory.NEUTRAL: [
        "process", "data", "system", "flow", "step", "stage",
        "information", "analysis", "report", "document", "record",
        "procedure", "workflow", "operation", "function", "service",
    ],
    SemanticCategory.FOUNDATION: [
        "foundation", "base", "core", "fundamental", "infrastructure",
        "platform", "layer", "underlying", "support", "backbone",
        "ground", "bottom", "essential", "basic",
    ],
    SemanticCategory.HIGHLIGHT: [
        "important", "key", "critical", "priority", "focus",
        "highlight", "emphasis", "attention", "main", "primary",
        "featured", "star", "standout", "notable",
    ],
    SemanticCategory.TECHNOLOGY: [
        "technology", "tech", "digital", "software", "hardware",
        "computer", "application", "api", "database", "cloud",
        "server", "network", "code", "algorithm", "ai", "ml",
        "automation", "integration", "microservice",
    ],
    SemanticCategory.BUSINESS: [
        "business", "enterprise", "corporate", "strategy", "finance",
        "revenue", "cost", "budget", "investment", "roi",
        "market", "customer", "sales", "marketing", "operations",
        "management", "executive", "leadership",
    ],
    SemanticCategory.PEOPLE: [
        "user", "team", "customer", "employee", "stakeholder",
        "people", "person", "human", "staff", "workforce",
        "collaboration", "community", "group", "organization",
    ],
    SemanticCategory.TIME: [
        "time", "timeline", "schedule", "milestone", "phase",
        "quarter", "year", "month", "week", "day",
        "deadline", "duration", "period", "roadmap", "plan",
    ],
    SemanticCategory.SECURITY: [
        "security", "protection", "privacy", "compliance", "safety",
        "authentication", "authorization", "encryption", "firewall",
        "access", "control", "governance", "audit", "regulation",
    ],
}


# Icon suggestions per category
CATEGORY_ICONS = {
    SemanticCategory.POSITIVE: ["arrow_up", "growth", "check", "star", "target"],
    SemanticCategory.NEGATIVE: ["warning", "alert", "close", "arrow_down", "stop"],
    SemanticCategory.NEUTRAL: ["flow", "gear", "document", "data", "grid"],
    SemanticCategory.FOUNDATION: ["layers", "foundation", "server", "database", "building"],
    SemanticCategory.HIGHLIGHT: ["star", "bell", "bookmark", "flag", "lightbulb"],
    SemanticCategory.TECHNOLOGY: ["code", "api", "cloud", "server", "chip"],
    SemanticCategory.BUSINESS: ["chart", "briefcase", "growth", "target", "building"],
    SemanticCategory.PEOPLE: ["user", "team", "customer", "handshake", "community"],
    SemanticCategory.TIME: ["calendar", "clock", "timeline", "milestone", "schedule"],
    SemanticCategory.SECURITY: ["lock", "shield", "key", "security", "shield_check"],
}


# =============================================================================
# SEMANTIC MAPPER CLASS
# =============================================================================

class SemanticMapper:
    """
    Maps concepts and entities to visual attributes based on semantic analysis.

    The SemanticMapper analyzes text content to determine:
    - Appropriate colors based on concept category
    - Suggested icons for entities
    - Visual weight/importance
    - Shape preferences

    It supports both universal mappings and industry-specific vocabularies.
    """

    def __init__(self, vocabularies_path: Optional[str] = None):
        """
        Initialize the semantic mapper.

        Args:
            vocabularies_path: Path to industry_vocabularies.json (optional)
        """
        self._keyword_index: Dict[str, SemanticCategory] = {}
        self._industry_mappings: Dict[str, Dict[str, SemanticMapping]] = {}

        # Build keyword index
        self._build_keyword_index()

        # Load industry vocabularies if path provided
        if vocabularies_path is None:
            # Try default location
            default_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "data",
                "industry_vocabularies.json"
            )
            if os.path.exists(default_path):
                vocabularies_path = default_path

        if vocabularies_path and os.path.exists(vocabularies_path):
            self._load_industry_vocabularies(vocabularies_path)

    def _build_keyword_index(self) -> None:
        """Build index mapping keywords to categories."""
        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                self._keyword_index[keyword.lower()] = category

    def _load_industry_vocabularies(self, path: str) -> None:
        """Load industry-specific vocabularies from JSON file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for industry, mappings in data.get("industries", {}).items():
                self._industry_mappings[industry] = {}
                for concept, mapping_data in mappings.items():
                    self._industry_mappings[industry][concept.lower()] = (
                        SemanticMapping.from_dict(mapping_data)
                    )
        except Exception as e:
            # Silently continue without industry vocabularies
            pass

    def analyze_text(self, text: str) -> SemanticCategory:
        """
        Analyze text and determine its semantic category.

        Args:
            text: Text to analyze (entity label, description, etc.)

        Returns:
            SemanticCategory for the text
        """
        text_lower = text.lower()

        # Count matches for each category
        category_scores: Dict[SemanticCategory, int] = {}

        for keyword, category in self._keyword_index.items():
            if keyword in text_lower:
                category_scores[category] = category_scores.get(category, 0) + 1

        # Return category with highest score, or NEUTRAL if no matches
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        return SemanticCategory.NEUTRAL

    def get_semantic_color(
        self,
        text: str,
        industry: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Get semantic colors for text content.

        Args:
            text: Text to analyze
            industry: Optional industry for specialized mappings

        Returns:
            Tuple of (primary_color, secondary_color, accent_color)
        """
        # Check industry-specific mappings first
        if industry and industry in self._industry_mappings:
            text_lower = text.lower()
            for concept, mapping in self._industry_mappings[industry].items():
                if concept in text_lower:
                    return (
                        mapping.primary_color,
                        mapping.secondary_color,
                        mapping.accent_color,
                    )

        # Fall back to category-based colors
        category = self.analyze_text(text)
        colors = SEMANTIC_COLORS.get(category, SEMANTIC_COLORS[SemanticCategory.NEUTRAL])
        return (colors["primary"], colors["secondary"], colors["accent"])

    def suggest_icon(
        self,
        text: str,
        category: Optional[SemanticCategory] = None,
        industry: Optional[str] = None
    ) -> Optional[str]:
        """
        Suggest an icon for text content.

        Args:
            text: Text to analyze
            category: Optional pre-determined category
            industry: Optional industry for specialized suggestions

        Returns:
            Icon ID from icon library, or None if no suggestion
        """
        # Check industry-specific mappings first
        if industry and industry in self._industry_mappings:
            text_lower = text.lower()
            for concept, mapping in self._industry_mappings[industry].items():
                if concept in text_lower and mapping.icon_suggestions:
                    return mapping.icon_suggestions[0]

        # Determine category if not provided
        if category is None:
            category = self.analyze_text(text)

        # Get icons for category
        icons = CATEGORY_ICONS.get(category, CATEGORY_ICONS[SemanticCategory.NEUTRAL])
        return icons[0] if icons else None

    def get_mapping_for_entity(
        self,
        entity_label: str,
        entity_description: Optional[str] = None,
        industry: Optional[str] = None
    ) -> SemanticMapping:
        """
        Get complete semantic mapping for an entity.

        Args:
            entity_label: Entity's display label
            entity_description: Optional entity description
            industry: Optional industry for specialized mappings

        Returns:
            SemanticMapping with all visual attributes
        """
        # Combine text for analysis
        full_text = entity_label
        if entity_description:
            full_text = f"{entity_label} {entity_description}"

        # Check industry-specific mappings
        if industry and industry in self._industry_mappings:
            text_lower = full_text.lower()
            for concept, mapping in self._industry_mappings[industry].items():
                if concept in text_lower:
                    return mapping

        # Build mapping from category analysis
        category = self.analyze_text(full_text)
        colors = SEMANTIC_COLORS.get(category, SEMANTIC_COLORS[SemanticCategory.NEUTRAL])
        icons = CATEGORY_ICONS.get(category, [])

        return SemanticMapping(
            category=category,
            primary_color=colors["primary"],
            secondary_color=colors["secondary"],
            accent_color=colors["accent"],
            icon_suggestions=icons,
            keywords=[],
        )

    def get_semantic_guidance(self, industry: Optional[str] = None) -> str:
        """
        Generate semantic guidance text for LLM prompts.

        This provides context to the LLM about how to apply semantic
        color and icon mappings when generating infographic briefs.

        Args:
            industry: Optional industry for specialized guidance

        Returns:
            Guidance text to include in LLM system prompt
        """
        guidance = """
SEMANTIC COLOR MAPPING GUIDELINES:

Apply colors based on concept semantics to enhance visual communication:

1. POSITIVE CONCEPTS (growth, success, opportunity):
   - Use GREEN tones (#34A853) for upward trends, achievements, benefits
   - Apply to entities representing goals met, improvements, gains

2. NEGATIVE CONCEPTS (risk, threat, decline):
   - Use RED tones (#EA4335) for warnings, risks, problems, failures
   - Apply to entities representing challenges, threats, issues

3. PROCESS/DATA CONCEPTS (neutral operations):
   - Use BLUE tones (#4285F4) for workflows, data flows, systems
   - Default color for procedural or informational entities

4. FOUNDATION CONCEPTS (infrastructure, base layers):
   - Use GRAY tones (#5F6368) for underlying platforms, core systems
   - Apply to bottom layers in architecture diagrams

5. HIGHLIGHT CONCEPTS (important, key, critical):
   - Use YELLOW/AMBER tones (#FBBC05) for emphasis, attention-grabbing
   - Apply sparingly to draw focus to key elements

6. TECHNOLOGY CONCEPTS (software, digital):
   - Use BLUE tones (#4285F4) for technical components
   - Suggest appropriate tech icons (server, cloud, api, code)

7. SECURITY CONCEPTS (protection, compliance):
   - Use ORANGE tones (#FF5722) for security-related elements
   - Suggest shield, lock, key icons

When generating entity colors, consider:
- The entity's label and description text
- Its role in the diagram (is it a risk? a goal? infrastructure?)
- The visual hierarchy (should it stand out or blend in?)
"""

        # Add industry-specific guidance if available
        if industry and industry in self._industry_mappings:
            guidance += f"\n\nINDUSTRY-SPECIFIC MAPPINGS ({industry.upper()}):\n"
            for concept, mapping in self._industry_mappings[industry].items():
                guidance += f"- {concept}: {mapping.primary_color} (icons: {', '.join(mapping.icon_suggestions[:3])})\n"

        return guidance

    def classify_entities(
        self,
        entities: List[Dict[str, Any]],
        industry: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Classify a list of entities with semantic mappings.

        Enhances each entity with semantic color and icon suggestions.

        Args:
            entities: List of entity dicts with 'label' and optional 'description'
            industry: Optional industry for specialized mappings

        Returns:
            Entities enhanced with semantic_color and icon_suggestion fields
        """
        enhanced = []
        for entity in entities:
            label = entity.get("label", "")
            description = entity.get("description", "")

            mapping = self.get_mapping_for_entity(label, description, industry)

            enhanced_entity = entity.copy()
            enhanced_entity["semantic_category"] = mapping.category.value
            enhanced_entity["semantic_color"] = mapping.primary_color
            enhanced_entity["secondary_color"] = mapping.secondary_color
            enhanced_entity["accent_color"] = mapping.accent_color

            # Only add icon suggestion if not already specified
            if not entity.get("icon_hint") and mapping.icon_suggestions:
                enhanced_entity["icon_hint"] = mapping.icon_suggestions[0]

            enhanced.append(enhanced_entity)

        return enhanced


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_mapper_instance: Optional[SemanticMapper] = None


def get_semantic_mapper() -> SemanticMapper:
    """Get singleton SemanticMapper instance."""
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = SemanticMapper()
    return _mapper_instance


def get_semantic_color(text: str, industry: Optional[str] = None) -> str:
    """
    Quick helper to get semantic primary color for text.

    Args:
        text: Text to analyze
        industry: Optional industry

    Returns:
        Primary color hex code
    """
    mapper = get_semantic_mapper()
    primary, _, _ = mapper.get_semantic_color(text, industry)
    return primary


def suggest_icon_for_text(text: str, industry: Optional[str] = None) -> Optional[str]:
    """
    Quick helper to suggest icon for text.

    Args:
        text: Text to analyze
        industry: Optional industry

    Returns:
        Icon ID or None
    """
    mapper = get_semantic_mapper()
    return mapper.suggest_icon(text, industry=industry)


def enhance_brief_with_semantics(
    brief: Dict[str, Any],
    industry: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enhance an InfographBrief with semantic mappings.

    Processes all entities in the brief and adds semantic color
    and icon suggestions based on their labels and descriptions.

    Args:
        brief: InfographBrief dictionary
        industry: Optional industry for specialized mappings

    Returns:
        Enhanced brief with semantic attributes
    """
    mapper = get_semantic_mapper()

    enhanced = brief.copy()

    # Enhance entities
    if "entities" in enhanced:
        enhanced["entities"] = mapper.classify_entities(
            enhanced["entities"],
            industry=industry
        )

    # Analyze diagram title for overall theme
    if "title" in enhanced:
        category = mapper.analyze_text(enhanced["title"])
        enhanced["semantic_theme"] = category.value

    return enhanced

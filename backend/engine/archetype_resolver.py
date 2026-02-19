"""
archetype_resolver.py — Resolution system for finding archetype rules.

The ArchetypeResolver provides a unified interface for:
1. Looking up predefined archetype rules
2. Loading learned archetype rules from JSON files
3. Graceful fallback to canvas mode for unknown archetypes

Priority order:
1. Learned (training wins) - Rules discovered from PPTX templates
2. Predefined - Built-in rules for standard archetypes
3. Canvas fallback - Generic freeform layout (never fails)

Usage:
    resolver = ArchetypeResolver()
    rules = resolver.resolve("funnel")
    archetype = UniversalArchetype(rules)
"""

import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

from .archetype_rules import (
    ArchetypeRules,
    LayoutStrategy,
    PREDEFINED_ARCHETYPE_RULES,
    get_predefined_rules,
    list_predefined_archetypes,
)


# Default paths for rules storage
DEFAULT_RULES_DIR = Path(__file__).parent.parent / "data" / "archetype_rules"
LEARNED_RULES_SUBDIR = "learned"


class ArchetypeResolver:
    """
    Resolves archetype IDs to ArchetypeRules.

    The resolver maintains registries of:
    - Predefined rules (built into the code)
    - Learned rules (loaded from JSON files)
    - Custom rules (added at runtime)

    Resolution priority: Learned > Custom > Predefined > Canvas Fallback
    """

    def __init__(self, rules_dir: Optional[str] = None):
        """
        Initialize the resolver.

        Args:
            rules_dir: Directory containing JSON rule files.
                       Defaults to backend/data/archetype_rules/
        """
        self.rules_dir = Path(rules_dir) if rules_dir else DEFAULT_RULES_DIR
        self.learned_dir = self.rules_dir / LEARNED_RULES_SUBDIR

        # Registries
        self._learned_rules: Dict[str, ArchetypeRules] = {}
        self._custom_rules: Dict[str, ArchetypeRules] = {}

        # Load learned rules from disk
        self._load_learned_rules()

    def resolve(self, archetype_id: str) -> ArchetypeRules:
        """
        Resolve an archetype ID to rules.

        Args:
            archetype_id: The archetype identifier (e.g., "funnel", "pyramid")

        Returns:
            ArchetypeRules for the archetype (never fails - falls back to canvas)
        """
        # Normalize ID
        archetype_id = archetype_id.lower().strip()

        # Priority 1: Learned rules
        if archetype_id in self._learned_rules:
            return self._learned_rules[archetype_id]

        # Priority 2: Custom rules
        if archetype_id in self._custom_rules:
            return self._custom_rules[archetype_id]

        # Priority 3: Predefined rules
        predefined = get_predefined_rules(archetype_id)
        if predefined:
            return predefined

        # Priority 4: Try to load from JSON file
        json_rules = self._load_rules_from_json(archetype_id)
        if json_rules:
            return json_rules

        # Priority 5: Canvas fallback (never fails)
        return self._canvas_fallback(archetype_id)

    def resolve_multiple(self, archetype_ids: List[str]) -> Dict[str, ArchetypeRules]:
        """
        Resolve multiple archetype IDs.

        Args:
            archetype_ids: List of archetype identifiers

        Returns:
            Dict mapping archetype_id to ArchetypeRules
        """
        return {aid: self.resolve(aid) for aid in archetype_ids}

    def register_custom(self, rules: ArchetypeRules) -> None:
        """
        Register custom rules at runtime.

        Args:
            rules: ArchetypeRules to register
        """
        self._custom_rules[rules.archetype_id.lower()] = rules

    def register_learned(self, rules: ArchetypeRules) -> None:
        """
        Register learned rules (and optionally persist to disk).

        Args:
            rules: ArchetypeRules learned from training
        """
        self._learned_rules[rules.archetype_id.lower()] = rules

    def save_learned(self, rules: ArchetypeRules) -> str:
        """
        Save learned rules to JSON file.

        Args:
            rules: ArchetypeRules to save

        Returns:
            Path to the saved JSON file
        """
        # Ensure directory exists
        self.learned_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        filename = f"{rules.archetype_id.lower()}.json"
        filepath = self.learned_dir / filename

        # Convert to dict and save
        rules_dict = rules.to_dict()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(rules_dict, f, indent=2)

        # Also register in memory
        self.register_learned(rules)

        return str(filepath)

    def list_available(self, include_canvas: bool = False) -> List[Dict[str, Any]]:
        """
        List all available archetypes.

        Args:
            include_canvas: Whether to include the canvas fallback

        Returns:
            List of archetype info dicts
        """
        archetypes = []

        # Predefined
        for archetype_id in list_predefined_archetypes():
            rules = get_predefined_rules(archetype_id)
            if rules:
                archetypes.append({
                    "id": archetype_id,
                    "name": rules.display_name,
                    "description": rules.description,
                    "category": rules.category,
                    "source": "predefined",
                    "confidence": 1.0,
                })

        # Learned
        for archetype_id, rules in self._learned_rules.items():
            archetypes.append({
                "id": archetype_id,
                "name": rules.display_name,
                "description": rules.description,
                "category": rules.category,
                "source": "learned",
                "confidence": rules.confidence_score,
            })

        # Custom
        for archetype_id, rules in self._custom_rules.items():
            archetypes.append({
                "id": archetype_id,
                "name": rules.display_name,
                "description": rules.description,
                "category": rules.category,
                "source": "custom",
                "confidence": 1.0,
            })

        # Canvas
        if include_canvas:
            archetypes.append({
                "id": "canvas",
                "name": "Canvas (Freeform)",
                "description": "Flexible freeform layout",
                "category": "other",
                "source": "builtin",
                "confidence": 1.0,
            })

        return archetypes

    def search(self, query: str) -> List[ArchetypeRules]:
        """
        Search for archetypes by keyword.

        Args:
            query: Search query string

        Returns:
            List of matching ArchetypeRules
        """
        query = query.lower()
        matches = []

        # Search predefined
        for archetype_id in list_predefined_archetypes():
            rules = get_predefined_rules(archetype_id)
            if rules and self._matches_query(rules, query):
                matches.append(rules)

        # Search learned
        for rules in self._learned_rules.values():
            if self._matches_query(rules, query):
                matches.append(rules)

        # Search custom
        for rules in self._custom_rules.values():
            if self._matches_query(rules, query):
                matches.append(rules)

        return matches

    def _matches_query(self, rules: ArchetypeRules, query: str) -> bool:
        """Check if rules match a search query."""
        searchable = " ".join([
            rules.archetype_id,
            rules.display_name,
            rules.description,
            rules.category,
            " ".join(rules.keywords),
            " ".join(rules.example_prompts),
        ]).lower()
        return query in searchable

    def _load_learned_rules(self) -> None:
        """Load learned rules from JSON files."""
        if not self.learned_dir.exists():
            return

        for json_file in self.learned_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                rules = ArchetypeRules.from_dict(data)
                self._learned_rules[rules.archetype_id.lower()] = rules
            except Exception as e:
                # Log error but continue
                print(f"Warning: Failed to load {json_file}: {e}")

    def _load_rules_from_json(self, archetype_id: str) -> Optional[ArchetypeRules]:
        """Try to load rules from a JSON file."""
        # Check predefined rules directory
        json_path = self.rules_dir / f"{archetype_id}.json"
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return ArchetypeRules.from_dict(data)
            except Exception:
                pass

        # Check learned rules directory
        json_path = self.learned_dir / f"{archetype_id}.json"
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                rules = ArchetypeRules.from_dict(data)
                self._learned_rules[archetype_id] = rules
                return rules
            except Exception:
                pass

        return None

    def _canvas_fallback(self, archetype_id: str) -> ArchetypeRules:
        """
        Create canvas fallback rules for unknown archetypes.

        The canvas archetype uses freeform positioning and can handle
        any input - it never fails.
        """
        return ArchetypeRules(
            archetype_id=archetype_id,
            display_name=f"Canvas ({archetype_id})",
            description=f"Freeform layout for '{archetype_id}'",
            layout_strategy=LayoutStrategy.FREEFORM,
            supports_overlays=True,
            supports_nested=True,
            min_elements=1,
            max_elements=100,
            category="other",
            confidence_score=0.5,  # Lower confidence for fallback
        )

    def reload(self) -> None:
        """Reload all learned rules from disk."""
        self._learned_rules.clear()
        self._load_learned_rules()


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_default_resolver: Optional[ArchetypeResolver] = None


def get_resolver() -> ArchetypeResolver:
    """Get the default resolver instance."""
    global _default_resolver
    if _default_resolver is None:
        _default_resolver = ArchetypeResolver()
    return _default_resolver


def resolve_archetype(archetype_id: str) -> ArchetypeRules:
    """
    Convenience function to resolve an archetype.

    Args:
        archetype_id: The archetype identifier

    Returns:
        ArchetypeRules for the archetype
    """
    return get_resolver().resolve(archetype_id)


def list_archetypes() -> List[Dict[str, Any]]:
    """
    Convenience function to list available archetypes.

    Returns:
        List of archetype info dicts
    """
    return get_resolver().list_available()

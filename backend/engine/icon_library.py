"""
icon_library.py — Icon/Pictogram system with semantic search.

Provides 100+ SVG icons organized by category with keyword-based search.
Icons are rendered as custom geometry in PPTX shapes or as path elements in SVG.

Usage:
    from backend.engine.icon_library import IconLibrary, get_icon_library

    library = get_icon_library()

    # Get icon by exact name
    icon = library.get("database")

    # Search by keyword
    results = library.search("cloud")  # Returns ["cloud", "network", ...]

    # Get all icons in category
    tech_icons = library.get_by_category("technology")
"""

import os
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum
import re


# =============================================================================
# DATA MODELS
# =============================================================================

class IconCategory(Enum):
    """Icon category types."""
    TECHNOLOGY = "technology"
    BUSINESS = "business"
    PEOPLE = "people"
    GENERAL = "general"
    ARROWS = "arrows"
    DATA = "data"
    COMMUNICATION = "communication"
    SECURITY = "security"
    FINANCE = "finance"
    PROCESS = "process"


@dataclass
class IconDefinition:
    """
    Definition of a single SVG icon.

    Attributes:
        id: Unique identifier (e.g., "database")
        category: Category for organization
        keywords: List of search keywords
        path: SVG path data (d attribute)
        viewBox: SVG viewBox (default "0 0 24 24")
        fill_rule: SVG fill rule (default "evenodd")
    """
    id: str
    category: str
    keywords: List[str]
    path: str
    viewBox: str = "0 0 24 24"
    fill_rule: str = "evenodd"

    @property
    def viewBox_values(self) -> Tuple[float, float, float, float]:
        """Parse viewBox into (min_x, min_y, width, height)."""
        parts = self.viewBox.split()
        if len(parts) == 4:
            return tuple(float(p) for p in parts)
        return (0, 0, 24, 24)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "category": self.category,
            "keywords": self.keywords,
            "path": self.path,
            "viewBox": self.viewBox,
        }

    @classmethod
    def from_dict(cls, id: str, data: Dict) -> "IconDefinition":
        """Create from dictionary."""
        return cls(
            id=id,
            category=data.get("category", "general"),
            keywords=data.get("keywords", []),
            path=data.get("path", ""),
            viewBox=data.get("viewBox", "0 0 24 24"),
        )


@dataclass
class IconSearchResult:
    """Result from icon search with relevance score."""
    icon: IconDefinition
    score: float  # 0-1, higher is more relevant
    match_type: str  # "exact", "keyword", "partial"


# =============================================================================
# ICON LIBRARY
# =============================================================================

class IconLibrary:
    """
    Library of SVG icons with semantic search capability.

    Loads icons from icons.json and provides search functionality
    based on icon names and keywords.
    """

    def __init__(self, icons_path: Optional[str] = None):
        """
        Initialize the icon library.

        Args:
            icons_path: Path to icons.json file. If None, uses default location.
        """
        self._icons: Dict[str, IconDefinition] = {}
        self._categories: Dict[str, List[str]] = {}
        self._keyword_index: Dict[str, Set[str]] = {}

        # Load icons
        if icons_path is None:
            icons_path = os.path.join(
                os.path.dirname(__file__), "..", "data", "icons.json"
            )

        self._load_icons(icons_path)

    def _load_icons(self, path: str) -> None:
        """Load icons from JSON file."""
        if not os.path.exists(path):
            # No icons file - library will be empty
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return

        icons_data = data.get("icons", {})

        for icon_id, icon_data in icons_data.items():
            icon = IconDefinition.from_dict(icon_id, icon_data)
            self._icons[icon_id] = icon

            # Index by category
            category = icon.category
            if category not in self._categories:
                self._categories[category] = []
            self._categories[category].append(icon_id)

            # Index by keywords
            for keyword in icon.keywords:
                keyword_lower = keyword.lower()
                if keyword_lower not in self._keyword_index:
                    self._keyword_index[keyword_lower] = set()
                self._keyword_index[keyword_lower].add(icon_id)

            # Also index the icon name itself
            name_words = re.split(r'[_\s]+', icon_id.lower())
            for word in name_words:
                if word not in self._keyword_index:
                    self._keyword_index[word] = set()
                self._keyword_index[word].add(icon_id)

    @property
    def count(self) -> int:
        """Total number of icons in the library."""
        return len(self._icons)

    @property
    def categories(self) -> List[str]:
        """List of available categories."""
        return list(self._categories.keys())

    def get(self, icon_id: str) -> Optional[IconDefinition]:
        """
        Get an icon by its ID.

        Args:
            icon_id: Icon identifier (e.g., "database", "cloud")

        Returns:
            IconDefinition if found, None otherwise
        """
        return self._icons.get(icon_id)

    def get_by_category(self, category: str) -> List[IconDefinition]:
        """
        Get all icons in a category.

        Args:
            category: Category name (e.g., "technology", "business")

        Returns:
            List of IconDefinition objects
        """
        icon_ids = self._categories.get(category, [])
        return [self._icons[id] for id in icon_ids]

    def search(
        self,
        query: str,
        limit: int = 10,
        category: Optional[str] = None
    ) -> List[IconSearchResult]:
        """
        Search for icons by query string.

        Searches icon names and keywords. Returns results sorted by relevance.

        Args:
            query: Search query (can be multiple words)
            limit: Maximum number of results
            category: Optional category filter

        Returns:
            List of IconSearchResult objects sorted by relevance
        """
        query = query.lower().strip()
        if not query:
            return []

        # Split query into words
        query_words = re.split(r'\s+', query)

        # Track scores for each icon
        scores: Dict[str, Tuple[float, str]] = {}

        for word in query_words:
            # Exact name match (highest priority)
            if word in self._icons:
                icon = self._icons[word]
                if category is None or icon.category == category:
                    scores[word] = (1.0, "exact")

            # Keyword match
            if word in self._keyword_index:
                for icon_id in self._keyword_index[word]:
                    if category is not None and self._icons[icon_id].category != category:
                        continue

                    if icon_id not in scores:
                        scores[icon_id] = (0.8, "keyword")
                    else:
                        # Boost score for multiple matches
                        current_score, match_type = scores[icon_id]
                        scores[icon_id] = (min(1.0, current_score + 0.1), match_type)

            # Partial match in icon names
            for icon_id in self._icons:
                if category is not None and self._icons[icon_id].category != category:
                    continue

                if word in icon_id and icon_id not in scores:
                    scores[icon_id] = (0.5, "partial")
                elif word in icon_id and icon_id in scores:
                    current_score, match_type = scores[icon_id]
                    scores[icon_id] = (min(1.0, current_score + 0.05), match_type)

        # Sort by score (descending)
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x][0], reverse=True)

        # Build results
        results = []
        for icon_id in sorted_ids[:limit]:
            score, match_type = scores[icon_id]
            results.append(IconSearchResult(
                icon=self._icons[icon_id],
                score=score,
                match_type=match_type,
            ))

        return results

    def search_simple(
        self,
        query: str,
        limit: int = 10,
        category: Optional[str] = None
    ) -> List[str]:
        """
        Simple search returning just icon IDs.

        Args:
            query: Search query
            limit: Maximum number of results
            category: Optional category filter

        Returns:
            List of icon IDs
        """
        results = self.search(query, limit=limit, category=category)
        return [r.icon.id for r in results]

    def suggest_icon(self, concept: str) -> Optional[IconDefinition]:
        """
        Suggest the best icon for a concept.

        Args:
            concept: Concept or entity name (e.g., "User Authentication", "Cloud Storage")

        Returns:
            Best matching IconDefinition or None
        """
        results = self.search(concept, limit=1)
        if results:
            return results[0].icon
        return None

    def get_icon_for_entity(
        self,
        entity_label: str,
        entity_description: Optional[str] = None,
        icon_hint: Optional[str] = None
    ) -> Optional[IconDefinition]:
        """
        Get the best icon for an entity based on its label, description, and hint.

        Priority:
        1. Explicit icon_hint if valid
        2. Search by entity label
        3. Search by description keywords

        Args:
            entity_label: Entity display name
            entity_description: Optional longer description
            icon_hint: Optional explicit icon ID hint

        Returns:
            Best matching IconDefinition or None
        """
        # Try explicit hint first
        if icon_hint:
            icon = self.get(icon_hint)
            if icon:
                return icon
            # Hint might be a search term
            results = self.search(icon_hint, limit=1)
            if results:
                return results[0].icon

        # Search by label
        results = self.search(entity_label, limit=3)
        if results and results[0].score >= 0.5:
            return results[0].icon

        # Try description if provided
        if entity_description:
            results = self.search(entity_description, limit=1)
            if results and results[0].score >= 0.6:
                return results[0].icon

        return None

    def list_all(self) -> List[IconDefinition]:
        """Get all icons in the library."""
        return list(self._icons.values())

    def get_category_summary(self) -> Dict[str, int]:
        """Get count of icons per category."""
        return {cat: len(ids) for cat, ids in self._categories.items()}


# =============================================================================
# ICON RENDERING UTILITIES
# =============================================================================

def scale_svg_path(
    path: str,
    source_size: float,
    target_width: float,
    target_height: float,
    offset_x: float = 0,
    offset_y: float = 0
) -> str:
    """
    Scale an SVG path to fit within target dimensions.

    Args:
        path: SVG path data string
        source_size: Original viewBox size (assumes square)
        target_width: Target width
        target_height: Target height
        offset_x: X offset for positioning
        offset_y: Y offset for positioning

    Returns:
        Scaled SVG path string
    """
    # Calculate scale factor (maintain aspect ratio)
    scale = min(target_width / source_size, target_height / source_size)

    # Parse and transform path commands
    # This is a simplified transformer that handles common path commands
    result = []
    commands = re.findall(r'([A-Za-z])([^A-Za-z]*)', path)

    for cmd, args in commands:
        if not args.strip():
            result.append(cmd)
            continue

        # Parse numbers
        numbers = [float(n) for n in re.findall(r'-?\d+\.?\d*', args)]

        # Transform based on command type
        if cmd in 'MmLlTt':
            # Move, Line, Smooth quadratic - pairs of coordinates
            scaled = []
            for i in range(0, len(numbers), 2):
                if i + 1 < len(numbers):
                    x = numbers[i] * scale + offset_x
                    y = numbers[i + 1] * scale + offset_y
                    scaled.extend([x, y])
            result.append(f"{cmd}{' '.join(str(n) for n in scaled)}")

        elif cmd in 'HhVv':
            # Horizontal/Vertical lines - single coordinates
            scaled = [n * scale + (offset_x if cmd in 'Hh' else offset_y) for n in numbers]
            result.append(f"{cmd}{' '.join(str(n) for n in scaled)}")

        elif cmd in 'CcSs':
            # Cubic bezier, smooth cubic - sets of coordinates
            scaled = []
            for i in range(0, len(numbers), 2):
                if i + 1 < len(numbers):
                    x = numbers[i] * scale + offset_x
                    y = numbers[i + 1] * scale + offset_y
                    scaled.extend([x, y])
            result.append(f"{cmd}{' '.join(str(n) for n in scaled)}")

        elif cmd in 'QqTt':
            # Quadratic bezier - sets of coordinates
            scaled = []
            for i in range(0, len(numbers), 2):
                if i + 1 < len(numbers):
                    x = numbers[i] * scale + offset_x
                    y = numbers[i + 1] * scale + offset_y
                    scaled.extend([x, y])
            result.append(f"{cmd}{' '.join(str(n) for n in scaled)}")

        elif cmd in 'Aa':
            # Arc - special handling (rx ry x-axis-rotation large-arc sweep x y)
            if len(numbers) >= 7:
                scaled = [
                    numbers[0] * scale,  # rx
                    numbers[1] * scale,  # ry
                    numbers[2],          # x-axis-rotation (unchanged)
                    numbers[3],          # large-arc-flag (unchanged)
                    numbers[4],          # sweep-flag (unchanged)
                    numbers[5] * scale + offset_x,  # x
                    numbers[6] * scale + offset_y,  # y
                ]
                result.append(f"{cmd}{' '.join(str(n) for n in scaled)}")

        elif cmd in 'Zz':
            result.append(cmd)

        else:
            # Unknown command - pass through
            result.append(f"{cmd}{args}")

    return ''.join(result)


def icon_to_svg_element(
    icon: IconDefinition,
    x: float,
    y: float,
    size: float,
    fill_color: str = "#333333"
) -> str:
    """
    Generate SVG element string for an icon.

    Args:
        icon: IconDefinition to render
        x: X position
        y: Y position
        size: Icon size (width and height)
        fill_color: Fill color

    Returns:
        SVG path element string
    """
    # Get viewBox dimensions
    vb = icon.viewBox_values
    vb_width = vb[2]

    # Scale path to fit
    scaled_path = scale_svg_path(icon.path, vb_width, size, size, x, y)

    return f'<path d="{scaled_path}" fill="{fill_color}" />'


def icon_path_to_points(
    path: str,
    viewBox_size: float = 24,
    target_width: float = 1.0,
    target_height: float = 1.0
) -> List[Tuple[str, List[Tuple[float, float]]]]:
    """
    Convert SVG path to list of point segments for PPTX rendering.

    Returns a list of (command, points) tuples suitable for custGeom.

    Args:
        path: SVG path data
        viewBox_size: Source viewBox size
        target_width: Target width in inches
        target_height: Target height in inches

    Returns:
        List of (command, points) tuples
    """
    scale_x = target_width / viewBox_size
    scale_y = target_height / viewBox_size

    segments = []
    current_x, current_y = 0, 0
    start_x, start_y = 0, 0

    commands = re.findall(r'([A-Za-z])([^A-Za-z]*)', path)

    for cmd, args in commands:
        numbers = [float(n) for n in re.findall(r'-?\d+\.?\d*', args)]

        if cmd == 'M':
            # Absolute move
            for i in range(0, len(numbers), 2):
                if i + 1 < len(numbers):
                    x, y = numbers[i] * scale_x, numbers[i + 1] * scale_y
                    if i == 0:
                        segments.append(('moveTo', [(x, y)]))
                        start_x, start_y = x, y
                    else:
                        segments.append(('lineTo', [(x, y)]))
                    current_x, current_y = x, y

        elif cmd == 'm':
            # Relative move
            for i in range(0, len(numbers), 2):
                if i + 1 < len(numbers):
                    x = current_x + numbers[i] * scale_x
                    y = current_y + numbers[i + 1] * scale_y
                    if i == 0:
                        segments.append(('moveTo', [(x, y)]))
                        start_x, start_y = x, y
                    else:
                        segments.append(('lineTo', [(x, y)]))
                    current_x, current_y = x, y

        elif cmd == 'L':
            # Absolute line
            for i in range(0, len(numbers), 2):
                if i + 1 < len(numbers):
                    x, y = numbers[i] * scale_x, numbers[i + 1] * scale_y
                    segments.append(('lineTo', [(x, y)]))
                    current_x, current_y = x, y

        elif cmd == 'l':
            # Relative line
            for i in range(0, len(numbers), 2):
                if i + 1 < len(numbers):
                    x = current_x + numbers[i] * scale_x
                    y = current_y + numbers[i + 1] * scale_y
                    segments.append(('lineTo', [(x, y)]))
                    current_x, current_y = x, y

        elif cmd == 'H':
            # Absolute horizontal line
            for n in numbers:
                x = n * scale_x
                segments.append(('lineTo', [(x, current_y)]))
                current_x = x

        elif cmd == 'h':
            # Relative horizontal line
            for n in numbers:
                x = current_x + n * scale_x
                segments.append(('lineTo', [(x, current_y)]))
                current_x = x

        elif cmd == 'V':
            # Absolute vertical line
            for n in numbers:
                y = n * scale_y
                segments.append(('lineTo', [(current_x, y)]))
                current_y = y

        elif cmd == 'v':
            # Relative vertical line
            for n in numbers:
                y = current_y + n * scale_y
                segments.append(('lineTo', [(current_x, y)]))
                current_y = y

        elif cmd == 'C':
            # Absolute cubic bezier
            for i in range(0, len(numbers), 6):
                if i + 5 < len(numbers):
                    x1 = numbers[i] * scale_x
                    y1 = numbers[i + 1] * scale_y
                    x2 = numbers[i + 2] * scale_x
                    y2 = numbers[i + 3] * scale_y
                    x = numbers[i + 4] * scale_x
                    y = numbers[i + 5] * scale_y
                    segments.append(('cubicBezTo', [(x1, y1), (x2, y2), (x, y)]))
                    current_x, current_y = x, y

        elif cmd == 'c':
            # Relative cubic bezier
            for i in range(0, len(numbers), 6):
                if i + 5 < len(numbers):
                    x1 = current_x + numbers[i] * scale_x
                    y1 = current_y + numbers[i + 1] * scale_y
                    x2 = current_x + numbers[i + 2] * scale_x
                    y2 = current_y + numbers[i + 3] * scale_y
                    x = current_x + numbers[i + 4] * scale_x
                    y = current_y + numbers[i + 5] * scale_y
                    segments.append(('cubicBezTo', [(x1, y1), (x2, y2), (x, y)]))
                    current_x, current_y = x, y

        elif cmd in 'Ss':
            # Smooth cubic bezier - simplified handling
            # Would need to track previous control point for proper handling
            for i in range(0, len(numbers), 4):
                if i + 3 < len(numbers):
                    if cmd == 'S':
                        x2 = numbers[i] * scale_x
                        y2 = numbers[i + 1] * scale_y
                        x = numbers[i + 2] * scale_x
                        y = numbers[i + 3] * scale_y
                    else:
                        x2 = current_x + numbers[i] * scale_x
                        y2 = current_y + numbers[i + 1] * scale_y
                        x = current_x + numbers[i + 2] * scale_x
                        y = current_y + numbers[i + 3] * scale_y
                    # Use current point as first control point (simplified)
                    segments.append(('cubicBezTo', [(current_x, current_y), (x2, y2), (x, y)]))
                    current_x, current_y = x, y

        elif cmd in 'Zz':
            # Close path
            segments.append(('close', []))
            current_x, current_y = start_x, start_y

    return segments


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_library_instance: Optional[IconLibrary] = None


def get_icon_library() -> IconLibrary:
    """Get the singleton icon library instance."""
    global _library_instance
    if _library_instance is None:
        _library_instance = IconLibrary()
    return _library_instance


def reset_library() -> None:
    """Reset the singleton instance (for testing)."""
    global _library_instance
    _library_instance = None

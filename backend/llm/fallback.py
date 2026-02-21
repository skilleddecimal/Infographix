"""Fallback keyword-based parser when LLM is not available."""

import re
from typing import Any


class FallbackParser:
    """Keyword-based prompt parser.

    Uses pattern matching and heuristics to extract intent
    when LLM is not available.
    """

    # Keyword patterns for each archetype
    ARCHETYPE_KEYWORDS = {
        "funnel": [
            r"\bfunnel\b",
            r"\bconversion\b",
            r"\bsales\s+funnel\b",
            r"\bmarketing\s+funnel\b",
            r"\blead\s+funnel\b",
            r"\bpipeline\b",
        ],
        "pyramid": [
            r"\bpyramid\b",
            r"\bhierarchy\b",
            r"\bmaslow\b",
            r"\btier(ed|s)?\b",
            r"\blevel(s)?\b",
        ],
        "timeline": [
            r"\btimeline\b",
            r"\broadmap\b",
            r"\bmilestone(s)?\b",
            r"\bhistor(y|ical)\b",
            r"\bevolution\b",
            r"\bphase(s)?\b",
        ],
        "process": [
            r"\bprocess\b",
            r"\bworkflow\b",
            r"\bstep(s)?\b",
            r"\bprocedure\b",
            r"\bhow\s+to\b",
            r"\bsequence\b",
        ],
        "cycle": [
            r"\bcycle\b",
            r"\bcircular\b",
            r"\blifecycle\b",
            r"\biterative\b",
            r"\bcontinuous\b",
            r"\bloop\b",
        ],
        "hub_spoke": [
            r"\bhub\s*(and|&)?\s*spoke\b",
            r"\bcentral\s+\w+\s+(with|and)\b",
            r"\bradiat(e|ing)\b",
        ],
        "matrix": [
            r"\bmatrix\b",
            r"\b2x2\b",
            r"\bquadrant(s)?\b",
            r"\bgrid\b",
        ],
        "comparison": [
            r"\bcompar(e|ison)\b",
            r"\bvs\.?\b",
            r"\bversus\b",
            r"\bside\s*(-|\s)*by\s*(-|\s)*side\b",
            r"\bbefore\s*(and|&)?\s*after\b",
        ],
        "org_chart": [
            r"\borg(anization(al)?|)?\s*chart\b",
            r"\bteam\s+structure\b",
            r"\breporting\s+structure\b",
        ],
        "venn": [
            r"\bvenn\b",
            r"\boverlap(ping)?\b",
            r"\bintersect(ion)?\b",
            r"\bcircles?\s+diagram\b",
        ],
        "gauge": [
            r"\bgauge\b",
            r"\bkpi\b",
            r"\bprogress\s*(meter|bar)?\b",
            r"\bdashboard\b",
            r"\bspeedometer\b",
        ],
        "bullet_list": [
            r"\blist\b",
            r"\bbullet(s|ed)?\b",
            r"\bpoints?\b",
            r"\bitems?\b",
        ],
        "flowchart": [
            r"\bflowchart\b",
            r"\bdecision\s+tree\b",
            r"\bbranching\b",
            r"\bif.*then\b",
        ],
        "target": [
            r"\btarget\b",
            r"\bbullseye\b",
            r"\bconcentric\b",
            r"\bgoal(s)?\b",
        ],
    }

    # Word-to-number mapping
    WORD_NUMBERS = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12,
    }

    # Orientation keywords
    ORIENTATION_KEYWORDS = {
        "horizontal": [r"\bhorizontal\b", r"\bleft\s+to\s+right\b", r"\bwide\b"],
        "vertical": [r"\bvertical\b", r"\btop\s+to\s+bottom\b", r"\btall\b"],
        "radial": [r"\bradial\b", r"\bcircular\b", r"\bround\b"],
    }

    # Style keywords
    STYLE_KEYWORDS = {
        "modern": [r"\bmodern\b", r"\bclean\b", r"\bminimal(ist)?\b"],
        "corporate": [r"\bcorporate\b", r"\bprofessional\b", r"\bbusiness\b"],
        "playful": [r"\bplayful\b", r"\bfun\b", r"\bcolorful\b"],
        "elegant": [r"\belegant\b", r"\bsophisticated\b", r"\bluxury\b"],
        "tech": [r"\btech\b", r"\bdigital\b", r"\bsoftware\b"],
    }

    def parse(self, prompt: str) -> dict[str, Any]:
        """Parse prompt into structured intent.

        Args:
            prompt: User prompt.

        Returns:
            Parsed intent dictionary.
        """
        prompt_lower = prompt.lower()

        # Classify archetype
        classification = self.classify(prompt_lower)

        # Extract count
        count = self._extract_count(prompt_lower)

        # Extract orientation
        orientation = self._extract_orientation(prompt_lower)

        # Extract style hints
        style_hints = self._extract_style_hints(prompt_lower)

        # Extract items
        items = self.extract_items(prompt, classification["archetype"])

        return {
            "archetype": classification["archetype"],
            "confidence": classification["confidence"],
            "item_count": count,
            "orientation": orientation,
            "style_hints": style_hints,
            "items": items,
            "parameters": {},
        }

    def classify(self, prompt: str) -> dict[str, Any]:
        """Classify prompt into archetype.

        Args:
            prompt: User prompt (lowercase).

        Returns:
            Dict with archetype and confidence.
        """
        prompt_lower = prompt.lower()
        scores = {}

        for archetype, patterns in self.ARCHETYPE_KEYWORDS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, prompt_lower)
                score += len(matches)

            if score > 0:
                scores[archetype] = score

        if not scores:
            # Default to process
            return {"archetype": "process", "confidence": 0.3}

        # Get highest scoring archetype
        best_archetype = max(scores, key=scores.get)
        max_score = scores[best_archetype]

        # Calculate confidence based on match strength
        confidence = min(0.9, 0.5 + 0.1 * max_score)

        return {"archetype": best_archetype, "confidence": confidence}

    def _extract_count(self, prompt: str) -> int | None:
        """Extract item count from prompt.

        Args:
            prompt: User prompt.

        Returns:
            Count if found, None otherwise.
        """
        # Try numeric patterns
        patterns = [
            r"(\d+)\s*(step|stage|phase|level|item|point|milestone)s?",
            r"(\d+)\s*-\s*(step|stage|phase)",
            r"with\s+(\d+)\s+(step|stage|phase|level|item)s?",
        ]

        for pattern in patterns:
            match = re.search(pattern, prompt)
            if match:
                return int(match.group(1))

        # Try word numbers
        for word, num in self.WORD_NUMBERS.items():
            pattern = rf"\b{word}\s+(step|stage|phase|level|item|point|milestone)s?"
            if re.search(pattern, prompt):
                return num

        return None

    def _extract_orientation(self, prompt: str) -> str | None:
        """Extract orientation from prompt.

        Args:
            prompt: User prompt.

        Returns:
            Orientation if found.
        """
        for orientation, patterns in self.ORIENTATION_KEYWORDS.items():
            for pattern in patterns:
                if re.search(pattern, prompt):
                    return orientation
        return None

    def _extract_style_hints(self, prompt: str) -> list[str]:
        """Extract style hints from prompt.

        Args:
            prompt: User prompt.

        Returns:
            List of style keywords found.
        """
        hints = []
        for style, patterns in self.STYLE_KEYWORDS.items():
            for pattern in patterns:
                if re.search(pattern, prompt):
                    hints.append(style)
                    break
        return hints

    def extract_items(
        self,
        prompt: str,
        archetype: str,
    ) -> list[dict[str, Any]]:
        """Extract content items from prompt.

        Args:
            prompt: User prompt.
            archetype: Detected archetype.

        Returns:
            List of extracted items.
        """
        items = []

        # Try to find quoted strings as item names
        quoted = re.findall(r'"([^"]+)"', prompt)
        if quoted:
            for title in quoted:
                items.append({"title": title})
            return items

        # Try to find comma-separated lists
        # Pattern: "stages: A, B, C" or "steps are: A, B, C"
        list_patterns = [
            r"(?:stage|step|phase|item|level)s?[:\s]+(.+?)(?:\.|$)",
            r"(?:include|including|like|such as)[:\s]+(.+?)(?:\.|$)",
        ]

        for pattern in list_patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                list_text = match.group(1)
                # Split by commas or "and"
                parts = re.split(r",\s*|\s+and\s+", list_text)
                for part in parts:
                    part = part.strip()
                    if part and len(part) > 1:
                        items.append({"title": part})
                if items:
                    return items

        # Try numbered lists
        numbered = re.findall(r"(?:^|\s)(\d+)[.\)]\s*([^,\d]+)", prompt)
        if numbered:
            for _, title in numbered:
                title = title.strip()
                if title:
                    items.append({"title": title})
            return items

        return items

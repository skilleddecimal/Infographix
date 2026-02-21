"""Prompt parser using LLM for natural language understanding."""

from dataclasses import dataclass, field
from typing import Any

from backend.llm.client import LLMClient, LLMConfig
from backend.llm.fallback import FallbackParser


@dataclass
class ParsedIntent:
    """Parsed intent from user prompt."""

    # Diagram type
    archetype: str

    # Classification confidence
    confidence: float

    # Number of items (stages, steps, etc.)
    item_count: int | None = None

    # Orientation preference
    orientation: str | None = None

    # Style hints extracted from prompt
    style_hints: list[str] = field(default_factory=list)

    # Extracted content items
    items: list[dict[str, Any]] = field(default_factory=list)

    # Additional parameters
    parameters: dict[str, Any] = field(default_factory=dict)

    # Whether LLM was used
    used_llm: bool = False

    # Raw LLM response for debugging
    raw_response: dict[str, Any] | None = None


class PromptParser:
    """Parse user prompts into structured intents.

    Uses LLM for natural language understanding when available,
    falls back to keyword-based parsing otherwise.
    """

    def __init__(
        self,
        llm_config: LLMConfig | None = None,
        use_llm: bool = True,
    ):
        """Initialize prompt parser.

        Args:
            llm_config: Configuration for LLM client.
            use_llm: Whether to use LLM (vs fallback only).
        """
        self.llm_config = llm_config or LLMConfig()
        self.use_llm = use_llm

        self._llm_client = None
        self._fallback_parser = FallbackParser()

    @property
    def llm_client(self) -> LLMClient:
        """Get or create LLM client."""
        if self._llm_client is None:
            self._llm_client = LLMClient(self.llm_config)
        return self._llm_client

    def parse(self, prompt: str) -> ParsedIntent:
        """Parse user prompt into structured intent.

        Args:
            prompt: User's natural language prompt.

        Returns:
            ParsedIntent with archetype and parameters.
        """
        # Try LLM first if enabled
        if self.use_llm:
            try:
                return self._parse_with_llm(prompt)
            except Exception:
                # Fall through to fallback
                pass

        # Use fallback parser
        return self._parse_with_fallback(prompt)

    def _parse_with_llm(self, prompt: str) -> ParsedIntent:
        """Parse using LLM.

        Args:
            prompt: User prompt.

        Returns:
            ParsedIntent from LLM.
        """
        # Extract intent
        intent_response = self.llm_client.extract_intent(prompt)

        archetype = intent_response.get("archetype", "process")
        confidence = intent_response.get("confidence", 0.8)

        # Extract entities for the detected archetype
        entities_response = self.llm_client.extract_entities(prompt, archetype)

        items = entities_response.get("items", [])
        count = entities_response.get("count")
        if not count and items:
            count = len(items)

        return ParsedIntent(
            archetype=archetype,
            confidence=confidence,
            item_count=count or intent_response.get("item_count"),
            orientation=intent_response.get("orientation"),
            style_hints=intent_response.get("style_hints", []),
            items=items,
            parameters={
                "direction": entities_response.get("direction"),
                **entities_response.get("additional_info", {}),
            },
            used_llm=True,
            raw_response={
                "intent": intent_response,
                "entities": entities_response,
            },
        )

    def _parse_with_fallback(self, prompt: str) -> ParsedIntent:
        """Parse using fallback keyword-based parser.

        Args:
            prompt: User prompt.

        Returns:
            ParsedIntent from fallback.
        """
        result = self._fallback_parser.parse(prompt)

        return ParsedIntent(
            archetype=result["archetype"],
            confidence=result["confidence"],
            item_count=result.get("item_count"),
            orientation=result.get("orientation"),
            style_hints=result.get("style_hints", []),
            items=result.get("items", []),
            parameters=result.get("parameters", {}),
            used_llm=False,
        )

    def is_llm_available(self) -> bool:
        """Check if LLM is available.

        Returns:
            True if LLM can be used.
        """
        try:
            return self.llm_client.is_available()
        except Exception:
            return False

    def extract_content(
        self,
        prompt: str,
        archetype: str,
    ) -> list[dict[str, Any]]:
        """Extract content items from prompt.

        Args:
            prompt: User prompt.
            archetype: Detected archetype.

        Returns:
            List of content items.
        """
        if self.use_llm and self.is_llm_available():
            try:
                entities = self.llm_client.extract_entities(prompt, archetype)
                return entities.get("items", [])
            except Exception:
                pass

        return self._fallback_parser.extract_items(prompt, archetype)

    def classify(self, prompt: str) -> tuple[str, float]:
        """Classify prompt into archetype.

        Args:
            prompt: User prompt.

        Returns:
            Tuple of (archetype, confidence).
        """
        if self.use_llm and self.is_llm_available():
            try:
                return self.llm_client.classify_archetype(prompt)
            except Exception:
                pass

        result = self._fallback_parser.classify(prompt)
        return result["archetype"], result["confidence"]

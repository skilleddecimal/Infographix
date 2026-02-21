"""LLM API client for prompt decoding."""

import json
import os
from dataclasses import dataclass
from typing import Any, Literal

from backend.llm.prompts import INTENT_EXTRACTION_PROMPT, ENTITY_EXTRACTION_PROMPT


@dataclass
class LLMConfig:
    """Configuration for LLM client."""

    provider: Literal["anthropic", "openai"] = "anthropic"
    model: str = "claude-3-haiku-20240307"
    max_tokens: int = 1024
    temperature: float = 0.3
    timeout: float = 30.0


class LLMClient:
    """Client for interacting with LLM APIs.

    Supports Anthropic Claude and OpenAI GPT models.
    Only used for natural language understanding, not generation.
    """

    def __init__(self, config: LLMConfig | None = None):
        """Initialize LLM client.

        Args:
            config: LLM configuration.
        """
        self.config = config or LLMConfig()
        self._client = None

    @property
    def client(self):
        """Lazy-load the API client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self):
        """Create the appropriate API client."""
        if self.config.provider == "anthropic":
            try:
                from anthropic import Anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY not set")
                return Anthropic(api_key=api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")

        elif self.config.provider == "openai":
            try:
                from openai import OpenAI
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not set")
                return OpenAI(api_key=api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")

        raise ValueError(f"Unknown provider: {self.config.provider}")

    def extract_intent(self, prompt: str) -> dict[str, Any]:
        """Extract intent from user prompt.

        Args:
            prompt: User's natural language prompt.

        Returns:
            Structured intent with archetype and parameters.
        """
        system_prompt = INTENT_EXTRACTION_PROMPT

        response = self._call_api(
            system_prompt=system_prompt,
            user_prompt=prompt,
        )

        return self._parse_json_response(response)

    def extract_entities(self, prompt: str, archetype: str) -> dict[str, Any]:
        """Extract entities from prompt for a specific archetype.

        Args:
            prompt: User's prompt.
            archetype: Detected archetype.

        Returns:
            Extracted entities (stage names, counts, etc.).
        """
        system_prompt = ENTITY_EXTRACTION_PROMPT.format(archetype=archetype)

        response = self._call_api(
            system_prompt=system_prompt,
            user_prompt=prompt,
        )

        return self._parse_json_response(response)

    def classify_archetype(self, prompt: str) -> tuple[str, float]:
        """Classify prompt into archetype.

        Args:
            prompt: User's prompt.

        Returns:
            Tuple of (archetype, confidence).
        """
        intent = self.extract_intent(prompt)
        archetype = intent.get("archetype", "process")
        confidence = intent.get("confidence", 0.8)
        return archetype, confidence

    def _call_api(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Call the LLM API.

        Args:
            system_prompt: System/instruction prompt.
            user_prompt: User's input.

        Returns:
            Model response text.
        """
        if self.config.provider == "anthropic":
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
            )
            return response.content[0].text

        elif self.config.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content

        raise ValueError(f"Unknown provider: {self.config.provider}")

    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """Parse JSON from LLM response.

        Args:
            response: Raw response text.

        Returns:
            Parsed JSON object.
        """
        # Try to find JSON in the response
        response = response.strip()

        # Check for JSON code block
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                response = response[start:end].strip()

        # Try direct JSON parsing
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON object boundaries
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(response[start:end])
                except json.JSONDecodeError:
                    pass

        # Return empty dict on failure
        return {}

    def is_available(self) -> bool:
        """Check if LLM client is available.

        Returns:
            True if API key is set and client can be created.
        """
        try:
            _ = self.client
            return True
        except (ImportError, ValueError):
            return False

# InfographAI — AI-Powered Corporate Infographic Generator

## Project Overview

Build a global SaaS web application that generates structurally intelligent, editable corporate infographics from natural language prompts. The tool understands diagram archetypes (marketectures, process flows, tech stacks, etc.) and produces clean, brand-themed, editable output — not generic image-based infographics.

The core value proposition: users anywhere in the world describe what they need in plain language (multilingual), optionally provide brand context (colors, logos, templates), and receive a structurally correct, editable infographic they can download as PPTX or PNG.

**Target scale**: Global end users across all time zones. Architecture must support millions of generations per month with sub-15-second response times, multi-provider LLM redundancy, tiered cost optimization, and SaaS billing infrastructure.

---

## Tech Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **LLM Gateway**: LiteLLM for unified multi-provider interface (Claude, GPT, Gemini)
- **LLM Providers**: Anthropic Claude Sonnet 4.5 (primary reasoning), OpenAI GPT-4o mini (fast/cheap tier), Google Gemini 2.5 Pro (vision analysis), Claude Haiku 4.5 (medium tier)
- **PPTX Generation**: python-pptx for native editable PowerPoint output
- **SVG Generation**: svgwrite for SVG output + CairoSVG for PNG rasterization
- **Image Processing**: Pillow for logo handling and PNG export
- **Caching**: Redis for response caching, prompt caching, and rate limit state
- **Task Queue**: Celery + Redis for async generation and batch processing
- **Database**: PostgreSQL for user accounts, usage metering, and generation history
- **ORM**: SQLAlchemy + Alembic for migrations
- **Auth**: JWT tokens + OAuth2 (Google, Microsoft SSO for enterprise)
- **Internationalization**: text measurement must support CJK, RTL (Arabic/Hebrew), and Latin scripts

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Canvas Editor**: Fabric.js for in-browser editing of generated infographics
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **HTTP Client**: Axios
- **i18n**: react-i18next for UI translations

### Infrastructure
- **Container Orchestration**: Docker Compose (dev), Kubernetes (production)
- **Cloud**: AWS (primary) or GCP — multi-region deployment for global latency
- **CDN**: CloudFront or Cloudflare for static assets and generated file delivery
- **File Storage**: S3 for generated PPTX/PNG/SVG files with TTL-based cleanup
- **Monitoring**: Prometheus + Grafana for LLM cost tracking, latency, and usage metrics
- **Environment Variables**: .env file for API keys and configuration

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Global CDN (CloudFront/Cloudflare)             │
└──────────────────────────┬───────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────────┐
│                      React Frontend                               │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐              │
│  │ Prompt UI │  │ Brief Review │  │ Fabric.js     │  i18n        │
│  │ + Inputs  │  │ Confirmation │  │ Editor Canvas │  (multi-lang)│
│  └─────┬─────┘  └──────┬───────┘  └───────┬───────┘              │
└────────┼───────────────┼───────────────────┼─────────────────────┘
         │               │                   │
         ▼               ▼                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (multi-region)                   │
│                                                                    │
│  ┌──────────────┐  ┌────────────┐  ┌──────────────┐              │
│  │ /api/analyze  │  │ /api/gen   │  │ /api/export  │              │
│  │ (Brief Gen)   │  │ (Render)   │  │ (PPTX/PNG)   │              │
│  └──────┬────────┘  └─────┬──────┘  └──────┬───────┘              │
│         │                 │                 │                      │
│  ┌──────▼─────────────────▼─────────────────▼──────┐              │
│  │              Core Engine                         │              │
│  │  ┌─────────────────────────────────────────────┐│              │
│  │  │          LLM Gateway (LiteLLM)              ││              │
│  │  │  ┌─────────┐ ┌─────────┐ ┌──────────────┐  ││              │
│  │  │  │ Claude  │ │ GPT-4o  │ │ Gemini 2.5   │  ││              │
│  │  │  │ Sonnet  │ │ mini    │ │ Pro          │  ││              │
│  │  │  │(complex)│ │(simple) │ │(vision)      │  ││              │
│  │  │  └─────────┘ └─────────┘ └──────────────┘  ││              │
│  │  │  Tiered routing · Fallback · Cost tracking  ││              │
│  │  └─────────────────────────────────────────────┘│              │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────────┐│              │
│  │  │ Layout Eng │ │ Brand/Theme│ │ Text Measure ││              │
│  │  │ (Spatial)  │ │ Engine     │ │ (i18n-aware) ││              │
│  │  └────────────┘ └────────────┘ └──────────────┘│              │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────────┐│              │
│  │  │ Archetype  │ │ PPTX Render│ │ SVG/PNG      ││              │
│  │  │ Library    │ │ Engine     │ │ Render       ││              │
│  │  └────────────┘ └────────────┘ └──────────────┘│              │
│  └─────────────────────────────────────────────────┘              │
│                                                                    │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐                │
│  │ Usage Meter│  │ Auth/JWT   │  │ Rate Limiter │                │
│  │ (billing)  │  │ + OAuth    │  │ (per-user)   │                │
│  └──────┬─────┘  └────────────┘  └──────────────┘                │
└─────────┼────────────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────────────────┐
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐               │
│  │ PostgreSQL │  │ Redis      │  │ S3 / Object  │               │
│  │ (users,    │  │ (cache,    │  │ Storage      │               │
│  │  metering, │  │  sessions, │  │ (generated   │               │
│  │  history)  │  │  rate lim) │  │  files + CDN)│               │
│  └────────────┘  └────────────┘  └──────────────┘               │
└──────────────────────────────────────────────────────────────────┘
```

---

## Technical Process Flow — End to End

This section documents exactly what happens at every step, from user keystroke to downloaded PPTX file. Every developer and AI assistant working on this project should understand this flow completely.

```
USER INPUT                    BACKEND PROCESSING                           OUTPUT
─────────                    ──────────────────                           ──────

┌──────────────┐    POST /api/analyze    ┌─────────────────────┐
│ User types   │ ──────────────────────► │ 1. INPUT PROCESSING │
│ prompt +     │    (multipart form)     │                     │
│ colors +     │                         │ • Parse prompt text  │
│ logo +       │                         │ • Extract hex colors │
│ sample img   │                         │ • Process logo       │
│ + diagram    │                         │   (Pillow: extract   │
│   type       │                         │    dominant colors)  │
└──────────────┘                         │ • Process sample img │
                                         │   (if provided)      │
                                         │ • Process template   │
                                         │   PPTX (extract      │
                                         │   theme colors/fonts)│
                                         └──────────┬──────────┘
                                                    │
                                                    ▼
                                         ┌─────────────────────┐
                                         │ 2. LLM REASONING    │
                                         │   (llm_reasoning.py) │
                                         │                     │
                                         │ Build Claude prompt: │
                                         │ • System prompt with │
                                         │   archetype defs     │
                                         │ • User's prompt text │
                                         │ • Extracted colors   │
                                         │ • Brand preset data  │
                                         │   (if brand detected)│
                                         │ • Sample image       │
                                         │   (Claude Vision)    │
                                         │                     │
                                         │ Claude returns JSON: │
                                         │  InfographBrief      │
                                         │  {                   │
                                         │   diagram_type,      │
                                         │   entities[],        │
                                         │   layers[],          │
                                         │   connections[],     │
                                         │   theme              │
                                         │  }                   │
                                         └──────────┬──────────┘
                                                    │
                              ◄─────────────────────┘
     ┌──────────────┐         (returns InfographBrief)
     │ User reviews │ ◄──────────────────────────────
     │ brief:       │
     │ • Entities   │
     │ • Layout     │    User edits or confirms
     │ • Colors     │ ──────────────────────────────►
     └──────────────┘    POST /api/generate
                         (sends confirmed brief)
                                                    │
                                                    ▼
                                         ┌─────────────────────┐
                                         │ 3. TEXT MEASUREMENT  │
                                         │  (text_measure.py)   │
                                         │                     │
                                         │ For EVERY entity:    │
                                         │ • Call fit_text_to_  │
                                         │   width() with label │
                                         │ • Determine:         │
                                         │   - Font size (pt)   │
                                         │   - Line breaks      │
                                         │   - Required height  │
                                         │ • Store as           │
                                         │   PositionedText     │
                                         │                     │
                                         │ This MUST happen     │
                                         │ BEFORE layout grid   │
                                         │ computation so block │
                                         │ heights adapt to     │
                                         │ text content.        │
                                         └──────────┬──────────┘
                                                    │
                                                    ▼
                                         ┌─────────────────────┐
                                         │ 4. LAYOUT ENGINE     │
                                         │  (layout_engine.py)  │
                                         │                     │
                                         │ a. Select archetype  │
                                         │    layout strategy   │
                                         │    (marketecture/    │
                                         │     flow/stack/etc)  │
                                         │                     │
                                         │ b. Compute grid:     │
                                         │    • Row/col count   │
                                         │    • Cell positions  │
                                         │    • Gutter spacing  │
                                         │    • Row height      │
                                         │      proportions     │
                                         │                     │
                                         │ c. Place entities:   │
                                         │    • Center blocks   │
                                         │      in grid cells   │
                                         │    • Adjust block    │
                                         │      height to fit   │
                                         │      measured text   │
                                         │    • Handle cross-   │
                                         │      cutting bands   │
                                         │                     │
                                         │ d. Compute connectors│
                                         │    • Start/end pts   │
                                         │      on shape edges  │
                                         │    • Route paths     │
                                         │                     │
                                         │ e. Apply theme:      │
                                         │    • Primary color   │
                                         │      → emphasis      │
                                         │    • Secondary →     │
                                         │      normal blocks   │
                                         │    • Accent →        │
                                         │      highlights      │
                                         │    • Background      │
                                         │                     │
                                         │ OUTPUT:              │
                                         │  PositionedLayout    │
                                         │  {                   │
                                         │   elements[]: each   │
                                         │     has x,y,w,h in   │
                                         │     INCHES + text +  │
                                         │     colors           │
                                         │   connectors[]:      │
                                         │     start/end pts    │
                                         │   title, subtitle    │
                                         │  }                   │
                                         └──────────┬──────────┘
                                                    │
                                         ┌──────────┴──────────┐
                                         │                     │
                                    ┌────▼─────┐        ┌─────▼──────┐
                                    │ 5a. PPTX │        │ 5b. SVG    │
                                    │ RENDERER │        │ RENDERER   │
                                    │          │        │            │
                                    │ For each │        │ For each   │
                                    │ element: │        │ element:   │
                                    │ • Convert│        │ • Write    │
                                    │   inches │        │   <rect>,  │
                                    │   to EMU │        │   <text>,  │
                                    │ • Create │        │   <line>   │
                                    │   PPTX   │        │   tags     │
                                    │   shape  │        │ • Inline   │
                                    │ • Set    │        │   styles   │
                                    │   fill,  │        │ • Semantic │
                                    │   text,  │        │   IDs for  │
                                    │   border │        │   Fabric   │
                                    │ • NO     │        │            │
                                    │   position│       │ OUTPUT:    │
                                    │   math   │        │ SVG string │
                                    │   here!  │        │ for browser│
                                    │          │        │ preview    │
                                    │ OUTPUT:  │        └────────────┘
                                    │ .pptx    │
                                    │ file     │
                                    └────┬─────┘
                                         │
                              ◄──────────┘
     ┌──────────────┐    (returns SVG preview +
     │ User sees    │     download URLs)
     │ preview in   │ ◄──────────────────────────────
     │ browser      │
     │              │
     │ Options:     │
     │ • Download   │────► GET /api/download/{id}.pptx ──► .pptx file
     │   PPTX       │
     │ • Download   │────► GET /api/download/{id}.png  ──► .png file
     │   PNG         │
     │ • Edit in    │────► Fabric.js canvas loads SVG
     │   browser    │      User edits shapes/text/colors
     │              │      POST /api/export (canvas JSON)
     │              │      ──► Re-render to PPTX/PNG
     └──────────────┘
```

### Detailed Step Breakdown:

**Step 1 — Input Processing (50-200ms)**
Happens in the API route handler. Parse the multipart form, validate inputs. If a logo is uploaded, use Pillow to resize it (max 500x500) and run k-means color extraction (k=5) to identify dominant colors. If a PPTX template is uploaded, use python-pptx to read the slide master's color scheme and font theme. If a sample image is uploaded, hold it in memory for passing to Claude Vision in step 2. Normalize all hex colors to 6-digit lowercase format.

**Step 2 — LLM Reasoning (2-5 seconds)**
Single Claude API call with structured output. The system prompt encodes archetype definitions and design rules. User content includes: the prompt, detected/provided colors, brand context, and optionally the sample image (as vision input). Claude returns a JSON InfographBrief. Validate the JSON against the Pydantic schema. If validation fails, retry once with an error correction prompt. Total budget: max 2 retries.

**Step 3 — Text Measurement (50-100ms)**
Iterate over every entity in the brief. For each entity's label (and optional description), call fit_text_to_width() to determine the optimal font size and line wrapping given the estimated block width. The estimated block width comes from: content_width / max_entities_per_row. Store results as PositionedText objects attached to each entity. This step MUST complete before step 4 begins because block heights depend on text measurement results.

**Step 4 — Layout Computation (10-50ms)**
Pure math, no I/O. Select the archetype strategy based on diagram_type. Compute the grid. Place entities into grid cells with centered positioning. Adjust block heights based on text measurement results from step 3. Compute connector start/end points based on placed block positions. Apply the theme color mapping (which entities get primary vs secondary vs accent colors). Output a complete PositionedLayout where every element has absolute inch-based coordinates.

**Step 5a — PPTX Rendering (100-300ms)**
Iterate over PositionedLayout.elements. For each element, convert inches to EMUs and create the appropriate python-pptx shape. Set fill, border, text, and font properties from the PositionedElement data. No position computation happens here — just mechanical translation from the layout engine's output to python-pptx API calls. Save to disk.

**Step 5b — SVG Rendering (50-100ms)**
Iterate over the same PositionedLayout. For each element, write SVG tags with inline styles and semantic IDs. The SVG uses inch-based coordinates scaled to a viewBox. This SVG is returned to the frontend for browser preview and Fabric.js loading.

**Total generation time: 3-6 seconds** (dominated by the Claude API call in step 2).

### Data Flow Summary:

```
UserPrompt ──► InfographBrief ──► PositionedText[] ──► PositionedLayout ──► PPTX file
                 (from Claude)     (text measurement)    (layout engine)      (renderer)
                                                              │
                                                              └──► SVG string
                                                                   (renderer)
                                                                      │
                                                                      └──► Fabric.js JSON
                                                                           (frontend)
```

### Critical Rule — Separation of Concerns:
- **llm_gateway.py** — ONLY talks to LLM providers via LiteLLM. ONLY returns LLMResponse. Handles routing, fallback, caching, cost tracking. No other module imports provider SDKs.
- **complexity_classifier.py** — ONLY classifies prompt complexity. Returns a ModelTier. Never calls LLMs.
- **llm_reasoning.py** — ONLY builds prompts and parses InfographBrief from LLM responses. Calls llm_gateway.complete(). Never imports anthropic/openai/google SDKs.
- **text_measure.py** — ONLY measures text. Never creates shapes. Never calls LLMs.
- **layout_engine.py** — ONLY computes positions. Never talks to LLMs, never creates PPTX shapes.
- **pptx_renderer.py** — ONLY creates PPTX shapes from PositionedLayout. Never computes positions. Never talks to LLMs.
- **svg_renderer.py** — ONLY creates SVG from PositionedLayout. Same rules.
- **metering.py** — ONLY tracks usage and enforces limits. Never generates content.
- **cache.py** — ONLY manages cache reads/writes. Never generates content.

If any module violates these boundaries, the system becomes fragile and unmaintainable.

---

## Global Scale Architecture

This section covers the infrastructure and patterns required to serve InfographAI as a global SaaS product with multi-provider LLM support, cost optimization, multilingual generation, and usage-based billing.

### LLM Gateway (llm_gateway.py)

The LLM Gateway is the abstraction layer that prevents vendor lock-in and enables intelligent model routing. No module in the system should ever import an LLM provider SDK directly — all LLM calls go through the gateway.

**Implementation using LiteLLM:**

```python
# llm_gateway.py — EVERY LLM call goes through here. No exceptions.

import litellm
import hashlib
import json
import redis
from typing import Optional
from dataclasses import dataclass
from enum import Enum

class ModelTier(Enum):
    FAST = "fast"       # Simple diagrams, cheap models
    STANDARD = "standard"  # Medium complexity
    PREMIUM = "premium"    # Complex reasoning
    VISION = "vision"      # Image analysis

# Model mapping — change these without touching any other code
MODEL_MAP = {
    ModelTier.FAST: [
        "gpt-4o-mini",                    # $0.15/$0.60 per M — primary fast
        "claude-haiku-4-5-20251001",      # $1/$5 per M — fallback fast
        "gemini/gemini-2.5-flash",        # $0.15/$0.60 per M — fallback fast
    ],
    ModelTier.STANDARD: [
        "claude-haiku-4-5-20251001",      # $1/$5 per M — primary standard
        "gpt-4o",                          # $2.50/$10 per M — fallback standard
        "gemini/gemini-2.5-pro",          # $1.25/$10 per M — fallback standard
    ],
    ModelTier.PREMIUM: [
        "claude-sonnet-4-5-20250929",     # $3/$15 per M — primary premium
        "gpt-4o",                          # $2.50/$10 per M — fallback premium
        "gemini/gemini-3-pro-preview",    # $2/$12 per M — fallback premium
    ],
    ModelTier.VISION: [
        "gemini/gemini-2.5-pro",          # Best multimodal — primary vision
        "claude-sonnet-4-5-20250929",     # Good vision — fallback
        "gpt-4o",                          # Acceptable vision — fallback
    ],
}

@dataclass
class LLMResponse:
    content: str                # Raw response text
    model_used: str             # Actual model that served the request
    input_tokens: int           # For cost tracking
    output_tokens: int          # For cost tracking
    cost_usd: float             # Estimated cost of this call
    latency_ms: int             # Response time
    cache_hit: bool = False     # Whether served from cache

class LLMGateway:
    def __init__(self, redis_client: redis.Redis, cache_ttl_seconds: int = 3600):
        self.redis = redis_client
        self.cache_ttl = cache_ttl_seconds

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        tier: ModelTier = ModelTier.STANDARD,
        response_format: Optional[dict] = None,  # {"type": "json_object"} for JSON mode
        images: Optional[list] = None,  # Base64 images for vision
        temperature: float = 0.3,
        max_tokens: int = 4096,
        skip_cache: bool = False,
    ) -> LLMResponse:
        """
        Send a completion request through the gateway.
        Handles: caching, model selection, fallback, cost tracking.
        """

        # 1. Check cache first (skip for vision requests)
        if not skip_cache and not images:
            cache_key = self._cache_key(system_prompt, user_prompt, tier)
            cached = self.redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                return LLMResponse(**data, cache_hit=True)

        # 2. Try models in priority order with fallback
        models = MODEL_MAP[tier]
        last_error = None

        for model in models:
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": self._build_user_content(user_prompt, images)},
                ]

                response = await litellm.acompletion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )

                result = LLMResponse(
                    content=response.choices[0].message.content,
                    model_used=model,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    cost_usd=litellm.completion_cost(response),
                    latency_ms=int(response._response_ms) if hasattr(response, '_response_ms') else 0,
                )

                # 3. Cache successful responses
                if not skip_cache and not images:
                    self.redis.setex(
                        cache_key,
                        self.cache_ttl,
                        json.dumps({
                            'content': result.content,
                            'model_used': result.model_used,
                            'input_tokens': result.input_tokens,
                            'output_tokens': result.output_tokens,
                            'cost_usd': result.cost_usd,
                            'latency_ms': result.latency_ms,
                        })
                    )

                # 4. Track cost in Redis for metering
                self._track_cost(result)

                return result

            except Exception as e:
                last_error = e
                continue  # Try next model in fallback chain

        raise RuntimeError(f"All models failed for tier {tier}. Last error: {last_error}")

    def _cache_key(self, system_prompt: str, user_prompt: str, tier: ModelTier) -> str:
        """Generate deterministic cache key from inputs."""
        content = f"{tier.value}:{system_prompt}:{user_prompt}"
        return f"llm_cache:{hashlib.sha256(content.encode()).hexdigest()}"

    def _build_user_content(self, text: str, images: Optional[list]) -> any:
        """Build multimodal content if images present."""
        if not images:
            return text
        content = [{"type": "text", "text": text}]
        for img in images:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img}"}
            })
        return content

    def _track_cost(self, response: LLMResponse):
        """Increment daily cost counters in Redis for monitoring."""
        from datetime import date
        day_key = f"llm_cost:{date.today().isoformat()}"
        self.redis.incrbyfloat(day_key, response.cost_usd)
        self.redis.expire(day_key, 86400 * 30)  # Keep 30 days
```

**Critical rules for the LLM Gateway:**
- NEVER import `anthropic`, `openai`, or `google.generativeai` anywhere except in litellm's internals. All code uses `LLMGateway.complete()`.
- NEVER hardcode model strings outside of `MODEL_MAP`. If you need to change models, change them in one place.
- ALL responses go through the same `LLMResponse` dataclass regardless of provider.
- Cost tracking happens automatically on every call — this feeds into usage metering.

### Tiered Model Routing (complexity_classifier.py)

Route requests to the cheapest model that can handle the task. This runs BEFORE the LLM call.

```python
# complexity_classifier.py — classify prompt complexity to select model tier

from engine.llm_gateway import ModelTier

def classify_complexity(
    prompt: str,
    diagram_type: Optional[str],
    has_sample_image: bool,
    entity_count_hint: Optional[int] = None,
) -> ModelTier:
    """
    Classify request complexity to determine which model tier to use.

    Rules (in priority order):
    1. Vision requests → always VISION tier
    2. Explicit complex types → PREMIUM
    3. Simple explicit types → FAST
    4. Ambiguous / auto-detect → STANDARD or PREMIUM based on heuristics
    """

    # Vision analysis always uses vision tier
    if has_sample_image:
        return ModelTier.VISION

    # Known-simple diagram types
    simple_types = {'process_flow', 'timeline', 'comparison'}
    # Known-complex diagram types
    complex_types = {'marketecture', 'org_structure', 'hub_spoke', 'value_chain'}

    if diagram_type in simple_types:
        # Even simple types can be complex with many entities
        if entity_count_hint and entity_count_hint > 8:
            return ModelTier.STANDARD
        return ModelTier.FAST

    if diagram_type in complex_types:
        return ModelTier.PREMIUM

    # Auto-detect mode — analyze prompt for complexity signals
    prompt_lower = prompt.lower()
    complexity_signals = [
        'marketecture', 'architecture', 'ecosystem', 'cross-cutting',
        'integration', 'platform', 'multi-layer', 'hierarchy',
        'organizational', 'value chain', 'business units',
    ]
    signal_count = sum(1 for s in complexity_signals if s in prompt_lower)

    if signal_count >= 2:
        return ModelTier.PREMIUM
    elif signal_count >= 1:
        return ModelTier.STANDARD
    else:
        return ModelTier.FAST  # Default to cheapest for simple/unclear requests
```

**Expected cost distribution at scale:**
- ~60% of requests → FAST tier (~$0.001/request)
- ~25% of requests → STANDARD tier (~$0.009/request)
- ~10% of requests → PREMIUM tier (~$0.027/request)
- ~5% of requests → VISION tier (~$0.017/request)
- **Weighted average: ~$0.005/request** (vs $0.027 if using Sonnet for everything)

### Response Caching Strategy (cache.py)

Multiple caching layers to minimize both LLM costs and generation latency.

**Layer 1 — LLM Response Cache (Redis, TTL: 1 hour)**
Same prompt + same colors + same diagram type = same InfographBrief. Cache the LLM response. Cache hit rate expectation: 15-30% (users often regenerate with minor tweaks, and popular prompts from templates will repeat).

**Layer 2 — Generated File Cache (S3, TTL: 24 hours)**
Same InfographBrief = same PPTX/SVG output. Cache the rendered files. If a brief hasn't changed, skip the entire layout + render pipeline and serve the cached file. Cache hit rate: 30-50% (users often download the same file multiple times, or share links).

**Layer 3 — System Prompt Cache (LLM Provider Level)**
The system prompt (~2,500 tokens of archetype definitions and rules) is identical for every request. All three providers offer prompt caching:
- Anthropic: cache reads at $0.30/M tokens (90% discount vs $3/M standard)
- OpenAI: automatic caching, ~50% discount on cached prefixes
- Gemini: context caching with configurable TTL, up to 75% discount

**ALWAYS enable provider-level prompt caching.** At 1M requests/month, system prompt caching alone saves $2,000-5,000/month.

**Cache invalidation rules:**
- LLM response cache: invalidate when system prompt version changes (track via hash)
- File cache: invalidate when layout engine code version changes
- Never cache vision analysis results (image inputs are unique)

### Multi-Language & Internationalization (i18n)

Global users will submit prompts and expect infographic text in their language. This affects multiple layers.

**LLM Layer:**
All three providers handle multilingual prompts well. The system prompt should remain in English (it's the control layer), but explicitly instruct the model: "Generate all entity labels and descriptions in the same language as the user's prompt. If the user writes in Japanese, all output text must be in Japanese."

**Text Measurement Layer (text_measure.py updates):**
CJK characters are approximately 2x the width of Latin characters at the same point size. The `fit_text_to_width()` function MUST account for this:

```python
def _estimate_char_width_multiplier(text: str) -> float:
    """Estimate width multiplier based on script detection."""
    cjk_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff'   # CJK Unified
                    or '\u3040' <= c <= '\u309f'   # Hiragana
                    or '\u30a0' <= c <= '\u30ff'   # Katakana
                    or '\uac00' <= c <= '\ud7af')  # Korean
    if len(text) == 0:
        return 1.0
    cjk_ratio = cjk_count / len(text)
    # CJK characters are ~1.8x wider than Latin at same point size
    return 1.0 + (cjk_ratio * 0.8)
```

**RTL Language Support:**
Arabic and Hebrew text flows right-to-left. In PowerPoint, this is handled by paragraph-level settings:
```python
# For RTL text in python-pptx
from pptx.oxml.ns import qn
pPr = paragraph._element.get_or_add_pPr()
pPr.set(qn('a:rtl'), '1')
```
The layout engine should detect RTL scripts and flip horizontal flow directions for process flows and timelines.

**Font Fallback Chain:**
Calibri doesn't cover CJK or Arabic. Bundle and use this fallback chain:
1. User-specified font (from brand preset)
2. Calibri (Latin, Cyrillic, Greek)
3. Noto Sans CJK (Chinese, Japanese, Korean) — download from Google Fonts
4. Noto Sans Arabic (Arabic, Farsi, Urdu)
5. Noto Sans Hebrew
6. Noto Sans (everything else)
7. DejaVu Sans (ultimate fallback, always available on Linux)

In PPTX rendering, set the font on each run, with a fallback font in the slide master theme for characters the primary font doesn't cover.

### Usage Metering & SaaS Billing (metering.py)

Track every generation for billing, analytics, and abuse prevention.

**Per-request metering — store in PostgreSQL:**

```python
# metering.py — track every generation

@dataclass
class GenerationRecord:
    id: str                      # UUID
    user_id: str                 # FK to users table
    timestamp: datetime
    prompt_text: str             # Original prompt (for analytics, truncated to 500 chars)
    diagram_type: str
    model_tier: str              # "fast", "standard", "premium", "vision"
    model_used: str              # Actual model string
    input_tokens: int
    output_tokens: int
    llm_cost_usd: float          # Actual LLM cost
    generation_time_ms: int      # Total wall clock time
    cache_hit: bool              # Whether LLM response came from cache
    output_format: str           # "pptx", "svg", "png"
    entity_count: int            # Number of entities in generated diagram
    language_detected: str       # ISO 639-1 language code
```

**Usage limits by tier:**

```python
PLAN_LIMITS = {
    "free": {
        "generations_per_month": 5,
        "max_entities_per_diagram": 10,
        "allowed_tiers": [ModelTier.FAST],
        "export_formats": ["png"],           # No PPTX on free
        "brand_presets": False,
        "sample_upload": False,
    },
    "pro": {
        "generations_per_month": 100,
        "max_entities_per_diagram": 25,
        "allowed_tiers": [ModelTier.FAST, ModelTier.STANDARD, ModelTier.PREMIUM],
        "export_formats": ["pptx", "png", "svg"],
        "brand_presets": True,
        "sample_upload": True,
    },
    "business": {
        "generations_per_month": 500,        # Per seat
        "max_entities_per_diagram": 50,
        "allowed_tiers": [ModelTier.FAST, ModelTier.STANDARD, ModelTier.PREMIUM, ModelTier.VISION],
        "export_formats": ["pptx", "png", "svg"],
        "brand_presets": True,
        "sample_upload": True,
        "team_brand_kits": True,
        "priority_generation": True,         # Dedicated queue, no wait
    },
    "enterprise": {
        "generations_per_month": -1,         # Unlimited
        "max_entities_per_diagram": 100,
        "allowed_tiers": [ModelTier.FAST, ModelTier.STANDARD, ModelTier.PREMIUM, ModelTier.VISION],
        "export_formats": ["pptx", "png", "svg"],
        "brand_presets": True,
        "sample_upload": True,
        "team_brand_kits": True,
        "priority_generation": True,
        "sso": True,
        "api_access": True,
        "custom_archetypes": True,
    },
}
```

**Pricing model guidance (based on cost analysis):**
- Free: $0/month — 5 gens/month, PNG only (cost to you: ~$0.005/user/month)
- Pro: $15-20/month — 100 gens, all formats (cost: ~$0.50/user/month, 97% margin)
- Business: $49-79/month per seat — 500 gens, team features (cost: ~$2.50/seat/month)
- Enterprise: Custom pricing — unlimited, SSO, API, custom archetypes

### Rate Limiting & Abuse Prevention (rate_limiter.py)

**Per-user rate limits (Redis-based):**
- Free tier: 2 requests/minute, 5/day
- Pro: 10 requests/minute, 100/day
- Business: 20 requests/minute, 500/day
- Enterprise: 60 requests/minute, unlimited/day

**Per-provider rate limit handling:**
LLM providers impose their own rate limits. The gateway must handle this gracefully:

```python
# In llm_gateway.py — retry logic with provider fallback

MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # Exponential backoff in seconds

async def _call_with_retry(self, model: str, messages: list, **kwargs):
    for attempt in range(MAX_RETRIES):
        try:
            return await litellm.acompletion(model=model, messages=messages, **kwargs)
        except litellm.RateLimitError:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAYS[attempt])
                continue
            raise  # Exhausted retries, let fallback handle it
        except litellm.ServiceUnavailableError:
            raise  # Immediately try next provider in fallback chain
```

**Abuse detection:**
- Flag accounts generating >10x their plan limit within 24 hours
- Flag accounts with >50% identical prompts (bot behavior)
- Flag accounts uploading images that aren't infographics/diagrams (content abuse)
- All flags go to a review queue, not auto-ban

### File Storage & CDN (storage.py)

Generated files (PPTX, PNG, SVG) need to be stored and served globally with low latency.

**Storage strategy:**
- Generated files → S3 (or equivalent object storage) with CDN in front
- File naming: `{user_id}/{generation_id}/{filename}.{ext}` — enables per-user cleanup
- TTL: Free tier files expire after 24 hours. Pro/Business after 30 days. Enterprise: configurable.
- Download URLs: signed S3 URLs with 1-hour expiry (prevents hotlinking)

**File size estimates per generation:**
- PPTX: 50-200 KB (shapes only, no images)
- SVG: 20-80 KB
- PNG (1920×1080): 100-500 KB

At 1M generations/month: ~200 GB new storage/month. With 30-day TTL, steady-state storage is ~200 GB. This is trivial in S3 costs (~$5/month).

### Monitoring & Observability

**Key metrics to track (Prometheus/Grafana):**
- `llm_request_total` — counter by model, tier, cache_hit
- `llm_request_duration_seconds` — histogram by model
- `llm_cost_usd_total` — counter by model (THE most important business metric)
- `generation_total` — counter by diagram_type, output_format
- `generation_duration_seconds` — histogram (LLM time vs layout time vs render time)
- `active_users_daily` — gauge
- `plan_usage_ratio` — gauge by plan tier (how close users are to limits)
- `provider_error_total` — counter by provider (monitors provider health)
- `cache_hit_ratio` — gauge (target: >25% for LLM cache, >40% for file cache)

**Alerting rules:**
- LLM daily cost exceeds budget by 20% → alert
- Provider error rate >5% for 5 minutes → alert (consider disabling provider)
- Average generation latency >20 seconds for 10 minutes → alert
- Cache hit ratio drops below 10% → alert (cache may be misconfigured)

---

## Directory Structure

```
infograph-ai/
├── CLAUDE.md                    # This file
├── docker-compose.yml           # Dev: API + Frontend + Redis + PostgreSQL
├── docker-compose.prod.yml      # Production overrides
├── kubernetes/                  # K8s manifests for production deployment
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── configmap.yaml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Settings, env vars, plan limits
│   ├── database.py              # SQLAlchemy engine, session factory
│   ├── models.py                # SQLAlchemy ORM models (User, Generation, Plan)
│   ├── fonts/                   # Bundled fonts for text measurement (multi-script)
│   │   ├── DejaVuSans.ttf       # Fallback (always available on Linux)
│   │   ├── DejaVuSans-Bold.ttf
│   │   ├── NotoSansCJKsc-Regular.ttf   # Chinese/Japanese/Korean
│   │   ├── NotoSansArabic-Regular.ttf  # Arabic/Farsi/Urdu
│   │   ├── NotoSansHebrew-Regular.ttf  # Hebrew
│   │   ├── NotoSans-Regular.ttf        # Universal Latin/Cyrillic/Greek
│   │   ├── calibri.ttf          # If legally available
│   │   └── arial.ttf            # If legally available
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py            # API route definitions
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── dependencies.py      # Shared dependencies (auth, rate limiting)
│   │   ├── auth.py              # JWT token validation, OAuth2 handlers
│   │   └── middleware.py        # Rate limiting, usage tracking, CORS
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── llm_gateway.py       # LiteLLM multi-provider abstraction (THE entry point for ALL LLM calls)
│   │   ├── complexity_classifier.py  # Classify prompt → ModelTier for cost routing
│   │   ├── units.py             # EMU conversions, slide constants, layout constants
│   │   ├── text_measure.py      # Pillow-based text measurement + fit_text_to_width() (i18n-aware)
│   │   ├── positioned.py        # PositionedElement, PositionedConnector, PositionedLayout dataclasses
│   │   ├── grid_layout.py       # Grid computation: compute_grid(), compute_centered_block()
│   │   ├── layout_engine.py     # Main orchestrator: brief → PositionedLayout
│   │   ├── llm_reasoning.py     # System prompt + brief generation (calls llm_gateway, NOT provider SDKs)
│   │   ├── brand_engine.py      # Color palette, font, theme management
│   │   ├── pptx_renderer.py     # python-pptx PPTX generation (consumes PositionedLayout ONLY)
│   │   ├── svg_renderer.py      # SVG generation + PNG rasterization (consumes PositionedLayout ONLY)
│   │   └── archetype_library.py # Registry mapping diagram_type strings to archetype classes
│   ├── services/
│   │   ├── __init__.py
│   │   ├── cache.py             # Multi-layer caching (Redis LLM cache + S3 file cache)
│   │   ├── metering.py          # Usage tracking, plan limit enforcement, billing records
│   │   ├── rate_limiter.py      # Per-user and per-provider rate limiting
│   │   ├── storage.py           # S3/object storage for generated files, signed URLs
│   │   └── i18n.py              # Language detection, script detection, RTL handling
│   ├── archetypes/
│   │   ├── __init__.py
│   │   ├── base.py              # Base archetype ABC with compute_layout(brief) → PositionedLayout
│   │   ├── marketecture.py      # Layered architecture diagrams (grid + bands)
│   │   ├── process_flow.py      # Step-by-step process flows (horizontal chain)
│   │   ├── tech_stack.py        # Technology stack diagrams (vertical stack)
│   │   ├── comparison.py        # Side-by-side comparisons (table grid)
│   │   ├── timeline.py          # Timeline / roadmap diagrams (horizontal line + markers)
│   │   ├── org_structure.py     # Organizational hierarchy (tree layout)
│   │   ├── value_chain.py       # Value chain / pipeline diagrams (chevron chain)
│   │   └── hub_spoke.py         # Hub and spoke / ecosystem diagrams (radial)
│   ├── templates/
│   │   └── brand_presets/       # JSON files for known brand themes
│   │       ├── opentext.json
│   │       ├── generic_blue.json
│   │       ├── generic_dark.json
│   │       └── generic_light.json
│   └── tests/
│       ├── test_text_measure.py # Test fit_text_to_width with edge cases (long labels, CJK, Arabic, RTL)
│       ├── test_grid_layout.py  # Test grid computation, verify no overlaps, within bounds
│       ├── test_layout_engine.py # Test full brief → PositionedLayout for each archetype
│       ├── test_pptx_render.py  # Test PPTX output opens, correct shape count, correct colors
│       ├── test_reasoning.py    # Test prompt → InfographBrief JSON parsing (all providers)
│       ├── test_archetypes.py   # Test each archetype strategy with varying entity counts
│       ├── test_llm_gateway.py  # Test model routing, fallback, caching, cost tracking
│       ├── test_complexity.py   # Test complexity classifier assigns correct tiers
│       ├── test_metering.py     # Test usage tracking, plan limit enforcement
│       └── test_i18n.py         # Test CJK text measurement, RTL detection, font fallback
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   ├── public/
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   └── client.ts         # Axios API client
│       ├── stores/
│       │   └── infographStore.ts # Zustand store
│       ├── components/
│       │   ├── PromptPanel.tsx       # Main input form
│       │   ├── ColorPicker.tsx       # Color schema selector (up to 10 colors)
│       │   ├── FileUpload.tsx        # Upload sample/template/logo
│       │   ├── DiagramTypeSelector.tsx # Archetype picker cards
│       │   ├── BriefReview.tsx       # AI brief confirmation step
│       │   ├── GenerationLoader.tsx  # Loading state during generation
│       │   ├── CanvasEditor.tsx      # Fabric.js based editor
│       │   ├── EditorToolbar.tsx     # Editing tools (text, color, align, etc.)
│       │   ├── ExportPanel.tsx       # Download options (PPTX, PNG, SVG)
│       │   └── Layout.tsx           # Page layout wrapper
│       ├── hooks/
│       │   ├── useGenerate.ts       # Generation API hook
│       │   └── useEditor.ts        # Fabric.js editor hook
│       ├── types/
│       │   └── index.ts            # TypeScript type definitions
│       └── utils/
│           ├── colors.ts           # Color utility functions
│           └── fabricHelpers.ts    # Fabric.js helper functions
└── docs/
    ├── archetypes.md             # Documentation of supported diagram types
    └── api.md                    # API documentation
```

---

## Core Data Models

### InfographRequest (User Input)
```python
class InfographRequest(BaseModel):
    prompt: str                              # Natural language description
    diagram_type: Optional[str] = None       # "marketecture", "process_flow", etc. or None for auto-detect
    colors: Optional[List[str]] = None       # Up to 10 hex color codes e.g. ["#0073e6", "#ffffff"]
    sample_image: Optional[UploadFile] = None  # Reference infographic image
    template_file: Optional[UploadFile] = None # Corporate template (PPTX/PDF)
    logo_file: Optional[UploadFile] = None     # Company logo
    output_format: str = "pptx"              # "pptx", "svg", "png"
```

### InfographBrief (AI-Generated Structural Plan)
```python
class InfographBrief(BaseModel):
    diagram_type: str                        # Detected or confirmed archetype
    title: str                               # Infographic title
    description: str                         # Plain English summary of what will be built
    entities: List[Entity]                   # All items/blocks to render
    layers: Optional[List[Layer]] = None     # For layered diagrams (marketectures, stacks)
    connections: Optional[List[Connection]] = None  # For flow/relationship diagrams
    theme: ThemeSpec                         # Colors, fonts, spacing
    layout_hint: str                         # "grid_3x3", "horizontal_layers", "radial", etc.

class Entity(BaseModel):
    id: str
    label: str
    description: Optional[str] = None
    group: Optional[str] = None              # Which layer/section it belongs to
    emphasis: str = "normal"                 # "normal", "primary", "secondary", "accent"
    icon_hint: Optional[str] = None          # Semantic hint for icon selection

class Layer(BaseModel):
    id: str
    label: str
    position: str                            # "top", "middle", "bottom", "cross-cutting"
    entities: List[str]                      # Entity IDs in this layer

class Connection(BaseModel):
    from_entity: str
    to_entity: str
    label: Optional[str] = None
    style: str = "arrow"                     # "arrow", "dashed", "bidirectional"

class ThemeSpec(BaseModel):
    primary_color: str                       # Hex
    secondary_color: str
    accent_color: str
    background_color: str = "#ffffff"
    text_color: str = "#333333"
    font_family: str = "Calibri"
    corner_radius: int = 8                   # px for rounded rectangles
    padding: int = 16
```

### InfographOutput (Generated Result)
```python
class InfographOutput(BaseModel):
    brief: InfographBrief                    # The structural plan used
    svg_content: str                         # SVG string for browser preview
    canvas_json: dict                        # Fabric.js compatible JSON for editor
    file_urls: dict                          # {"pptx": "/api/download/xxx.pptx", "png": "..."}
```

---

## API Endpoints

### POST /api/analyze
Accepts user prompt + optional inputs. Calls Claude API to reason about the request and produce an InfographBrief. Returns the brief for user confirmation.

**Request**: InfographRequest (multipart/form-data)
**Response**: InfographBrief

### POST /api/generate
Accepts a confirmed InfographBrief. Runs the layout engine, renders SVG, generates PPTX, produces Fabric.js JSON. Returns all outputs.

**Request**: InfographBrief (JSON)
**Response**: InfographOutput

### POST /api/export
Accepts modified Fabric.js canvas JSON from the frontend editor. Re-renders to PPTX/PNG/SVG.

**Request**: `{ canvas_json: dict, format: "pptx" | "png" | "svg" }`
**Response**: File download

### GET /api/archetypes
Returns the list of supported diagram types with descriptions and example prompts.

**Response**: `List[{ id: str, name: str, description: str, example_prompt: str }]`

### GET /api/brand-presets
Returns available brand theme presets.

**Response**: `List[{ id: str, name: str, colors: ThemeSpec }]`

---

## LLM Reasoning Layer (llm_reasoning.py)

This is the intelligence core. It uses Claude API with a carefully crafted system prompt.

### System Prompt for Claude (embed this in llm_reasoning.py):

```
You are an expert corporate infographic architect. Your job is to analyze a user's request
and produce a structured specification for an infographic diagram.

You understand these diagram archetypes:
- MARKETECTURE: Layered architecture showing business units, platforms, and integration layers.
  Spatial logic: horizontal layers stacked vertically, entities as blocks within layers.
- PROCESS_FLOW: Sequential steps in a process with directional flow.
  Spatial logic: left-to-right or top-to-bottom chain with connectors.
- TECH_STACK: Technology layers from infrastructure to application.
  Spatial logic: vertical stack, bottom = infrastructure, top = user-facing.
- COMPARISON: Side-by-side comparison of 2-4 items across dimensions.
  Spatial logic: columns for items, rows for comparison criteria.
- TIMELINE: Chronological sequence of events or milestones.
  Spatial logic: horizontal timeline with markers and descriptions.
- ORG_STRUCTURE: Hierarchical organization chart.
  Spatial logic: tree layout, top = leadership, branching downward.
- VALUE_CHAIN: Sequential value-adding stages in a business process.
  Spatial logic: horizontal pipeline with chevron or arrow shapes.
- HUB_SPOKE: Central concept with radiating related concepts.
  Spatial logic: central circle with surrounding satellite elements.

When analyzing a request:
1. Identify the diagram type (or recommend one if not specified)
2. Extract all entities, their groupings, and relationships
3. Determine the spatial layout that best communicates the message
4. Identify emphasis — what should stand out visually
5. Apply the color theme (use provided colors or suggest appropriate ones)

CRITICAL RULES:
- Corporate infographics use SHAPES, TEXT, and SPATIAL RELATIONSHIPS — never stock photos or clip art
- Every entity must have a clear label
- Hierarchy is communicated through size, position, and color intensity
- Maintain generous whitespace — crowded diagrams fail
- Text should be concise — labels not paragraphs
- When a brand is mentioned (e.g., "OpenText"), use known brand colors if available

Respond ONLY with valid JSON matching the InfographBrief schema. No markdown, no explanation.
```

### Implementation Notes:
- **CRITICAL: llm_reasoning.py calls LLMGateway.complete(), NEVER provider SDKs directly**
- Use `ModelTier.PREMIUM` for brief generation by default. The complexity_classifier determines the tier before calling this module.
- Use `response_format={"type": "json_object"}` for JSON mode when available (GPT, Gemini). For Claude, the system prompt's "Respond ONLY with valid JSON" instruction handles this.
- If user provides a sample image, use `ModelTier.VISION` with images parameter to send it for structural analysis before generating the brief
- If user provides a template PPTX, extract the slide master colors and fonts using python-pptx and pass them as context in the user prompt
- If user provides a logo, extract dominant colors using Pillow and include them in the prompt context
- Add to system prompt for i18n: "Generate all entity labels, titles, and descriptions in the same language as the user's prompt. If the user writes in Japanese, all output text must be in Japanese."
- Validate the JSON response against the InfographBrief Pydantic schema. If validation fails, retry once with the validation error message included in the prompt. Max 2 retries total.

---

## Layout Engine (layout_engine.py)

The layout engine is the CRITICAL layer that solves python-pptx's alignment and sizing problems. It takes an InfographBrief and computes absolute positions for every element BEFORE any rendering happens. The renderers (PPTX, SVG) are dumb — they just plot what the layout engine tells them.

### Unit System & Conversions (units.py)

python-pptx uses EMUs (English Metric Units). All layout computation happens in a floating-point coordinate system first, then converts to EMUs at render time. Create a dedicated units.py module:

```python
# units.py — MUST be used everywhere, never hardcode EMU values

from pptx.util import Inches, Pt, Emu

# Slide dimensions (16:9 widescreen)
SLIDE_WIDTH_INCHES = 13.333
SLIDE_HEIGHT_INCHES = 7.5
SLIDE_WIDTH_EMU = Inches(SLIDE_WIDTH_INCHES)
SLIDE_HEIGHT_EMU = Inches(SLIDE_HEIGHT_INCHES)

# Working coordinate system (float inches — all layout math uses this)
# Convert to EMU only at final render step
def inches_to_emu(inches: float) -> int:
    return int(inches * 914400)

def emu_to_inches(emu: int) -> float:
    return emu / 914400.0

def pt_to_emu(pt: float) -> int:
    return int(pt * 12700)

# Layout constants (in inches for readability)
MARGIN_TOP = 0.8        # Top margin
MARGIN_BOTTOM = 0.5     # Bottom margin
MARGIN_LEFT = 0.6       # Left margin
MARGIN_RIGHT = 0.6      # Right margin
TITLE_HEIGHT = 0.9      # Reserved for title area
GUTTER_H = 0.25         # Horizontal gutter between blocks
GUTTER_V = 0.2          # Vertical gutter between rows/layers
MIN_BLOCK_WIDTH = 1.5   # Minimum entity block width
MAX_BLOCK_WIDTH = 3.5   # Maximum entity block width
MIN_BLOCK_HEIGHT = 0.7  # Minimum entity block height
MAX_BLOCK_HEIGHT = 1.8  # Maximum entity block height
CROSS_CUT_HEIGHT = 0.6  # Height of cross-cutting layer bands
CONNECTOR_MARGIN = 0.1  # Gap between connector endpoint and shape edge

# Derived usable area
CONTENT_LEFT = MARGIN_LEFT
CONTENT_TOP = MARGIN_TOP + TITLE_HEIGHT
CONTENT_WIDTH = SLIDE_WIDTH_INCHES - MARGIN_LEFT - MARGIN_RIGHT
CONTENT_HEIGHT = SLIDE_HEIGHT_INCHES - MARGIN_TOP - TITLE_HEIGHT - MARGIN_BOTTOM
```

### Text Measurement System (text_measure.py)

This is the module that prevents text overflow — the #1 problem with python-pptx. Uses Pillow to pre-measure text before rendering.

```python
# text_measure.py — measure text BEFORE placing it in shapes

from PIL import ImageFont
import os

# Bundle fallback fonts with the project
FONT_DIR = os.path.join(os.path.dirname(__file__), '..', 'fonts')
FONT_MAP = {
    'Calibri': 'calibri.ttf',
    'Arial': 'arial.ttf',
    'Segoe UI': 'segoeui.ttf',
}
FALLBACK_FONT = 'DejaVuSans.ttf'  # Always available on Linux

def get_font(family: str, size_pt: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a font for measurement. Falls back gracefully."""
    filename = FONT_MAP.get(family, FALLBACK_FONT)
    path = os.path.join(FONT_DIR, filename)
    if not os.path.exists(path):
        path = os.path.join(FONT_DIR, FALLBACK_FONT)
    return ImageFont.truetype(path, size_pt)

def measure_text(text: str, font_family: str, font_size_pt: int, bold: bool = False) -> tuple[float, float]:
    """Returns (width_inches, height_inches) of rendered text."""
    font = get_font(font_family, font_size_pt, bold)
    bbox = font.getbbox(text)
    width_px = bbox[2] - bbox[0]
    height_px = bbox[3] - bbox[1]
    # Convert pixels to inches (Pillow uses 72 DPI for point-based fonts)
    return (width_px / 72.0, height_px / 72.0)

def fit_text_to_width(text: str, max_width_inches: float, font_family: str,
                       max_font_size: int = 24, min_font_size: int = 10,
                       bold: bool = False) -> dict:
    """
    Find the largest font size that fits text within max_width, with optional wrapping.
    Returns: {
        'font_size': int,
        'lines': list[str],       # Text split into lines
        'total_height': float,    # Total height in inches
        'fits': bool              # Whether it fit at all
    }
    """
    padding_inches = 0.15  # Internal padding on each side
    available_width = max_width_inches - (2 * padding_inches)

    for size in range(max_font_size, min_font_size - 1, -1):
        # Try single line first
        w, h = measure_text(text, font_family, size, bold)
        if w <= available_width:
            return {
                'font_size': size,
                'lines': [text],
                'total_height': h + 0.1,  # Add breathing room
                'fits': True
            }

        # Try word-wrapping into 2 lines
        words = text.split()
        if len(words) >= 2:
            best_split = None
            for i in range(1, len(words)):
                line1 = ' '.join(words[:i])
                line2 = ' '.join(words[i:])
                w1, _ = measure_text(line1, font_family, size, bold)
                w2, _ = measure_text(line2, font_family, size, bold)
                if w1 <= available_width and w2 <= available_width:
                    best_split = [line1, line2]
                    break
            if best_split:
                line_height = h * 1.3  # 1.3x line spacing
                return {
                    'font_size': size,
                    'lines': best_split,
                    'total_height': line_height * 2 + 0.1,
                    'fits': True
                }

        # Try 3 lines for very long text at smaller sizes
        if len(words) >= 3 and size <= 14:
            # Split into roughly equal thirds
            third = len(words) // 3
            lines = [
                ' '.join(words[:third]),
                ' '.join(words[third:2*third]),
                ' '.join(words[2*third:])
            ]
            max_w = max(measure_text(l, font_family, size, bold)[0] for l in lines)
            if max_w <= available_width:
                line_height = h * 1.3
                return {
                    'font_size': size,
                    'lines': lines,
                    'total_height': line_height * 3 + 0.1,
                    'fits': True
                }

    # Couldn't fit — return minimum size with truncation
    return {
        'font_size': min_font_size,
        'lines': [text[:30] + '...' if len(text) > 30 else text],
        'total_height': 0.3,
        'fits': False
    }
```

### Grid Layout System (grid_layout.py)

The grid system computes cell positions BEFORE placing entities. This guarantees alignment.

```python
# grid_layout.py — grid-based positioning for all block-style diagrams

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class GridCell:
    """A single cell in the layout grid."""
    row: int
    col: int
    x: float          # Left edge in inches
    y: float          # Top edge in inches
    width: float      # Cell width in inches
    height: float     # Cell height in inches
    col_span: int = 1 # How many columns this cell spans (for cross-cutting elements)

@dataclass
class LayoutGrid:
    """Complete grid definition."""
    cells: List[GridCell]
    total_width: float
    total_height: float
    row_count: int
    col_count: int

def compute_grid(
    num_columns: int,
    num_rows: int,
    content_left: float,
    content_top: float,
    content_width: float,
    content_height: float,
    gutter_h: float = 0.25,
    gutter_v: float = 0.2,
    row_heights: Optional[List[float]] = None,  # Proportional weights per row
) -> LayoutGrid:
    """
    Compute a grid of cells that fills the content area evenly.

    If row_heights is provided, rows are sized proportionally.
    Example: row_heights=[1, 3, 1] means middle row gets 3/5 of height.
    """
    # Column widths (equal)
    total_gutter_h = gutter_h * (num_columns - 1)
    col_width = (content_width - total_gutter_h) / num_columns

    # Row heights
    total_gutter_v = gutter_v * (num_rows - 1)
    available_height = content_height - total_gutter_v

    if row_heights:
        total_weight = sum(row_heights)
        row_h = [(w / total_weight) * available_height for w in row_heights]
    else:
        row_h = [available_height / num_rows] * num_rows

    # Generate cells
    cells = []
    current_y = content_top
    for r in range(num_rows):
        current_x = content_left
        for c in range(num_columns):
            cells.append(GridCell(
                row=r, col=c,
                x=current_x, y=current_y,
                width=col_width, height=row_h[r]
            ))
            current_x += col_width + gutter_h
        current_y += row_h[r] + gutter_v

    return LayoutGrid(
        cells=cells,
        total_width=content_width,
        total_height=content_height,
        row_count=num_rows,
        col_count=num_columns
    )

def compute_centered_block(cell: GridCell, block_width: float, block_height: float) -> tuple:
    """Center a block within a grid cell. Returns (x, y, w, h) in inches."""
    x = cell.x + (cell.width - block_width) / 2
    y = cell.y + (cell.height - block_height) / 2
    return (x, y, block_width, block_height)

def compute_full_width_band(
    content_left: float,
    y_position: float,
    content_width: float,
    band_height: float,
    margin_inset: float = 0.0
) -> tuple:
    """Compute a full-width horizontal band (for cross-cutting layers like AI Layer)."""
    return (
        content_left + margin_inset,
        y_position,
        content_width - (2 * margin_inset),
        band_height
    )
```

### Positioned Element Model (positioned.py)

The layout engine outputs a list of PositionedElements. Renderers consume this — they NEVER compute positions themselves.

```python
# positioned.py — the contract between layout engine and renderers

from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class PositionedText:
    """Text content with pre-computed sizing."""
    content: str
    lines: List[str]           # Pre-wrapped lines
    font_size_pt: int          # Pre-computed to fit
    font_family: str
    bold: bool = False
    color: str = "#333333"
    alignment: str = "center"  # "left", "center", "right"

@dataclass
class PositionedElement:
    """A fully positioned, render-ready element."""
    id: str
    element_type: str          # "block", "band", "connector", "title", "subtitle", "label"
    x_inches: float
    y_inches: float
    width_inches: float
    height_inches: float
    fill_color: str            # Hex color
    stroke_color: Optional[str] = None
    stroke_width_pt: float = 1.0
    corner_radius_inches: float = 0.08
    text: Optional[PositionedText] = None
    opacity: float = 1.0
    layer_id: Optional[str] = None
    z_order: int = 0           # Lower = further back

@dataclass
class PositionedConnector:
    """A connector line between two elements."""
    id: str
    start_x: float             # Inches
    start_y: float
    end_x: float
    end_y: float
    style: str = "arrow"       # "arrow", "dashed", "bidirectional", "plain"
    color: str = "#666666"
    stroke_width_pt: float = 1.5
    label: Optional[PositionedText] = None

@dataclass
class PositionedLayout:
    """Complete render-ready layout. This is what renderers consume."""
    slide_width_inches: float
    slide_height_inches: float
    background_color: str
    elements: List[PositionedElement] = field(default_factory=list)
    connectors: List[PositionedConnector] = field(default_factory=list)
    title: Optional[PositionedElement] = None
    subtitle: Optional[PositionedElement] = None
```

### Archetype Layout Strategies

Each archetype implements a `compute_layout(brief: InfographBrief) -> PositionedLayout` function. Here's the strategy for each:

**MARKETECTURE layout strategy:**
1. Count layers from brief. Typical: top = AI/Platform layer, middle = BU blocks, bottom = infrastructure/data layer
2. Compute row_heights proportionally: cross-cutting bands get weight 1, main BU row gets weight 3
3. For each layer, compute a grid with N columns = number of entities in that layer
4. Cross-cutting elements (like MyAviator): use compute_full_width_band() spanning all columns
5. BU blocks: compute_centered_block() within each grid cell
6. Measure all text FIRST using fit_text_to_width(), use the computed font sizes and line breaks

**PROCESS_FLOW layout strategy:**
1. Single row of steps, left-to-right
2. Compute grid with 1 row, N columns (N = number of steps)
3. Place step blocks centered in each cell
4. Add connectors between adjacent blocks: start_x = block[n].right_edge + CONNECTOR_MARGIN, end_x = block[n+1].left_edge - CONNECTOR_MARGIN, y = vertical midpoint
5. If > 6 steps, use 2 rows with a U-turn connector: top row left-to-right, bottom row right-to-left

**TECH_STACK layout strategy:**
1. Vertical stack, one row per layer, full width blocks
2. Compute grid with N rows, 1 column
3. Bottom row = infrastructure, top row = application/user layer
4. Stack order is reversed from brief order (bottom-up)
5. Each layer block is full content width minus small inset

**COMPARISON layout strategy:**
1. Grid with N+1 columns (first column for criteria labels) and M+1 rows (first row for item headers)
2. Header row gets smaller height weight
3. Alternate row background colors (subtle tint) for readability

**TIMELINE layout strategy:**
1. Horizontal line at vertical center of content area
2. Evenly spaced markers along the line
3. Alternating above/below placement for descriptions to avoid crowding
4. Date labels directly on/below markers

**HUB_SPOKE layout strategy:**
1. Central element at center of content area
2. Satellite elements placed in a circle around center
3. Radius = min(content_width, content_height) * 0.35
4. Angle between satellites = 360° / N, starting at top (270°)
5. Connectors from center edge to each satellite edge

**ORG_STRUCTURE layout strategy:**
1. Tree layout with root at top center
2. Each level gets a horizontal row
3. Children are evenly spaced under their parent
4. Connectors: vertical line down from parent, horizontal line across children, vertical line up to each child

### Layout Rules (enforced by all strategies):
- Minimum margin from canvas edge: 0.6 inches
- Minimum gutter between elements: 0.25 inches horizontal, 0.2 inches vertical
- Title area: top 0.9 inches of canvas, always reserved
- Text MUST be measured with fit_text_to_width() before block height is finalized
- Block height adjusts to fit text (min 0.7", max 1.8"), never the other way around
- If computed layout exceeds slide bounds, reduce block sizes proportionally rather than overlapping
- Cross-cutting layers always render BEHIND entity blocks (z_order = -1)

---

## PPTX Renderer (pptx_renderer.py)

Generates native editable PowerPoint files using python-pptx. This renderer is DUMB — it only plots what PositionedLayout tells it. No position computation happens here.

### Critical python-pptx Rules:

**Every measurement must go through units.py:**
```python
from pptx.util import Inches, Pt, Emu
from engine.units import inches_to_emu

# CORRECT:
shape.left = inches_to_emu(element.x_inches)
shape.top = inches_to_emu(element.y_inches)
shape.width = inches_to_emu(element.width_inches)
shape.height = inches_to_emu(element.height_inches)

# WRONG — never hardcode EMU values:
# shape.left = 1828800
```

**Shape creation pattern for entity blocks:**
```python
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

def add_rounded_rect(slide, element: PositionedElement):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        inches_to_emu(element.x_inches),
        inches_to_emu(element.y_inches),
        inches_to_emu(element.width_inches),
        inches_to_emu(element.height_inches)
    )

    # Fill color
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor.from_string(element.fill_color.lstrip('#'))

    # Border
    if element.stroke_color:
        shape.line.color.rgb = RGBColor.from_string(element.stroke_color.lstrip('#'))
        shape.line.width = Pt(element.stroke_width_pt)
    else:
        shape.line.fill.background()  # No border

    # Corner radius — python-pptx adjustment property
    # Adjustment value 0-50000 controls roundness (16667 = ~1/6 of shape height)
    if hasattr(shape, 'adjustments') and len(shape.adjustments) > 0:
        shape.adjustments[0] = min(0.15, element.corner_radius_inches / element.height_inches)

    # Text — use pre-computed lines and font size from PositionedText
    if element.text:
        tf = shape.text_frame
        tf.word_wrap = True
        tf.auto_size = None  # DISABLE auto-size — we pre-computed the right font size
        tf.margin_left = Inches(0.1)
        tf.margin_right = Inches(0.1)
        tf.margin_top = Inches(0.05)
        tf.margin_bottom = Inches(0.05)

        # Vertical centering
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        shape.text_frame.word_wrap = True

        # Use MSO_ANCHOR for vertical alignment
        from pptx.enum.text import MSO_ANCHOR
        tf.auto_size = None
        # Set vertical centering via XML (python-pptx doesn't expose this cleanly)
        from pptx.oxml.ns import qn
        txBody = shape._element.txBody
        bodyPr = txBody.find(qn('a:bodyPr'))
        bodyPr.set('anchor', 'ctr')

        # Clear default paragraph and add our pre-wrapped lines
        for i, line in enumerate(element.text.lines):
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()
            p.alignment = PP_ALIGN.CENTER
            run = p.add_run()
            run.text = line
            run.font.size = Pt(element.text.font_size_pt)
            run.font.color.rgb = RGBColor.from_string(element.text.color.lstrip('#'))
            run.font.name = element.text.font_family
            run.font.bold = element.text.bold

    return shape
```

**Connector creation — use simple lines, NOT native connectors:**
```python
def add_connector_line(slide, connector: PositionedConnector):
    """
    Draw connectors as freeform line shapes, NOT as PowerPoint connectors.
    Native connectors don't attach properly when created programmatically.
    """
    from pptx.enum.shapes import MSO_SHAPE

    # Straight horizontal or vertical connectors as line shapes
    connector_shape = slide.shapes.add_connector(
        1,  # Straight connector type
        inches_to_emu(connector.start_x),
        inches_to_emu(connector.start_y),
        inches_to_emu(connector.end_x),
        inches_to_emu(connector.end_y)
    )
    connector_shape.line.color.rgb = RGBColor.from_string(connector.color.lstrip('#'))
    connector_shape.line.width = Pt(connector.stroke_width_pt)

    # Arrowhead
    if connector.style in ('arrow', 'bidirectional'):
        connector_shape.line.end_marker.type = 2  # Triangle arrowhead
        connector_shape.line.end_marker.width = 2
        connector_shape.line.end_marker.length = 2
    if connector.style == 'bidirectional':
        connector_shape.line.begin_marker.type = 2
        connector_shape.line.begin_marker.width = 2
        connector_shape.line.begin_marker.length = 2
    if connector.style == 'dashed':
        connector_shape.line.dash_style = 4  # Dash

    # Add label if present
    if connector.label:
        mid_x = (connector.start_x + connector.end_x) / 2
        mid_y = (connector.start_y + connector.end_y) / 2
        txBox = slide.shapes.add_textbox(
            inches_to_emu(mid_x - 0.5),
            inches_to_emu(mid_y - 0.15),
            inches_to_emu(1.0),
            inches_to_emu(0.3)
        )
        p = txBox.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = connector.label.content
        run.font.size = Pt(connector.label.font_size_pt)
        run.font.color.rgb = RGBColor.from_string(connector.label.color.lstrip('#'))
```

**Full render pipeline:**
```python
def render_pptx(layout: PositionedLayout, output_path: str):
    """Render a PositionedLayout to an editable PPTX file."""
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    prs.slide_width = inches_to_emu(layout.slide_width_inches)
    prs.slide_height = inches_to_emu(layout.slide_height_inches)

    slide_layout = prs.slide_layouts[6]  # Blank layout
    slide = prs.slides.add_slide(slide_layout)

    # Background color
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor.from_string(layout.background_color.lstrip('#'))

    # Sort elements by z_order (lowest first = rendered first = behind)
    sorted_elements = sorted(layout.elements, key=lambda e: e.z_order)

    # Title
    if layout.title:
        add_text_box(slide, layout.title)

    # Subtitle
    if layout.subtitle:
        add_text_box(slide, layout.subtitle)

    # All elements
    for element in sorted_elements:
        if element.element_type in ('block', 'band'):
            add_rounded_rect(slide, element)
        elif element.element_type == 'label':
            add_text_box(slide, element)

    # Connectors (rendered last = on top)
    for connector in layout.connectors:
        add_connector_line(slide, connector)

    prs.save(output_path)
```

### Key Requirements:
- Every visual element is a native PowerPoint shape (AutoShape or TextBox) — NOT an image
- Shapes use exact colors from PositionedElement
- Text is live editable, uses pre-computed font sizes from layout engine
- DISABLE text auto-size on all shapes — we control sizing
- Set word_wrap = True on all text frames
- Use vertical centering (anchor = 'ctr') on all block text
- Rounded rectangles via MSO_SHAPE.ROUNDED_RECTANGLE with adjustments
- Slide size: 16:9 widescreen (13.333" × 7.5")
- Do NOT group shapes in v1 — grouping complicates editing and is fragile in python-pptx
- Do NOT use native connectors — use simple line shapes with arrowheads
- Add a title text box at top
- Support multi-slide output for complex diagrams (if >15 entities, split logically across slides)

---

## SVG Renderer (svg_renderer.py)

Generates SVG for browser preview and Fabric.js consumption.

### Key Requirements:
- Output clean, well-structured SVG with semantic IDs on every element
- Every shape has: id, data-entity-id, data-layer attributes for editor interaction
- Text elements are <text> nodes, not paths (editable)
- Colors as inline styles (not CSS classes, for portability)
- Rounded rectangles via rx/ry attributes
- Connectors as <path> or <line> with marker-end for arrowheads
- Viewbox set to match canvas dimensions
- Must be parseable by Fabric.js loadSVGFromString()

---

## Fabric.js Canvas Editor (CanvasEditor.tsx)

### Key Requirements:
- Load the generated SVG into Fabric.js canvas
- Every shape is independently selectable, movable, resizable
- Double-click any text to edit inline
- Toolbar provides:
  - Text: font size, bold, italic, alignment
  - Shape: fill color (color picker), stroke color, stroke width, corner radius
  - Arrangement: bring to front, send to back, align left/center/right/top/middle/bottom
  - Add: new text box, new rectangle, new circle, new line/arrow
  - Delete: remove selected element
  - Undo/Redo: full undo/redo stack
- Canvas supports:
  - Zoom in/out (scroll wheel + zoom controls)
  - Pan (space + drag or middle mouse)
  - Multi-select (shift + click or drag select)
  - Snap to grid (toggleable, 8px grid)
  - Smart alignment guides (show guides when element edges align with others)
- Canvas background color is editable
- Export modified canvas as JSON for backend re-rendering

---

## Brand Engine (brand_engine.py)

### Key Requirements:
- Accepts explicit hex colors from user OR brand preset name
- Brand presets are JSON files in templates/brand_presets/
- Each preset defines: primary, secondary, accent, background, text_color, font_family
- If user provides partial colors (e.g., just primary), auto-generate complementary colors using color theory:
  - Secondary: 20% lighter version of primary
  - Accent: complementary or analogous color
  - Background: very light tint of primary or white
  - Text: dark gray or white depending on background
- If user uploads a logo, extract dominant colors using Pillow (k-means on logo pixels) and suggest a theme
- OpenText preset example:
  ```json
  {
    "id": "opentext",
    "name": "OpenText Corporate",
    "primary_color": "#0073e6",
    "secondary_color": "#00a3e0",
    "accent_color": "#6cc24a",
    "background_color": "#f5f7fa",
    "text_color": "#1a1a2e",
    "font_family": "Calibri"
  }
  ```

---

## Frontend User Flow

### Step 1: Input (PromptPanel.tsx)
- Large text area for the prompt (with placeholder examples that rotate)
- DiagramTypeSelector: horizontal scrollable card picker showing archetype icons + names. "Auto-detect" selected by default.
- ColorPicker: click to add colors (up to 10), or type hex codes, or select from brand presets dropdown
- Three upload zones: "Reference Sample (optional)", "Corporate Template (optional)", "Logo (optional)"
- "Generate" button — prominent, primary color

### Step 2: Brief Review (BriefReview.tsx)
- Shows the AI-generated structural plan in a clean, readable card layout
- Displays: diagram type, title, list of entities with groupings, proposed layout description, color theme swatches
- "Edit Brief" allows inline editing of entity names, adding/removing entities, changing groupings
- "Regenerate" button to re-run analysis with modifications
- "Build It" button to proceed to generation

### Step 3: Generation (GenerationLoader.tsx)
- Animated loading state (progress bar or skeleton of diagram assembling)
- Target: under 15 seconds total generation time

### Step 4: Editor + Export (CanvasEditor.tsx + ExportPanel.tsx)
- Full canvas editor takes up main screen area
- Right sidebar: ExportPanel with download buttons for PPTX, PNG, SVG
- Top toolbar: editing tools
- "New Infographic" button to start over

---

## Implementation Priorities (Build Order)

### Phase 1: Core Generation (build this first)
1. `engine/units.py` — EMU conversions and layout constants. This is the foundation.
2. `engine/positioned.py` — PositionedElement, PositionedConnector, PositionedLayout dataclasses.
3. `engine/text_measure.py` — Pillow-based text measurement with fit_text_to_width(). Bundle DejaVuSans.ttf as fallback font. Write tests immediately (test_text_measure.py).
4. `engine/grid_layout.py` — Grid computation: compute_grid(), compute_centered_block(), compute_full_width_band(). Write tests (test_grid_layout.py).
5. `archetypes/base.py` — Base archetype ABC with compute_layout(brief: InfographBrief) → PositionedLayout interface.
6. `archetypes/marketecture.py` — First archetype implementation using grid_layout utilities.
7. `engine/layout_engine.py` — Orchestrator that selects archetype and runs: text measurement → grid computation → element placement → connector routing → theme application → PositionedLayout output.
8. `engine/pptx_renderer.py` — Render PositionedLayout to PPTX. Test with: generate a hardcoded PositionedLayout and verify the PPTX opens correctly in PowerPoint with all shapes aligned.
9. `engine/llm_reasoning.py` — Claude API integration. System prompt with archetype definitions. JSON output parsing to InfographBrief.
10. `engine/brand_engine.py` — Brand presets, color complementary generation.
11. FastAPI app skeleton: main.py, config.py, routes.py, schemas.py — wire up /api/analyze and /api/generate endpoints.
12. Minimal React frontend — prompt input + diagram type selector → API call → download PPTX button.
13. **Validation test**: "Build a Marketecture of OpenText Business Units with MyAviator as the AI Layer in standard OpenText blue theme" → verify PPTX output has correct structure, alignment, text sizing, and colors.

### Phase 2: Browser Preview + More Archetypes
7. SVG renderer — generate SVG from same layout data
8. Frontend SVG preview (display generated SVG in browser)
9. Add process_flow, comparison, and timeline archetypes
10. Brand engine — color extraction from logos, preset management
11. Brief review confirmation step in frontend

### Phase 3: In-Browser Editor
12. Fabric.js canvas integration — load SVG, enable editing
13. Editor toolbar — text editing, color changes, shape manipulation
14. Export from editor — send modified canvas back to backend for PPTX re-render
15. Add remaining archetypes (org_structure, hub_spoke, value_chain)

### Phase 4: Global Scale Infrastructure
16. `engine/llm_gateway.py` — LiteLLM integration with multi-provider routing, fallback, cost tracking
17. `engine/complexity_classifier.py` — Prompt complexity → ModelTier routing
18. `services/cache.py` — Redis LLM response cache + S3 file cache with TTL management
19. `services/rate_limiter.py` — Per-user rate limiting (Redis-based sliding window)
20. `services/storage.py` — S3 integration for generated file storage, signed download URLs, CDN
21. Refactor `llm_reasoning.py` to call `llm_gateway.py` instead of Anthropic SDK directly
22. Verify all three providers (Claude, GPT, Gemini) produce valid InfographBrief JSON for the same prompts
23. Provider-level prompt caching enabled for all providers

### Phase 5: SaaS & Auth
24. PostgreSQL schema: users, plans, generations, team_brand_kits tables
25. `api/auth.py` — JWT authentication, Google/Microsoft OAuth2 login
26. `services/metering.py` — Per-user generation counting, plan limit enforcement
27. `api/middleware.py` — Auth middleware, rate limit middleware, usage tracking on every request
28. Frontend: login/signup flow, plan selection, usage dashboard
29. Stripe integration for subscription billing (Pro, Business tiers)
30. Admin dashboard: LLM cost monitoring, user analytics, provider health

### Phase 6: Advanced Features & Polish
31. Sample image analysis — use Vision tier to analyze uploaded reference infographics
32. Template extraction — parse uploaded PPTX templates for theme/layout hints
33. Multi-slide support for complex diagrams (>15 entities)
34. Undo/redo, snap-to-grid, alignment guides in editor
35. `services/i18n.py` — Language detection, CJK text measurement, RTL layout support
36. Noto Sans font bundle for CJK, Arabic, Hebrew rendering in PPTX
37. Team brand kit management (Business/Enterprise tier feature)
38. API access for Enterprise tier (programmatic infographic generation)
39. Custom archetype builder for Enterprise customers

---

## Environment Variables (.env)

```
# LLM Provider Keys (all required for full fallback support)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# Default model preferences (override via MODEL_MAP in llm_gateway.py)
DEFAULT_PREMIUM_MODEL=claude-sonnet-4-5-20250929
DEFAULT_STANDARD_MODEL=claude-haiku-4-5-20251001
DEFAULT_FAST_MODEL=gpt-4o-mini
DEFAULT_VISION_MODEL=gemini/gemini-2.5-pro

# Application
APP_HOST=0.0.0.0
APP_PORT=8000
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=["http://localhost:5173","https://app.infographai.com"]

# Database
DATABASE_URL=postgresql://infographai:password@localhost:5432/infographai

# Redis (caching, rate limiting, task queue)
REDIS_URL=redis://localhost:6379/0
LLM_CACHE_TTL_SECONDS=3600
FILE_CACHE_TTL_SECONDS=86400

# File Storage
STORAGE_BACKEND=local                    # "local" for dev, "s3" for production
AWS_S3_BUCKET=infographai-outputs
AWS_S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
CDN_BASE_URL=https://cdn.infographai.com

# File handling
UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
MAX_UPLOAD_SIZE_MB=10
GENERATED_FILE_TTL_HOURS=720             # 30 days for paid, 24 hours for free

# Auth
JWT_SECRET_KEY=...
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
MICROSOFT_OAUTH_CLIENT_ID=...
MICROSOFT_OAUTH_CLIENT_SECRET=...

# Monitoring
ENABLE_COST_TRACKING=true
LLM_DAILY_BUDGET_USD=500                 # Alert if exceeded
SENTRY_DSN=...                           # Error tracking (optional)

# Rate Limiting
RATE_LIMIT_FREE_RPM=2                    # Requests per minute for free tier
RATE_LIMIT_PRO_RPM=10
RATE_LIMIT_BUSINESS_RPM=20
RATE_LIMIT_ENTERPRISE_RPM=60
```

---

## Testing Requirements

- Unit tests for each archetype's layout computation (given N entities, verify positions don't overlap, fit within canvas, maintain minimum spacing)
- Unit tests for PPTX renderer (verify generated file opens in python-pptx, has correct number of shapes, correct colors)
- Unit tests for text measurement with CJK characters (verify wider width estimation) and Arabic/Hebrew (verify RTL detection)
- Unit tests for LLM Gateway: mock each provider, verify fallback behavior when primary fails, verify cache hit/miss, verify cost tracking increments
- Unit tests for complexity classifier: verify each diagram type maps to expected tier, verify ambiguous prompts use heuristics correctly
- Unit tests for metering: verify plan limits are enforced, verify generation records are created, verify rate limiting blocks excess requests
- Integration test: full flow from prompt → brief → layout → PPTX for each supported archetype
- Integration test: same prompt sent through Claude, GPT, and Gemini via gateway — all three produce valid InfographBrief JSON
- Test the OpenText marketecture case specifically:
  - Prompt: "Build a Marketecture of OpenText Business Units with MyAviator as the AI Layer in standard OpenText blue theme"
  - Expected: 3-layer diagram, 8 BU blocks in main layer, MyAviator as cross-cutting band, OpenText blue palette
  - Validate: all text readable, no overlapping shapes, correct colors, file opens cleanly in PowerPoint
- Multi-language test cases:
  - Japanese: "OpenTextのビジネスユニットのマーケテクチャを作成してください" → verify CJK text fits in blocks, correct font fallback
  - Arabic: verify RTL text rendering in PPTX, paragraph direction set correctly
  - Mixed: "Build a tech stack with 数据分析 and Machine Learning layers" → verify mixed-script text measurement

---

## Key Design Principles

1. **Structure over decoration**: These are corporate diagrams, not art. Clean shapes, clear labels, consistent spacing. No gradients, shadows, or visual noise unless the brand theme specifically calls for it.
2. **Editable over beautiful**: Every output must be natively editable. A slightly less polished PPTX that users can modify beats a pixel-perfect PNG they can't touch.
3. **Smart defaults, full control**: The AI makes good default choices (layout, colors, sizing) but the user can override everything.
4. **Fast feedback loop**: Prompt to preview should be under 15 seconds globally. Editing should be instant. Export should be under 5 seconds.
5. **Archetype-driven**: Don't try to solve infinite layout problems. Support specific diagram types with purpose-built layout algorithms. Add new archetypes incrementally.
6. **Provider-agnostic**: No module except llm_gateway.py should know or care which LLM provider is being used. All LLM calls go through the gateway. All responses are normalized to the same dataclass.
7. **Cost-aware by default**: Every generation tracks its cost. The complexity classifier routes to the cheapest capable model. Caching prevents redundant LLM calls. These aren't optimizations — they're core architecture.
8. **Global-first**: Multi-language text measurement, font fallback for all scripts, RTL support, and multi-region deployment are not afterthoughts — they're built into the layout engine and renderer from day one.
9. **Metered and bounded**: Every user action is tracked, rate-limited, and bounded by their plan. Free users get a taste. Paid users get value. No one gets to abuse the system.

---

## Known Pitfalls & Solutions (python-pptx)

These are specific gotchas that WILL bite you. Claude Code and all developers must be aware of these.

### Pitfall 1: Text overflow / invisible text
**Problem**: Text set at 18pt in a 1.5" wide box may render outside the box in PowerPoint. python-pptx has no text measurement capability.
**Solution**: ALWAYS use text_measure.py's fit_text_to_width() BEFORE creating any text-containing shape. Never guess font sizes. Never rely on python-pptx's auto_size — disable it explicitly with `tf.auto_size = None`.

### Pitfall 2: EMU calculation errors
**Problem**: Hardcoded EMU values like `shape.left = 1828800` are unreadable, error-prone, and make debugging impossible.
**Solution**: ALL positioning goes through units.py. Use `inches_to_emu(2.0)` not `Inches(2.0)` when you need to do math on the values first. Inches() returns Emu objects which can behave unexpectedly in arithmetic.

### Pitfall 3: Rounded rectangle corner radius
**Problem**: python-pptx doesn't expose corner radius as a simple property. The adjustment value is a proportion (0 to 1) not a pixel/inch value.
**Solution**: Set `shape.adjustments[0] = desired_radius_inches / shape_height_inches`, capped at 0.15 to avoid pill shapes. Always check `len(shape.adjustments) > 0` first.

### Pitfall 4: Native connectors don't attach
**Problem**: PowerPoint connectors created via python-pptx don't bind to shapes. Moving a shape in the editor leaves the connector behind.
**Solution**: Don't use MSO_CONNECTOR types. Use simple line shapes (add_connector with type 1 for straight lines). Accept that connectors won't auto-follow shapes — users will need to manually adjust if they move blocks. This is acceptable for v1.

### Pitfall 5: Vertical text alignment
**Problem**: python-pptx doesn't have a clean API for vertical centering of text within a shape.
**Solution**: Access the XML directly:
```python
from pptx.oxml.ns import qn
bodyPr = shape._element.txBody.find(qn('a:bodyPr'))
bodyPr.set('anchor', 'ctr')  # Vertical center
```

### Pitfall 6: Slide layout interference
**Problem**: Default slide layouts add placeholder shapes that interfere with your custom shapes.
**Solution**: Always use `slide_layouts[6]` (Blank layout). If that index varies, iterate layouts and find the one named "Blank". Never use layouts with title/content placeholders.

### Pitfall 7: Color format
**Problem**: RGBColor.from_string() expects "RRGGBB" without the "#" prefix. Passing "#0073e6" will crash.
**Solution**: Always strip the hash: `RGBColor.from_string(hex_color.lstrip('#'))`. Do this in the renderer, not in the layout engine — the layout engine works with standard "#RRGGBB" hex strings.

### Pitfall 8: Shape ordering / z-order
**Problem**: python-pptx renders shapes in the order they're added. There's no z-index property.
**Solution**: Sort PositionedLayout.elements by z_order before rendering. Add background elements (bands, layers) first, then entity blocks, then connectors last.

### Pitfall 9: Multi-line text spacing
**Problem**: Adding multiple paragraphs with add_paragraph() creates extra vertical space between lines due to default paragraph spacing.
**Solution**: Set space_before and space_after to 0 on each paragraph:
```python
p = tf.add_paragraph()
p.space_before = Pt(0)
p.space_after = Pt(0)
p.line_spacing = 1.0  # Single spacing
```

### Pitfall 10: File corruption on empty text
**Problem**: Creating a shape with an empty text frame or empty paragraph can occasionally cause PowerPoint to flag the file as corrupted.
**Solution**: Always ensure at least one run with at least one space character in every text frame. If an element has no text, use a TextBox type instead of putting empty text in a shape.

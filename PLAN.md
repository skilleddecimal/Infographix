# Infographix: AI-Powered PowerPoint Infographic Generator

## Project Overview

A commercial SaaS tool that generates professional PowerPoint infographic slides using AI. Users describe what they want, and the system produces pixel-perfect, editable PPTX files with creative variations.

**Business Model:** Free / Pro / Enterprise tiers
**Tech Stack:** Python (FastAPI) + React (TypeScript) + In-house ML models + LLM (prompt only)
**Design:** Modern teal (#0D9488) and white theme

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INFOGRAPHIX ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌────────────┐ │
│  │   React     │     │   FastAPI   │     │  ML Engine  │     │   PPTX     │ │
│  │  Frontend   │────▶│   Backend   │────▶│  (In-house) │────▶│  Renderer  │ │
│  │             │     │             │     │             │     │            │ │
│  └─────────────┘     └─────────────┘     └─────────────┘     └────────────┘ │
│        │                   │                   │                    │        │
│        │                   │                   │                    │        │
│  ┌─────▼─────┐       ┌─────▼─────┐       ┌─────▼─────┐        ┌─────▼─────┐ │
│  │  Auth &   │       │ PostgreSQL │       │  Model    │        │  Output   │ │
│  │  Billing  │       │  + Redis   │       │  Storage  │        │   PPTX    │ │
│  └───────────┘       └───────────┘       └───────────┘        └───────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation & PPTX Parser (Weeks 1-3)

### 1.1 Project Setup & Security Infrastructure

**Files to create:**
- `backend/` - Python backend with FastAPI
- `frontend/` - React + TypeScript + Vite
- `ml/` - ML models and training
- `shared/` - Shared types and schemas

**Security foundations:**
- Environment variable management (pydantic-settings)
- Input validation on all endpoints (Pydantic v2)
- Rate limiting middleware
- CORS configuration (strict origins)
- Security headers (helmet equivalent)
- SQL injection prevention (SQLAlchemy ORM only)
- XSS prevention (React default + DOMPurify)
- CSRF tokens for state-changing operations
- Secrets management (.env, never committed)

**Code quality:**
- Pre-commit hooks (ruff, black, mypy, pytest)
- GitHub Actions CI/CD pipeline
- Test coverage requirements (80%+ per phase)
- Conventional commits + semantic versioning

### 1.2 PPTX Parser → DSL Extractor

**Goal:** Extract exact shape data from PPTX into our DSL (JSON scene graph)

**Components:**
```
backend/
├── parser/
│   ├── __init__.py
│   ├── pptx_reader.py      # High-level PPTX reading
│   ├── shape_extractor.py  # Extract shapes, groups, z-order
│   ├── path_parser.py      # Parse freeform Bezier paths
│   ├── style_extractor.py  # Colors, gradients, effects
│   └── text_extractor.py   # Text runs, fonts, alignment
├── dsl/
│   ├── __init__.py
│   ├── schema.py           # Pydantic models for DSL
│   ├── scene_graph.py      # Scene graph data structures
│   └── validators.py       # DSL validation rules
```

**DSL Schema (core):**
```python
class Shape(BaseModel):
    id: str
    type: Literal["autoShape", "freeform", "text", "image", "group"]
    group_path: list[str]  # ["root", "funnel_group", "layer_1"]
    z_index: int
    bbox: BoundingBox  # x, y, width, height in EMUs
    transform: Transform  # rotation, flip_h, flip_v, scale
    path: Optional[list[PathCommand]]  # For freeforms
    fill: Fill  # solid, gradient, pattern, none
    stroke: Stroke  # color, width, dash style
    effects: Effects  # shadow, glow, reflection
    text: Optional[TextContent]  # runs with formatting

class SlideScene(BaseModel):
    canvas: Canvas  # width, height, background
    shapes: list[Shape]
    theme: ThemeColors  # Accent1-6, background, text colors
    metadata: SlideMetadata
```

### 1.3 Phase 1 Testing & Validation

**Test categories:**
- Unit tests: Parser functions (90%+ coverage)
- Integration tests: Full PPTX → DSL pipeline
- Golden tests: Known PPTX files produce expected DSL
- Edge cases: Complex freeforms, nested groups, gradients

**Validation criteria:**
- Round-trip: PPTX → DSL → PPTX produces identical visuals
- All shape types supported (autoShape, freeform, text, image, group)
- Freeform paths accurate to <1 EMU error
- Theme colors correctly resolved

---

## Phase 2: DSL Renderer & Constraint Engine (Weeks 4-6)

### 2.1 PPTX Renderer (DSL → PPTX)

**Goal:** Convert DSL scene graph back to pixel-perfect PPTX

**Components:**
```
backend/
├── renderer/
│   ├── __init__.py
│   ├── pptx_writer.py      # High-level PPTX generation
│   ├── shape_renderer.py   # Render shapes from DSL
│   ├── path_renderer.py    # Generate freeform paths
│   ├── style_renderer.py   # Apply fills, strokes, effects
│   └── text_renderer.py    # Render text with formatting
```

### 2.2 Constraint Engine

**Goal:** Enforce layout rules for "corporate polish"

**Components:**
```
backend/
├── constraints/
│   ├── __init__.py
│   ├── engine.py           # Constraint solver
│   ├── alignment.py        # Center, edge, distribute
│   ├── spacing.py          # Equal gaps, rhythm
│   ├── snapping.py         # Grid snap, guide snap
│   ├── text_fitting.py     # Text-safe zones, overflow
│   └── rules/
│       ├── funnel.py       # Funnel-specific rules
│       ├── timeline.py     # Timeline rules
│       ├── pyramid.py      # Pyramid rules
│       └── ...
```

**Constraint types:**
- **Alignment:** `align_centers(shapes)`, `align_edges(shapes, "left")`
- **Spacing:** `equal_vertical_gaps(shapes)`, `distribute_horizontal(shapes)`
- **Snapping:** `snap_to_grid(shape, grid_size)`, `snap_to_guides(shape)`
- **Hierarchy:** `ensure_visual_hierarchy(shapes)` (z-order, size)

### 2.3 Phase 2 Testing & Validation

**Test categories:**
- Unit tests: Renderer functions, constraint functions
- Round-trip tests: DSL → PPTX → DSL produces identical DSL
- Visual regression: Rendered PPTX matches reference images
- Constraint tests: Verify alignment/spacing rules enforced

**Validation criteria:**
- Rendered PPTX opens correctly in PowerPoint/LibreOffice
- All shape properties preserved (colors, effects, text)
- Constraint engine fixes spacing errors within 2px tolerance
- Performance: Render 50-shape slide in <500ms

---

## Phase 3: Component Library & Template System (Weeks 7-9)

### 3.1 Component Discovery & Registry

**Goal:** Identify reusable motifs and parameterize them

**Components:**
```
backend/
├── components/
│   ├── __init__.py
│   ├── registry.py         # Component type registry
│   ├── detector.py         # Detect components in DSL
│   ├── templates/
│   │   ├── funnel_layer.py
│   │   ├── timeline_node.py
│   │   ├── pyramid_tier.py
│   │   ├── process_step.py
│   │   ├── icon_bubble.py
│   │   └── ...
│   └── parameters.py       # Component parameter schemas
```

**Component definition:**
```python
class FunnelLayerComponent(BaseComponent):
    name = "funnel_layer"
    parameters = {
        "layer_index": int,  # 1-N
        "color_token": str,  # "accent_1", "primary"
        "icon": Optional[str],
        "title": str,
        "description": Optional[str],
        "taper_ratio": float,  # 0.0-1.0
        "accent_style": Literal["ring", "arc", "glow", "none"],
    }
```

### 3.2 Template Ingestion Pipeline

**Goal:** Import PPTX templates and extract component patterns

**Pipeline:**
1. Parse PPTX → DSL
2. Detect component patterns (clustering, rule matching)
3. Extract parameters for each instance
4. Store template definition with variation ranges

**Storage:**
```
backend/
├── templates/
│   ├── store.py            # Template storage (DB + files)
│   ├── ingestion.py        # Template import pipeline
│   ├── variation.py        # Variation range extraction
│   └── library/            # Built-in templates
│       ├── funnels/
│       ├── timelines/
│       ├── pyramids/
│       └── ...
```

### 3.3 Phase 3 Testing & Validation

**Test categories:**
- Component detection accuracy (precision/recall)
- Parameter extraction correctness
- Template ingestion end-to-end
- Component instantiation produces valid DSL

**Validation criteria:**
- 95%+ detection accuracy on known templates
- Parameters correctly extracted for all component types
- Templates stored and retrieved correctly
- Component instantiation matches original within tolerance

---

## Phase 4: In-House ML Models (Weeks 10-14)

### 4.1 Model Architecture

**Goal:** Train models locally for semantic understanding and generation

**Models to train:**

**Model A: Prompt → Intent Classifier**
- Input: User prompt (text)
- Output: Archetype + parameters
- Architecture: Fine-tuned BERT/DistilBERT
- Training data: Synthetic prompts + labeled archetypes

**Model B: Intent → Layout Generator**
- Input: Archetype + parameters + constraints
- Output: DSL scene graph
- Architecture: Encoder-Decoder Transformer (small T5 or custom)
- Training data: Template DSLs + variations

**Model C: Style Recommender**
- Input: Content + brand guidelines
- Output: Style tokens (colors, fonts, effects)
- Architecture: Small MLP or rule-based + learned weights
- Training data: Professional slide style examples

**Directory structure:**
```
ml/
├── models/
│   ├── intent_classifier/
│   │   ├── model.py
│   │   ├── train.py
│   │   ├── inference.py
│   │   └── config.yaml
│   ├── layout_generator/
│   │   ├── model.py
│   │   ├── train.py
│   │   ├── inference.py
│   │   └── config.yaml
│   └── style_recommender/
│       ├── model.py
│       ├── train.py
│       ├── inference.py
│       └── config.yaml
├── training/
│   ├── data_pipeline.py
│   ├── augmentation.py
│   ├── evaluation.py
│   └── checkpoints/
├── inference/
│   ├── engine.py           # Unified inference API
│   ├── batch.py            # Batch processing
│   └── optimization.py     # ONNX, quantization
└── data/
    ├── prompts/            # Synthetic prompt dataset
    ├── templates/          # Template DSL dataset
    └── styles/             # Style examples dataset
```

### 4.2 Training Pipeline

**Data generation (using your 50+ templates):**
1. Parse your 50+ professional PPTX templates
2. Extract DSL + component parameters
3. Generate synthetic prompts for each template (~10-20 per template = 500-1000 samples)
4. Augment with variations (color swaps, text changes) → 5000+ training samples
5. Supplement with free professional templates from SlidesCarnival, SlidesGo, etc.

**Training infrastructure (No Local GPU):**
- PyTorch + HuggingFace Transformers
- **CPU training** for smaller models (Intent Classifier, Style Recommender)
  - DistilBERT fine-tuning: ~2-4 hours on modern CPU
  - Small MLP: minutes on CPU
- **Cloud GPU** for Layout Generator (rent when needed)
  - Lambda Labs (~$1/hr for A10)
  - Vast.ai (cheap spot GPUs)
  - Google Colab Pro ($10/mo for limited GPU)
- MLflow for experiment tracking
- Model versioning and rollback

**CPU-Friendly Model Choices:**
- Intent Classifier: DistilBERT (66M params) - CPU trainable
- Layout Generator: Small T5 (60M params) or custom small Transformer
- Style Recommender: MLP or rule-based with learned weights - CPU trainable

**GPU Rental Strategy:**
- Train on Colab Pro for initial experiments (free tier has limits)
- Use Lambda Labs or Vast.ai for production training runs
- Export to ONNX for CPU inference in production

### 4.3 Inference Optimization

**Production requirements:**
- Inference <500ms for layout generation
- Batch processing for enterprise
- Model quantization (INT8) for CPU deployment
- ONNX export for cross-platform

### 4.4 Phase 4 Testing & Validation

**Test categories:**
- Model accuracy metrics (F1, BLEU, custom metrics)
- Inference latency benchmarks
- A/B testing against rule-based baseline
- Edge case handling (unusual prompts)

**Validation criteria:**
- Intent classifier: 90%+ accuracy on test set
- Layout generator: 85%+ structural similarity to ground truth
- Style recommender: Human preference score >4/5
- Inference: <500ms p95 latency

---

## Phase 5: Creativity Engine (Weeks 15-17)

### 5.1 Controlled Variation System

**Goal:** Generate creative variations while preserving brand constraints

**Variation operators:**
```python
class VariationOperator(ABC):
    @abstractmethod
    def apply(self, dsl: SlideScene, params: dict) -> SlideScene:
        pass

class PaletteVariation(VariationOperator):
    """Change colors within theme tokens"""

class TaperVariation(VariationOperator):
    """Adjust funnel/pyramid taper ratio"""

class AccentStyleVariation(VariationOperator):
    """Swap ring/arc/glow styles"""

class LabelPlacementVariation(VariationOperator):
    """Inside vs callout labels"""

class DepthVariation(VariationOperator):
    """Shadow/3D effect intensity"""
```

**Components:**
```
backend/
├── creativity/
│   ├── __init__.py
│   ├── variation_engine.py   # Apply variations
│   ├── operators/
│   │   ├── palette.py
│   │   ├── geometry.py
│   │   ├── style.py
│   │   └── layout.py
│   ├── constraints.py        # Brand constraint checker
│   └── sampling.py           # Sample from variation space
```

### 5.2 LLM Integration (Prompt Decoding Only)

**Goal:** Use external LLM only for natural language understanding

**Scope (EXTERNAL LLM):**
- Parse user prompt → structured intent
- Extract entities (topics, stage names, counts)
- Determine archetype from description

**NOT sent to external LLM:**
- Training data
- Generated DSL
- User documents
- Style information

**Implementation:**
```
backend/
├── llm/
│   ├── __init__.py
│   ├── client.py           # LLM API client (Claude/GPT)
│   ├── prompts.py          # System prompts for parsing
│   ├── parser.py           # Parse LLM response → Intent
│   └── fallback.py         # Fallback to local model if API fails
```

### 5.3 Phase 5 Testing & Validation

**Test categories:**
- Variation diversity metrics
- Brand constraint satisfaction
- LLM parsing accuracy
- End-to-end prompt → PPTX pipeline

**Validation criteria:**
- Variations are visually distinct but brand-consistent
- 100% of generated slides pass brand constraints
- LLM parsing: 95%+ accuracy on test prompts
- Full pipeline: prompt → PPTX in <3s

---

## Phase 6: Backend API & Database (Weeks 18-20)

### 6.1 API Design

**RESTful + WebSocket API:**
```
POST   /api/v1/generate          # Generate slide from prompt
GET    /api/v1/generate/{id}     # Get generation status/result
POST   /api/v1/variations        # Generate variations
GET    /api/v1/templates         # List available templates
POST   /api/v1/templates/import  # Import custom template (Pro+)
GET    /api/v1/downloads/{id}    # Download PPTX
WS     /api/v1/ws/generate       # Real-time generation updates
```

**Directory structure:**
```
backend/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── routes/
│   │   ├── generate.py
│   │   ├── templates.py
│   │   ├── downloads.py
│   │   ├── auth.py
│   │   └── billing.py
│   ├── middleware/
│   │   ├── auth.py          # JWT validation
│   │   ├── rate_limit.py    # Tier-based limits
│   │   ├── logging.py       # Request logging
│   │   └── security.py      # Security headers
│   └── dependencies.py      # Dependency injection
```

### 6.2 Database Schema

**PostgreSQL tables:**
```sql
-- Users & Auth
users (id, email, password_hash, plan, created_at, ...)
sessions (id, user_id, token_hash, expires_at, ...)
api_keys (id, user_id, key_hash, name, scopes, ...)

-- Usage & Billing
usage (id, user_id, action, credits_used, timestamp)
subscriptions (id, user_id, plan, stripe_id, status, ...)
invoices (id, user_id, amount, stripe_invoice_id, ...)

-- Generations
generations (id, user_id, prompt, intent, dsl, status, ...)
downloads (id, generation_id, format, file_path, ...)

-- Templates (Pro+)
custom_templates (id, user_id, name, dsl_template, ...)

-- Enterprise
organizations (id, name, owner_id, ...)
org_members (org_id, user_id, role, ...)
brand_guidelines (id, org_id, colors, fonts, ...)
```

### 6.3 Caching & Queue

**Redis for:**
- Session cache
- Rate limiting counters
- Generation job queue
- Real-time WebSocket pub/sub

**Celery/ARQ for:**
- Async generation jobs
- Batch processing (Enterprise)
- Template ingestion

### 6.4 Phase 6 Testing & Validation

**Test categories:**
- API endpoint tests (all routes)
- Authentication/authorization tests
- Rate limiting tests per tier
- Database migration tests
- Load testing (concurrent users)

**Validation criteria:**
- All endpoints return correct responses
- Auth properly enforced on protected routes
- Rate limits enforced per tier
- Database handles 10k+ concurrent users
- API response time <100ms (excluding generation)

---

## Phase 7: Frontend Application (Weeks 21-25)

### 7.1 Design System

**Color palette (Teal + White):**
```css
:root {
  /* Primary - Teal */
  --color-primary-50: #F0FDFA;
  --color-primary-100: #CCFBF1;
  --color-primary-200: #99F6E4;
  --color-primary-300: #5EEAD4;
  --color-primary-400: #2DD4BF;
  --color-primary-500: #14B8A6;  /* Main teal */
  --color-primary-600: #0D9488;  /* Dark teal */
  --color-primary-700: #0F766E;
  --color-primary-800: #115E59;
  --color-primary-900: #134E4A;

  /* Neutrals */
  --color-white: #FFFFFF;
  --color-gray-50: #F9FAFB;
  --color-gray-100: #F3F4F6;
  --color-gray-200: #E5E7EB;
  --color-gray-300: #D1D5DB;
  --color-gray-400: #9CA3AF;
  --color-gray-500: #6B7280;
  --color-gray-600: #4B5563;
  --color-gray-700: #374151;
  --color-gray-800: #1F2937;
  --color-gray-900: #111827;

  /* Semantic */
  --color-success: #10B981;
  --color-warning: #F59E0B;
  --color-error: #EF4444;
}
```

**Typography:**
- Headings: Inter (or similar modern sans-serif)
- Body: Inter
- Code: JetBrains Mono

### 7.2 Component Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/              # Base UI components
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Modal.tsx
│   │   │   └── ...
│   │   ├── layout/          # Layout components
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── ...
│   │   ├── generate/        # Generation flow
│   │   │   ├── PromptInput.tsx
│   │   │   ├── ArchetypeSelector.tsx
│   │   │   ├── PreviewCanvas.tsx
│   │   │   ├── VariationGrid.tsx
│   │   │   └── ...
│   │   ├── templates/       # Template browser
│   │   ├── settings/        # User settings
│   │   └── billing/         # Subscription UI
│   ├── pages/
│   │   ├── Home.tsx
│   │   ├── Generate.tsx
│   │   ├── Templates.tsx
│   │   ├── Pricing.tsx
│   │   ├── Dashboard.tsx
│   │   └── ...
│   ├── hooks/               # Custom React hooks
│   ├── stores/              # Zustand stores
│   ├── api/                 # API client
│   ├── utils/               # Utility functions
│   └── types/               # TypeScript types
```

### 7.3 Key Features

**Generation flow:**
1. Prompt input with suggestions
2. Archetype preview (funnel, timeline, etc.)
3. Live preview with SVG rendering
4. Variation selection grid
5. Download options (PPTX, PDF, PNG)

**User experience:**
- Drag-and-drop template import
- Real-time generation progress
- Inline editing of generated content
- Version history (Pro+)
- Team collaboration (Enterprise)

### 7.4 Phase 7 Testing & Validation

**Test categories:**
- Component unit tests (Vitest)
- Integration tests (React Testing Library)
- E2E tests (Playwright)
- Visual regression tests (Chromatic/Percy)
- Accessibility tests (axe-core)

**Validation criteria:**
- All components render correctly
- Forms validate and submit properly
- Generation flow works end-to-end
- Responsive design (mobile, tablet, desktop)
- Lighthouse score >90 (performance, a11y)

---

## Phase 8: Authentication & Billing (Weeks 26-28)

### 8.1 Authentication

**Features:**
- Email/password registration
- OAuth (Google, Microsoft)
- Email verification
- Password reset
- 2FA (TOTP) for Pro/Enterprise
- API keys for programmatic access

**Security:**
- bcrypt password hashing (cost factor 12)
- JWT with short expiry (15m) + refresh tokens
- Secure cookie settings (httpOnly, secure, sameSite)
- Brute force protection (account lockout)
- Session invalidation on password change

### 8.2 Billing & Subscriptions

**Stripe integration:**
- Subscription management
- Usage-based billing (credits)
- Invoice generation
- Payment method management
- Webhook handling

**Plan structure:**

| Feature | Free | Pro ($29/mo) | Enterprise (Custom) |
|---------|------|--------------|---------------------|
| Generations/mo | 10 | 200 | Unlimited |
| Templates | Basic | All | All + Custom |
| Variations | 2 | 10 | Unlimited |
| Export formats | PPTX | PPTX, PDF, PNG | All + API |
| Custom branding | No | No | Yes |
| Team members | 1 | 1 | Unlimited |
| API access | No | Limited | Full |
| Support | Community | Email | Dedicated |

### 8.3 Phase 8 Testing & Validation

**Test categories:**
- Auth flow tests (register, login, logout, reset)
- OAuth integration tests
- Stripe webhook tests (mocked)
- Plan enforcement tests
- Security penetration tests

**Validation criteria:**
- Auth flows work correctly
- Plan limits enforced
- Stripe webhooks processed correctly
- No auth bypasses (security audit)

---

## Phase 9: Enterprise Features (Weeks 29-32)

### 9.1 Multi-tenancy

**Features:**
- Organization management
- Role-based access control (Admin, Editor, Viewer)
- User invitation system
- Audit logging

### 9.2 Brand Guidelines Engine

**Features:**
- Custom color palettes
- Font restrictions
- Logo placement rules
- Approved templates only
- Compliance checking

### 9.3 API & Integrations

**Features:**
- REST API with OpenAPI spec
- Webhooks for generation events
- Microsoft 365 integration
- Google Workspace integration
- Zapier/Make connectors

### 9.4 Phase 9 Testing & Validation

**Test categories:**
- Multi-tenant isolation tests
- RBAC permission tests
- Brand compliance tests
- API contract tests
- Integration tests with external services

**Validation criteria:**
- Tenant data strictly isolated
- RBAC permissions enforced
- Brand guidelines applied correctly
- API meets OpenAPI spec
- Integrations work reliably

---

## Phase 10: Deployment & Operations (Weeks 33-35)

### 10.1 Infrastructure

**Production stack (Cloud-Agnostic):**
- Docker containers (backend, frontend, ML)
- Kubernetes (EKS/AKS) or Docker Compose (simpler)
- PostgreSQL (local → RDS/Azure SQL later)
- Redis (local → ElastiCache/Azure Cache later)
- MinIO (local) → S3/Azure Blob later
- Nginx/Traefik → CloudFront/Azure CDN later

**Environments:**
- Development: Docker Compose on local PC
- Staging: Same Docker stack (cloud VPS when ready)
- Production: AWS or Azure (decision later)

**Cloud migration strategy:**
- All services containerized with standard interfaces
- Environment variables for cloud-specific config
- Terraform modules for both AWS and Azure
- Feature flags for cloud-specific optimizations

### 10.2 CI/CD Pipeline

```yaml
# GitHub Actions workflow
on: [push, pull_request]

jobs:
  test:
    - Lint (ruff, eslint)
    - Type check (mypy, tsc)
    - Unit tests
    - Integration tests
    - Security scan (bandit, npm audit)

  build:
    - Build Docker images
    - Push to registry

  deploy:
    - Deploy to staging (on main)
    - Deploy to production (on release tag)
```

### 10.3 Monitoring & Observability

**Stack:**
- Prometheus + Grafana (metrics)
- Loki or ELK (logs)
- Jaeger/Tempo (tracing)
- Sentry (error tracking)
- PagerDuty/OpsGenie (alerting)

**Key metrics:**
- Generation success rate
- Generation latency (p50, p95, p99)
- API error rate
- Model inference time
- User engagement (DAU, generations/user)

### 10.4 Phase 10 Testing & Validation

**Test categories:**
- Infrastructure as Code tests
- Deployment rollback tests
- Disaster recovery tests
- Load testing (production scale)
- Chaos engineering (failure injection)

**Validation criteria:**
- Zero-downtime deployments
- Rollback completes in <5 minutes
- System recovers from failures automatically
- Handles 1000+ concurrent users
- Alerts fire correctly on issues

---

## Security Checklist (All Phases)

### Application Security
- [ ] Input validation on all user inputs
- [ ] Output encoding to prevent XSS
- [ ] Parameterized queries (no SQL injection)
- [ ] CSRF protection on state-changing operations
- [ ] Secure session management
- [ ] Rate limiting on all endpoints
- [ ] File upload validation and scanning

### Infrastructure Security
- [ ] HTTPS everywhere (TLS 1.3)
- [ ] Security headers (CSP, HSTS, X-Frame-Options)
- [ ] Secrets management (Vault or cloud KMS)
- [ ] Network segmentation
- [ ] Regular dependency updates
- [ ] Vulnerability scanning (Snyk, Dependabot)

### Data Security
- [ ] Encryption at rest (database, files)
- [ ] Encryption in transit (TLS)
- [ ] PII handling compliance (GDPR, CCPA)
- [ ] Data retention policies
- [ ] Audit logging for sensitive operations

### Compliance
- [ ] Privacy policy
- [ ] Terms of service
- [ ] Cookie consent (GDPR)
- [ ] Data processing agreements (Enterprise)
- [ ] SOC 2 preparation (if required)

---

## File Structure Summary

```
infographix/
├── backend/
│   ├── api/                 # FastAPI routes
│   ├── parser/              # PPTX → DSL
│   ├── renderer/            # DSL → PPTX
│   ├── dsl/                 # Scene graph schema
│   ├── components/          # Component library
│   ├── constraints/         # Layout engine
│   ├── creativity/          # Variation engine
│   ├── llm/                 # LLM integration
│   ├── auth/                # Authentication
│   ├── billing/             # Stripe integration
│   ├── db/                  # Database models
│   ├── tests/               # Backend tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page routes
│   │   ├── hooks/           # Custom hooks
│   │   ├── stores/          # State management
│   │   ├── api/             # API client
│   │   └── styles/          # CSS/Tailwind
│   ├── tests/               # Frontend tests
│   └── package.json
├── ml/
│   ├── models/              # Model definitions
│   ├── training/            # Training scripts
│   ├── inference/           # Inference engine
│   └── data/                # Training data
├── infrastructure/
│   ├── docker/              # Dockerfiles
│   ├── k8s/                 # Kubernetes manifests
│   └── terraform/           # Infrastructure as code
├── docs/
│   ├── api/                 # API documentation
│   ├── architecture/        # Architecture docs
│   └── runbooks/            # Operations guides
├── .github/
│   └── workflows/           # CI/CD pipelines
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## Verification Strategy

### Per-Phase Verification

Each phase ends with:
1. Unit test coverage ≥ 80%
2. Integration tests pass
3. Manual QA sign-off
4. Security review (for auth/billing phases)
5. Performance benchmarks meet targets

### End-to-End Verification

1. User journey testing: Signup → Generate → Download
2. Cross-browser testing: Chrome, Firefox, Safari, Edge
3. Mobile responsiveness verification
4. Load testing: 1000 concurrent users
5. Penetration testing: OWASP Top 10 coverage

### Model Verification

1. Accuracy metrics on held-out test sets
2. A/B testing against baseline
3. Human evaluation (quality scores)
4. Edge case testing (unusual inputs)
5. Bias testing (style recommendations)

---

## Timeline Summary

| Phase | Duration | Focus |
|-------|----------|-------|
| 1 | Weeks 1-3 | Foundation & PPTX Parser |
| 2 | Weeks 4-6 | DSL Renderer & Constraints |
| 3 | Weeks 7-9 | Component Library & Templates |
| 4 | Weeks 10-14 | In-House ML Models |
| 5 | Weeks 15-17 | Creativity Engine |
| 6 | Weeks 18-20 | Backend API & Database |
| 7 | Weeks 21-25 | Frontend Application |
| 8 | Weeks 26-28 | Auth & Billing |
| 9 | Weeks 29-32 | Enterprise Features |
| 10 | Weeks 33-35 | Deployment & Operations |

**Total: ~35 weeks to production-ready SaaS**

---

## Next Steps

1. **Approve this plan**
2. **Set up development environment** (Phase 1.1)
3. **Begin PPTX parser implementation** (Phase 1.2)

---

## Phase 1 Quick Start (Immediate Actions)

Once approved, I will:

### Day 1: Project Scaffolding

```bash
# Create project structure
infographix/
├── backend/           # Python 3.11+ with FastAPI
├── frontend/          # React 18 + TypeScript + Vite
├── ml/                # ML models (later phases)
├── docker-compose.yml # Local development
├── pyproject.toml     # Python dependencies (uv/poetry)
└── .github/           # CI/CD workflows
```

### Day 1-2: Backend Foundation
- FastAPI app with health check
- Pydantic v2 models for DSL schema
- Pre-commit hooks (ruff, black, mypy)
- Basic test structure (pytest)

### Day 3-5: PPTX Parser Core
- `python-pptx` + `lxml` for PPTX reading
- Shape extraction (autoShape, freeform, text, image, group)
- Transform parsing (rotation, flip, scale)
- Style extraction (fills, strokes, effects)

### Day 6-8: Freeform Path Parser
- Bezier curve extraction from PPTX XML
- Path command normalization (moveTo, lineTo, curveTo)
- Coordinate system handling (EMUs)

### Day 9-10: Testing & Validation
- Unit tests for all parser functions
- Golden tests with your 50+ templates
- Round-trip validation (PPTX → DSL → verify)

### Prerequisites to Have Ready
1. **Your 50+ PPTX templates** in a folder
2. **Python 3.11+** installed
3. **Node.js 20+** installed
4. **Docker Desktop** installed
5. **VS Code** (recommended) with Python + TypeScript extensions

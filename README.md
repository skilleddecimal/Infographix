# Infographix

AI-Powered PowerPoint Infographic Generator

## Overview

Infographix transforms natural language descriptions into professional, editable PowerPoint infographic slides. Describe what you want ("create a 5-stage sales funnel"), and the system generates pixel-perfect PPTX files with modern styling and creative variations.

## Features

- **Natural Language Input**: Describe your infographic in plain English
- **25+ Diagram Types**: Funnels, pyramids, timelines, flowcharts, and more
- **Professional Styling**: Modern teal/white design with shadows, gradients, and effects
- **Editable Output**: Download as fully editable .pptx files
- **Variations**: Generate multiple design options to choose from

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI
- **Frontend**: React 18 / TypeScript / Vite / Tailwind CSS
- **ML**: PyTorch / HuggingFace Transformers (in-house models)
- **LLM**: Claude/GPT API (prompt parsing only)
- **PPTX**: python-pptx / lxml

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop (optional, for full stack)

### Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn backend.api.main:app --reload
```

Backend will be available at http://localhost:8000

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend will be available at http://localhost:5173

### Docker Setup (Full Stack)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

Services:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Project Structure

```
infographix/
├── backend/
│   ├── api/           # FastAPI routes
│   ├── parser/        # PPTX → DSL extraction
│   ├── renderer/      # DSL → PPTX generation
│   ├── dsl/           # Scene graph schema
│   ├── components/    # Reusable components
│   ├── constraints/   # Layout engine
│   └── tests/         # Backend tests
├── frontend/
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── api/         # API client
│   │   └── types/       # TypeScript types
│   └── ...
├── ml/                # ML models (Phase 4+)
├── infrastructure/    # Docker, K8s configs
└── docs/              # Documentation
```

## API Endpoints

```
POST   /api/v1/generate          # Generate slide from prompt
GET    /api/v1/generate/{id}     # Get generation status
GET    /api/v1/templates         # List templates
POST   /api/v1/parse             # Parse PPTX to DSL
GET    /api/v1/downloads/{id}    # Download generated PPTX
```

## Development

### Running Tests

```bash
# Backend tests
pytest backend/tests -v

# Frontend tests
cd frontend && npm test
```

### Code Quality

```bash
# Lint and format
ruff check backend --fix
ruff format backend

# Type checking
mypy backend
```

### Pre-commit Hooks

```bash
pre-commit install
pre-commit run --all-files
```

## Configuration

Copy `.env.example` to `.env` and configure:

```env
DEBUG=true
ANTHROPIC_API_KEY=your-key-here
```

## License

MIT

## Contributing

See [PLAN.md](PLAN.md) for the development roadmap.

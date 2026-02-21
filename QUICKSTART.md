# Infographix Quick Start Guide

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop (optional, for full stack)

## Backend Setup

```bash
# Navigate to project
cd C:\Users\raymo\mlbase\Infographix

# Create virtual environment (optional but recommended)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
python -m uvicorn backend.api.main:app --reload
```

Backend available at: http://localhost:8000
API Docs: http://localhost:8000/docs

## Frontend Setup

```bash
# In a separate terminal
cd C:\Users\raymo\mlbase\Infographix\frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend available at: http://localhost:5173

## Docker Setup (Full Stack)

```bash
cd C:\Users\raymo\mlbase\Infographix

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

## Running Tests

```bash
# Backend tests
python -m pytest backend/tests -v

# With coverage
python -m pytest backend/tests -v --cov=backend --cov-report=term-missing

# Frontend tests
cd frontend && npm test
```

## Code Quality

```bash
# Lint Python code
python -m ruff check backend --fix
python -m ruff format backend

# Type check
python -m mypy backend

# Install pre-commit hooks
pre-commit install
pre-commit run --all-files
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/generate` | Generate slide from prompt |
| GET | `/api/v1/generate/{id}` | Get generation status |
| GET | `/api/v1/templates` | List available templates |
| POST | `/api/v1/parse` | Parse PPTX to DSL |
| GET | `/api/v1/downloads/{id}` | Download generated PPTX |

## Example API Usage

```bash
# Health check
curl http://localhost:8000/health

# Generate slide
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a 5-stage sales funnel"}'

# List templates
curl http://localhost:8000/api/v1/templates
```

## Environment Variables

Create a `.env` file in the project root:

```env
DEBUG=true
ENVIRONMENT=development
ANTHROPIC_API_KEY=your-api-key
```

## Project Structure

```
Infographix/
├── backend/
│   ├── api/          # FastAPI routes
│   ├── dsl/          # DSL schema models
│   ├── parser/       # PPTX → DSL
│   ├── renderer/     # DSL → PPTX (Phase 2)
│   └── tests/        # Backend tests
├── frontend/
│   └── src/          # React components
├── infrastructure/
│   └── docker/       # Dockerfiles
├── docker-compose.yml
├── requirements.txt
└── pyproject.toml
```

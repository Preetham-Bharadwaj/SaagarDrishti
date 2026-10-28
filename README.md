# SaagarDrishti (ಸಾಗರದೃಷ್ಟಿ)

> **Agentic AI-powered Marine Intelligence & Coastal Advisory Platform for the Karnataka Coast**

SaagarDrishti integrates oceanographic data ingestion, multi-agent AI orchestration, and an intuitive bilingual web dashboard tailored for artisanal and mechanized fishers, coastal authorities, and marine researchers along the ~320 km coastline of Karnataka (spanning from Mangalore/Talapady to Karwar/Majali).

---

## 🌊 Architecture Overview

```text
SaagarDrishti/
├── backend/                  # Python FastAPI Backend
│   ├── app/                  # Application core, routers, adapters, agents & schemas
│   │   ├── adapters/         # INCOIS, Copernicus Marine, Open-Meteo Marine adapters
│   │   ├── agents/           # Multi-agent orchestration, planners & workers
│   │   ├── api/v1/           # REST endpoints (PFZ advisories, safety, queries, health)
│   │   ├── geo/              # Karnataka coastal bounding boxes, ports & landing centers
│   │   ├── schemas/          # Pydantic models & validation
│   │   └── services/         # INCOIS/PFZ ingestion, warnings & workflows
│   ├── tests/                # Comprehensive unit and integration test suite
│   ├── docs/                 # In-depth source audits & specifications
│   ├── requirements.txt      # Python dependencies
│   └── .env.example          # Environment variable template
│
└── frontend/                 # Next.js 15 & React 19 Web Application
    ├── app/                  # Next.js App Router (Dashboard, Map, Alerts, Intelligence)
    ├── components/           # UI components, interactive Leaflet maps, chat panel
    ├── hooks/                # Custom React hooks (theme, language, state)
    ├── lib/                  # API clients, translation dictionary, geocoding & types
    ├── package.json          # Frontend dependencies
    └── .env.example          # Frontend environment variable template
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+** and **npm**

### 2. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your configuration

# Run backend development server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Interactive API documentation will be available at `http://127.0.0.1:8000/docs`.

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Configure environment
copy .env.example .env.local

# Run frontend development server
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 🔒 Security & Environment Variables

Sensitive secrets, API keys, credentials, and local environment files (`.env`, `.env.local`) are strictly excluded from version control via `.gitignore`. Always populate credentials via local `.env` files using `.env.example` as a template.

---

## 📄 License
This project is licensed under the MIT License.

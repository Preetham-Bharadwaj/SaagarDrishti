# SaagarDrishti (ಸಾಗರದೃಷ್ಟಿ)

> **Agentic AI-powered Marine Intelligence Platform for the Karnataka Coast**

SaagarDrishti is a backend workspace designed to ingest, validate, analyze, and orchestrate marine intelligence data along the ~320 km coastline of Karnataka (stretching from Talapady/Mangalore to Karwar/Majali). 

This repository provides the foundational, modular backend structure built with **Python** and **FastAPI**, featuring typed Pydantic models, geospatial utilities, data ingestion services, multi-agent orchestration scaffolding, and dataset exploration notebooks.

---

## 📁 Project Structure & File Guide

Below is the directory breakdown explaining the purpose of each component:

```
Saagardristi/
│
├── .env.example                # Template for environment variables (copy to .env)
├── .gitignore                  # Git ignore rules for caches, virtual environments, & datasets
├── README.md                   # Project documentation and Windows setup guide
├── requirements.txt            # Python dependencies (FastAPI, Pydantic, Shapely, Pytest, etc.)
│
├── app/                        # Main application package
│   ├── __init__.py             # App version and package initialization
│   ├── main.py                 # FastAPI application entrypoint with middleware and routes
│   │
│   ├── core/                   # Global configuration and settings
│   │   ├── __init__.py         # Exports application settings
│   │   └── config.py           # Pydantic BaseSettings loading from environment/.env
│   │
│   ├── api/                    # API routing layer
│   │   ├── __init__.py         # API router package
│   │   ├── router.py           # Top-level API router merging versioned endpoints
│   │   └── v1/
│   │       ├── __init__.py     # V1 router package
│   │       └── health.py       # Health check and service status endpoints
│   │
│   ├── schemas/                # Typed request and response models (Pydantic)
│   │   ├── __init__.py         # Exports all data schemas
│   │   ├── common.py           # Base API responses, coordinates, and bounding boxes
│   │   ├── pfz.py              # Potential Fishing Zone (PFZ) advisory schemas
│   │   └── marine.py           # Oceanographic parameter schemas (SST, Chlorophyll, Waves)
│   │
│   ├── adapters/               # External marine data source adapters
│   │   ├── __init__.py         # Exports data adapters
│   │   ├── base.py             # Abstract BaseMarineDataAdapter interface
│   │   └── incois.py           # INCOIS (Indian National Centre for Ocean Information Services) adapter
│   │
│   ├── services/               # Core business logic and ingestion pipelines
│   │   ├── __init__.py         # Exports domain services
│   │   └── pfz_ingestion.py    # PFZ advisory ingestion, validation, and geographic boundary checks
│   │
│   ├── agents/                 # Multi-agent orchestration scaffolding
│   │   ├── __init__.py         # Exports base agent and orchestrator
│   │   ├── base.py             # Abstract BaseAgent interface with async run() contract
│   │   └── orchestrator.py     # AgentOrchestrator for managing multi-agent dispatch
│   │
│   └── geo/                    # Geospatial tools and coastal boundaries
│       ├── __init__.py         # Exports geospatial utilities
│       └── coordinates.py      # Karnataka bounding box, landing centers (Malpe, Karwar, etc.), distance calc
│
├── data/                       # Marine datasets directory (ignored by git, preserved with .gitkeep)
│   ├── raw/                    # Raw satellite/INCOIS downloaded data
│   └── processed/              # Cleaned, structured, or cached files
│
├── notebooks/                  # Dataset exploration notebooks
│   └── 01_karnataka_coast_exploration.ipynb  # Interactive coastal coordinate and boundary exploration
│
└── tests/                      # Automated unit test suite
    ├── __init__.py             # Test package initialization
    ├── conftest.py             # Pytest fixtures and FastAPI TestClient
    ├── test_health.py          # Tests for root and health check endpoints
    ├── test_schemas.py         # Tests for Pydantic validation rules
    ├── test_geo.py             # Tests for Karnataka bounding box & distance formulas
    └── test_pfz_ingestion.py   # Tests for PFZ advisory validation logic
```

---

## 🛠️ Windows Setup Guide

Follow these steps using **PowerShell** or **Command Prompt** to set up and run the workspace on Windows.

### Prerequisites
- **Python 3.10+** (Confirm by running `python --version`)
- **Git**

---

### Step 1: Open Terminal in Project Directory
Open PowerShell and navigate to the project directory:
```powershell
cd c:\Users\ASUS\OneDrive\Documents\GitHub\Saagardristi
```

---

### Step 2: Create a Python Virtual Environment
Creating a dedicated virtual environment ensures dependencies do not conflict with other Python projects on your machine:

```powershell
python -m venv .venv
```

---

### Step 3: Activate the Virtual Environment
Activate the environment in your shell:

**PowerShell:**
```powershell
.\.venv\Scripts\Activate.ps1
```
*(Note: If you receive a script execution policy error in PowerShell, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once, then re-run the activation script.)*

**Command Prompt (cmd):**
```cmd
.\.venv\Scripts\activate.bat
```

Once activated, your terminal prompt will show `(.venv)`.

---

### Step 4: Install Dependencies
Upgrade pip and install the project requirements:
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 5: Configure Environment Variables
Copy the template configuration file to `.env`:

**PowerShell:**
```powershell
Copy-Item .env.example .env
```

**Command Prompt:**
```cmd
copy .env.example .env
```

You can customize parameters such as `APP_PORT` or `DEBUG` in `.env`.

---

## 🚀 Running the API Server

Start the development server with live reload enabled:
```powershell
uvicorn app.main:app --reload
```

- **Root Endpoint**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Health Check**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
- **Interactive API Docs (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative Docs (ReDoc)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Running Unit Tests

Run the complete test suite using `pytest`:
```powershell
pytest -v
```

To run a specific test module:
```powershell
pytest tests/test_geo.py -v
pytest tests/test_pfz_ingestion.py -v
```

---

## 📓 Dataset Exploration Notebooks

To run and explore the Karnataka coast marine datasets using Jupyter:
```powershell
jupyter lab
```
Navigate to `notebooks/01_karnataka_coast_exploration.ipynb` in the browser interface.

---

## 📡 INCOIS Data Acquisition & Ingestion

SaagarDrishti connects directly to the official operational **INCOIS GeoServer WFS** services and supports authorized manual file ingestion.

### Verified Upstream Endpoint:
- **Service**: INCOIS GeoServer WFS (Web Feature Service)
- **Base URL**: `https://incois.gov.in`
- **WFS Endpoint**: `/geoserver/PFZ_LandingCentres/ows`
- **Feature Layer**: `PFZ_LandingCentres:LandingCenters_29Apr2024`
- **Karnataka CQL Filter**: `SECTOR_NAM='KARNATAKA'`
- **Full Query URL**:
  ```
  https://incois.gov.in/geoserver/PFZ_LandingCentres/ows?service=WFS&version=1.1.0&request=GetFeature&typeName=PFZ_LandingCentres:LandingCenters_29Apr2024&outputFormat=application/json&CQL_FILTER=SECTOR_NAM='KARNATAKA'
  ```

---

### Command-Line Ingestion Example (Windows)

Make sure your virtual environment is activated (`.\.venv\Scripts\Activate.ps1`), then run:

#### 1. Ingest Local Authorized File (Offline / Safe Mode):
```powershell
python scripts/ingest_karnataka_pfz.py --file tests/fixtures/incois_karnataka_sample.json
```

#### 2. Live Acquisition from INCOIS WFS:
```powershell
python scripts/ingest_karnataka_pfz.py --live
```

---

### Manual Download & Ingestion Procedure

If direct outbound internet access is restricted or an authorized advisory file is distributed offline:

1. **Download via Web Browser**:
   - Open the verified INCOIS WFS query in your browser:
     [INCOIS Karnataka PFZ WFS Query](https://incois.gov.in/geoserver/PFZ_LandingCentres/ows?service=WFS&version=1.1.0&request=GetFeature&typeName=PFZ_LandingCentres:LandingCenters_29Apr2024&outputFormat=application/json&CQL_FILTER=SECTOR_NAM=%27KARNATAKA%27)
   - Save the returned JSON/GeoJSON payload to your local project:
     `c:\Users\ASUS\OneDrive\Documents\GitHub\Saagardristi\backend\data\raw\incois_karnataka_latest.json`
2. **Execute Ingestion & Validation**:
   ```powershell
   python scripts/ingest_karnataka_pfz.py --file data/raw/incois_karnataka_latest.json
   ```
3. **Audit Report**:
   The ingestion service checks for missing coordinates, invalid ranges, duplicate records, expired dates, and generates a structured summary.

---

## 🧭 Next Steps
1. **Specialized AI Agents**: Subclass `BaseAgent` in `app/agents/` to create domain agents (e.g., Fishing Advisory Agent, Marine Weather Alert Agent, Coastal Hazard Agent).
2. **Spatial Queries**: Expand `app/geo/` to interface with GeoJSON/Shapefiles representing Karnataka fishing zones, bathymetric contours, and marine protected areas.


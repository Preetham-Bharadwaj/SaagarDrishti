# Marine Weather & Coastal Hazard Source Audit Report

**Date of Audit**: October 26, 2026  
**Target Region**: Karnataka Coast (12.5°N - 15.2°N, 73.0°E - 75.3°E)  
**System**: SaagarDrishti Marine Intelligence Platform  
**Auditor**: Antigravity AI Engineering Team  

---

## 1. Executive Summary & Regulatory Grounding

Maritime safety off the Karnataka coastline (spanning ~320 km across Dakshina Kannada, Udupi, and Uttara Kannada districts) depends critically on accurate sea-state forecasting and statutory government warnings. Small-scale fishing vessels (<15 m Length Overall) face severe capsizing risks from steep swell waves and breaking surf in coastal waters.

### Authoritative Agency Roles:
1. **India Meteorological Department (IMD)**: Official statutory authority for weather forecasts, cyclone alerts, and coastal warning bulletins for Indian territorial waters.
2. **Indian National Centre for Ocean Information Services (INCOIS)**: Provides High Wave Alerts, Ocean State Forecasts (OSF), and Swell Surge warnings.
3. **Department of Fisheries, Government of Karnataka (DFO)**: Issues port closure orders, seasonal monsoon fishing ban enforcement (typically June 1 - July 31), and VHF marine radio alerts.

---

## 2. Official IMD Marine Bulletin Investigation & Ingestion Architecture

### 2.1 Live Portal Inspection & Findings
* **Portal**: [https://mausam.imd.gov.in/responsive/marine_forecast.php](https://mausam.imd.gov.in/responsive/marine_forecast.php)
* **Inspection Details**:
  * Live inspection of the public web portal revealed that coastal weather warnings are linked through client-side JavaScript switch statements (e.g., `case 'link5'` for Kerala, Karnataka, Lakshadweep).
  * The actual bulletin documents are unversioned, dynamically hashed PDF files (e.g., `../../backend/assets/cwc_thiru_pdf/0c5c213741ad73c5f435d6ca199a9327.pdf`) accompanied by rendered multi-page image scans (`1_fishermen warning_<hash>.png`).
  * Programmatic REST/JSON APIs under IMD / MoES are not publicly exposed without ministerial credentials and fixed-IP whitelisting.
* **Architecture Decision**:
  * Because the public website links change hash names unpredictably upon staff upload and consist of unstructured multi-page PDFs with visual bilingual text, **automated scraping of this endpoint is fragile and cannot be guaranteed reliable for automated life-safety decisions**.
  * Inventing undocumented endpoints is strictly prohibited.
  * **Solution**: SaagarDrishti implements a verified **Manual Ingestion Pipeline** for authorized official IMD bulletins via `OfficialWarningService` and `scripts/ingest_imd_warning.py`.

### 2.2 Manual Ingestion Workflow
Official IMD bulletins received via fax, email, or downloaded from CWC Thiruvananthapuram are ingested into the platform using standardized JSON payloads:

```powershell
# Ingest an official verified IMD bulletin:
.\.venv\Scripts\python.exe scripts/ingest_imd_warning.py --file <path_to_bulletin.json>

# Ingest the verified sample fixture:
.\.venv\Scripts\python.exe scripts/ingest_imd_warning.py --sample
```

**Validated Bulletin Attributes**:
* `bulletin_id`: Unique identifier (e.g., `IMD-CWC-THIRU-20261026-FW01`)
* `issuing_authority`: Official body (e.g., `IMD Cyclone Warning Centre, Thiruvananthapuram`)
* `issued_at`, `valid_from`, `valid_to`: UTC/local timestamps enforcing `valid_from <= now <= valid_to`
* `severity`: `NO_WARNING`, `ADVISORY`, `WARNING`, `SEVERE_WARNING`
* `fishermen_advised_not_to_venture`: Explicit life-safety flag
* `warning_text`: Full verbatim alert text

---

## 3. Open-Meteo Marine Weather API: NWP Model Forecast Verification

To provide continuous, high-resolution physical wave parameters without undocumented scraping, SaagarDrishti integrates the **Open-Meteo Marine Weather API**.

### 3.1 Model vs. Observation Distinction
* **Critical Clarification**: Open-Meteo outputs are **Numerical Weather Prediction (NWP) model forecasts** (ECMWF / ERA5-Wave / GFS-Wave), **NOT in-situ buoy or coastal sensor observations**.
* The schemas in `app/schemas/marine_hazard.py` explicitly designate these hourly steps as `HourlyMarineForecastStep` with `is_model_forecast: True`.

### 3.2 Endpoint Telemetry & Specifications
* **Base URL**: `https://marine-api.open-meteo.com/v1/marine`
* **Coverage**: Global maritime waters on a 0.083° to 0.1° spatial grid (~9 km resolution).
* **Grid Resolution**: Coordinates are snapped to the nearest marine grid point (~9 km offshore), not onshore beach lines.
* **Update Cadence**: 4 times daily; hourly forecast slices up to 7 days ahead.
* **Timezone Handling**: Local timestamps returned in `Asia/Kolkata` (UTC+5:30). If offset is missing, system safely defaults to +19800s.
* **Field Specifications & Units**:
  | Field | Type | Units | Description |
  |---|---|---|---|
  | `wave_height` | `float` | meters (m) | Combined significant wave height |
  | `wind_wave_height` | `float` | meters (m) | Locally wind-generated wave component |
  | `swell_wave_height` | `float` | meters (m) | Distant swell wave component |
  | `wave_direction` | `float` | degrees (0–360°) | Mean wave propagation direction from North |
  | `wave_period` | `float` | seconds (s) | Mean wave period |
  | `swell_wave_direction` | `float` | degrees (0–360°) | Swell propagation direction |
  | `swell_wave_period` | `float` | seconds (s) | Swell wave period |

---

## 4. Sea-State Classification Thresholds & Documented Origin

### 4.1 Documented Source
The sea-state categories used in SaagarDrishti originate from the **Douglas Sea State Scale** and **World Meteorological Organization (WMO) Code Table 3700**:

| Wave Height Range ($H_s$) | WMO / Douglas Sea State | SaagarDrishti Small-Craft Prototype Label |
|---|---|---|
| `< 0.50 m` | State 0–2: Calm (glassy/rippled) to Smooth | `CALM` |
| `0.50 m - 1.25 m` | State 3: Slight | `SLIGHT` |
| `1.25 m - 2.50 m` | State 4: Moderate | `MODERATE` |
| `2.50 m - 4.00 m` | State 5: Rough | `ROUGH` |
| `> 4.00 m` | State 6+: Very Rough / High / Phenomenal | `VERY_ROUGH` |
| `null / missing` | Unknown / Model error | `UNKNOWN` |

### 4.2 Intended Use & Boundaries
> [!IMPORTANT]
> **Regulatory Boundary**:
> * These thresholds are adapted in SaagarDrishti solely as an **exploratory prototype descriptive heuristic** for small artisanal coastal fishing craft (<15 m Length Overall).
> * They are **NOT statutory warnings issued by IMD or the Karnataka Department of Fisheries**.
> * They are **NOT universal vessel safety limits**. Suitability depends on vessel hull type, engine reliability, skipper experience, and localized bar conditions.
> * The platform **never claims a location is safe solely from wave height**.

---

## 5. Safety Governance & The Discrepancy Override Rule

### 5.1 Strict Separation of Sources
Official statutory warnings (`OfficialMarineWarning`) and numerical model forecasts (`MarineHazardForecast`) are maintained in separate, distinct data structures. They are never conflated or averaged.

### 5.2 Discrepancy Detection & Statutory Override
If an active official IMD/DFO bulletin issues a `WARNING` or `SEVERE_WARNING` (or flags `fishermen_advised_not_to_venture = True`), while the numerical wave model indicates `CALM` or `SLIGHT` waves (e.g. 0.65 m wave height during squally pre-monsoon convective winds):

1. The system flags `sources_disagree = True` in both `evidence_audit` and `response`.
2. The response highlights the conflict prominently at the very top:
   > **⚠️ DISCREPANCY DETECTED**: While the ECMWF/ERAssWave numerical model indicates Slight seas (0.65 m), the India Meteorological Department has issued an active WARNING: *"[Official Warning Text]"*.
   > **STATUTORY OVERRIDE**: Official government warnings strictly supersede all numerical model outputs and prototype heuristics. Small-craft fishers are advised NOT to venture into sea.

### 5.3 Stale & Missing Forecast Governance
* If upstream model data is missing (all wave heights null) or stale (latest forecast time step is in the past), the platform returns `DATA_UNAVAILABLE`.
* The platform returns:
  * Source timestamp (`retrieved_at`)
  * Target location and model grid coordinates (`latitude`, `longitude`)
  * Spatial grid resolution (~9 km)
  * Explicit limitations and fallback instructions
* **Absence of Warning != Safe**: Missing or stale forecast data is **never** presented as an indication of calm or safe sea conditions.

---

## 6. How to Run Verification & Testing

### Live Smoke Test
```powershell
# Executes live request to Open-Meteo Marine API:
.\.venv\Scripts\python.exe scripts/marine_hazard_smoke_test.py
```

### Full Test Suite (Offline & Mocked)
```powershell
# Executes all unit and integration tests deterministically:
.\.venv\Scripts\python.exe -m pytest -v
```
All unit tests run deterministically against verified fixtures without requiring internet connectivity.

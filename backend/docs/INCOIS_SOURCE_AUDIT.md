# INCOIS Source Verification Audit Report

**Date of Audit**: October 26, 2026  
**Target System**: SaagarDrishti Marine Intelligence Platform (Karnataka Coast)  
**Auditor**: Antigravity AI Pair Programmer  

---

## ⚠️ Critical Operational Safety Notice

> **IMPORTANT**: Marine intelligence advisories directly affect human safety and vessel navigation at sea.
> SaagarDrishti adheres to strict ethical guidelines:
> 1. Under **no circumstances** will historical or reference data be presented to fishers as active live Potential Fishing Zones (PFZ).
> 2. Synthetic, simulated, or fabricated coordinates must **never** be generated or passed off as real advisory coordinates.
> 3. SaagarDrishti will **never assert or imply that maritime navigation or fishing is safe** in any zone without authoritative, current, unexpired advisories and meteorological clearance from official agencies (INCOIS / IMD).

---

## 1. Live Execution Audit

On October 26, 2026, the live ingestion script was executed against the official upstream endpoint:

```powershell
python scripts/ingest_karnataka_pfz.py --live
```

### Execution Telemetry & Request Details:
* **HTTP Command**: `GET`
* **Target URL**:  
  `https://incois.gov.in/geoserver/PFZ_LandingCentres/ows?service=WFS&version=1.1.0&request=GetFeature&typeName=PFZ_LandingCentres:LandingCenters_29Apr2024&outputFormat=application/json&CQL_FILTER=SECTOR_NAM='KARNATAKA'`
* **HTTP Response Status**: `200 OK`
* **Response Content-Type**: `application/json;charset=utf-8`
* **Payload Size**: 20,800 bytes
* **Feature Count**: 29 features returned
* **Errors**: None encountered during HTTP transport or JSON parsing.
* **Audit Result**:
  * **Structure Valid**: `PASSED`
  * **Validity Status**: `EXPIRED`
  * **Expiry Notice**: `Advisory is expired (validity ended on 2024-04-28 18:30 UTC)`

---

## 2. Geometry vs. Attribute Analysis

Inspection of the raw GeoJSON objects revealed a critical architectural distinction between the layer's **geometry** and its **properties**:

```json
{
  "type": "Feature",
  "id": "LandingCenters_29Apr2024.73",
  "geometry": {
    "type": "Point",
    "coordinates": [74.79000092, 13.0]
  },
  "properties": {
    "OBJECTID": 126,
    "SECTOR_NAM": "KARNATAKA",
    "DIST_NAME": "Dakshina Kannada",
    "LC_NAME": "Suratakal Pt",
    "LC_UNIQUE_": "KA0302a",
    "LONGITUDE": 74.79,
    "LATITUDE": 13.0,
    "FORECAST_I": 32599,
    "FORECAST_D": "2024-04-27T18:30:00Z",
    "VALIDITY_D": "2024-04-28T18:30:00Z",
    "DIRECTION": "NW",
    "BEARING": 279,
    "DISTANCE_F": 12,
    "DISTANCE_T": 17,
    "DEPTH_FROM": 23,
    "DEPTH_TO": 28,
    "LATITUDE_D": 13,
    "LATITUDE_M": 1,
    "LATITUDE_S": 11,
    "LATITUDE_1": "N",
    "LONGITUDE_": 74,
    "LONGITUDE1": 39,
    "LONGITUD_1": 50,
    "LONGITUD_2": "E",
    "STATUS": "YES"
  }
}
```

### Key Findings:
1. **The Feature Geometry is NOT a PFZ Location**:
   * The GeoJSON `geometry.coordinates` (`[74.79, 13.0]`) represent the **onshore / coastal fish landing center** (`Suratakal Pt`), matching `LONGITUDE` and `LATITUDE`.
   * These geometries are spatial reference landmarks on the Karnataka coastline.
2. **The Target PFZ Coordinates are Stored Only in Table Properties**:
   * The actual offshore fishing zone coordinate is recorded in degree-minute-second (DMS) properties:
     `13° 1' 11" N`, `74° 39' 50" E` (decimal: `13.01972°N, 74.66389°E`).
   * This hotspot lies ~14.5 km northwest of Surathkal port at an ocean depth of 23–28 meters.
3. **Classification**:
   * This layer is a **Coastal Landing Center Reference Layer** carrying **embedded historical advisory attributes**. It must not be treated as a pure geometry point cloud of current fish aggregation zones.

---

## 3. Temporal Analysis & Portal Comparison

The temporal validity of the WFS layer was audited against other live INCOIS services:

| Source Channel | Source URL / Layer | Published Validity Period | Status for Karnataka Coast |
| :--- | :--- | :--- | :--- |
| **GeoServer WFS** | `PFZ_LandingCentres:LandingCenters_29Apr2024` | `2024-04-27T18:30:00Z` to `2024-04-28T18:30:00Z` | **Historical Snapshot** (Lapsed April 2024) |
| **GeoServer WFS (Lines)** | `PFZ_Automation:pfzlines` | Year 2026, Julian Day 295 (October 2026) | **0 features for Karnataka** (only GUJ, MH, GOA, AND, NIC present) |
| **WebGIS Data Process** | `MarineFisheries/dataprocess.jsp?lcid=...` | `2025-01-08` to `2025-01-09` | **Historical Broadcast** (23 of 29 centers active in DB) |
| **Official Text Portal** | `MarineFisheries/TextDataHome?mfid=1` | N/A | **No Active Table** (Displays general methodology text) |

### Evidence & GeoServer Metadata:
* Querying `https://incois.gov.in/geoserver/PFZ_LandingCentres/ows?service=WFS&version=1.1.0&request=GetCapabilities` confirmed that only one FeatureType exists in this namespace: `LandingCenters_29Apr2024`.
* The layer identifier explicitly incorporates the date string `29Apr2024`.
* Conclusion: The GeoServer WFS landing centers layer is a **static reference dataset published on April 29, 2024**, and is **not an automatically updating operational feed**.

---

## 4. Fixture Provenance & Test Audit

* **File**: [`tests/fixtures/incois_karnataka_sample.json`](file:///c:/Users/ASUS/OneDrive/Documents/GitHub/Saagardristi/backend/tests/fixtures/incois_karnataka_sample.json)
* **Provenance**: Actual verbatim response slice (3 features) downloaded directly from the live INCOIS GeoServer WFS endpoint on October 26, 2026 (`Suratakal Pt`, `Belekeri`, `Udiyavara`).
* **Integrity Classification**: Confirmed authentic historical source payload.
* **Labeling**: Tests strictly treat this fixture as a historical snapshot. Unit tests in [`tests/test_pfz_ingestion.py`](file:///c:/Users/ASUS/OneDrive/Documents/GitHub/Saagardristi/backend/tests/test_pfz_ingestion.py) explicitly verify that our ingestion validation flags it as `is_expired = True` when evaluated against current timestamps.

---

## 5. Verified Retrieval Paths & Upstream Blockers

### Verified Acquisition Paths:
1. **Landing Center Spatial Reference Base**:
   * Method: Query `PFZ_LandingCentres:LandingCenters_29Apr2024` via WFS.
   * Utility: Establishes the authoritative 29 official Karnataka landing centers, administrative sectors, and local bearing baselines.
2. **Tabular Advisory Scraper (`dataprocess.jsp`)**:
   * Method: `GET https://incois.gov.in/MarineFisheries/dataprocess.jsp?lcid={LC_ID}&mfid=1`
   * Utility: Queries INCOIS's internal database table for each landing center.
   * Limitation: Subject to HTML parsing and upstream formatting errors (e.g., INCOIS swapped the textual headers for Latitude and Longitude in their HTML output, though degree suffixes `N`/`E` remain accurate).
3. **Manual Authorized File Ingestion**:
   * Method: `PFZIngestionService.ingest_from_file(path)`
   * Utility: Allows operators to ingest daily bulletins downloaded directly from INCOIS or state fisheries departments.

### Current Upstream Blockers for Live Real-Time Feeds:
* **No Public REST API**: INCOIS does not currently offer a versioned, documented REST/JSON API for live PFZ streaming.
* **Monsoon & Cloud Occlusion**: Optical and thermal satellite sensors (MODIS, Oceansat) cannot penetrate dense monsoon cloud cover; during these intervals, INCOIS suspends PFZ generation for the Karnataka sector.
* **Static WFS Layering**: The primary GeoServer WFS endpoint has not had a newer landing center layer published since April 2024.

---

## 6. Recommendations for SaagarDrishti Backend

1. **Role Separation**:
   * Maintain `PFZ_LandingCentres` strictly as **Spatial Reference Data** for coastal departure points.
   * Distinguish landing center coordinates (`landing_center_coordinate`) from target hotspots (`coordinate`).
2. **Mandatory Expiration Enforcement**:
   * The `PFZIngestionService.validate_advisory()` logic must continue to enforce the `is_expired` check, preventing expired advisories from driving active user alerts.
3. **Fallback to Multi-Sensor Pipeline**:
   * In future development phases, live SST and Chlorophyll-a raster layers (from Copernicus/NOAA or INCOIS ERDDAP/THREDDS) should complement tabular bulletins when cloud cover permits.

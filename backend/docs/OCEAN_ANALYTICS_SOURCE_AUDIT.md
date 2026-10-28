# Ocean Analytics & Copernicus Marine Data Store Source Audit Report

**Date of Audit**: October 26, 2026  
**Target Region**: Arabian Sea & Karnataka Coastal Waters (12.5°N - 15.2°N, 73.0°E - 75.3°E)  
**System**: SaagarDrishti Marine Intelligence Platform  
**Auditor**: Antigravity AI Engineering Team  

---

## 1. Executive Summary & Scope

To enhance maritime situational awareness and environmental intelligence along the Karnataka coast, SaagarDrishti investigates and implements its first **Ocean Analytics** capability.

This audit:
1. Inspects the official **Copernicus Marine Data Store (CMEMS)** operated by Mercator Ocean International for the European Commission.
2. Identifies and verifies the authoritative sea-surface temperature (SST) product covering the Arabian Sea and Karnataka coastal waters: **OSTIA Global Ocean SST Level-4**.
3. Investigates satellite-derived bio-geo-chemical chlorophyll-a products as subsequent biological variables.
4. Documents technical specifications (product IDs, resolution, units, temporal cadence, access terms).
5. Implements `OceanDataAdapter` with typed normalization, deterministic spatial summaries, and offline fallback fixture support.
6. Enforces strict **Ecological and Safety Boundaries**, prohibiting unsupported inferences of fish abundance or vessel safety from SST alone.

---

## 2. Copernicus Marine Product Verification

### 2.1 Primary Product: Operational Sea Surface Temperature (SST)

* **Product Title**: Global Ocean OSTIA Sea Surface Temperature and Sea Ice Analysis
* **Product Identifier**: `SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001`
* **Dataset Identifier**: `cmems_SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001`
* **Production Center**: UK Met Office, under Copernicus Marine Service (CMEMS)
* **Product Classification**: **Level-4 (L4) Multi-Sensor Satellite Analysis** with in-situ data assimilation (Optimal Interpolation).
* **Spatial Coverage**: Global ($180^\circ\text{W} - 180^\circ\text{E}, 90^\circ\text{S} - 90^\circ\text{N}$), fully covering the Arabian Sea and Karnataka shelf waters ($12.5^\circ\text{N} - 15.2^\circ\text{N}, 73.0^\circ\text{E} - 75.3^\circ\text{E}$).
* **Spatial Resolution**: $0.05^\circ \times 0.05^\circ$ (~5.5 km grid spacing).
* **Temporal Resolution & Update Cadence**: Daily foundation SST (issued daily around 06:00 UTC for the previous day, representing foundation water temperature free of diurnal solar warming).
* **Original Data Format**: NetCDF-4 (Climate and Forecast Metadata Convention CF-1.4 / CF-1.7).
* **Core Variables & Units**:
  * `analysed_sst`: Foundation sea surface temperature in **Kelvin (K)**.
  * `analysis_error`: Standard deviation of the error estimate in **Kelvin (K)**.
  * `mask`: Land/sea/ice classification flag ($1 = \text{ocean}, 2 = \text{land}, 3 = \text{sea ice}$).
  * `sea_ice_fraction`: Fractional ice cover ($0.0 - 1.0$).
* **Standardization & Unit Conversion**:
  $$T_{\text{Celsius}} = T_{\text{Kelvin}} - 273.15$$
  SaagarDrishti preserves `value_raw` (in Kelvin) and computes `value_si` (in Celsius) rounded deterministically to 2 decimal places.

### 2.2 Secondary Product: Bio-Geo-Chemical Chlorophyll Concentration

* **Product Title**: Global Ocean Bio-Geo-Chemical L4 NRT Observations
* **Product Identifier**: `OCEANCOLOUR_GLO_BGC_L4_NRT_009_102`
* **Dataset Identifier**: `cmems_obs-oc_glo_bgc-plankton_nrt_l4-gapfree-multi-4km_P1D`
* **Production Center**: ACRI-ST / Copernicus Ocean Colour Thematic Assembly Centre (OCTAC)
* **Product Classification**: **Level-4 Gap-Free Interpolated Ocean Colour Analysis**
* **Spatial Resolution**: 4 km ($0.0416^\circ$) or $0.25^\circ$ daily product.
* **Core Variables**: `CHL` (Mass concentration of chlorophyll-a in sea water, $\text{mg}/\text{m}^3$).
* **Operational Verification Status**:
  * Product structure verified in Copernicus catalogue.
  * Identified as subsequent biological layer to complement physical SST once authenticated CMEMS data access pipeline is active.

---

## 3. Product Categorization & Scientific Distinctions

It is critical in marine systems to distinguish among data types rather than conflating them:

| Category | Definition in SaagarDrishti | Copernicus OSTIA Level-4 SST Status |
| :--- | :--- | :--- |
| **Level-4 Satellite Analysis** (`L4_SATELLITE_ANALYSIS`) | Gridded, gap-free product produced by optimal interpolation blending multiple satellite sensors (infrared and microwave) with in-situ drifting buoys and ship observations. | **YES**. OSTIA removes clouds and diurnal warm layers to represent foundation SST. |
| **Satellite-Derived Swath** (`L3_SATELLITE_COLLATED`) | Raw or collated single-satellite track observations with gaps due to cloud cover and orbital passes. | **NO**. OSTIA is gap-free L4. |
| **Numerical Model Forecast** (`NUMERICAL_MODEL_FORECAST`) | Physics-based predictive hydrodynamic simulation (e.g., ECMWF, NEMO, GFS-Wave). | **NO**. OSTIA is an observational analysis, not a forward prognostic model forecast. |
| **In-Situ Sensor** (`IN_SITU_SENSOR`) | Direct physical telemetry from moored buoys, Argo floats, or coastal tide gauges. | **NO**, although in-situ measurements are assimilated into the OSTIA analysis. |

---

## 4. Access Requirements, Usage Terms & Credential Blocker Audit

### 4.1 Usage Terms & Licensing
* **License**: Copernicus Open Access (Creative Commons Attribution 4.0 International / CC-BY 4.0).
* **Permitted Use**: Free and open for operational, commercial, and research applications, provided attribution is given to Copernicus Marine Service.

### 4.2 Access Protocol & Authentication Blocker
* **Data Portal**: [https://data.marine.copernicus.eu/](https://data.marine.copernicus.eu/)
* **Authentication Authority**: Keycloak OpenID Connect / CAS at `https://auth.marine.copernicus.eu/`.
* **Access Policy**:
  * Unauthenticated programmatic access to the Copernicus Marine Data Store returns **HTTP 401 Unauthorized** or **HTTP 403 Forbidden**.
  * Access requires a free registered user account.
  * Required environment variables in SaagarDrishti:
    * `COPERNICUSMARINE_SERVICE_USERNAME`
    * `COPERNICUSMARINE_SERVICE_PASSWORD`
* **Audit Result**:
  * Live probe without credentials correctly detected and reported:
    * **Status**: `CREDENTIALS_REQUIRED` (HTTP 401).
    * **Honest reporting**: The system does NOT pretend to have fetched live data or fabricate fake temperatures.
    * **Status in Availability Service**: Explicitly recorded as `DataStatus.NOT_VERIFIED` with documentation of the credential requirement.

### 4.3 Audited Provenance of Test Fixture (`tests/fixtures/copernicus_sst_karnataka_sample.json`)
> [!IMPORTANT]
> **AUDIT FINDING ON FIXTURE PROVENANCE**:
> The file `tests/fixtures/copernicus_sst_karnataka_sample.json` is a **manually prepared synthetic test fixture** constructed according to UK Met Office OSTIA L4 specifications (0.05° grid spacing, Kelvin values, land masking, realistic analysis error ~0.35 K) for offline unit testing and schema validation.
> It is **NOT** a real downloaded binary/NetCDF subset directly from the live Copernicus Marine API, because live downloads require registered user credentials which have not yet been provided.
> SaagarDrishti strictly enforces honest data provenance: `is_real_download: false` and `fixture_type: "MANUALLY_PREPARED_TEST_FIXTURE"`. No live provenance is claimed without cryptographic or network verification evidence.

### 4.4 Configuring Copernicus Credentials in Local `.env`
To configure live Copernicus access securely without exposing secrets:
1. Register for a free account at [https://data.marine.copernicus.eu/](https://data.marine.copernicus.eu/).
2. Copy the template configuration file:
   ```powershell
   Copy-Item .env.example .env
   ```
3. Open `.env` in your local editor and set the credentials:
   ```bash
   COPERNICUSMARINE_SERVICE_USERNAME=your_copernicus_username_here
   COPERNICUSMARINE_SERVICE_PASSWORD=your_copernicus_password_here
   ```
4. **Security Notice**:
   * `.env` is explicitly ignored in `.gitignore` (along with `.env.local`, `*.key`, `*.pem`).
   * **NEVER** commit `.env` to Git or version control.
   * `scripts/ocean_analytics.py` and application logs never print or log passwords.

---

## 5. Critical Ecological & Marine Safety Governance

### 5.1 Prohibition of Fish Abundance & Catch Inference from SST Alone
> [!CAUTION]
> **MANDATORY SAFETY & SCIENTIFIC CONSTRAINT**:
> SST alone **DOES NOT PROVE** fish abundance, catch yield, or a safe fishing location.
> Inferring commercial fish concentrations solely from sea-surface temperature is scientifically invalid and prohibited in SaagarDrishti.

**Scientific Justification**:
1. **Multi-Parameter Complexity**: Marine pelagic fish distribution is driven by primary biological productivity (phytoplankton/Chlorophyll-a), zooplankton abundance, mixed-layer depth, dissolved oxygen, and thermocline depth. SST is only a single physical boundary condition.
2. **Thermal Envelope Non-Uniqueness**: Water temperatures of $28^\circ\text{C} - 29^\circ\text{C}$ are standard across thousands of square kilometers of the tropical Arabian Sea; they do not isolate specific fish schools.
3. **Official Advisory Role**: INCOIS Potential Fishing Zone (PFZ) advisories combine concurrent thermal infrared gradients with ocean colour (Chlorophyll-a) front matching and seasonal validation. SaagarDrishti preserves INCOIS as the sole authoritative PFZ source.

### 5.2 Prohibition of Navigation Safety Claims from SST
* SST measures surface water thermal state; it provides zero information on significant wave height, wind gusts, swell period, or convective thunderstorm activity.
* Official IMD Marine Weather Bulletins and INCOIS Ocean State Forecasts remain the sole authorities for small-craft sea-state clearance.

Every `OceanAreaSummary` generated by SaagarDrishti attaches the mandatory statutory disclaimer:
> *"ECOLOGICAL & SAFETY NOTICE: Sea Surface Temperature (SST) is an oceanographic physical parameter. Thermal fronts or gradients may indicate upwelling or water mass boundaries, but SST ALONE DOES NOT PROVE fish abundance, catch yield, or maritime navigation safety. Operational fishing decisions require official multi-parameter advisories (INCOIS PFZ) and official statutory IMD weather clearances."*

---

## 6. Architecture & Spatial Gradient Algorithm

### 6.1 Schema Design (`app/schemas/ocean_analytics.py`)
* `OceanVariableType`: Enum (`analysed_sst`, `chlorophyll_a`, `analysis_error`, `sea_ice_fraction`).
* `OceanProductCategory`: Enum (`L4_SATELLITE_ANALYSIS`, `L3_SATELLITE_COLLATED`, `NUMERICAL_MODEL_FORECAST`, `IN_SITU_SENSOR`).
* `OceanGridPoint`: Normalized grid cell preserving raw value, SI value ($^\circ\text{C}$), units, coordinates, analysis error, land mask flag, and quality flags (`0=nominal, 2=land_masked, 3=invalid/missing`).
* `OceanAreaSummary`: Bounded statistical aggregation:
  * `mean_value`, `min_value`, `max_value`, `std_dev` across valid ocean cells.
  * `regional_range_celsius`: Macro-regional temperature range across all valid sea cells ($\max(T) - \min(T)$).
  * `max_spatial_gradient_c_per_km`: Maximum local horizontal gradient between neighboring valid sea cells ($^\circ\text{C}/\text{km}$).
  * `mean_spatial_gradient_c_per_km`: Mean local horizontal gradient across evaluated neighboring pairs ($^\circ\text{C}/\text{km}$).
  * `evaluated_neighbor_pairs_count`: Count of evaluated neighboring pairs within neighborhood radius.
  * `thermal_front_threshold_c_per_km`: Physical threshold ($0.0500^\circ\text{C}/\text{km}$).
  * `thermal_front_detected`: Boolean flag triggered only when $\max(\nabla T) \ge 0.0500^\circ\text{C}/\text{km}$.
  * `is_stale`: Boolean flag triggered if observation timestamp is older than 72 hours.
  * `gradient_notes`: Descriptive annotations distinguishing macro range from local gradients.
  * `ecological_disclaimer`: Mandatory disclaimer text.
* `OceanProductMetadata`: Complete provenance, licensing, production center, resolution, fixture audit, and observation timestamp.
* `OceanAnalyticsPayload`: Container encapsulating metadata, grid points, summary, and retrieval provenance.

### 6.2 Spatial Gradient vs. Regional Range Algorithm

SaagarDrishti strictly distinguishes between **Macro-Regional Temperature Range** and **Local Spatial Temperature Gradient**:

1. **Macro-Regional SST Range** ($^\circ\text{C}$):
   $$\text{Range}_{\text{regional}} = T_{\max} - T_{\min}$$
   * Represents the overall temperature span across the entire Karnataka coastal bounding box (~300 km).
   * **Limitation**: A temperature difference of $0.70^\circ\text{C}$ across 300 km is only $\approx 0.0023^\circ\text{C}/\text{km}$ and does NOT constitute a physical front. Regional range must never be confused with a localized thermal gradient.

2. **Local Horizontal Spatial Gradient** ($^\circ\text{C}/\text{km}$):
   $$\nabla T_{AB} = \frac{|T_A - T_B|}{d(A, B)} \quad \left[\frac{^\circ\text{C}}{\text{km}}\right]$$
   where $d(A, B)$ is the great-circle distance computed via the Haversine formula.

3. **Neighborhood Distance Constraint**:
   * Evaluates pairs $(A, B)$ satisfying $0.5\text{ km} \le d(A, B) \le 40.0\text{ km}$.
   * Excludes distant cell pairs (e.g. Karwar to Mangalore at 220 km), preventing macro-scale regional differences from corrupting local front metrics.

4. **Land Barrier Filtering**:
   * For each candidate pair of valid sea cells $(A, B)$, the algorithm checks against all land-masked points $L$.
   * An intervening land cell blocks the direct path if:
     $$d(A, L) + d(L, B) \le d(A, B) \times 1.15 \quad \text{and} \quad \min(d(A, L), d(L, B)) \ge 0.5\text{ km}$$
   * Any pair traversing a land headland, barrier, or island is excluded from gradient calculation.

5. **Front Detection Threshold**:
   * Standard oceanographic threshold: $0.0500^\circ\text{C}/\text{km}$ (equivalent to $\ge 0.50^\circ\text{C}$ over 10 km).
   * Only gradients meeting or exceeding this threshold trigger `thermal_front_detected = True`.

6. **Physical Value Sanity & Staleness Enforcement**:
   * Physical sanity: $260.0\,\text{K} \le T_K \le 325.0\,\text{K}$ ($-13^\circ\text{C}$ to $+52^\circ\text{C}$) and $\text{error} \ge 0.0\,\text{K}$. Unphysical values receive `quality_flag = 3` and are omitted from calculation.
   * Staleness check: Observations older than 72 hours set `is_stale = True` and trigger explicit warning banners.

---

## 7. Verification Results

### 7.1 Local Analytics Verification (`scripts/ocean_analytics.py --local`)
* **Source**: `tests/fixtures/copernicus_sst_karnataka_sample.json` (Manually prepared test fixture)
* **Valid Ocean Cells**: 10
* **Land Masked Cells**: 3 (Karwar Port, Malpe Beach, Mangalore Port)
* **Missing Cells**: 0
* **Mean SST**: $28.39^\circ\text{C}$
* **Min SST**: $28.00^\circ\text{C}$ (Offshore Mangalore)
* **Max SST**: $28.70^\circ\text{C}$ (Coastal Karwar)
* **Spatial Standard Deviation**: $0.19^\circ\text{C}$
* **Mean Analysis Error**: $\pm 0.338\,\text{K}$
* **Regional SST Range**: $0.70^\circ\text{C}$ (macro spread across region)
* **Evaluated Neighbor Pairs**: 3 (Karwar 26.85 km, Honnavar 37.78 km, Bhatkal 37.94 km)
* **Max Local Spatial Gradient**: $0.0074^\circ\text{C}/\text{km}$
* **Mean Local Spatial Gradient**: $0.0060^\circ\text{C}/\text{km}$
* **Thermal Front Threshold**: $0.0500^\circ\text{C}/\text{km}$
* **Thermal Front Detected**: **NO** ($0.0074^\circ\text{C}/\text{km} < 0.0500^\circ\text{C}/\text{km}$).
  *(Correctly identifies that a gentle 0.70°C variation over 300 km is a regional spread, not a localized front).*

### 7.2 Live Network Probe & Authenticated Retrieval Verification (`scripts/ocean_analytics.py --live`)
* **Authentication Method**: OpenID Connect Password Grant via Keycloak (`https://auth.marine.copernicus.eu/realms/MIS/protocol/openid-connect/token`, Client ID: `toolbox`, Scope: `openid profile email`).
* **Authentication Result**: HTTP 200 OK (`Token type: Bearer`, validity: 300 seconds).
* **Data Retrieval Method**: Copernicus OGC Web Map Tile Service (WMTS) `GetFeatureInfo` endpoint (`https://wmts.marine.copernicus.eu/teroWmts`) querying layer `SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001/METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2/analysed_sst` in EPSG:4326.
* **Retrieved Observation Date**: `2026-10-25` (UK Met Office OSTIA Level-4 foundation SST daily analysis).
* **Live Retrieved Features**: 8 coastal points along Karnataka:
  - Karwar Offshore (14.80°N, 73.80°E): $303.35\,\text{K} \to 30.20^\circ\text{C}$ (Valid Ocean)
  - Karwar Coastal (14.80°N, 74.05°E): $303.25\,\text{K} \to 30.10^\circ\text{C}$ (Valid Ocean)
  - Honnavar Coastal (14.30°N, 74.20°E): $303.22\,\text{K} \to 30.07^\circ\text{C}$ (Valid Ocean)
  - Bhatkal Coastal (13.90°N, 74.30°E): $303.36\,\text{K} \to 30.21^\circ\text{C}$ (Valid Ocean)
  - Malpe Offshore (13.35°N, 74.50°E): $303.34\,\text{K} \to 30.19^\circ\text{C}$ (Valid Ocean)
  - Mangalore Offshore (12.85°N, 74.60°E): $303.24\,\text{K} \to 30.09^\circ\text{C}$ (Valid Ocean)
  - Mangalore Coastal (12.85°N, 74.75°E): $302.95\,\text{K} \to 29.80^\circ\text{C}$ (Valid Ocean)
  - Mangalore Onshore (12.85°N, 75.20°E): `null` $\to$ Land Masked (`quality_flag=2`)
* **Real Live Analytics Results**:
  - Valid Sea Cells: 7
  - Land Cells: 1
  - Mean SST: $30.09^\circ\text{C}$
  - Min SST: $29.80^\circ\text{C}$
  - Max SST: $30.21^\circ\text{C}$
  - Regional SST Range: $0.41^\circ\text{C}$
  - Max Spatial Gradient: $0.0178^\circ\text{C}/\text{km}$
  - Thermal Front Detected: **NO** ($0.0178^\circ\text{C}/\text{km} < 0.0500^\circ\text{C}/\text{km}$)
* **Secret Protection Audit**: Zero secrets or credentials logged or exposed. Username masked in metadata, passwords and JWT tokens completely omitted from logs and source control.
* **Credential Block Handling**: When environment variables are absent, adapter faithfully reports `CREDENTIALS_REQUIRED` (HTTP 401 blocker) with actionable onboarding instructions.

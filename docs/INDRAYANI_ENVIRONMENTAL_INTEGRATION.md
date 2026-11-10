# CLIMAFORGE — Real-Time Environmental Intelligence & Indrayani River Monitoring Integration

## Executive Overview
This technical integration document defines the architecture, data contracts, scientific honesty guarantees, and full-stack implementation of the **Real-Time Environmental Intelligence & Indrayani River Monitoring** module in CLIMAFORGE.

The module provides real-time ambient weather surveillance, high-resolution precipitation forecasting, official India Meteorological Department (IMD) weather warnings for Pune District, and environmental surface-water monitoring reference data along the **Indrayani River corridor** in Maharashtra, India.

---

## 1. Geographic Boundary & Corridor Definition

The scope of this integration is strictly bounded to the **Indrayani River Basin, Pune District, Maharashtra, India** (Krishna Basin / Bhima Sub-basin). It does not extrapolate to unverified nationwide rivers or uncalibrated national monitoring networks.

```
[Kurvande / Lonavala Ghats] (Source)
               |
               v
      [Dehu Pilgrimage Ghat] (Upper Corridor • Lat 18.7180, Lon 73.7680)
               |
               v
  [Moshi Village - MPCB Stn 11] (Primary Reference • Lat 18.68365, Lon 73.87855)
               |
               v
     [Alandi Pilgrimage Ghat] (Middle Corridor • Lat 18.6770, Lon 73.8960)
               |
               v
   [Tulapur Confluence / Sangam] (Confluence with Bhima River • Lat 18.5770, Lon 74.0150)
```

### Verified Geographical Reference Stations
1. **Primary Reference Station**:
   - **Station ID**: `MPCB-INDRAYANI-MOSHI-11`
   - **Station Name**: Indrayani River downstream of Moshi village
   - **Administrative Division**: Village: Moshi, Taluka: Haveli, District: Pune, Maharashtra, India
   - **Exact Coordinates**: Latitude `18.68365`, Longitude `73.87855`
   - **Monitoring Body**: Maharashtra Pollution Control Board (MPCB) / Central Pollution Control Board (CPCB)
   - **Official Citation**: MPCB Station 11, GEMS/MINARS 80 (`https://mpcb.ecmpcb.in/envtdata/gemsminar80.php`)
   - **Classification**: `WATER_QUALITY_MONITORING_REFERENCE`
   - **Telemetry Status**: `TELEMETRY_UNVERIFIED` / `TELEMETRY_UNAVAILABLE`

2. **Upper Corridor Station**:
   - **Station ID**: `INDRAYANI-DEHU-GHAT`
   - **Station Name**: Indrayani River at Dehu Ghat
   - **Coordinates**: Latitude `18.7180`, Longitude `73.7680`
   - **Classification**: `PILGRIMAGE_GHAT_REFERENCE` (Sant Tukaram Maharaj Temple & Ghats)

3. **Middle Corridor Station**:
   - **Station ID**: `INDRAYANI-ALANDI-GHAT`
   - **Station Name**: Indrayani River at Alandi Ghat
   - **Coordinates**: Latitude `18.6770`, Longitude `73.8960`
   - **Classification**: `PILGRIMAGE_GHAT_REFERENCE` (Sant Dnyaneshwar Maharaj Samadhi Temple)

4. **Lower Corridor Confluence Station**:
   - **Station ID**: `INDRAYANI-TULAPUR-CONFLUENCE`
   - **Station Name**: Indrayani-Bhima Confluence at Tulapur (Triveni Sangam)
   - **Coordinates**: Latitude `18.5770`, Longitude `74.0150`
   - **Classification**: `BASIN_CONFLUENCE_REFERENCE`

---

## 2. Scientific Honesty & Hydrological Telemetry Guarantees

In strict adherence to CLIMAFORGE core safety principles, **scientific honesty is paramount**:

> [!CAUTION]
> **MANDATORY SCIENTIFIC & SAFETY DISCLAIMER**
> The Moshi reference point is an official Maharashtra Pollution Control Board (MPCB) surface-water quality monitoring reference. Automated live flood-level telemetry (CWC / India-WRIS) is currently unmonitored at this site.
> 
> Required User-Facing Statements:
> - *"Verified geographical environmental monitoring reference — flood telemetry not verified."*
> - *"Indrayani River telemetry currently unavailable."*
> 
> Under no circumstances does CLIMAFORGE fabricate live water-level readings, stage heights, danger thresholds, or simulated live flood levels. When live telemetry is absent, `water_level_m` returns `null` and is explicitly labeled `TELEMETRY_UNVERIFIED`.

---

## 3. Upstream Data Sources & Providers

### 3.1 Hyperlocal Weather & Precipitation (Open-Meteo)
* **Provider**: Open-Meteo Weather API (`https://api.open-meteo.com/v1/forecast`)
* **Default Coordinates**: Latitude `18.68365`, Longitude `73.87855` (Moshi Reference)
* **Caching Strategy**: Thread-safe in-memory cache with 10-minute (600s) TTL. Cache keys are rounded to 3 decimal places (~110-meter precision), preventing duplicate upstream calls while maintaining hyperlocal accuracy.
* **Timeout & Resilience**: Strict 10-second HTTP timeout (`OPEN_METEO_TIMEOUT_SECONDS = 10.0`).
* **Null Preservation**: Missing upstream values are never coerced to `0.0`. Missing data is retained as `None` / `null` to avoid false assertions of zero rainfall or freezing temperatures.
* **Offline Fallback**: In the event of network disruption or upstream API failure, the client falls back to cached responses or deterministic offline estimates with `quality_status = 'OFFLINE_FALLBACK'` and `freshness_status = 'STALE'`.

### 3.2 India Meteorological Department (IMD) Weather Warnings
* **Target District**: Pune District, Maharashtra, India.
* **Configuration Parameters**:
  - `IMD_ENABLED`: Boolean toggle (default `True`).
  - `IMD_API_KEY`: Official API key / authorization token (server-side only).
  - `IMD_API_BASE_URL`: Base URL for IMD national / regional weather warning endpoints.
  - `IMD_TIMEOUT_SECONDS`: 10.0s connection timeout.
* **Credential Isolation**: All IMD credentials remain strictly server-side in `backend/.env`. Zero tokens or API keys are exposed to the client or frontend bundles.
* **Graceful Fallback**: When `IMD_API_KEY` is unconfigured, the system returns an official district advisory with `provider_status = 'UNCONFIGURED_FALLBACK'`, providing authentic Pune District monsoon awareness without failing or blocking the application.

---

## 4. Backend API Endpoints & Contracts

All endpoints are mounted under `/api/environmental` and root `/environmental` and are guarded by JWT/RBAC (`PERM_SCENARIO_READ`):

| Endpoint | Method | Query Parameters | Description |
| :--- | :--- | :--- | :--- |
| `/api/environmental/weather` | `GET` | `lat`, `lon` | Ambient weather observation (temperature, humidity, precipitation, wind, weather code). |
| `/api/environmental/forecast` | `GET` | `lat`, `lon`, `location_name`, `force_refresh` | 48-hour hourly precipitation forecast, probability %, and 7-day daily summaries. |
| `/api/environmental/warnings` | `GET` | `district`, `state`, `force_refresh` | Official IMD weather warnings for Pune District with alert severity levels. |
| `/api/environmental/indrayani` | `GET` | `station_id`, `force_refresh` | Unified Indrayani snapshot: station metadata, weather, 24h rainfall, IMD alerts, and MPCB records. |
| `/api/environmental/indrayani/stations` | `GET` | None | Directory of verified geographical stations along the Indrayani River corridor. |
| `/api/environmental/indrayani/history` | `GET` | `station_id` | Historical MPCB water quality monitoring samples (pH, Dissolved Oxygen, BOD). |

---

## 5. Frontend Dashboard Architecture (`EnvironmentalTab.tsx`)

The frontend delivers a rich, real-time command dashboard matching CLIMAFORGE's high-contrast operations theme:

1. **Geolocation Control Bar**:
   - **Browser GPS Integration**: Requests high-accuracy coordinates via standard Geolocation API with explicit user consent, displaying accuracy radius in meters (`±14m`).
   - **Corridor Presets**: One-click switching between Moshi (MPCB Station 11), Dehu Ghat, Alandi Ghat, Tulapur Sangam, PCMC Central, and Pune City.
   - **Manual Coordinate Input**: Validated inputs with numerical bounds checking ($-90 \le \text{lat} \le 90$, $-180 \le \text{lon} \le 180$).

2. **Scientific Honesty Banner**:
   - High-visibility amber card clearly citing MPCB Station 11 as a surface-water quality reference and certifying that flood telemetry is currently unavailable.

3. **Real-Time Weather KPI Cards**:
   - Ambient Temperature (°C), Precipitation Rate (mm/h), 24h Expected Rainfall (mm), Relative Humidity (%), and Wind Speed & Direction (km/h, bearing).

4. **Interactive SVG River Corridor Map**:
   - High-performance SVG canvas projecting real coordinates onto the Indrayani River corridor ($18.52^\circ\text{N} - 18.78^\circ\text{N}$, $73.70^\circ\text{E} - 74.08^\circ\text{E}$).
   - Visualizes Indrayani River centerline, confluence with Bhima River, corridor reference stations, and user GPS position with accuracy uncertainty radius.
   - Layer toggles: `ALL`, `LIVE`, `FORECAST`, `HISTORICAL`.

5. **IMD Warnings & Station Inspector**:
   - District warning card showing warning level badge (`GREEN`, `YELLOW`, `ORANGE`, `RED`), description, and issuing office.
   - Station inspector drawer with village, taluka, monitoring body, source citation, and telemetry notice.

6. **24-Hour Precipitation Forecast Bar Chart**:
   - Hourly bar visualization displaying expected precipitation (mm) and rain probability (%) for operational readiness.

7. **Historical Water Quality Archive**:
   - Tabular record of verified MPCB laboratory samples for Moshi (pH 7.4, DO 5.6 mg/L, BOD 3.8 mg/L) with parameter notes.

---

## 6. Protection of Authoritative Algorithms 0–13

The Real-Time Environmental Intelligence module is strictly decoupled from the deterministic calculation engine:

* **Algorithms 0–13 Untouched**: Algorithms 0–3 (Risk Score, Hotspots, Exposure), 4–7 (Cascade Graph, Noisy-OR, Critical Nodes, Break-Points), and 8, 10–13 (Resource Allocation, Intervention Ranking, What-If, Comparison, Final Decision) remain 100% authoritative and isolated.
* **No Uncontrolled Ingestion**: Live weather data and unverified river telemetry are never silently fed into authoritative deterministic formulas without operator review.
* **Full Backward Compatibility**: All previous milestones (M0–M8, M10–M15, M16A.1–M16A.7) pass 100% of regression tests.


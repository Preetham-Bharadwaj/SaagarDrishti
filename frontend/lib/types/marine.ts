export interface GeoCoordinate {
  latitude: number;
  longitude: number;
}

export type QueryIntent =
  | 'nearest_pfz'
  | 'marine_conditions'
  | 'weather_hazard'
  | 'general_marine_information';

export type DataStatus = 'current' | 'expired' | 'unavailable' | 'not_verified';

export type QueryWorkflowStatus =
  | 'SUCCESS'
  | 'DATA_UNAVAILABLE'
  | 'LOCATION_REQUIRED'
  | 'EVIDENCE_REJECTED'
  | 'ERROR';

export type WaveHazardLevel =
  | 'calm'
  | 'slight'
  | 'moderate'
  | 'rough'
  | 'very_rough'
  | 'unknown';

export type OfficialWarningSeverity =
  | 'no_warning'
  | 'advisory'
  | 'warning'
  | 'severe_warning';

export interface SourceAvailabilityReport {
  source_name: string;
  source_url: string;
  status: DataStatus;
  latest_verified_timestamp: string | null;
  validity_window: string | null;
  limitations: string[];
  notes: string;
}

export interface CandidatePFZResult {
  hotspot_id: string;
  coordinate: GeoCoordinate;
  distance_km: number;
  bearing_deg?: number | null;
  depth_m?: number | null;
  landing_center: string;
  valid_from?: string | null;
  valid_to: string;
  data_source: string;
}

export interface HourlyMarineForecastStep {
  time_local: string;
  is_model_forecast: boolean;
  wave_height_m?: number | null;
  wind_wave_height_m?: number | null;
  swell_wave_height_m?: number | null;
  wave_direction_deg?: number | null;
  wave_period_s?: number | null;
  wind_wave_direction_deg?: number | null;
  swell_wave_direction_deg?: number | null;
  swell_wave_period_s?: number | null;
  hazard_level: WaveHazardLevel;
}

export interface MarineHazardForecast {
  source: string;
  source_url: string;
  retrieved_at: string;
  model_label: string;
  latitude: number;
  longitude: number;
  grid_resolution_km: number;
  timezone: string;
  utc_offset_seconds: number;
  forecast_hours: HourlyMarineForecastStep[];
  current_hour_observation?: HourlyMarineForecastStep | null;
  forecast_valid_time?: string | null;
  is_stale: boolean;
  is_data_available: boolean;
  peak_wave_height_m?: number | null;
  peak_hazard_level: WaveHazardLevel;
  data_quality_notes: string[];
  safety_disclaimer: string;
}

export interface OfficialMarineWarning {
  bulletin_id: string;
  issuing_authority: string;
  issued_at: string;
  valid_from: string;
  valid_to: string;
  coastal_zone: string;
  severity: OfficialWarningSeverity;
  warning_type: string;
  warning_text: string;
  wind_speed_knots_min?: number | null;
  wind_speed_knots_max?: number | null;
  fishermen_advised_not_to_venture: boolean;
  source_document: string;
  ingested_at: string;
}

export interface OceanSSTResult {
  source_name: string;
  product_id: string;
  dataset_id: string;
  product_category: string;
  production_center: string;
  observation_timestamp: string;
  retrieved_at: string;
  is_live_retrieval: boolean;
  is_stale: boolean;
  coverage_min_lat: number;
  coverage_max_lat: number;
  coverage_min_lon: number;
  coverage_max_lon: number;
  spatial_resolution_deg: number;
  valid_cell_count: number;
  land_masked_cell_count: number;
  missing_cell_count: number;
  mean_sst_celsius?: number | null;
  min_sst_celsius?: number | null;
  max_sst_celsius?: number | null;
  regional_range_celsius?: number | null;
  max_spatial_gradient_c_per_km?: number | null;
  thermal_front_detected?: boolean | null;
  retrieval_status: string;
  quality_notes: string[];
  ecological_disclaimer: string;
}

export interface EvidenceAuditResult {
  passed: boolean;
  checks_performed: string[];
  provenance_sources: string[];
  is_landing_center_mistaken_for_pfz: boolean;
  is_expired: boolean;
  sources_disagree: boolean;
  rejection_reasons: string[];
  warnings: string[];
}

export interface MarineQueryRequest {
  query: string;
  user_location?: GeoCoordinate | null;
  departure_port?: string | null;
}

export interface MarineQueryResponse {
  query: string;
  intent: QueryIntent;
  status: QueryWorkflowStatus;
  answer: string;
  candidate_pfz?: CandidatePFZResult | null;
  marine_hazard?: MarineHazardForecast | null;
  official_warning?: OfficialMarineWarning | null;
  ocean_sst?: OceanSSTResult | null;
  sources_disagree: boolean;
  evidence_audit: EvidenceAuditResult;
  sources_checked: SourceAvailabilityReport[];
  tools_used: string[];
  timestamp: string;
}

export interface HealthCheckResponse {
  status: string;
  app_name: string;
  version: string;
  timestamp: string;
}

export interface GeocodingResult {
  placeId: string;
  displayName: string;
  name: string;
  latitude: number;
  longitude: number;
  type?: string;
  importance?: number;
}

export interface CoastalPort {
  id: string;
  name: string;
  district: string;
  state: string;
  coordinate: GeoCoordinate;
  description?: string;
}

export type SupportedLanguage = 'en' | 'kn' | 'ml' | 'ta' | 'te';

export interface MarineRouteInfo {
  originName: string;
  originCoord: GeoCoordinate;
  destinationName: string;
  destinationCoord: GeoCoordinate;
  distanceKm: number;
  estimatedHours: number;
  bearingDeg: number;
  routeType: 'to_pfz' | 'return_to_shore';
  safetyStatus: 'safe' | 'caution' | 'warning';
  safetySummary: string;
  crossesRestrictedZone?: boolean;
  restrictedZoneWarning?: string;
  limitations: string;
}

export interface RestrictedZone {
  id: string;
  name: string;
  category: 'marine_protected_area' | 'naval_exercise' | 'harbour_security';
  coordinates: [number, number][]; // [lat, lon]
  description: string;
  authority: string;
}

export interface CommunityReport {
  id: string;
  title: string;
  category: 'catch' | 'hazard' | 'weather';
  reportedAt: string;
  port: string;
  verified: boolean;
  statusText: string;
}


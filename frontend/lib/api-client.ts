import {
  HealthCheckResponse,
  MarineQueryRequest,
  MarineQueryResponse,
  SourceAvailabilityReport,
} from './types/marine';

// Candidate API URLs in priority order: environment variable first, then standard port 8000, then fallback port 8001
const CONFIGURED_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '');
const CANDIDATE_URLS = Array.from(
  new Set(
    [
      CONFIGURED_URL,
      'http://127.0.0.1:8000/api',
      'http://127.0.0.1:8001/api',
      'http://localhost:8000/api',
      'http://localhost:8001/api',
    ].filter(Boolean) as string[]
  )
);

let cachedWorkingBaseUrl: string | null = null;

/**
 * Fetch with configurable timeout
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = 15000
): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(id);
  }
}

/**
 * Resolve reachable API base URL
 */
async function getActiveBaseUrl(): Promise<string> {
  if (cachedWorkingBaseUrl) {
    return cachedWorkingBaseUrl;
  }

  for (const url of CANDIDATE_URLS) {
    try {
      const res = await fetchWithTimeout(`${url}/v1/health`, { method: 'GET' }, 2500);
      if (res.ok) {
        cachedWorkingBaseUrl = url;
        return url;
      }
    } catch {
      // try next candidate
    }
  }

  // default to configured or first candidate
  return CANDIDATE_URLS[0] || 'http://127.0.0.1:8000/api';
}

/**
 * Check backend system health
 */
export async function getBackendHealth(): Promise<{
  connected: boolean;
  data?: HealthCheckResponse;
  error?: string;
  url?: string;
}> {
  try {
    const baseUrl = await getActiveBaseUrl();
    const response = await fetchWithTimeout(
      `${baseUrl}/v1/health`,
      {
        method: 'GET',
        headers: { Accept: 'application/json' },
        cache: 'no-store',
      },
      5000
    );

    if (!response.ok) {
      cachedWorkingBaseUrl = null;
      return {
        connected: false,
        error: `HTTP ${response.status}: ${response.statusText}`,
        url: baseUrl,
      };
    }

    const data: HealthCheckResponse = await response.json();
    return { connected: true, data, url: baseUrl };
  } catch (err: unknown) {
    cachedWorkingBaseUrl = null;
    const message = err instanceof Error ? err.message : 'Connection failed';
    return { connected: false, error: message };
  }
}

/**
 * Get operational status of upstream marine data sources
 */
export async function getDataSources(): Promise<{
  success: boolean;
  data: SourceAvailabilityReport[];
  error?: string;
}> {
  try {
    const baseUrl = await getActiveBaseUrl();
    const response = await fetchWithTimeout(`${baseUrl}/v1/data-sources`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    });

    if (!response.ok) {
      return {
        success: false,
        data: [],
        error: `Failed to load data sources (HTTP ${response.status})`,
      };
    }

    const data: SourceAvailabilityReport[] = await response.json();
    return { success: true, data };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Network error';
    return { success: false, data: [], error: message };
  }
}

/**
 * Submit natural language marine intelligence query
 */
export async function submitMarineQuery(
  request: MarineQueryRequest
): Promise<{
  success: boolean;
  data?: MarineQueryResponse;
  error?: string;
}> {
  try {
    const baseUrl = await getActiveBaseUrl();
    const response = await fetchWithTimeout(
      `${baseUrl}/v1/query`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify(request),
      },
      30000
    );

    if (!response.ok) {
      let detail = `Server responded with status ${response.status}`;
      try {
        const errorJson = await response.json();
        if (errorJson?.detail) {
          detail =
            typeof errorJson.detail === 'string'
              ? errorJson.detail
              : JSON.stringify(errorJson.detail);
        }
      } catch {
        // fallback to default detail
      }
      return { success: false, error: detail };
    }

    const data: MarineQueryResponse = await response.json();
    return { success: true, data };
  } catch (err: unknown) {
    if (err instanceof Error && err.name === 'AbortError') {
      return {
        success: false,
        error: 'Query timed out after 30 seconds. Please try again.',
      };
    }
    const message = err instanceof Error ? err.message : 'Network connection failed';
    return { success: false, error: message };
  }
}

// ---- PFZ GeoJSON types ----
export interface PFZLayerMetadata {
  source: string;
  source_url: string;
  retrieved_at: string;
  julian_day: number | null;
  year: number | null;
  is_current: boolean;
  feature_count: number;
  chl_count: number;
  sst_count: number;
  validation_notes: string[];
}

export interface PFZGeoJSONResponse {
  type: 'FeatureCollection';
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  features: Record<string, any>[];
  metadata: PFZLayerMetadata;
}

/**
 * Fetch current-day Karnataka PFZ advisory lines from the backend.
 * The backend retrieves and filters live INCOIS WFS data.
 */
export async function getPFZGeoJSON(): Promise<{
  success: boolean;
  data?: PFZGeoJSONResponse;
  error?: string;
}> {
  try {
    const baseUrl = await getActiveBaseUrl();
    const response = await fetchWithTimeout(
      `${baseUrl}/v1/pfz/geojson`,
      {
        method: 'GET',
        headers: { Accept: 'application/json' },
        cache: 'no-store',
      },
      25000
    );

    if (!response.ok) {
      return {
        success: false,
        error: `PFZ endpoint returned HTTP ${response.status}`,
      };
    }

    const data: PFZGeoJSONResponse = await response.json();
    return { success: true, data };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Network error fetching PFZ data';
    return { success: false, error: message };
  }
}

import { CoastalPort, GeocodingResult, GeoCoordinate } from './types/marine';

/**
 * Verified Karnataka Coastal Landing Centers and Ports
 * Source: INCOIS Karnataka Reference Layer & Marine Fisheries Department
 */
export const KARNATAKA_PORTS: CoastalPort[] = [
  {
    id: 'malpe',
    name: 'Malpe',
    district: 'Udupi',
    state: 'Karnataka',
    coordinate: { latitude: 13.354, longitude: 74.704 },
    description: 'Major all-weather commercial fishing harbour and landing center in Udupi.',
  },
  {
    id: 'mangaluru',
    name: 'Mangaluru (Old Port)',
    district: 'Dakshina Kannada',
    state: 'Karnataka',
    coordinate: { latitude: 12.859, longitude: 74.836 },
    description: 'Bunder fishing port and estuary confluence of Netravati & Gurupura rivers.',
  },
  {
    id: 'karwar',
    name: 'Karwar (Baithkol)',
    district: 'Uttara Kannada',
    state: 'Karnataka',
    coordinate: { latitude: 14.808, longitude: 74.124 },
    description: 'Deep-water natural harbour in northern Karnataka coast.',
  },
  {
    id: 'honnavar',
    name: 'Honnavar',
    district: 'Uttara Kannada',
    state: 'Karnataka',
    coordinate: { latitude: 14.282, longitude: 74.445 },
    description: 'Sharavathi river mouth coastal landing center.',
  },
  {
    id: 'bhatkal',
    name: 'Bhatkal',
    district: 'Uttara Kannada',
    state: 'Karnataka',
    coordinate: { latitude: 13.978, longitude: 74.546 },
    description: 'Traditional marine fisheries landing port.',
  },
  {
    id: 'tadadi',
    name: 'Tadadi',
    district: 'Uttara Kannada',
    state: 'Karnataka',
    coordinate: { latitude: 14.526, longitude: 74.364 },
    description: 'Aghanashini estuary fishing port.',
  },
  {
    id: 'gangolli',
    name: 'Gangolli',
    district: 'Udupi',
    state: 'Karnataka',
    coordinate: { latitude: 13.636, longitude: 74.673 },
    description: 'Panchagangavalli river convergence fishing harbour.',
  },
  {
    id: 'ullal',
    name: 'Ullal',
    district: 'Dakshina Kannada',
    state: 'Karnataka',
    coordinate: { latitude: 12.805, longitude: 74.851 },
    description: 'Southern Karnataka coastal landing center.',
  },
];

/**
 * Validate latitude and longitude values
 */
export function validateCoordinates(lat: number, lon: number): {
  valid: boolean;
  error?: string;
} {
  if (isNaN(lat) || isNaN(lon)) {
    return { valid: false, error: 'Coordinates must be valid numbers' };
  }
  if (lat < -90 || lat > 90) {
    return { valid: false, error: 'Latitude must be between -90 and +90 degrees' };
  }
  if (lon < -180 || lon > 180) {
    return { valid: false, error: 'Longitude must be between -180 and +180 degrees' };
  }
  return { valid: true };
}

/**
 * Parse string into coordinate or return null
 */
export function parseCoordinateString(input: string): GeoCoordinate | null {
  // Try pattern: "13.35, 74.70" or "13.35 74.70"
  const regex = /^\s*([+-]?\d+(?:\.\d+)?)\s*[,\s]\s*([+-]?\d+(?:\.\d+)?)\s*$/;
  const match = input.match(regex);
  if (!match) return null;

  const lat = parseFloat(match[1]);
  const lon = parseFloat(match[2]);
  const validation = validateCoordinates(lat, lon);
  if (!validation.valid) return null;

  return { latitude: lat, longitude: lon };
}

/**
 * Search locations using OpenStreetMap Nominatim
 */
export async function searchLocations(
  query: string,
  limit: number = 6
): Promise<GeocodingResult[]> {
  const trimmed = query.trim();
  if (!trimmed || trimmed.length < 2) return [];

  // Check if query directly matches one of our curated Karnataka ports
  const lowerQuery = trimmed.toLowerCase();
  const matchedPorts: GeocodingResult[] = KARNATAKA_PORTS.filter(
    (p) =>
      p.name.toLowerCase().includes(lowerQuery) ||
      p.district.toLowerCase().includes(lowerQuery)
  ).map((p) => ({
    placeId: `port-${p.id}`,
    name: p.name,
    displayName: `${p.name}, ${p.district}, ${p.state}, India (Verified Coastal Port)`,
    latitude: p.coordinate.latitude,
    longitude: p.coordinate.longitude,
    type: 'port',
    importance: 0.9,
  }));

  try {
    const encoded = encodeURIComponent(trimmed);
    // Bias results towards India / Arabian Sea bounding box
    const url = `https://nominatim.openstreetmap.org/search?q=${encoded}&format=json&limit=${limit}&addressdetails=1&countrycodes=in`;

    const res = await fetch(url, {
      headers: {
        'Accept': 'application/json',
        'User-Agent': 'SaagarDrishti-MarineIntelligence/1.0',
      },
    });

    if (!res.ok) {
      return matchedPorts;
    }

    interface NominatimItem {
      place_id: number | string;
      display_name: string;
      name?: string;
      lat: string;
      lon: string;
      type?: string;
      importance?: number;
    }

    const json: NominatimItem[] = await res.json();
    const remoteResults: GeocodingResult[] = json.map((item) => ({
      placeId: String(item.place_id),
      displayName: item.display_name,
      name: item.name || item.display_name.split(',')[0],
      latitude: parseFloat(item.lat),
      longitude: parseFloat(item.lon),
      type: item.type,
      importance: item.importance,
    }));

    // Combine verified ports and remote results without duplicates
    const combined = [...matchedPorts];
    for (const remote of remoteResults) {
      const alreadyIncluded = combined.some(
        (c) =>
          Math.abs(c.latitude - remote.latitude) < 0.05 &&
          Math.abs(c.longitude - remote.longitude) < 0.05
      );
      if (!alreadyIncluded) {
        combined.push(remote);
      }
    }

    return combined.slice(0, limit);
  } catch {
    // If remote network fails (e.g. rate limit), return matching local ports
    return matchedPorts;
  }
}

/**
 * Reverse geocode coordinate into human readable name
 */
export async function reverseGeocode(
  coordinate: GeoCoordinate
): Promise<string> {
  // Check if near any verified port
  const nearbyPort = KARNATAKA_PORTS.find((p) => {
    const dLat = p.coordinate.latitude - coordinate.latitude;
    const dLon = p.coordinate.longitude - coordinate.longitude;
    return Math.sqrt(dLat * dLat + dLon * dLon) < 0.05;
  });

  if (nearbyPort) {
    return `${nearbyPort.name} Coast (${nearbyPort.district})`;
  }

  try {
    const url = `https://nominatim.openstreetmap.org/reverse?lat=${coordinate.latitude}&lon=${coordinate.longitude}&format=json`;
    const res = await fetch(url, {
      headers: {
        'Accept': 'application/json',
        'User-Agent': 'SaagarDrishti-MarineIntelligence/1.0',
      },
    });

    if (res.ok) {
      const data = await res.json();
      if (data?.display_name) {
        const parts = data.display_name.split(',');
        return parts.slice(0, 3).join(', ');
      }
    }
  } catch {
    // fallback
  }

  return `Lat ${coordinate.latitude.toFixed(3)}°, Lon ${coordinate.longitude.toFixed(3)}°`;
}

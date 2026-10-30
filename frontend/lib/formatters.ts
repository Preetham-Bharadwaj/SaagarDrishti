/**
 * Format date string into human-readable local and UTC presentation
 */
export function formatMarineDateTime(isoString?: string | null): string {
  if (!isoString) return 'Unavailable';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    }) + ' IST';
  } catch {
    return isoString;
  }
}

/**
 * Format wave height in meters with unit
 */
export function formatWaveHeight(m?: number | null): string {
  if (m === null || m === undefined || isNaN(m)) return 'Unavailable';
  return `${m.toFixed(1)} m`;
}

/**
 * Format sea surface temperature in Celsius
 */
export function formatSST(c?: number | null): string {
  if (c === null || c === undefined || isNaN(c)) return 'Unavailable';
  return `${c.toFixed(1)} °C`;
}

/**
 * Format distance in km
 */
export function formatDistance(km?: number | null): string {
  if (km === null || km === undefined || isNaN(km)) return 'Unavailable';
  return `${km.toFixed(1)} km`;
}

/**
 * Bearing in degrees with compass cardinal direction (e.g. 270° W)
 */
export function formatBearing(deg?: number | null): string {
  if (deg === null || deg === undefined || isNaN(deg)) return 'Unavailable';
  const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
  const index = Math.round(((deg % 360) / 22.5)) % 16;
  return `${Math.round(deg)}° (${directions[index]})`;
}

/**
 * Douglas sea state description
 */
export function getDouglasStateLabel(waveHeightM?: number | null): {
  state: number;
  label: string;
  badgeClass: string;
} {
  if (waveHeightM === null || waveHeightM === undefined) {
    return { state: -1, label: 'Unknown', badgeClass: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20' };
  }
  if (waveHeightM < 0.1) return { state: 0, label: 'Calm (Glassy)', badgeClass: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20' };
  if (waveHeightM < 0.5) return { state: 1, label: 'Calm (Rippled)', badgeClass: 'bg-teal-500/10 text-teal-600 dark:text-teal-400 border-teal-500/20' };
  if (waveHeightM < 1.25) return { state: 2, label: 'Smooth / Slight', badgeClass: 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20' };
  if (waveHeightM < 2.5) return { state: 3, label: 'Moderate', badgeClass: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20' };
  if (waveHeightM < 4.0) return { state: 4, label: 'Rough', badgeClass: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20' };
  return { state: 5, label: 'Very Rough / High', badgeClass: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20' };
}

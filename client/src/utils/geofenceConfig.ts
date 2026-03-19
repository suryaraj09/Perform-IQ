// Geofence configuration — update these when the store location changes
export const STORE_LAT = 22.991573;
export const STORE_LNG = 72.539284;
export const GEOFENCE_RADIUS = 100; // meters
export const GEOFENCE_CHECK_INTERVAL = 15 * 60 * 1000; // 15 minutes in ms

/**
 * Calculate great-circle distance between two GPS coordinates using Haversine formula.
 * @returns distance in meters
 */
export function haversineDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371000; // Earth radius in meters
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

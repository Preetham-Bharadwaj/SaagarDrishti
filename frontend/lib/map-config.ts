export interface MapTileOption {
  id: string;
  name: string;
  url: string;
  attribution: string;
  maxZoom: number;
  theme: 'light' | 'dark' | 'any';
}

export const MAP_TILE_PROVIDERS: MapTileOption[] = [
  {
    id: 'esri-dark',
    name: 'Esri Dark Canvas',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
    maxZoom: 16,
    theme: 'dark',
  },
  {
    id: 'osm-standard',
    name: 'OpenStreetMap Standard',
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
    theme: 'light',
  },
  {
    id: 'esri-ocean',
    name: 'Esri World Ocean / Bathymetry',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; Sources: GEBCO, NOAA, CHS, OSU, UNH, CSUMB, National Geographic, DeLorme, NAVTEQ, and other contributors',
    maxZoom: 13,
    theme: 'any',
  },
  {
    id: 'esri-light',
    name: 'Esri Light Gray Canvas',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
    maxZoom: 16,
    theme: 'light',
  },
  {
    id: 'esri-satellite',
    name: 'Esri World Imagery (Satellite)',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
    maxZoom: 18,
    theme: 'any',
  },
];

export interface MapLayerToggle {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  activeStatus: 'active' | 'expired' | 'disconnected' | 'live';
  statusLabel: string;
}

export const INITIAL_MAP_LAYERS: MapLayerToggle[] = [
  {
    id: 'pfz-advisories',
    name: 'Fishing Zones (PFZ)',
    description: 'Potential Fishing Zone vector lines — CHL & SST fronts from INCOIS WFS',
    enabled: true,
    activeStatus: 'live',
    statusLabel: 'Live Advisory Lines (INCOIS WFS)',
  },
  {
    id: 'marine-weather',
    name: 'Weather & Waves',
    description: 'Hourly ECMWF ERAssWave wave heights, swell period, and Douglas state',
    enabled: true,
    activeStatus: 'live',
    statusLabel: 'Live Model (Hourly)',
  },
  {
    id: 'ocean-sst',
    name: 'Sea Surface Temperature',
    description: 'Level-4 Foundation Sea Surface Temperature analysis slice (5.5 km grid)',
    enabled: true,
    activeStatus: 'live',
    statusLabel: 'L4 Analysis (Copernicus CMEMS)',
  },
  {
    id: 'chlorophyll',
    name: 'Chlorophyll',
    description: 'Ocean color chlorophyll-a front concentration indicators',
    enabled: true,
    activeStatus: 'live',
    statusLabel: 'Bio-optical Fronts',
  },
  {
    id: 'ocean-currents',
    name: 'Ocean Currents',
    description: 'Coastal shelf surface current vectors & drift direction',
    enabled: true,
    activeStatus: 'live',
    statusLabel: 'Shelf Circulation Vectors',
  },
  {
    id: 'restricted-zones',
    name: 'Restricted Zones',
    description: 'Marine protected areas and coastal exclusion perimeters',
    enabled: true,
    activeStatus: 'live',
    statusLabel: 'Verified Marine Boundaries',
  },
  {
    id: 'coastal-ports',
    name: 'Coastal Ports',
    description: 'Verified Karnataka coastal landing centers (Spatial Reference Baseline)',
    enabled: true,
    activeStatus: 'live',
    statusLabel: 'Reference Baseline (29 Ports)',
  },
];

export interface VerifiedRestrictedZone {
  id: string;
  name: string;
  category: 'marine_protected' | 'naval_perimeter' | 'coral_reef';
  coordinates: [number, number][]; // [lat, lon]
  description: string;
  authority: string;
  isOfficial: boolean;
}

/**
 * Authoritative Karnataka Marine Sensitive & Exclusion Perimeters
 * Sources: Ministry of Environment, Forest & Climate Change (MoEFCC) & Coast Guard Navigational Notices
 */
export const KARNATAKA_RESTRICTED_ZONES: VerifiedRestrictedZone[] = [
  {
    id: 'st-marys-reserve',
    name: 'St. Mary’s Islands Geological & Marine Reef Protected Perimeter',
    category: 'marine_protected',
    coordinates: [
      [13.385, 74.655],
      [13.395, 74.685],
      [13.365, 74.695],
      [13.355, 74.665],
    ],
    description:
      'National Geological Monument & Marine Reef Zone. Commercial bottom trawling and anchoring strictly prohibited.',
    authority: 'Karnataka Forest Dept / Coastal Zone Management Authority',
    isOfficial: true,
  },
  {
    id: 'netrani-coral-sanctuary',
    name: 'Netrani Island Marine Biodiversity Zone',
    category: 'coral_reef',
    coordinates: [
      [14.035, 74.305],
      [14.045, 74.345],
      [14.005, 74.355],
      [13.995, 74.315],
    ],
    description:
      'Fragile coral reef ecological zone. Mechanized netting and underwater disturbance restricted.',
    authority: 'Wildlife Division / Indian Coast Guard',
    isOfficial: true,
  },
];

export const KARNATAKA_MAP_CENTER = {
  latitude: 13.36,
  longitude: 74.5,
  zoom: 8,
};


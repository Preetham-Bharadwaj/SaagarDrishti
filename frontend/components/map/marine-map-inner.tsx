'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Rectangle,
  Polygon,
  Polyline,
  GeoJSON,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import L from 'leaflet';
import {
  Search,
  Crosshair,
  Maximize2,
  Minimize2,
  Compass,
  Layers,
  MapPin,
  Waves,
  Thermometer,
  Fish,
  ShieldAlert,
  Info,
  AlertTriangle,
  RefreshCw,
  Wind,
  Navigation,
  Anchor,
  Ban,
  Check,
  Zap,
} from 'lucide-react';
import { useTheme } from '../theme-provider';
import {
  MAP_TILE_PROVIDERS,
  INITIAL_MAP_LAYERS,
  KARNATAKA_MAP_CENTER,
  KARNATAKA_RESTRICTED_ZONES,
  MapLayerToggle,
} from '../../lib/map-config';
import {
  KARNATAKA_PORTS,
  searchLocations,
  parseCoordinateString,
  reverseGeocode,
} from '../../lib/geocoding';
import {
  GeoCoordinate,
  GeocodingResult,
  MarineQueryResponse,
  MarineRouteInfo,
} from '../../lib/types/marine';
import {
  getPFZGeoJSON,
  PFZGeoJSONResponse,
  PFZLayerMetadata,
} from '../../lib/api-client';
import {
  formatWaveHeight,
  formatSST,
  getDouglasStateLabel,
  formatMarineDateTime,
  formatBearing,
  formatDistance,
} from '../../lib/formatters';

interface MarineMapInnerProps {
  selectedCoordinate: GeoCoordinate;
  onSelectCoordinate: (coord: GeoCoordinate, name?: string) => void;
  selectedLocationName?: string;
  activeQueryResponse?: MarineQueryResponse | null;
  activeRoute?: MarineRouteInfo | null;
  onClearRoute?: () => void;
}

// Controller component to smoothly fly/pan map
function MapViewController({
  targetCoordinate,
  zoom,
}: {
  targetCoordinate: GeoCoordinate;
  zoom?: number;
}) {
  const map = useMap();

  useEffect(() => {
    map.invalidateSize();
  }, [map]);

  useEffect(() => {
    map.flyTo(
      [targetCoordinate.latitude, targetCoordinate.longitude],
      zoom || map.getZoom(),
      { duration: 1.2 }
    );
  }, [targetCoordinate, zoom, map]);

  return null;
}

// Map Click Listener to pick coordinates anywhere
function MapClickHandler({
  onMapClick,
}: {
  onMapClick: (coord: GeoCoordinate) => void;
}) {
  useMapEvents({
    click(e) {
      onMapClick({ latitude: e.latlng.lat, longitude: e.latlng.lng });
    },
  });
  return null;
}

export default function MarineMapInner({
  selectedCoordinate,
  onSelectCoordinate,
  selectedLocationName,
  activeQueryResponse,
  activeRoute,
  onClearRoute,
}: MarineMapInnerProps) {
  const { theme } = useTheme();

  // Layers & Tile State
  const [layers, setLayers] = useState<MapLayerToggle[]>(INITIAL_MAP_LAYERS);
  const [selectedTileId, setSelectedTileId] = useState<string>(
    theme === 'dark' ? 'esri-dark' : 'osm-standard'
  );
  const [isLayerBoxOpen, setIsLayerBoxOpen] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<GeocodingResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  // PFZ GeoJSON layer state
  const [pfzData, setPfzData] = useState<PFZGeoJSONResponse | null>(null);
  const [pfzMeta, setPfzMeta] = useState<PFZLayerMetadata | null>(null);
  const [pfzLoading, setPfzLoading] = useState(false);
  const [pfzError, setPfzError] = useState<string | null>(null);
  const pfzGeoJsonKey = useRef(0);

  const fetchPFZData = useCallback(async () => {
    setPfzLoading(true);
    setPfzError(null);
    const result = await getPFZGeoJSON();
    if (result.success && result.data) {
      setPfzData(result.data);
      setPfzMeta(result.data.metadata);
      pfzGeoJsonKey.current += 1;
    } else {
      setPfzError(result.error || 'Failed to load PFZ data');
    }
    setPfzLoading(false);
  }, []);

  useEffect(() => {
    fetchPFZData();
  }, [fetchPFZData]);

  // Sync default tile with theme
  useEffect(() => {
    setSelectedTileId(theme === 'dark' ? 'esri-dark' : 'osm-standard');
  }, [theme]);

  // Debounced search
  useEffect(() => {
    if (!searchQuery.trim() || searchQuery.length < 2) {
      setSearchResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      const results = await searchLocations(searchQuery);
      setSearchResults(results);
      setIsSearching(false);
      setIsSearchOpen(true);
    }, 350);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleManualCoordSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = parseCoordinateString(searchQuery);
    if (parsed) {
      onSelectCoordinate(
        parsed,
        `Lat ${parsed.latitude.toFixed(2)}°, Lon ${parsed.longitude.toFixed(2)}°`
      );
      setIsSearchOpen(false);
      setSearchQuery('');
    }
  };

  const handleSelectSearchResult = (result: GeocodingResult) => {
    onSelectCoordinate(
      { latitude: result.latitude, longitude: result.longitude },
      result.name
    );
    setSearchQuery('');
    setIsSearchOpen(false);
  };

  const handleMapClick = async (coord: GeoCoordinate) => {
    const placeName = await reverseGeocode(coord);
    onSelectCoordinate(coord, placeName);
  };

  const handleLocateMe = () => {
    if (typeof window !== 'undefined' && 'geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const coord = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          };
          const name = await reverseGeocode(coord);
          onSelectCoordinate(coord, `My Location (${name})`);
        },
        (error) => {
          alert(`Location access denied or unavailable: ${error.message}`);
        },
        { enableHighAccuracy: true, timeout: 8000 }
      );
    }
  };

  const toggleLayer = (layerId: string) => {
    setLayers((prev) =>
      prev.map((l) => (l.id === layerId ? { ...l, enabled: !l.enabled } : l))
    );
  };

  const isLayerActive = (id: string) =>
    layers.find((l) => l.id === id)?.enabled ?? false;

  const activeTile =
    MAP_TILE_PROVIDERS.find((p) => p.id === selectedTileId) ||
    MAP_TILE_PROVIDERS[0];

  // Custom User Location Pin with Pulsing Ripple Ring
  const createUserPinIcon = (name: string) =>
    L.divIcon({
      className: 'custom-user-pin',
      html: `
        <div style="position: relative; display: flex; align-items: center; justify-content: center; width: 44px; height: 44px;">
          <div style="position: absolute; width: 44px; height: 44px; border-radius: 50%; background: rgba(56, 189, 248, 0.35); animation: ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
          <div style="position: absolute; width: 28px; height: 28px; border-radius: 50%; background: rgba(2, 132, 199, 0.45); animation: pulse 2s infinite;"></div>
          <div style="width: 18px; height: 18px; border-radius: 50%; background: #0284c7; border: 3px solid #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.5); z-index: 2;"></div>
          <div style="position: absolute; top: -22px; white-space: nowrap; background: rgba(11, 21, 36, 0.92); border: 1px solid #38bdf8; border-radius: 6px; padding: 2px 8px; color: #ffffff; font-size: 11px; font-weight: bold; box-shadow: 0 4px 10px rgba(0,0,0,0.4);">
            ${name} (You are here)
          </div>
        </div>
      `,
      iconSize: [44, 44],
      iconAnchor: [22, 22],
    });

  // PFZ Callout Badge Icons matching mockup: PFZ - 1 (High Potential) & PFZ - 2 (Moderate)
  const createPFZCalloutIcon = (label: string, potential: string, color: string) =>
    L.divIcon({
      className: 'custom-pfz-badge',
      html: `
        <div style="display: flex; align-items: center; gap: 6px; background: ${color}; border: 1.5px solid #ffffff; padding: 4px 10px; border-radius: 20px; box-shadow: 0 4px 14px rgba(0,0,0,0.5); color: #ffffff; font-size: 11px; font-weight: bold; white-space: nowrap; transform: translate(-50%, -100%);">
          <span style="font-size: 13px;">🐟</span>
          <div>
            <div>${label}</div>
            <div style="font-size: 9px; opacity: 0.9; font-weight: normal;">${potential}</div>
          </div>
        </div>
      `,
      iconSize: [120, 36],
      iconAnchor: [60, 36],
    });

  // Coastal Port Icon
  const createPortIcon = (name: string) =>
    L.divIcon({
      className: 'custom-port-icon',
      html: `
        <div style="display: flex; align-items: center; gap: 5px; background: rgba(11, 21, 36, 0.92); border: 1px solid rgba(56, 189, 248, 0.7); padding: 2px 7px; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.4); color: #e0f2fe; font-size: 11px; font-weight: 500; white-space: nowrap;">
          <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #38bdf8;"></span>
          ${name}
        </div>
      `,
      iconSize: [80, 24],
      iconAnchor: [40, 12],
    });

  // Route Badge Icon
  const createRouteBadgeIcon = (text: string) =>
    L.divIcon({
      className: 'custom-route-badge',
      html: `
        <div style="display: flex; align-items: center; gap: 5px; background: rgba(16, 185, 129, 0.95); border: 1.5px solid #ffffff; padding: 4px 10px; border-radius: 12px; box-shadow: 0 4px 14px rgba(0,0,0,0.4); color: #ffffff; font-size: 11px; font-weight: bold; white-space: nowrap;">
          <span>⛵</span>
          <span>${text}</span>
        </div>
      `,
      iconSize: [220, 28],
      iconAnchor: [110, 14],
    });

  // Restricted Zone Badge Icon
  const createRestrictedBadgeIcon = (name: string) =>
    L.divIcon({
      className: 'custom-restricted-badge',
      html: `
        <div style="display: flex; align-items: center; gap: 4px; background: rgba(225, 29, 72, 0.92); border: 1.5px solid #ffffff; padding: 3px 8px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); color: #ffffff; font-size: 10px; font-weight: bold; white-space: nowrap;">
          <span>🚫</span>
          <span>${name}</span>
        </div>
      `,
      iconSize: [160, 24],
      iconAnchor: [80, 12],
    });

  // Ocean Current Vectors Icon
  const createCurrentVectorIcon = (deg: number) =>
    L.divIcon({
      className: 'custom-current-arrow',
      html: `
        <div style="transform: rotate(${deg}deg); opacity: 0.65; color: #38bdf8; font-size: 16px; font-weight: bold;">
          ➔
        </div>
      `,
      iconSize: [20, 20],
      iconAnchor: [10, 10],
    });

  // PFZ GeoJSON Style
  const pfzStyle = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (feature?: any): L.PathOptions => {
      const cat = feature?.properties?.pfz_category?.toLowerCase();
      if (cat === 'chl') {
        return {
          color: '#10b981', // emerald
          weight: 3.5,
          opacity: 0.95,
        };
      }
      return {
        color: '#f59e0b', // amber
        weight: 3.5,
        opacity: 0.95,
        dashArray: '6 4',
      };
    },
    []
  );

  // PFZ popup
  const onEachPFZFeature = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (feature: any, layer: L.Layer) => {
      const p = feature?.properties || {};
      const cat = p.pfz_category_label || p.Category || 'Unknown';
      const uid = p.UID || p.uid || '—';
      const date = p.advisory_date || '—';
      const isCurrent: boolean = p.is_current ?? true;

      const popupHtml = `
        <div style="font-size:12px; min-width:200px; color:#e2e8f0">
          <div style="font-weight:700; color:#10b981; margin-bottom:5px;">
            🐟 INCOIS PFZ Advisory Line
          </div>
          <div style="display:grid; grid-template-columns:auto 1fr; gap:2px 8px; font-size:11px;">
            <span style="color:#94a3b8">Category:</span>
            <span style="font-weight:600; color:${p.pfz_category === 'chl' ? '#34d399' : '#fbbf24'}">${cat}</span>
            <span style="color:#94a3b8">UID:</span>
            <span style="font-family:monospace">${uid}</span>
            <span style="color:#94a3b8">Advisory Date:</span>
            <span>${date}</span>
            <span style="color:#94a3b8">Status:</span>
            <span style="font-weight:600; color:#34d399">${isCurrent ? 'Verified Current ✓' : 'Historical'}</span>
          </div>
          <div style="margin-top:6px; padding-top:4px; border-top:1px solid #334155; font-size:10px; color:#94a3b8;">
            Lines indicate productive ocean fronts & thermocline convergence.
          </div>
        </div>
      `;
      (layer as L.Path).on('mouseover', function (this: L.Path) {
        this.setStyle({ weight: 5, opacity: 1 });
      });
      (layer as L.Path).on('mouseout', function (this: L.Path) {
        this.setStyle({ weight: 3.5, opacity: 0.95 });
      });
      layer.bindPopup(popupHtml, { maxWidth: 280 });
    },
    []
  );

  // Conditions info
  const hazard = activeQueryResponse?.marine_hazard;
  const sst = activeQueryResponse?.ocean_sst;
  const waveHeightVal =
    hazard?.current_hour_observation?.wave_height_m ?? 0.6;
  const sstTemp = sst?.mean_sst_celsius ?? 30.1;

  // Active route coordinates
  const originCoord: [number, number] = [
    selectedCoordinate.latitude,
    selectedCoordinate.longitude,
  ];
  const destCoord: [number, number] = activeRoute
    ? [activeRoute.destinationCoord.latitude, activeRoute.destinationCoord.longitude]
    : [13.48, 74.45]; // default PFZ - 1 area off Malpe

  const routeMidpoint: [number, number] = [
    (originCoord[0] + destCoord[0]) / 2,
    (originCoord[1] + destCoord[1]) / 2,
  ];

  return (
    <div
      className={`relative w-full h-full overflow-hidden select-none ${
        isFullscreen ? 'fixed inset-0 z-50 bg-black' : 'min-h-[500px]'
      }`}
    >
      {/* ── Top Floating Location Search Bar ── */}
      <div className="absolute top-4 left-4 z-[500] w-[88%] sm:w-96">
        <div className="relative">
          <form onSubmit={handleManualCoordSubmit} className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => searchResults.length > 0 && setIsSearchOpen(true)}
              placeholder="Search location (e.g. Malpe, Mangaluru) or enter lat, lon"
              className="w-full pl-9 pr-9 py-2.5 rounded-xl bg-white/95 dark:bg-[#0c182a]/95 text-xs sm:text-sm text-slate-800 dark:text-slate-100 placeholder-slate-400 border border-slate-300 dark:border-slate-700/80 shadow-lg backdrop-blur-md focus:outline-none focus:ring-2 focus:ring-cyan-500 transition-all"
            />
            <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
            <button
              type="button"
              onClick={handleLocateMe}
              className="absolute right-2.5 top-2.5 p-1 rounded-lg text-slate-400 hover:text-cyan-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title="Locate my position"
            >
              <Crosshair className="h-4 w-4" />
            </button>
          </form>

          {/* Autocomplete Dropdown */}
          {isSearchOpen && searchResults.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1.5 max-h-60 overflow-y-auto rounded-xl bg-white dark:bg-[#0c182a] border border-slate-200 dark:border-slate-700/80 shadow-2xl backdrop-blur-md py-1.5 text-xs">
              <div className="px-3 py-1 text-[10px] uppercase font-semibold text-slate-400 dark:text-slate-500 border-b border-slate-200 dark:border-slate-800">
                Coastal Landing Points & Ports
              </div>
              {searchResults.map((result) => (
                <button
                  key={result.placeId}
                  onClick={() => handleSelectSearchResult(result)}
                  className="w-full px-3 py-2 text-left hover:bg-slate-100 dark:hover:bg-cyan-950/40 text-slate-800 dark:text-slate-200 flex items-start gap-2 border-b border-slate-100 dark:border-slate-800/40 last:border-b-0 transition-colors"
                >
                  <MapPin className="h-3.5 w-3.5 text-cyan-500 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold text-xs">{result.name}</div>
                    <div className="text-[11px] text-slate-400 truncate">
                      {result.displayName}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Floating Map Layers Control Box (Top-Right Overlay matching mockup) ── */}
      <div className="absolute top-4 right-16 z-[500] hidden md:block">
        <div className="rounded-2xl bg-[#091526]/95 border border-slate-700/80 p-3 shadow-2xl backdrop-blur-md text-white w-56">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs font-bold text-slate-200">
            <span className="flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5 text-cyan-400" />
              Map Layers
            </span>
          </div>

          <div className="mt-2 space-y-1.5 text-xs">
            {layers.map((layer) => {
              const checked = layer.enabled;

              return (
                <label
                  key={layer.id}
                  className="flex items-center justify-between p-1.5 rounded-lg hover:bg-slate-800/60 cursor-pointer transition-colors group"
                >
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleLayer(layer.id)}
                      className="rounded border-slate-600 text-cyan-500 focus:ring-cyan-500 bg-slate-900 h-3.5 w-3.5"
                    />
                    <span className="text-[11px] font-medium text-slate-200 group-hover:text-white">
                      {layer.name}
                    </span>
                  </div>

                  {/* Layer Color Dot / Icon */}
                  <span
                    className={`h-2 w-2 rounded-full ${
                      layer.id === 'pfz-advisories'
                        ? 'bg-emerald-400'
                        : layer.id === 'marine-weather'
                        ? 'bg-sky-400'
                        : layer.id === 'ocean-sst'
                        ? 'bg-amber-400'
                        : layer.id === 'chlorophyll'
                        ? 'bg-purple-400'
                        : layer.id === 'ocean-currents'
                        ? 'bg-cyan-400'
                        : layer.id === 'restricted-zones'
                        ? 'bg-rose-500'
                        : 'bg-blue-400'
                    }`}
                  />
                </label>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Right Vertical Map Action Buttons ── */}
      <div className="absolute top-4 right-4 z-[500] flex flex-col gap-2">
        <button
          onClick={() => setIsLayerBoxOpen(!isLayerBoxOpen)}
          className="md:hidden p-2.5 rounded-xl bg-white/95 dark:bg-[#0c182a]/95 text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-700/80 shadow-lg backdrop-blur-md hover:bg-slate-100"
          title="Toggle Layers"
        >
          <Layers className="h-4 w-4" />
        </button>

        <button
          onClick={handleLocateMe}
          className="p-2.5 rounded-xl bg-white/95 dark:bg-[#0c182a]/95 text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-700/80 shadow-lg backdrop-blur-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          title="GPS Locate Me"
        >
          <Crosshair className="h-4 w-4 text-cyan-500" />
        </button>

        <button
          onClick={() => {
            onSelectCoordinate(
              { latitude: 13.354, longitude: 74.704 },
              'Malpe Port'
            );
          }}
          className="p-2.5 rounded-xl bg-white/95 dark:bg-[#0c182a]/95 text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-700/80 shadow-lg backdrop-blur-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          title="Reset to Malpe Coast"
        >
          <Compass className="h-4 w-4 text-sky-500" />
        </button>

        <button
          onClick={() => setIsFullscreen(!isFullscreen)}
          className="p-2.5 rounded-xl bg-white/95 dark:bg-[#0c182a]/95 text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-700/80 shadow-lg backdrop-blur-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen Map'}
        >
          {isFullscreen ? (
            <Minimize2 className="h-4 w-4" />
          ) : (
            <Maximize2 className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* ── Floating "Sea Conditions at Your Location" Card (Bottom-Left on Map matching mockup) ── */}
      <div className="absolute bottom-6 left-4 z-[500] w-64 rounded-2xl bg-[#091526]/95 border border-slate-700/80 p-3.5 shadow-2xl backdrop-blur-md text-white hidden sm:block">
        <h4 className="text-xs font-bold text-slate-200 mb-2.5 flex items-center justify-between">
          <span>Sea Conditions at Your Location</span>
          <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
        </h4>

        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 flex items-center gap-1.5">
              <Waves className="h-3.5 w-3.5 text-sky-400" /> Wave Height
            </span>
            <span className="font-semibold text-slate-100">
              {waveHeightVal.toFixed(1)} m
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-400 flex items-center gap-1.5">
              <Wind className="h-3.5 w-3.5 text-cyan-400" /> Wind Speed
            </span>
            <span className="font-semibold text-slate-100">8 km/h (N)</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-400 flex items-center gap-1.5">
              <Thermometer className="h-3.5 w-3.5 text-amber-400" /> Sea Temp (SST)
            </span>
            <span className="font-semibold text-slate-100">
              {sstTemp.toFixed(1)} °C
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-400 flex items-center gap-1.5">
              <span className="text-purple-400 font-bold">🧪</span> Chlorophyll
            </span>
            <span className="font-semibold text-emerald-400">Moderate</span>
          </div>
        </div>

        <div className="mt-2.5 pt-2 border-t border-slate-800 text-[10px] text-slate-400 flex items-center justify-between">
          <span>Updated: 27 Oct 2026, 05:30 AM</span>
        </div>
      </div>

      {/* ── Scale Bar Overlay (Bottom-Center) ── */}
      <div className="absolute bottom-6 left-72 z-[500] hidden lg:flex items-center gap-1 px-3 py-1 rounded-lg bg-black/60 backdrop-blur-xs text-[10px] font-mono text-white border border-white/20">
        <span>0</span>
        <div className="w-8 border-b-2 border-white" />
        <span>10</span>
        <div className="w-8 border-b-2 border-white" />
        <span>20</span>
        <div className="w-8 border-b-2 border-white" />
        <span>30 km</span>
      </div>

      {/* ── Leaflet Interactive Map Canvas ── */}
      <MapContainer
        center={[KARNATAKA_MAP_CENTER.latitude, KARNATAKA_MAP_CENTER.longitude]}
        zoom={9}
        scrollWheelZoom={true}
        className="w-full h-full"
      >
        <MapViewController targetCoordinate={selectedCoordinate} />
        <MapClickHandler onMapClick={handleMapClick} />

        {/* Base Tile Layer */}
        <TileLayer
          key={activeTile.id}
          url={activeTile.url}
          attribution={activeTile.attribution}
          maxZoom={activeTile.maxZoom}
        />

        {/* User / Target Location Pin */}
        <Marker
          position={[selectedCoordinate.latitude, selectedCoordinate.longitude]}
          icon={createUserPinIcon(selectedLocationName || 'Malpe')}
        >
          <Popup>
            <div className="text-xs space-y-1">
              <div className="font-bold text-cyan-400 flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5" />
                {selectedLocationName || 'Selected Location'}
              </div>
              <div className="text-slate-300 font-mono">
                {selectedCoordinate.latitude.toFixed(4)}°N,{' '}
                {selectedCoordinate.longitude.toFixed(4)}°E
              </div>
              <p className="text-[10px] text-slate-400 pt-1 border-t border-slate-700">
                Departure point for marine navigation and fishing zone discovery.
              </p>
            </div>
          </Popup>
        </Marker>

        {/* Coastal Ports Baseline Markers */}
        {isLayerActive('coastal-ports') &&
          KARNATAKA_PORTS.map((port) => (
            <Marker
              key={port.id}
              position={[port.coordinate.latitude, port.coordinate.longitude]}
              icon={createPortIcon(port.name)}
              eventHandlers={{
                click: () => onSelectCoordinate(port.coordinate, port.name),
              }}
            >
              <Popup>
                <div className="text-xs space-y-1">
                  <div className="font-bold text-sky-400">
                    ⚓ {port.name} Harbour
                  </div>
                  <div className="text-slate-300 text-[11px]">
                    {port.district}, {port.state}
                  </div>
                  <div className="text-[10px] text-amber-300/90 font-medium">
                    Coastal departure baseline &bull; Valid landing port.
                  </div>
                  <button
                    onClick={() =>
                      onSelectCoordinate(port.coordinate, port.name)
                    }
                    className="mt-1 w-full py-1 text-center bg-blue-600 hover:bg-blue-500 text-white rounded text-[11px] font-medium transition-colors"
                  >
                    Select as Departure Point
                  </button>
                </div>
              </Popup>
            </Marker>
          ))}

        {/* Live INCOIS PFZ Advisory Lines */}
        {isLayerActive('pfz-advisories') &&
          pfzData &&
          pfzData.features.length > 0 && (
            <GeoJSON
              key={`pfz-${pfzGeoJsonKey.current}`}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              data={pfzData as any}
              style={pfzStyle}
              onEachFeature={onEachPFZFeature}
            />
          )}

        {/* Mockup PFZ Callout Badges (PFZ - 1 High Potential & PFZ - 2 Moderate) */}
        {isLayerActive('pfz-advisories') && (
          <>
            <Marker
              position={[13.48, 74.45]}
              icon={createPFZCalloutIcon(
                'PFZ - 1',
                'High Potential',
                'rgba(16, 185, 129, 0.95)'
              )}
            >
              <Popup>
                <div className="text-xs space-y-1">
                  <div className="font-bold text-emerald-400">
                    🐟 PFZ - 1 (High Potential)
                  </div>
                  <p className="text-slate-300">
                    Optimal sea surface thermal gradient with chlorophyll front.
                  </p>
                  <div className="text-[11px] text-slate-400">
                    Distance: 18 km (~1.2 hrs) from Malpe
                  </div>
                </div>
              </Popup>
            </Marker>

            <Marker
              position={[13.25, 74.62]}
              icon={createPFZCalloutIcon(
                'PFZ - 2',
                'Moderate',
                'rgba(217, 119, 6, 0.95)'
              )}
            >
              <Popup>
                <div className="text-xs space-y-1">
                  <div className="font-bold text-amber-400">
                    🐟 PFZ - 2 (Moderate Potential)
                  </div>
                  <p className="text-slate-300">
                    Secondary thermal front line along 30-meter bathymetric contour.
                  </p>
                </div>
              </Popup>
            </Marker>
          </>
        )}

        {/* Marine Route Polyline & Badge */}
        {activeRoute && (
          <>
            {/* Route Outer Glow Line */}
            <Polyline
              positions={[originCoord, destCoord]}
              pathOptions={{
                color: '#38bdf8',
                weight: 6,
                opacity: 0.5,
              }}
            />
            {/* Route Inner Dash Line */}
            <Polyline
              positions={[originCoord, destCoord]}
              pathOptions={{
                color: '#ffffff',
                weight: 3,
                dashArray: '8 6',
                opacity: 0.95,
              }}
            />
            {/* Midpoint Route Badge */}
            <Marker
              position={routeMidpoint}
              icon={createRouteBadgeIcon(
                `${activeRoute.routeType === 'return_to_shore' ? 'Return Route' : 'Recommended Route'} | ${activeRoute.distanceKm.toFixed(0)} km • ~${activeRoute.estimatedHours.toFixed(1)} hrs`
              )}
            >
              <Popup>
                <div className="text-xs space-y-1.5">
                  <div className="font-bold text-emerald-400">
                    ⛵ Indicative Nautical Route Guidance
                  </div>
                  <div className="text-slate-300">
                    Origin: {activeRoute.originName}
                    <br />
                    Destination: {activeRoute.destinationName}
                  </div>
                  <div className="text-[11px] text-slate-400">
                    Distance: {activeRoute.distanceKm.toFixed(1)} km &bull; Bearing:{' '}
                    {activeRoute.bearingDeg.toFixed(0)}°
                  </div>
                  {activeRoute.crossesRestrictedZone && (
                    <div className="p-1.5 rounded bg-rose-950/60 border border-rose-600/60 text-rose-300 text-[10px] font-bold">
                      ⚠️ Caution: Route passes near or through a Restricted Marine Area!
                    </div>
                  )}
                  <div className="text-[10px] text-slate-400 pt-1 border-t border-slate-700 italic">
                    {activeRoute.limitations}
                  </div>
                </div>
              </Popup>
            </Marker>
          </>
        )}

        {/* Restricted Maritime Zones Polygons (St Mary's & Netrani) */}
        {isLayerActive('restricted-zones') &&
          KARNATAKA_RESTRICTED_ZONES.map((zone) => (
            <React.Fragment key={zone.id}>
              <Polygon
                positions={zone.coordinates}
                pathOptions={{
                  color: '#e11d48',
                  weight: 2,
                  dashArray: '6 4',
                  fillColor: '#be123c',
                  fillOpacity: 0.22,
                }}
              >
                <Popup>
                  <div className="text-xs space-y-1">
                    <div className="font-bold text-rose-400 flex items-center gap-1">
                      <Ban className="h-3.5 w-3.5" />
                      {zone.name}
                    </div>
                    <p className="text-slate-300 text-[11px]">
                      {zone.description}
                    </p>
                    <div className="text-[10px] text-slate-400 pt-1 border-t border-slate-700">
                      Authority: {zone.authority}
                    </div>
                  </div>
                </Popup>
              </Polygon>

              {/* Centroid Badge */}
              <Marker
                position={[
                  zone.coordinates.reduce((acc, c) => acc + c[0], 0) /
                    zone.coordinates.length,
                  zone.coordinates.reduce((acc, c) => acc + c[1], 0) /
                    zone.coordinates.length,
                ]}
                icon={createRestrictedBadgeIcon('Restricted Zone (Do Not Enter)')}
              />
            </React.Fragment>
          ))}

        {/* Ocean Surface Current Arrows (mockup shelf current flow vectors) */}
        {isLayerActive('ocean-currents') && (
          <>
            <Marker position={[13.6, 74.3]} icon={createCurrentVectorIcon(160)} />
            <Marker position={[13.4, 74.35]} icon={createCurrentVectorIcon(165)} />
            <Marker position={[13.2, 74.45]} icon={createCurrentVectorIcon(170)} />
            <Marker position={[13.0, 74.55]} icon={createCurrentVectorIcon(175)} />
            <Marker position={[13.5, 74.2]} icon={createCurrentVectorIcon(160)} />
          </>
        )}
      </MapContainer>
    </div>
  );
}

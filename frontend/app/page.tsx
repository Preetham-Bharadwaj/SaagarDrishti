'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { NavRail } from '../components/layout/nav-rail';
import { AppHeader } from '../components/layout/app-header';
import { MarineChatPanel } from '../components/chat/marine-chat-panel';
import { MarineMap } from '../components/map/marine-map';
import { FishermanCards } from '../components/dashboard/fisherman-cards';
import {
  SafetyDetailsModal,
  WeatherForecastModal,
  CommunityModal,
  TechnicalProvenanceModal,
} from '../components/modals/marine-modals';
import {
  GeoCoordinate,
  MarineQueryResponse,
  MarineRouteInfo,
  SupportedLanguage,
} from '../lib/types/marine';
import { submitMarineQuery } from '../lib/api-client';
import {
  KARNATAKA_PORTS,
  reverseGeocode,
} from '../lib/geocoding';
import { KARNATAKA_RESTRICTED_ZONES } from '../lib/map-config';

export default function DashboardPage() {
  // Navigation Tab State: 'home' | 'map' | 'alerts' | 'community' | 'settings'
  const [activeTab, setActiveTab] = useState<
    'home' | 'map' | 'alerts' | 'community' | 'settings'
  >('home');

  // Selected Location (Default: Malpe Harbour, Udupi Coast, Karnataka)
  const [selectedLocation, setSelectedLocation] = useState<{
    name: string;
    coordinate: GeoCoordinate;
  }>({
    name: 'Malpe, Karnataka',
    coordinate: { latitude: 13.354, longitude: 74.704 },
  });

  // Language state
  const [currentLanguage, setCurrentLanguage] = useState<SupportedLanguage>('en');

  // Geolocation probe state
  const [isLocating, setIsLocating] = useState(false);

  // Active query & external query synchronization
  const [activeQueryResponse, setActiveQueryResponse] =
    useState<MarineQueryResponse | null>(null);
  const [externalResponse, setExternalResponse] = useState<{
    query: string;
    response: MarineQueryResponse;
    timestamp: string;
  } | null>(null);

  // Active route guidance
  const [activeRoute, setActiveRoute] = useState<MarineRouteInfo | null>(null);

  // Modal dialog states
  const [isSafetyModalOpen, setIsSafetyModalOpen] = useState(false);
  const [isForecastModalOpen, setIsForecastModalOpen] = useState(false);
  const [isCommunityModalOpen, setIsCommunityModalOpen] = useState(false);
  const [isProvenanceModalOpen, setIsProvenanceModalOpen] = useState(false);

  // Probe marine conditions whenever target location changes
  const probeLocationConditions = useCallback(
    async (name: string, coord: GeoCoordinate) => {
      const queryText = `What are the sea and wave hazard conditions near ${name}?`;
      const result = await submitMarineQuery({
        query: queryText,
        departure_port: name,
        user_location: coord,
      });

      if (result.success && result.data) {
        setActiveQueryResponse(result.data);
        setExternalResponse({
          query: queryText,
          response: result.data,
          timestamp: new Date().toISOString(),
        });
      }
    },
    []
  );

  useEffect(() => {
    probeLocationConditions(
      selectedLocation.name,
      selectedLocation.coordinate
    );
  }, [probeLocationConditions, selectedLocation.name, selectedLocation.coordinate]);

  const handleSelectCoordinate = (coord: GeoCoordinate, name?: string) => {
    const locName =
      name ||
      `Lat ${coord.latitude.toFixed(2)}°, Lon ${coord.longitude.toFixed(2)}°`;
    setSelectedLocation({
      name: locName,
      coordinate: coord,
    });
    probeLocationConditions(locName, coord);
  };

  // Chat Query Response synchronization
  const handleChatQueryResponse = (res: MarineQueryResponse) => {
    setActiveQueryResponse(res);
  };

  // Browser Geolocation Flow
  const handleTriggerGeolocation = () => {
    if (typeof window === 'undefined' || !('geolocation' in navigator)) {
      alert('Browser geolocation is not supported on this device.');
      return;
    }

    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        setIsLocating(false);
        const { latitude, longitude, accuracy } = pos.coords;
        const userCoord: GeoCoordinate = { latitude, longitude };

        // Determine whether user is on land or offshore:
        // Karnataka coastline runs approximately along longitude 74.65°E - 74.85°E.
        // If longitude < 74.60°E (between lat 12.8°N and 15°N), the position is offshore in the Arabian Sea.
        const isOffshore =
          latitude >= 12.5 &&
          latitude <= 15.2 &&
          longitude < 74.62;

        let detectedName = '';
        if (isOffshore) {
          detectedName = `Offshore Vessel (${latitude.toFixed(3)}°N, ${longitude.toFixed(3)}°E)`;
        } else {
          // Identify nearest coastal departure port
          let closestPort = KARNATAKA_PORTS[0];
          let minDistance = Infinity;
          for (const port of KARNATAKA_PORTS) {
            const dLat = port.coordinate.latitude - latitude;
            const dLon = port.coordinate.longitude - longitude;
            const d = Math.sqrt(dLat * dLat + dLon * dLon);
            if (d < minDistance) {
              minDistance = d;
              closestPort = port;
            }
          }
          const placeDesc = await reverseGeocode(userCoord);
          detectedName = `${closestPort.name} Coast (${placeDesc})`;
        }

        setSelectedLocation({
          name: detectedName,
          coordinate: userCoord,
        });
        probeLocationConditions(detectedName, userCoord);

        const accuracyText = accuracy ? ` (±${accuracy.toFixed(0)}m accuracy)` : '';
        const landSeaNote = isOffshore
          ? 'You appear to be offshore in the Arabian Sea. Current vessel coordinates locked.'
          : 'You appear to be on land. Calibrated to nearest Karnataka coastal harbour departure baseline.';

        alert(`📍 Location verified: ${detectedName}${accuracyText}.\n\n${landSeaNote}`);
      },
      (err) => {
        setIsLocating(false);
        alert(`Location permission denied or unavailable: ${err.message}. You can manually search or tap any port on the map.`);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  // Route Planning: View Route to PFZ
  const handlePlanRouteToPfz = () => {
    const origin = selectedLocation.coordinate;
    // Default destination: Candidate PFZ or primary PFZ - 1 off Malpe
    const dest = activeQueryResponse?.candidate_pfz?.coordinate || {
      latitude: 13.48,
      longitude: 74.45,
    };

    // Calculate Haversine distance
    const R = 6371; // km
    const dLat = ((dest.latitude - origin.latitude) * Math.PI) / 180;
    const dLon = ((dest.longitude - origin.longitude) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((origin.latitude * Math.PI) / 180) *
        Math.cos((dest.latitude * Math.PI) / 180) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const distKm = R * c;

    // Bearing
    const y =
      Math.sin(dLon) * Math.cos((dest.latitude * Math.PI) / 180);
    const x =
      Math.cos((origin.latitude * Math.PI) / 180) *
        Math.sin((dest.latitude * Math.PI) / 180) -
      Math.sin((origin.latitude * Math.PI) / 180) *
        Math.cos((dest.latitude * Math.PI) / 180) *
        Math.cos(dLon);
    const brng = ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;

    // Check intersection with St. Mary's restricted perimeter
    const crossesRestricted =
      Math.min(origin.latitude, dest.latitude) <= 13.395 &&
      Math.max(origin.latitude, dest.latitude) >= 13.355;

    setActiveRoute({
      originName: selectedLocation.name,
      originCoord: origin,
      destinationName: 'PFZ - 1 (High Potential)',
      destinationCoord: dest,
      distanceKm: distKm || 18,
      estimatedHours: (distKm || 18) / 15,
      bearingDeg: brng,
      routeType: 'to_pfz',
      safetyStatus: crossesRestricted ? 'caution' : 'safe',
      safetySummary: crossesRestricted
        ? 'Route passes near St. Mary’s Marine Heritage Reef. Steer clear of shallow shoals.'
        : 'Open Arabian Sea shelf waters. Normal coastal swell conditions.',
      crossesRestrictedZone: crossesRestricted,
      limitations:
        'Indicative nautical guidance. Verify navigational depth sounders, local tides, and VHF notices before steering.',
    });
  };

  // Route Planning: Return to Shore
  const handleReturnToShore = () => {
    const origin = selectedLocation.coordinate;
    // Nearest port is Malpe
    const dest = { latitude: 13.354, longitude: 74.704 };

    const R = 6371;
    const dLat = ((dest.latitude - origin.latitude) * Math.PI) / 180;
    const dLon = ((dest.longitude - origin.longitude) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((origin.latitude * Math.PI) / 180) *
        Math.cos((dest.latitude * Math.PI) / 180) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const distKm = Math.max(0.5, R * c);

    setActiveRoute({
      originName: selectedLocation.name,
      originCoord: origin,
      destinationName: 'Malpe Port (Shore Entrance)',
      destinationCoord: dest,
      distanceKm: distKm,
      estimatedHours: distKm / 15,
      bearingDeg: 95,
      routeType: 'return_to_shore',
      safetyStatus: 'safe',
      safetySummary: 'Direct eastward heading toward Malpe Harbour breakwater channel.',
      limitations:
        'Approach Malpe estuary channel strictly between navigation buoys. Comply with Port Officer VHF instructions.',
    });
  };

  // Handle Tab Selection from Nav Rail
  const handleSelectNavTab = (
    tab: 'home' | 'map' | 'alerts' | 'community' | 'settings'
  ) => {
    setActiveTab(tab);
    if (tab === 'alerts') setIsSafetyModalOpen(true);
    if (tab === 'community') setIsCommunityModalOpen(true);
    if (tab === 'settings') setIsProvenanceModalOpen(true);
  };

  return (
    <div className="min-h-screen flex bg-slate-50 dark:bg-[#060b13] text-slate-900 dark:text-slate-100 transition-colors">
      {/* ── 1. Left Vertical Navigation Rail (Matches Mockup) ── */}
      <NavRail activeTab={activeTab} onSelectTab={handleSelectNavTab} />

      {/* ── 2. Main Content Area ── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <AppHeader
          selectedLocation={selectedLocation}
          onTriggerGeolocation={handleTriggerGeolocation}
          isLocating={isLocating}
          currentLanguage={currentLanguage}
          onLanguageChange={setCurrentLanguage}
          weatherSummary={{
            temperatureC: 28,
            windSpeedKmh: 8,
            waveHeightM:
              activeQueryResponse?.marine_hazard?.current_hour_observation
                ?.wave_height_m ?? 0.6,
          }}
        />

        {/* Main Dashboard Body */}
        <main className="flex-1 max-w-[1920px] w-full mx-auto p-3 sm:p-5 space-y-4">
          {/* Main Top Split Grid: Conversational AI Assistant (Left) + Interactive Marine Map (Right) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-[650px] sm:h-[700px] max-h-[80vh]">
            {/* Left Column: Conversational AI Assistant (4 cols on lg) */}
            <div className="lg:col-span-5 xl:col-span-4 h-full rounded-3xl overflow-hidden border border-slate-200 dark:border-slate-800 shadow-xl flex flex-col">
              <MarineChatPanel
                selectedLocation={selectedLocation}
                onSelectCoordinate={handleSelectCoordinate}
                onQueryResponse={handleChatQueryResponse}
                externalResponse={externalResponse}
                currentLanguage={currentLanguage}
                onPlanRoute={handlePlanRouteToPfz}
                onShowOnMap={() => {
                  // Handled via map centering
                }}
                onViewDetails={() => setIsSafetyModalOpen(true)}
                onReturnToShore={handleReturnToShore}
              />
            </div>

            {/* Right Column: Interactive Leaflet Marine Map (7 cols on lg, 8 on xl) */}
            <div className="lg:col-span-7 xl:col-span-8 h-full rounded-3xl overflow-hidden border border-slate-200 dark:border-slate-800 shadow-xl relative flex flex-col">
              <MarineMap
                selectedCoordinate={selectedLocation.coordinate}
                selectedLocationName={selectedLocation.name}
                onSelectCoordinate={handleSelectCoordinate}
                activeQueryResponse={activeQueryResponse}
                activeRoute={activeRoute}
                onClearRoute={() => setActiveRoute(null)}
              />
            </div>
          </div>

          {/* Bottom Row: 4 Fisherman-First Cards (Directly matching mockup) */}
          <FishermanCards
            locationName={selectedLocation.name}
            coordinate={selectedLocation.coordinate}
            candidatePfz={activeQueryResponse?.candidate_pfz}
            hazardForecast={activeQueryResponse?.marine_hazard}
            officialWarning={activeQueryResponse?.official_warning}
            sstResult={activeQueryResponse?.ocean_sst}
            currentLanguage={currentLanguage}
            onViewRoute={handlePlanRouteToPfz}
            onViewSafetyDetails={() => setIsSafetyModalOpen(true)}
            onViewForecastDetails={() => setIsForecastModalOpen(true)}
            onPlanReturnRoute={handleReturnToShore}
            distanceToShoreKm={0}
            nearestShoreName="Malpe Port"
          />
        </main>
      </div>

      {/* ── Secondary Modals (Preserves Provenance, Detailed Bulletins & Developer Inspection) ── */}
      <SafetyDetailsModal
        isOpen={isSafetyModalOpen}
        onClose={() => setIsSafetyModalOpen(false)}
        warning={activeQueryResponse?.official_warning}
      />

      <WeatherForecastModal
        isOpen={isForecastModalOpen}
        onClose={() => setIsForecastModalOpen(false)}
        hazardForecast={activeQueryResponse?.marine_hazard}
      />

      <CommunityModal
        isOpen={isCommunityModalOpen}
        onClose={() => setIsCommunityModalOpen(false)}
      />

      <TechnicalProvenanceModal
        isOpen={isProvenanceModalOpen}
        onClose={() => setIsProvenanceModalOpen(false)}
        sstResult={activeQueryResponse?.ocean_sst}
      />
    </div>
  );
}

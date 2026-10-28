'use client';

import React, { useState, useEffect } from 'react';
import { AppHeader } from '../../components/layout/app-header';
import { MarineMap } from '../../components/map/marine-map';
import { MarineConditionsCard } from '../../components/dashboard/marine-conditions-card';
import { GeoCoordinate, MarineQueryResponse } from '../../lib/types/marine';
import { submitMarineQuery } from '../../lib/api-client';

export default function MarineMapPage() {
  const [selectedLocation, setSelectedLocation] = useState<{
    name: string;
    coordinate: GeoCoordinate;
  }>({
    name: 'Malpe Port',
    coordinate: { latitude: 13.354, longitude: 74.704 },
  });

  const [activeQueryResponse, setActiveQueryResponse] =
    useState<MarineQueryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchConditions = async (name: string, coord: GeoCoordinate) => {
    setIsLoading(true);
    const result = await submitMarineQuery({
      query: `What are the sea and wave hazard conditions near ${name}?`,
      departure_port: name,
      user_location: coord,
    });
    if (result.success && result.data) {
      setActiveQueryResponse(result.data);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    fetchConditions(selectedLocation.name, selectedLocation.coordinate);
  }, []);

  const handleSelectCoordinate = (coord: GeoCoordinate, name?: string) => {
    const locName =
      name ||
      `Lat ${coord.latitude.toFixed(2)}°, Lon ${coord.longitude.toFixed(2)}°`;
    setSelectedLocation({
      name: locName,
      coordinate: coord,
    });
    fetchConditions(locName, coord);
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-[#060b13] text-slate-900 dark:text-slate-100 transition-colors">
      <AppHeader selectedLocation={selectedLocation} />

      <main className="flex-1 max-w-[1920px] w-full mx-auto p-3 sm:p-5 flex flex-col gap-4">
        <div className="flex-1 min-h-[75vh] rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-800/80 shadow-lg relative">
          <MarineMap
            selectedCoordinate={selectedLocation.coordinate}
            selectedLocationName={selectedLocation.name}
            onSelectCoordinate={handleSelectCoordinate}
            activeQueryResponse={activeQueryResponse}
          />
        </div>

        <MarineConditionsCard
          locationName={selectedLocation.name}
          coordinate={selectedLocation.coordinate}
          hazardForecast={activeQueryResponse?.marine_hazard}
          sstResult={activeQueryResponse?.ocean_sst}
          isLoading={isLoading}
        />
      </main>
    </div>
  );
}

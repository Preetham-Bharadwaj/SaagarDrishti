'use client';

import React from 'react';
import {
  Waves,
  Wind,
  Thermometer,
  Compass,
  AlertTriangle,
  Clock,
  ShieldCheck,
  Navigation,
} from 'lucide-react';
import {
  MarineHazardForecast,
  OceanSSTResult,
  GeoCoordinate,
} from '../../lib/types/marine';
import {
  formatWaveHeight,
  formatSST,
  getDouglasStateLabel,
  formatBearing,
  formatMarineDateTime,
} from '../../lib/formatters';

interface MarineConditionsCardProps {
  locationName: string;
  coordinate: GeoCoordinate;
  hazardForecast?: MarineHazardForecast | null;
  sstResult?: OceanSSTResult | null;
  isLoading?: boolean;
}

export function MarineConditionsCard({
  locationName,
  coordinate,
  hazardForecast,
  sstResult,
  isLoading,
}: MarineConditionsCardProps) {
  const currentObs = hazardForecast?.current_hour_observation;
  const douglasState = getDouglasStateLabel(currentObs?.wave_height_m);

  return (
    <div className="rounded-2xl bg-white dark:bg-[#0c182a] border border-slate-200 dark:border-slate-800/80 p-4 shadow-sm transition-colors">
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800/80">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
            <Waves className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
              Live Marine Conditions
            </h3>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              {locationName} ({coordinate.latitude.toFixed(2)}°N,{' '}
              {coordinate.longitude.toFixed(2)}°E)
            </p>
          </div>
        </div>

        {hazardForecast && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-medium">
            ECMWF ERAssWave
          </span>
        )}
      </div>

      {isLoading ? (
        <div className="py-8 flex items-center justify-center text-xs text-slate-400">
          <div className="h-4 w-4 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mr-2" />
          Probing oceanographic sensors & wave model...
        </div>
      ) : (
        <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          {/* Wave Height */}
          <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-[#111e33] border border-slate-200/60 dark:border-slate-800/60">
            <span className="text-[11px] text-slate-400 flex items-center gap-1">
              <Waves className="h-3 w-3 text-sky-500" />
              Sig. Wave Height
            </span>
            <div className="text-base font-bold text-slate-800 dark:text-slate-100 mt-1">
              {formatWaveHeight(currentObs?.wave_height_m)}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              Peak: {formatWaveHeight(hazardForecast?.peak_wave_height_m)}
            </div>
          </div>

          {/* Douglas Sea State */}
          <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-[#111e33] border border-slate-200/60 dark:border-slate-800/60">
            <span className="text-[11px] text-slate-400 flex items-center gap-1">
              <Navigation className="h-3 w-3 text-teal-500" />
              Sea State (Douglas)
            </span>
            <div className="text-xs font-semibold mt-1">
              <span
                className={`inline-block px-1.5 py-0.5 rounded text-[10px] border ${douglasState.badgeClass}`}
              >
                {douglasState.label}
              </span>
            </div>
            <div className="text-[10px] text-slate-400 mt-1">
              Swell: {currentObs?.swell_wave_period_s ? `${currentObs.swell_wave_period_s.toFixed(1)}s` : 'Unavailable'}
            </div>
          </div>

          {/* Sea Surface Temperature */}
          <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-[#111e33] border border-slate-200/60 dark:border-slate-800/60">
            <span className="text-[11px] text-slate-400 flex items-center gap-1">
              <Thermometer className="h-3 w-3 text-cyan-500" />
              Foundation SST
            </span>
            <div className="text-base font-bold text-slate-800 dark:text-slate-100 mt-1">
              {formatSST(sstResult?.mean_sst_celsius)}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              {sstResult ? 'OSTIA L4 Satellite' : 'Awaiting Query'}
            </div>
          </div>

          {/* Wave Propagation Direction */}
          <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-[#111e33] border border-slate-200/60 dark:border-slate-800/60">
            <span className="text-[11px] text-slate-400 flex items-center gap-1">
              <Compass className="h-3 w-3 text-indigo-500" />
              Wave Direction
            </span>
            <div className="text-xs font-semibold text-slate-800 dark:text-slate-100 mt-1">
              {formatBearing(currentObs?.wave_direction_deg)}
            </div>
            <div className="text-[10px] text-slate-400 mt-1">
              Wind Wave: {formatBearing(currentObs?.wind_wave_direction_deg)}
            </div>
          </div>
        </div>
      )}

      {/* Timestamp & Provenance footer */}
      <div className="mt-3 pt-2 border-t border-slate-100 dark:border-slate-800/60 flex flex-wrap items-center justify-between text-[10px] text-slate-400">
        <span className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          Model step: {hazardForecast?.forecast_valid_time || 'Hourly operational forecast'}
        </span>
        <span className="italic text-slate-500">
          Numerical model output &mdash; not an authoritative in-situ sensor
        </span>
      </div>
    </div>
  );
}

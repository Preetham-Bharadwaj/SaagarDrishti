'use client';

import React from 'react';
import {
  Fish,
  ShieldCheck,
  ShieldAlert,
  CloudSun,
  Anchor,
  Compass,
  Waves,
  Wind,
  Thermometer,
  CloudRain,
  ExternalLink,
  ChevronRight,
  Home,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import {
  CandidatePFZResult,
  GeoCoordinate,
  MarineHazardForecast,
  OfficialMarineWarning,
  OceanSSTResult,
  SupportedLanguage,
} from '../../lib/types/marine';
import { TRANSLATIONS } from '../../lib/translations';
import {
  formatBearing,
  formatDistance,
  formatWaveHeight,
  formatSST,
  getDouglasStateLabel,
} from '../../lib/formatters';

interface FishermanCardsProps {
  locationName: string;
  coordinate: GeoCoordinate;
  candidatePfz?: CandidatePFZResult | null;
  hazardForecast?: MarineHazardForecast | null;
  officialWarning?: OfficialMarineWarning | null;
  sstResult?: OceanSSTResult | null;
  currentLanguage?: SupportedLanguage;
  onViewRoute?: () => void;
  onViewSafetyDetails?: () => void;
  onViewForecastDetails?: () => void;
  onPlanReturnRoute?: () => void;
  distanceToShoreKm?: number;
  nearestShoreName?: string;
}

export function FishermanCards({
  locationName,
  coordinate,
  candidatePfz,
  hazardForecast,
  officialWarning,
  sstResult,
  currentLanguage = 'en',
  onViewRoute,
  onViewSafetyDetails,
  onViewForecastDetails,
  onPlanReturnRoute,
  distanceToShoreKm = 0,
  nearestShoreName = 'Malpe Port',
}: FishermanCardsProps) {
  const t = TRANSLATIONS[currentLanguage] || TRANSLATIONS.en;

  const currentWave =
    hazardForecast?.current_hour_observation?.wave_height_m ??
    hazardForecast?.peak_wave_height_m ??
    0.8;
  const hasWarning = Boolean(
    officialWarning && officialWarning.severity !== 'no_warning'
  );

  const pfzDistance = candidatePfz?.distance_km ?? 18;
  const estHours = (pfzDistance / 15).toFixed(1); // average trawler speed ~15 km/h
  const sstTemp = sstResult?.mean_sst_celsius ?? 30.2;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 select-none">
      {/* ── CARD 1: Recommended Fishing Zone (Emerald / Green) ── */}
      <div className="rounded-2xl p-4 bg-emerald-500/10 dark:bg-emerald-950/20 border border-emerald-500/30 flex flex-col justify-between transition-all hover:border-emerald-500/50 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-2 text-emerald-800 dark:text-emerald-300">
            <div className="p-1.5 rounded-lg bg-emerald-500/20">
              <Fish className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            </div>
            <span className="text-xs font-semibold">
              {t.cards.recommendedPfz}
            </span>
          </div>

          <div className="flex items-baseline gap-2 mb-2">
            <h4 className="text-lg font-bold text-slate-900 dark:text-white">
              {candidatePfz ? `PFZ: ${candidatePfz.landing_center}` : 'PFZ - 1'}
            </h4>
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30">
              {t.cards.highPotential}
            </span>
          </div>

          <div className="space-y-1 text-xs text-slate-600 dark:text-slate-300">
            <div className="flex items-center gap-1.5">
              <Compass className="h-3.5 w-3.5 text-emerald-500" />
              <span>
                Distance: {pfzDistance.toFixed(0)} km (~{estHours} hrs)
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <Thermometer className="h-3.5 w-3.5 text-emerald-500" />
              <span>
                SST: {sstTemp.toFixed(1)} °C &bull; Chlorophyll: High
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <Waves className="h-3.5 w-3.5 text-emerald-500" />
              <span>
                Wave Height: {currentWave.toFixed(1)} m (Moderate)
              </span>
            </div>
          </div>
        </div>

        <button
          onClick={onViewRoute}
          className="mt-3 w-full py-2 px-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors shadow-xs"
        >
          <span>{t.cards.viewRoute}</span>
        </button>
      </div>

      {/* ── CARD 2: Safety Alerts (Red / Rose) ── */}
      <div
        className={`rounded-2xl p-4 border flex flex-col justify-between transition-all shadow-xs ${
          hasWarning
            ? 'bg-rose-500/10 dark:bg-rose-950/20 border-rose-500/40 hover:border-rose-500/60'
            : 'bg-rose-50/70 dark:bg-[#16121a] border-rose-200 dark:border-rose-950/50 hover:border-rose-300'
        }`}
      >
        <div>
          <div className="flex items-center gap-2 mb-2 text-rose-800 dark:text-rose-300">
            <div className="p-1.5 rounded-lg bg-rose-500/20">
              <ShieldAlert className="h-4 w-4 text-rose-600 dark:text-rose-400" />
            </div>
            <span className="text-xs font-semibold">{t.cards.safetyAlerts}</span>
          </div>

          <div className="mb-2">
            <h4
              className={`text-lg font-bold ${
                hasWarning
                  ? 'text-rose-600 dark:text-rose-400'
                  : 'text-slate-900 dark:text-white'
              }`}
            >
              {hasWarning
                ? officialWarning?.warning_type || t.cards.activeWarning
                : t.cards.noMajorAlerts}
            </h4>
          </div>

          <div className="space-y-1 text-xs text-slate-600 dark:text-slate-300">
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
              <span>Wave height: 0.6 – 1.2 m</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-3.5 w-3.5 rounded-full bg-amber-500/20 text-amber-500 flex items-center justify-center font-bold text-[9px] shrink-0">
                !
              </span>
              <span>Light rain possible tomorrow</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
              <span>No active cyclone warning</span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-400 text-[11px]">
              <AlertTriangle className="h-3 w-3 text-amber-500 shrink-0" />
              <span>Be cautious during early morning</span>
            </div>
          </div>
        </div>

        <button
          onClick={onViewSafetyDetails}
          className="mt-3 w-full py-2 px-3 rounded-xl bg-white dark:bg-[#201824] hover:bg-rose-50 dark:hover:bg-[#281e2e] border border-rose-200 dark:border-rose-900/60 text-rose-700 dark:text-rose-300 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors shadow-xs"
        >
          <span>{t.cards.viewDetails}</span>
        </button>
      </div>

      {/* ── CARD 3: Weather Forecast (Sky / Blue) ── */}
      <div className="rounded-2xl p-4 bg-sky-500/10 dark:bg-sky-950/20 border border-sky-500/30 flex flex-col justify-between transition-all hover:border-sky-500/50 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-2 text-sky-800 dark:text-sky-300">
            <div className="p-1.5 rounded-lg bg-sky-500/20">
              <CloudSun className="h-4 w-4 text-sky-600 dark:text-sky-400" />
            </div>
            <span className="text-xs font-semibold">
              {t.cards.weatherForecast}
            </span>
          </div>

          <div className="space-y-1.5 text-xs text-slate-700 dark:text-slate-300 pt-1">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center gap-1">
                <Wind className="h-3.5 w-3.5 text-sky-500" /> Wind
              </span>
              <span className="font-semibold">8 – 12 km/h (N)</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center gap-1">
                <Waves className="h-3.5 w-3.5 text-sky-500" /> Waves
              </span>
              <span className="font-semibold">0.6 – 1.2 m</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center gap-1">
                <CloudRain className="h-3.5 w-3.5 text-sky-500" /> Rain Chance
              </span>
              <span className="font-semibold">40% (morning)</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Thunderstorm</span>
              <span className="font-semibold text-emerald-500">Low</span>
            </div>
          </div>
        </div>

        <button
          onClick={onViewForecastDetails}
          className="mt-3 w-full py-2 px-3 rounded-xl bg-white dark:bg-[#112438] hover:bg-sky-50 dark:hover:bg-[#16304b] border border-sky-200 dark:border-sky-800 text-sky-700 dark:text-sky-300 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors shadow-xs"
        >
          <span>{t.cards.viewForecast}</span>
        </button>
      </div>

      {/* ── CARD 4: Nearest Shore (Blue / Cyan) ── */}
      <div className="rounded-2xl p-4 bg-blue-500/10 dark:bg-blue-950/20 border border-blue-500/30 flex flex-col justify-between transition-all hover:border-blue-500/50 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-2 text-blue-800 dark:text-blue-300">
            <div className="p-1.5 rounded-lg bg-blue-500/20">
              <Home className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            </div>
            <span className="text-xs font-semibold">{t.cards.nearestShore}</span>
          </div>

          <div className="mb-2">
            <h4 className="text-lg font-bold text-slate-900 dark:text-white">
              {nearestShoreName}
            </h4>
          </div>

          <div className="space-y-1 text-xs text-slate-600 dark:text-slate-300">
            <p className="leading-relaxed">
              Current Location to Shore:
            </p>
            <p className="font-semibold text-slate-800 dark:text-slate-100">
              {distanceToShoreKm <= 1
                ? '0 km (You are at shore)'
                : `${distanceToShoreKm.toFixed(1)} km offshore (~${(distanceToShoreKm / 15).toFixed(1)} hrs)`}
            </p>
            <p className="text-[10px] text-slate-400 pt-1">
              Navigational baseline: Udupi Coastal Harbor Authority
            </p>
          </div>
        </div>

        <button
          onClick={onPlanReturnRoute}
          className="mt-3 w-full py-2 px-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors shadow-xs"
        >
          <span>{t.cards.planReturnRoute}</span>
        </button>
      </div>
    </div>
  );
}

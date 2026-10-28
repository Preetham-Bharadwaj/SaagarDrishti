'use client';

import React, { useState, useEffect } from 'react';
import { AppHeader } from '../../components/layout/app-header';
import { SafetyAlertCard } from '../../components/dashboard/safety-alert-card';
import { submitMarineQuery } from '../../lib/api-client';
import { MarineQueryResponse } from '../../lib/types/marine';
import {
  ShieldAlert,
  AlertTriangle,
  Waves,
  ExternalLink,
  Info,
  Clock,
  ShieldCheck,
} from 'lucide-react';
import { formatWaveHeight, getDouglasStateLabel } from '../../lib/formatters';

export default function AlertsPage() {
  const [response, setResponse] = useState<MarineQueryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchAlerts = async () => {
    setIsLoading(true);
    const result = await submitMarineQuery({
      query: 'Are there any official IMD cyclone or marine warnings for the Karnataka coast?',
      departure_port: 'Malpe',
      user_location: { latitude: 13.36, longitude: 74.7 },
    });
    if (result.success && result.data) {
      setResponse(result.data);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    fetchAlerts();
  }, []);

  const hazard = response?.marine_hazard;
  const douglas = getDouglasStateLabel(hazard?.peak_wave_height_m);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-[#060b13] text-slate-900 dark:text-slate-100 transition-colors">
      <AppHeader />

      <main className="flex-1 max-w-6xl w-full mx-auto p-4 sm:p-6 space-y-6">
        {/* Banner */}
        <div className="p-6 rounded-3xl bg-gradient-to-r from-amber-900/30 via-rose-900/20 to-slate-900/40 border border-amber-500/20 backdrop-blur-md">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 text-xs font-semibold mb-2">
            <ShieldAlert className="h-3.5 w-3.5" />
            Statutory Marine Safety Protocol
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Safety Advisories & Weather Warnings
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-300 max-w-2xl mt-1">
            Authoritative regulatory notices from the India Meteorological Department (IMD) and numerical wave hazards from ECMWF.
          </p>
        </div>

        {/* Official Statutory Warning Card */}
        <SafetyAlertCard warning={response?.official_warning} />

        {/* Model Derived Wave Hazard Heuristic Section */}
        <div className="p-5 rounded-2xl bg-white dark:bg-[#0c182a] border border-slate-200 dark:border-slate-800/80 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-xl bg-sky-500/10 text-sky-600 dark:text-sky-400">
                <Waves className="h-4 w-4" />
              </div>
              <div>
                <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-100">
                  Numerical Wave Model Hazard Heuristic (Douglas Sea Scale)
                </h3>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  Open-Meteo ECMWF ERAssWave model output &bull; Karnataka Sector
                </p>
              </div>
            </div>

            <span className={`text-xs px-2.5 py-0.5 rounded-full border ${douglas.badgeClass}`}>
              State {douglas.state}: {douglas.label}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-[#111e33] border border-slate-200/60 dark:border-slate-800/60 text-xs">
              <span className="text-slate-400">Peak Wave Height:</span>
              <div className="text-base font-bold text-slate-800 dark:text-slate-100 mt-0.5">
                {formatWaveHeight(hazard?.peak_wave_height_m)}
              </div>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-[#111e33] border border-slate-200/60 dark:border-slate-800/60 text-xs">
              <span className="text-slate-400">Model Spatial Grid:</span>
              <div className="text-base font-bold text-slate-800 dark:text-slate-100 mt-0.5">
                ~9.0 km (0.083°)
              </div>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-[#111e33] border border-slate-200/60 dark:border-slate-800/60 text-xs">
              <span className="text-slate-400">Update Cadence:</span>
              <div className="text-base font-bold text-slate-800 dark:text-slate-100 mt-0.5">
                Hourly Forecast
              </div>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-amber-500/10 dark:bg-amber-950/30 border border-amber-500/20 text-xs text-amber-800 dark:text-amber-200 space-y-1">
            <div className="font-semibold flex items-center gap-1.5">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              Critical Regulatory Notice:
            </div>
            <p className="text-[11px] leading-relaxed">
              Numerical wave height forecasts are descriptive guidance for small coastal craft (&lt;15m) and are NOT statutory warnings. Absence of high waves does NOT confirm safe sea conditions. Fishers must always verify active IMD Bulletins.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

'use client';

import React, { useState, useEffect } from 'react';
import { AppHeader } from '../../components/layout/app-header';
import { IntelligenceCard } from '../../components/dashboard/intelligence-card';
import { submitMarineQuery } from '../../lib/api-client';
import { MarineQueryResponse } from '../../lib/types/marine';
import {
  Thermometer,
  Layers,
  Sparkles,
  Info,
  ExternalLink,
  ShieldCheck,
  Compass,
} from 'lucide-react';
import { formatSST, formatMarineDateTime } from '../../lib/formatters';

export default function IntelligencePage() {
  const [response, setResponse] = useState<MarineQueryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [port, setPort] = useState('Malpe');

  const fetchSST = async (selectedPort: string) => {
    setIsLoading(true);
    const result = await submitMarineQuery({
      query: `What is the Copernicus OSTIA sea surface temperature and thermal front status near ${selectedPort}?`,
      departure_port: selectedPort,
      user_location: { latitude: 13.36, longitude: 74.7 },
    });
    if (result.success && result.data) {
      setResponse(result.data);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    fetchSST(port);
  }, []);

  const sst = response?.ocean_sst;

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-[#060b13] text-slate-900 dark:text-slate-100 transition-colors">
      <AppHeader />

      <main className="flex-1 max-w-6xl w-full mx-auto p-4 sm:p-6 space-y-6">
        {/* Title Banner */}
        <div className="p-6 rounded-3xl bg-gradient-to-r from-teal-900/40 via-cyan-900/30 to-sky-950/40 border border-teal-500/20 backdrop-blur-md">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-500/10 text-teal-600 dark:text-teal-400 border border-teal-500/20 text-xs font-semibold mb-2">
                <Thermometer className="h-3.5 w-3.5" />
                Copernicus Marine Data Store Integration
              </div>
              <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                Ocean Analytics & Foundation SST
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-300 max-w-2xl mt-1">
                OSTIA Level-4 foundation sea-surface temperature analyses, horizontal temperature gradients, and thermal front detection along the Karnataka coast.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <select
                value={port}
                onChange={(e) => {
                  setPort(e.target.value);
                  fetchSST(e.target.value);
                }}
                className="bg-white dark:bg-[#0c182a] border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 dark:text-slate-200"
              >
                <option value="Malpe">Malpe Sector</option>
                <option value="Karwar">Karwar Sector</option>
                <option value="Mangaluru">Mangaluru Sector</option>
                <option value="Honnavar">Honnavar Sector</option>
              </select>
            </div>
          </div>
        </div>

        {/* Intelligence Card */}
        <IntelligenceCard sstResult={sst} />

        {/* Technical Specification & Governance Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-5 rounded-2xl bg-white dark:bg-[#0c182a] border border-slate-200 dark:border-slate-800/80 shadow-sm space-y-3">
            <h3 className="font-semibold text-sm flex items-center gap-2 text-slate-800 dark:text-slate-100">
              <Layers className="h-4 w-4 text-cyan-500" />
              Copernicus OSTIA Product Specification
            </h3>
            <ul className="text-xs space-y-2 text-slate-600 dark:text-slate-300">
              <li className="flex justify-between pb-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-400">Product Identifier:</span>
                <span className="font-mono text-cyan-600 dark:text-cyan-400">SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001</span>
              </li>
              <li className="flex justify-between pb-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-400">Dataset Identifier:</span>
                <span className="font-mono text-slate-300">METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2</span>
              </li>
              <li className="flex justify-between pb-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-400">Spatial Resolution:</span>
                <span>0.05° (~5.5 km grid spacing)</span>
              </li>
              <li className="flex justify-between pb-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-400">Temporal Cadence:</span>
                <span>Daily Foundation SST (no diurnal warming)</span>
              </li>
              <li className="flex justify-between pb-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-slate-400">Thermal Front Threshold:</span>
                <span className="font-semibold text-teal-400">&gt; 0.05 °C / km</span>
              </li>
            </ul>
          </div>

          <div className="p-5 rounded-2xl bg-white dark:bg-[#0c182a] border border-slate-200 dark:border-slate-800/80 shadow-sm space-y-3">
            <h3 className="font-semibold text-sm flex items-center gap-2 text-slate-800 dark:text-slate-100">
              <ShieldCheck className="h-4 w-4 text-teal-500" />
              Ecological Data Governance
            </h3>
            <div className="p-3 rounded-xl bg-teal-500/10 dark:bg-teal-950/30 border border-teal-500/20 text-xs text-teal-800 dark:text-teal-200 space-y-2">
              <p className="font-semibold">
                Boundary Rule: SST Alone Does NOT Prove Fish Abundance
              </p>
              <p className="text-[11px] leading-relaxed">
                Sea Surface Temperature and Chlorophyll-a are vital oceanographic indicators. While thermal gradients correlate with upwelling zones, fish aggregation depends on bathymetry, current convergence, and species-specific patterns.
              </p>
              <p className="text-[10px] text-slate-400 italic">
                Navigation decisions must strictly defer to official IMD warnings and verified INCOIS multi-sensor PFZ advisories.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

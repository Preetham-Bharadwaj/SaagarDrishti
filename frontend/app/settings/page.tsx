'use client';

import React from 'react';
import { AppHeader } from '../../components/layout/app-header';
import { UpstreamSourcesCard } from '../../components/dashboard/upstream-sources-card';
import {
  Settings,
  Database,
  Radio,
  Server,
  Key,
  Shield,
  Layers,
  CheckCircle2,
} from 'lucide-react';

export default function SettingsPage() {
  const apiBase =
    process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8001/api';

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-[#060b13] text-slate-900 dark:text-slate-100 transition-colors">
      <AppHeader />

      <main className="flex-1 max-w-6xl w-full mx-auto p-4 sm:p-6 space-y-6">
        {/* Banner */}
        <div className="p-6 rounded-3xl bg-gradient-to-r from-slate-900/40 via-cyan-950/30 to-slate-900/40 border border-slate-700/40 backdrop-blur-md">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20 text-xs font-semibold mb-2">
            <Settings className="h-3.5 w-3.5" />
            Platform Architecture & Data Settings
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            System Configuration & Data Feeds
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-300 max-w-2xl mt-1">
            Configure backend endpoints, inspect upstream provider health, and review zero-leakage security boundaries.
          </p>
        </div>

        {/* System Endpoints Section */}
        <div className="p-5 rounded-2xl bg-white dark:bg-[#0c182a] border border-slate-200 dark:border-slate-800/80 shadow-sm space-y-4">
          <h3 className="font-semibold text-sm flex items-center gap-2 text-slate-800 dark:text-slate-100">
            <Server className="h-4 w-4 text-cyan-500" />
            Backend API Connection
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-[#111e33] border border-slate-200/60 dark:border-slate-800/60 space-y-1">
              <span className="text-slate-400 font-medium">FastAPI Base URL:</span>
              <div className="font-mono text-cyan-600 dark:text-cyan-300 break-all">
                {apiBase}
              </div>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-[#111e33] border border-slate-200/60 dark:border-slate-800/60 space-y-1">
              <span className="text-slate-400 font-medium">Geocoding Service:</span>
              <div className="font-mono text-slate-300">
                OpenStreetMap Nominatim (Debounced, 350ms)
              </div>
            </div>
          </div>
        </div>

        {/* Security & Secret Protection Boundary */}
        <div className="p-5 rounded-2xl bg-white dark:bg-[#0c182a] border border-slate-200 dark:border-slate-800/80 shadow-sm space-y-3">
          <h3 className="font-semibold text-sm flex items-center gap-2 text-slate-800 dark:text-slate-100">
            <Shield className="h-4 w-4 text-emerald-500" />
            Security & Zero-Leakage Governance
          </h3>
          <div className="text-xs text-slate-600 dark:text-slate-400 space-y-2 leading-relaxed">
            <p>
              In accordance with SaagarDrishti specifications:
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>Copernicus Marine Data Store credentials and API keys are stored exclusively in the Python backend environment and never exposed to client-side bundles.</li>
              <li>Frontend communications occur over typed REST endpoints with CORS restrictions.</li>
              <li>User geolocation is requested explicitly and never stored or tracked without user consent.</li>
            </ul>
          </div>
        </div>

        {/* Upstream Sources Card */}
        <UpstreamSourcesCard />
      </main>
    </div>
  );
}

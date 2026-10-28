'use client';

import React from 'react';
import {
  BarChart2,
  Thermometer,
  Layers,
  Info,
  Clock,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import { OceanSSTResult } from '../../lib/types/marine';
import { formatSST, formatMarineDateTime } from '../../lib/formatters';

interface IntelligenceCardProps {
  sstResult?: OceanSSTResult | null;
}

export function IntelligenceCard({ sstResult }: IntelligenceCardProps) {
  return (
    <div className="rounded-2xl bg-white dark:bg-[#0c182a] border border-slate-200 dark:border-slate-800/80 p-4 shadow-sm transition-colors">
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800/80">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-xl bg-teal-500/10 text-teal-600 dark:text-teal-400">
            <Thermometer className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
              Copernicus Ocean Intelligence
            </h3>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              OSTIA Level-4 Foundation SST (5.5 km grid)
            </p>
          </div>
        </div>

        <span className="text-[10px] px-2 py-0.5 rounded-full bg-teal-500/10 text-teal-600 dark:text-teal-400 border border-teal-500/20 font-medium">
          {sstResult ? sstResult.retrieval_status : 'Awaiting Query'}
        </span>
      </div>

      <div className="mt-3 text-xs space-y-3">
        {sstResult ? (
          <>
            <div className="grid grid-cols-3 gap-2">
              <div className="p-2 rounded-xl bg-slate-50 dark:bg-[#111e33] border border-slate-200/50 dark:border-slate-800/50">
                <span className="text-[10px] text-slate-400">Spatial Mean</span>
                <div className="text-sm font-bold text-teal-600 dark:text-teal-400">
                  {formatSST(sstResult.mean_sst_celsius)}
                </div>
              </div>
              <div className="p-2 rounded-xl bg-slate-50 dark:bg-[#111e33] border border-slate-200/50 dark:border-slate-800/50">
                <span className="text-[10px] text-slate-400">Range (Min-Max)</span>
                <div className="text-sm font-bold text-slate-800 dark:text-slate-100">
                  {formatSST(sstResult.min_sst_celsius)} - {formatSST(sstResult.max_sst_celsius)}
                </div>
              </div>
              <div className="p-2 rounded-xl bg-slate-50 dark:bg-[#111e33] border border-slate-200/50 dark:border-slate-800/50">
                <span className="text-[10px] text-slate-400">Thermal Front</span>
                <div className="text-sm font-bold text-cyan-600 dark:text-cyan-400">
                  {sstResult.thermal_front_detected ? 'Detected (>0.05°C/km)' : 'None Detected'}
                </div>
              </div>
            </div>

            <div className="text-[11px] space-y-1 text-slate-400">
              <div>
                <span className="text-slate-500">Observation Timestamp: </span>
                {formatMarineDateTime(sstResult.observation_timestamp)}
              </div>
              <div>
                <span className="text-slate-500">Valid Ocean Cells: </span>
                {sstResult.valid_cell_count} unmasked sea points
              </div>
            </div>

            <p className="text-[10px] text-slate-400 italic bg-slate-50 dark:bg-slate-900/60 p-2 rounded-lg border border-slate-200/60 dark:border-slate-800/60">
              {sstResult.ecological_disclaimer}
            </p>
          </>
        ) : (
          <div className="py-3 text-slate-500 dark:text-slate-400 space-y-2">
            <p>
              Copernicus OSTIA foundation SST provides gap-free multi-satellite interpolated sea temperatures.
            </p>
            <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200/60 dark:border-slate-800/60 text-[11px] text-slate-400">
              Ask in the assistant (e.g. &ldquo;Check sea surface temperature near Malpe&rdquo;) to fetch verified SST data.
            </div>
          </div>
        )}
      </div>

      <div className="mt-3 pt-2 border-t border-slate-100 dark:border-slate-800/60 flex items-center justify-between text-[10px] text-slate-400">
        <span>Dataset: SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001</span>
        <a
          href="https://data.marine.copernicus.eu"
          target="_blank"
          rel="noopener noreferrer"
          className="text-teal-600 dark:text-teal-400 hover:underline flex items-center gap-1"
        >
          Copernicus Portal <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </div>
  );
}

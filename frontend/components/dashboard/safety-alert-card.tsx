'use client';

import React from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  ExternalLink,
  Info,
} from 'lucide-react';
import { OfficialMarineWarning } from '../../lib/types/marine';
import { formatMarineDateTime } from '../../lib/formatters';

interface SafetyAlertCardProps {
  warning?: OfficialMarineWarning | null;
}

export function SafetyAlertCard({ warning }: SafetyAlertCardProps) {
  const hasWarning = Boolean(warning && warning.severity !== 'no_warning');

  return (
    <div
      className={`rounded-2xl p-4 shadow-sm border transition-all ${
        hasWarning
          ? warning?.fishermen_advised_not_to_venture
            ? 'bg-rose-500/10 dark:bg-rose-950/40 border-rose-500/40 text-rose-900 dark:text-rose-100'
            : 'bg-amber-500/10 dark:bg-amber-950/40 border-amber-500/30 text-amber-900 dark:text-amber-100'
          : 'bg-white dark:bg-[#0c182a] border-slate-200 dark:border-slate-800/80 text-slate-800 dark:text-slate-100'
      }`}
    >
      <div className="flex items-center justify-between pb-2 border-b border-slate-200/40 dark:border-slate-800/60">
        <div className="flex items-center gap-2">
          <div
            className={`p-2 rounded-xl ${
              hasWarning
                ? 'bg-rose-500/20 text-rose-600 dark:text-rose-400'
                : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
            }`}
          >
            {hasWarning ? (
              <ShieldAlert className="h-4 w-4" />
            ) : (
              <ShieldCheck className="h-4 w-4" />
            )}
          </div>
          <div>
            <h3 className="text-sm font-semibold">Statutory Safety Alerts</h3>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              India Meteorological Dept (IMD) & Karnataka DFO
            </p>
          </div>
        </div>

        <span
          className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full border ${
            hasWarning
              ? 'bg-rose-500/20 text-rose-600 dark:text-rose-400 border-rose-500/30'
              : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
          }`}
        >
          {hasWarning ? warning?.severity.replace(/_/g, ' ') : 'Nominal / No Warning'}
        </span>
      </div>

      <div className="mt-3 text-xs space-y-2">
        {hasWarning && warning ? (
          <>
            <div className="font-semibold text-sm">
              {warning.warning_type}: {warning.coastal_zone}
            </div>
            <p className="text-xs leading-relaxed">{warning.warning_text}</p>
            <div className="grid grid-cols-2 gap-2 text-[11px] pt-1 text-slate-400">
              <div>
                <span className="text-slate-500">Issued: </span>
                {formatMarineDateTime(warning.issued_at)}
              </div>
              <div>
                <span className="text-slate-500">Valid To: </span>
                {formatMarineDateTime(warning.valid_to)}
              </div>
            </div>

            {warning.fishermen_advised_not_to_venture && (
              <div className="mt-2 p-2 rounded-lg bg-rose-600/20 border border-rose-600/40 text-rose-600 dark:text-rose-300 font-bold text-xs flex items-center gap-1.5">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                CRITICAL: Fishers are officially advised not to venture into sea.
              </div>
            )}
          </>
        ) : (
          <div className="py-2 text-slate-500 dark:text-slate-400 space-y-1.5">
            <p>
              No active severe cyclone warning bulletin is currently flagged for the Karnataka coastline.
            </p>
            <div className="flex items-center gap-1 text-[11px] text-slate-400">
              <Info className="h-3.5 w-3.5 text-cyan-500 shrink-0" />
              <span>
                Low wave forecasts do NOT prove conditions are safe. Always defer to official IMD notices before departure.
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="mt-3 pt-2 border-t border-slate-200/40 dark:border-slate-800/60 flex items-center justify-between text-[10px] text-slate-400">
        <span>Source: IMD Marine Bulletin / mausam.imd.gov.in</span>
        <a
          href="https://mausam.imd.gov.in/"
          target="_blank"
          rel="noopener noreferrer"
          className="text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1"
        >
          Check Official Portal <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </div>
  );
}

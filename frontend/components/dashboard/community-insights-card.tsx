'use client';

import React from 'react';
import { Users, Info, ShieldAlert, CheckCircle, Clock } from 'lucide-react';

export function CommunityInsightsCard() {
  return (
    <div className="rounded-2xl bg-white dark:bg-[#0c182a] border border-slate-200 dark:border-slate-800/80 p-4 shadow-sm transition-colors">
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800/80">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
            <Users className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
              Community & Fisher Insights
            </h3>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Coastal Observations & Local Marine Reports
            </p>
          </div>
        </div>

        <span className="text-[10px] px-2 py-0.5 rounded-full bg-zinc-500/10 text-zinc-500 dark:text-zinc-400 border border-zinc-500/20 font-medium">
          Crowdsource Channel
        </span>
      </div>

      <div className="mt-3 text-xs space-y-2.5">
        <div className="p-3 rounded-xl bg-slate-50 dark:bg-[#111e33] border border-slate-200/60 dark:border-slate-800/60 text-slate-600 dark:text-slate-400 space-y-1.5">
          <div className="flex items-center gap-1.5 font-medium text-slate-700 dark:text-slate-200">
            <Info className="h-3.5 w-3.5 text-indigo-500" />
            Verification Governance Notice:
          </div>
          <p className="text-[11px] leading-relaxed">
            No unverified synthetic community logs are injected. SaagarDrishti strictly prohibits displaying manufactured fisher catch reports or fake hazard coordinates.
          </p>
          <p className="text-[10px] text-slate-400 italic">
            Direct VHF / Fisher cooperative radio reports require validation against official INCOIS landing baselines before publication.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400">
          <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-900/40 border border-slate-200/50 dark:border-slate-800/50">
            <span className="text-slate-500">Karnataka Ports Monitored:</span>
            <div className="font-semibold text-slate-300 mt-0.5">29 Landing Centers</div>
          </div>
          <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-900/40 border border-slate-200/50 dark:border-slate-800/50">
            <span className="text-slate-500">Verification Protocol:</span>
            <div className="font-semibold text-emerald-400 mt-0.5">Strict Provenance Audit</div>
          </div>
        </div>
      </div>

      <div className="mt-3 pt-2 border-t border-slate-100 dark:border-slate-800/60 flex items-center justify-between text-[10px] text-slate-400">
        <span>Channel: Verified Port Authorities & Fisher Cooperatives</span>
        <span className="text-indigo-500 font-medium">Zero Synthetic Data Policy</span>
      </div>
    </div>
  );
}

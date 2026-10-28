'use client';

import React, { useEffect, useState } from 'react';
import {
  Database,
  ExternalLink,
  AlertCircle,
  CheckCircle2,
  Clock,
  RefreshCw,
} from 'lucide-react';
import { getDataSources } from '../../lib/api-client';
import { SourceAvailabilityReport } from '../../lib/types/marine';
import { formatMarineDateTime } from '../../lib/formatters';

export function UpstreamSourcesCard() {
  const [sources, setSources] = useState<SourceAvailabilityReport[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSources = async () => {
    setIsLoading(true);
    setError(null);
    const result = await getDataSources();
    if (result.success) {
      setSources(result.data);
    } else {
      setError(result.error || 'Failed to load upstream source reports');
    }
    setIsLoading(false);
  };

  useEffect(() => {
    fetchSources();
  }, []);

  return (
    <div className="rounded-2xl bg-white dark:bg-[#0c182a] border border-slate-200 dark:border-slate-800/80 p-4 shadow-sm transition-colors">
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800/80">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
            <Database className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
              Upstream Marine Data Sources & Audit Status
            </h3>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Operational availability & freshness tracked by backend engine
            </p>
          </div>
        </div>

        <button
          onClick={fetchSources}
          disabled={isLoading}
          title="Refresh Data Source Audit"
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="mt-3">
        {isLoading && sources.length === 0 ? (
          <div className="py-6 flex items-center justify-center text-xs text-slate-400">
            <div className="h-4 w-4 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mr-2" />
            Auditing INCOIS, Open-Meteo, IMD, and Copernicus endpoints...
          </div>
        ) : error ? (
          <div className="py-4 text-xs text-rose-500 bg-rose-50 dark:bg-rose-950/20 p-3 rounded-xl border border-rose-200 dark:border-rose-900/40">
            {error}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {sources.map((source, index) => {
              const isCurrent = source.status === 'current';
              const isExpired = source.status === 'expired';
              const isUnavailable = source.status === 'unavailable';

              return (
                <div
                  key={index}
                  className="p-3 rounded-xl bg-slate-50 dark:bg-[#111e33] border border-slate-200/60 dark:border-slate-800/60 flex flex-col justify-between text-xs space-y-2"
                >
                  <div>
                    <div className="flex items-start justify-between gap-1.5">
                      <h4 className="font-semibold text-slate-800 dark:text-slate-200 line-clamp-1">
                        {source.source_name}
                      </h4>
                      <span
                        className={`text-[9px] uppercase font-bold px-1.5 py-0.5 rounded shrink-0 ${
                          isCurrent
                            ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                            : isExpired
                            ? 'bg-amber-500/15 text-amber-600 dark:text-amber-400'
                            : 'bg-zinc-500/15 text-zinc-400'
                        }`}
                      >
                        {source.status}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                      {source.notes}
                    </p>
                  </div>

                  <div className="pt-2 border-t border-slate-200/40 dark:border-slate-800/40 text-[10px] text-slate-400 space-y-1">
                    <div className="flex items-center justify-between">
                      <span>Validity:</span>
                      <span className="font-mono text-slate-300">
                        {source.validity_window || 'N/A'}
                      </span>
                    </div>
                    {source.limitations.length > 0 && (
                      <div className="text-slate-400 truncate" title={source.limitations[0]}>
                        &bull; {source.limitations[0]}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

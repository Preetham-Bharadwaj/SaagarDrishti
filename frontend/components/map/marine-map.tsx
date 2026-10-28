'use client';

import dynamic from 'next/dynamic';
import React from 'react';
import { Compass } from 'lucide-react';
import {
  GeoCoordinate,
  MarineQueryResponse,
  MarineRouteInfo,
} from '../../lib/types/marine';

interface MarineMapProps {
  selectedCoordinate: GeoCoordinate;
  onSelectCoordinate: (coord: GeoCoordinate, name?: string) => void;
  selectedLocationName?: string;
  activeQueryResponse?: MarineQueryResponse | null;
  activeRoute?: MarineRouteInfo | null;
  onClearRoute?: () => void;
}

// Dynamically import MarineMapInner with ssr: false
const DynamicMarineMapInner = dynamic(() => import('./marine-map-inner'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[500px] bg-slate-900 flex flex-col items-center justify-center text-slate-400 gap-3">
      <div className="relative">
        <div className="h-12 w-12 rounded-2xl bg-cyan-500/10 flex items-center justify-center text-cyan-400 border border-cyan-500/20">
          <Compass className="h-6 w-6 animate-spin" />
        </div>
      </div>
      <div className="text-center">
        <p className="text-sm font-semibold text-slate-200">
          Loading Interactive Marine Map
        </p>
        <p className="text-xs text-slate-400">
          Rendering Leaflet Arabian Sea coastal canvas...
        </p>
      </div>
    </div>
  ),
});

export function MarineMap(props: MarineMapProps) {
  return <DynamicMarineMapInner {...props} />;
}

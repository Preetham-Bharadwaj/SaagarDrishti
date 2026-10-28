'use client';

import React from 'react';
import {
  Home,
  Map as MapIcon,
  Bell,
  Users,
  Settings,
  Waves,
} from 'lucide-react';

interface NavRailProps {
  activeTab: 'home' | 'map' | 'alerts' | 'community' | 'settings';
  onSelectTab: (tab: 'home' | 'map' | 'alerts' | 'community' | 'settings') => void;
}

export function NavRail({ activeTab, onSelectTab }: NavRailProps) {
  const navItems = [
    { id: 'home', label: 'Home', icon: Home },
    { id: 'map', label: 'Map', icon: MapIcon },
    { id: 'alerts', label: 'Alerts', icon: Bell },
    { id: 'community', label: 'Community', icon: Users },
    { id: 'settings', label: 'Settings', icon: Settings },
  ] as const;

  return (
    <aside className="w-16 md:w-20 shrink-0 bg-white dark:bg-[#070e1a] border-r border-slate-200 dark:border-slate-800/80 flex flex-col items-center py-4 justify-between select-none z-30 transition-colors">
      {/* Brand Icon */}
      <div className="flex flex-col items-center gap-6">
        <button
          onClick={() => onSelectTab('home')}
          className="h-11 w-11 rounded-2xl bg-gradient-to-tr from-cyan-600 via-sky-500 to-teal-400 p-[2px] shadow-lg shadow-cyan-500/20 hover:scale-105 active:scale-95 transition-all"
          title="SaagarDrishti — Home"
        >
          <div className="h-full w-full rounded-[14px] bg-slate-900 flex items-center justify-center">
            <Waves className="h-6 w-6 text-cyan-400" />
          </div>
        </button>

        {/* Navigation Items */}
        <nav className="flex flex-col items-center gap-2.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;

            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`flex flex-col items-center justify-center w-12 md:w-14 h-12 md:h-14 rounded-2xl transition-all group ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-500/30'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60'
                }`}
                title={item.label}
              >
                <Icon
                  className={`h-5 w-5 mb-0.5 group-hover:scale-110 transition-transform ${
                    isActive ? 'text-white' : ''
                  }`}
                />
                <span
                  className={`text-[10px] font-medium leading-none ${
                    isActive
                      ? 'text-white font-semibold'
                      : 'text-slate-500 dark:text-slate-400'
                  }`}
                >
                  {item.label}
                </span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Info or status dot */}
      <div className="flex flex-col items-center gap-2">
        <div
          className="h-2 w-2 rounded-full bg-emerald-500 ring-4 ring-emerald-500/20"
          title="Arabian Sea Live Grid Active"
        />
        <span className="text-[9px] font-mono text-slate-400 dark:text-slate-500">
          v0.1
        </span>
      </div>
    </aside>
  );
}

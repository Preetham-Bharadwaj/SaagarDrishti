'use client';

import React, { useState, useEffect } from 'react';
import {
  MapPin,
  CloudSun,
  Globe,
  Sun,
  Moon,
  User,
  Radio,
  Check,
  ChevronDown,
  Navigation,
} from 'lucide-react';
import { useTheme } from '../theme-provider';
import { getBackendHealth } from '../../lib/api-client';
import { GeoCoordinate, SupportedLanguage } from '../../lib/types/marine';
import { TRANSLATIONS } from '../../lib/translations';

interface AppHeaderProps {
  selectedLocation?: {
    name: string;
    coordinate: GeoCoordinate;
  };
  onTriggerGeolocation?: () => void;
  isLocating?: boolean;
  currentLanguage?: SupportedLanguage;
  onLanguageChange?: (lang: SupportedLanguage) => void;
  weatherSummary?: {
    temperatureC?: number;
    windSpeedKmh?: number;
    waveHeightM?: number;
  };
}

const LANGUAGES: { code: SupportedLanguage; label: string; native: string }[] = [
  { code: 'en', label: 'English', native: 'English' },
  { code: 'kn', label: 'Kannada', native: 'ಕನ್ನಡ' },
  { code: 'ml', label: 'Malayalam', native: 'മലയാളം' },
  { code: 'ta', label: 'Tamil', native: 'தமிழ்' },
  { code: 'te', label: 'Telugu', native: 'తెలుగు' },
];

export function AppHeader({
  selectedLocation = {
    name: 'Malpe, Karnataka',
    coordinate: { latitude: 13.354, longitude: 74.704 },
  },
  onTriggerGeolocation = () => {},
  isLocating = false,
  currentLanguage = 'en',
  onLanguageChange = () => {},
  weatherSummary,
}: AppHeaderProps) {
  const { theme, toggleTheme } = useTheme();
  const [isLangMenuOpen, setIsLangMenuOpen] = useState(false);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  const t = TRANSLATIONS[currentLanguage] || TRANSLATIONS.en;

  // Check health periodically
  useEffect(() => {
    let isMounted = true;
    const check = async () => {
      const res = await getBackendHealth();
      if (isMounted) setBackendOnline(res.connected);
    };
    check();
    const interval = setInterval(check, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const tempDisplay = weatherSummary?.temperatureC ?? 28;
  const windDisplay = weatherSummary?.windSpeedKmh ?? 8;
  const waveDisplay =
    weatherSummary?.waveHeightM !== undefined
      ? weatherSummary.waveHeightM.toFixed(1)
      : '0.6';

  const selectedLangObj =
    LANGUAGES.find((l) => l.code === currentLanguage) || LANGUAGES[0];

  return (
    <header className="w-full bg-white dark:bg-[#070e1a] border-b border-slate-200 dark:border-slate-800/80 px-4 md:px-6 py-2.5 transition-colors select-none">
      <div className="max-w-[1920px] mx-auto flex flex-wrap items-center justify-between gap-3">
        {/* Brand & Subtitle & Tagline */}
        <div className="flex items-center gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl md:text-2xl font-black tracking-tight text-slate-900 dark:text-white">
                Saagar<span className="text-cyan-500">Drishti</span>
              </span>
              <span className="text-[10px] md:text-xs font-semibold px-2 py-0.5 rounded-full bg-cyan-50 dark:bg-cyan-950/60 text-cyan-600 dark:text-cyan-400 border border-cyan-200 dark:border-cyan-800">
                {t.tagline}
              </span>
            </div>
            <p className="text-xs md:text-sm italic font-serif text-slate-500 dark:text-slate-400 hidden sm:block">
              {t.subTagline}
            </p>
          </div>
        </div>

        {/* Center / Right Control Cluster */}
        <div className="flex items-center flex-wrap gap-2 md:gap-3">
          {/* Location Pill with Live Location Trigger */}
          <div className="flex items-center gap-2 bg-slate-100 dark:bg-[#0f1d33] border border-slate-200 dark:border-slate-700/80 rounded-full px-3 py-1.5 shadow-sm">
            <MapPin className="h-4 w-4 text-cyan-500 shrink-0" />
            <div className="flex flex-col text-left">
              <span className="text-xs font-semibold text-slate-800 dark:text-slate-100 leading-tight truncate max-w-[150px] sm:max-w-[200px]">
                {selectedLocation.name}
              </span>
              <span className="text-[10px] font-mono text-slate-400 leading-tight">
                ({selectedLocation.coordinate.latitude.toFixed(2)}°N,{' '}
                {selectedLocation.coordinate.longitude.toFixed(2)}°E)
              </span>
            </div>
            <button
              onClick={onTriggerGeolocation}
              disabled={isLocating}
              className="ml-1 flex items-center gap-1 text-[11px] font-medium bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/25 px-2.5 py-0.5 rounded-full transition-all"
              title="Click to detect your live GPS location"
            >
              <Radio
                className={`h-3 w-3 ${isLocating ? 'animate-ping' : ''}`}
              />
              <span className="hidden sm:inline">
                {isLocating ? 'Locating...' : t.liveLocation}
              </span>
            </button>
          </div>

          {/* Weather & Waves Quick Pill */}
          <div className="hidden lg:flex items-center gap-2.5 bg-slate-100 dark:bg-[#0f1d33] border border-slate-200 dark:border-slate-700/80 rounded-full px-3.5 py-1.5 shadow-sm text-xs">
            <CloudSun className="h-4 w-4 text-amber-500" />
            <span className="font-semibold text-slate-800 dark:text-slate-100">
              {tempDisplay}°C
            </span>
            <span className="text-slate-300 dark:text-slate-700">|</span>
            <span className="text-slate-600 dark:text-slate-300">
              Wind {windDisplay} km/h
            </span>
            <span className="text-slate-300 dark:text-slate-700">|</span>
            <span className="text-cyan-600 dark:text-cyan-400 font-medium">
              Waves {waveDisplay} m
            </span>
          </div>

          {/* Language Selector Dropdown */}
          <div className="relative">
            <button
              onClick={() => setIsLangMenuOpen(!isLangMenuOpen)}
              className="flex items-center gap-1.5 bg-slate-100 dark:bg-[#0f1d33] border border-slate-200 dark:border-slate-700/80 hover:bg-slate-200 dark:hover:bg-slate-800/80 text-slate-700 dark:text-slate-200 rounded-full px-3 py-1.5 text-xs font-medium transition-all"
            >
              <Globe className="h-3.5 w-3.5 text-cyan-500" />
              <span>{selectedLangObj.native}</span>
              <ChevronDown className="h-3 w-3 opacity-60" />
            </button>

            {isLangMenuOpen && (
              <div className="absolute right-0 mt-1.5 w-36 bg-white dark:bg-[#0c182b] border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl z-50 py-1 overflow-hidden">
                {LANGUAGES.map((lang) => (
                  <button
                    key={lang.code}
                    onClick={() => {
                      onLanguageChange(lang.code);
                      setIsLangMenuOpen(false);
                    }}
                    className={`w-full flex items-center justify-between px-3 py-1.5 text-xs text-left transition-colors ${
                      currentLanguage === lang.code
                        ? 'bg-cyan-500/10 text-cyan-500 font-semibold'
                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                    }`}
                  >
                    <span>{lang.native}</span>
                    {currentLanguage === lang.code && (
                      <Check className="h-3.5 w-3.5 text-cyan-500" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Day/Night Theme Toggle Slider */}
          <button
            onClick={toggleTheme}
            aria-label="Toggle Theme"
            className="flex items-center bg-slate-100 dark:bg-[#0f1d33] border border-slate-200 dark:border-slate-700/80 rounded-full p-1 transition-colors"
            title={theme === 'dark' ? 'Switch to Light' : 'Switch to Dark'}
          >
            <div
              className={`p-1 rounded-full transition-all ${
                theme !== 'dark'
                  ? 'bg-amber-400 text-slate-900 shadow-sm'
                  : 'text-slate-400'
              }`}
            >
              <Sun className="h-3.5 w-3.5" />
            </div>
            <div
              className={`p-1 rounded-full transition-all ${
                theme === 'dark'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400'
              }`}
            >
              <Moon className="h-3.5 w-3.5" />
            </div>
          </button>

          {/* User Profile Avatar */}
          <div
            className="h-8 w-8 rounded-full bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 flex items-center justify-center text-slate-600 dark:text-slate-300 shadow-sm cursor-pointer hover:border-cyan-500 transition-colors"
            title="Fisher Profile"
          >
            <User className="h-4 w-4" />
          </div>

          {/* Compact Connectivity Dot */}
          <div
            className={`h-2.5 w-2.5 rounded-full ring-2 transition-all ${
              backendOnline
                ? 'bg-emerald-500 ring-emerald-500/20'
                : 'bg-rose-500 ring-rose-500/20'
            }`}
            title={
              backendOnline
                ? 'FastAPI Marine Backend Online'
                : 'FastAPI Backend Offline'
            }
          />
        </div>
      </div>
    </header>
  );
}

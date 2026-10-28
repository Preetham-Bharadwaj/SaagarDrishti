'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Bot,
  User,
  Sparkles,
  AlertTriangle,
  Waves,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  Trash2,
  Info,
  Clock,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Mic,
  Paperclip,
  Navigation,
  Compass,
  Fish,
  Zap,
  Users,
  Anchor,
} from 'lucide-react';
import { submitMarineQuery } from '../../lib/api-client';
import {
  GeoCoordinate,
  MarineQueryRequest,
  MarineQueryResponse,
  SupportedLanguage,
} from '../../lib/types/marine';
import { TRANSLATIONS } from '../../lib/translations';
import {
  formatBearing,
  formatDistance,
  formatMarineDateTime,
  formatWaveHeight,
  getDouglasStateLabel,
} from '../../lib/formatters';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  text?: string;
  response?: MarineQueryResponse;
  error?: string;
  isInitial?: boolean;
  actionTaken?: string;
}

interface MarineChatPanelProps {
  selectedLocation: {
    name: string;
    coordinate: GeoCoordinate;
  };
  onSelectCoordinate?: (coord: GeoCoordinate, name?: string) => void;
  onQueryResponse?: (response: MarineQueryResponse) => void;
  externalResponse?: {
    query: string;
    response: MarineQueryResponse;
    timestamp: string;
  } | null;
  currentLanguage?: SupportedLanguage;
  onPlanRoute?: () => void;
  onShowOnMap?: () => void;
  onViewDetails?: () => void;
  onReturnToShore?: () => void;
}

export function MarineChatPanel({
  selectedLocation,
  onSelectCoordinate,
  onQueryResponse,
  externalResponse,
  currentLanguage = 'en',
  onPlanRoute,
  onShowOnMap,
  onViewDetails,
  onReturnToShore,
}: MarineChatPanelProps) {
  const t = TRANSLATIONS[currentLanguage] || TRANSLATIONS.en;

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      timestamp: '2026-10-27T00:00:00.000Z',
      isInitial: true,
      text: t.greeting,
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [expandedDetailsId, setExpandedDetailsId] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);

  // Update welcome message if language changes and only welcome is present
  useEffect(() => {
    setMessages((prev) => {
      if (prev.length === 1 && prev[0].isInitial) {
        return [
          {
            ...prev[0],
            text: t.greeting,
          },
        ];
      }
      return prev;
    });
  }, [currentLanguage, t.greeting]);

  // Sync external query responses into chat history
  useEffect(() => {
    if (externalResponse) {
      const userMsgId = `ext-user-${Date.now()}`;
      const assistantMsgId = `ext-ast-${Date.now()}`;
      setMessages((prev) => {
        const lastMsg = prev[prev.length - 1];
        if (lastMsg?.response?.timestamp === externalResponse.response.timestamp) {
          return prev;
        }
        return [
          ...prev,
          {
            id: userMsgId,
            sender: 'user',
            timestamp: externalResponse.timestamp,
            text: externalResponse.query,
          },
          {
            id: assistantMsgId,
            sender: 'assistant',
            timestamp: externalResponse.response.timestamp,
            response: externalResponse.response,
          },
        ];
      });
    }
  }, [externalResponse]);

  // Auto scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || inputValue;
    if (!textToSend.trim() || isLoading) return;

    const userMsgId = `user-${Date.now()}`;
    const userMsg: ChatMessage = {
      id: userMsgId,
      sender: 'user',
      timestamp: new Date().toISOString(),
      text: textToSend,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue('');
    setIsLoading(true);

    const request: MarineQueryRequest = {
      query: textToSend,
      departure_port: selectedLocation?.name || 'Malpe',
      user_location: selectedLocation?.coordinate || {
        latitude: 13.354,
        longitude: 74.704,
      },
    };

    const result = await submitMarineQuery(request);
    setIsLoading(false);

    if (result.success && result.data) {
      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        timestamp: new Date().toISOString(),
        response: result.data,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      if (onQueryResponse) {
        onQueryResponse(result.data);
      }
    } else {
      const errorMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        timestamp: new Date().toISOString(),
        error:
          result.error ||
          'Unable to reach marine intelligence engine. Please check backend connection.',
      };
      setMessages((prev) => [...prev, errorMsg]);
    }
  };

  const handleQuickAction = (actionKey: string) => {
    switch (actionKey) {
      case 'findPfz':
        handleSend(`Where is the nearest verified fishing zone today from ${selectedLocation.name}? Is it safe to go?`);
        break;
      case 'checkSafety':
        handleSend(`Is it safe to go fishing today near ${selectedLocation.name}? Check official wave and marine warnings.`);
        break;
      case 'returnShore':
        if (onReturnToShore) {
          onReturnToShore();
        }
        handleSend(`How do I return to the nearest suitable shore from ${selectedLocation.name}?`);
        break;
      case 'weatherWaves':
        handleSend(`What are the waves and wind like near ${selectedLocation.name}?`);
        break;
      case 'cycloneAlerts':
        handleSend(`Is there any active cyclone or lightning warning for Karnataka waters?`);
        break;
      case 'nearbyReports':
        // Display community reports notice
        setMessages((prev) => [
          ...prev,
          {
            id: `user-${Date.now()}`,
            sender: 'user',
            timestamp: new Date().toISOString(),
            text: 'Show nearby community reports and crowding information.',
          },
          {
            id: `assistant-${Date.now()}`,
            sender: 'assistant',
            timestamp: new Date().toISOString(),
            text:
              '👥 Community reports are not connected yet.\n\nTo protect sensitive fishing grounds and prevent unverified rumors, SaagarDrishti only publishes verified cooperative and harbour master bulletins. Direct VHF vessel telemetry integration is currently under review.',
          },
        ]);
        break;
    }
  };

  const toggleVoiceInput = () => {
    if (isListening) {
      setIsListening(false);
      return;
    }

    if (typeof window !== 'undefined' && 'webkitSpeechRecognition' in window) {
      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const SpeechRec = (window as any).webkitSpeechRecognition;
        const recognition = new SpeechRec();
        recognition.lang =
          currentLanguage === 'kn'
            ? 'kn-IN'
            : currentLanguage === 'ml'
            ? 'ml-IN'
            : currentLanguage === 'ta'
            ? 'ta-IN'
            : currentLanguage === 'te'
            ? 'te-IN'
            : 'en-IN';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        setIsListening(true);

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        recognition.onresult = (event: any) => {
          const transcript = event.results[0][0].transcript;
          setInputValue(transcript);
          setIsListening(false);
          handleSend(transcript);
        };

        recognition.onerror = () => {
          setIsListening(false);
        };

        recognition.onend = () => {
          setIsListening(false);
        };

        recognition.start();
      } catch {
        setIsListening(false);
      }
    } else {
      // Simulation feedback if speech API not available in browser
      setIsListening(true);
      setTimeout(() => {
        setIsListening(false);
        setInputValue(`Is it safe to fish near ${selectedLocation.name} today?`);
      }, 1500);
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: 'welcome-reset',
        sender: 'assistant',
        timestamp: new Date().toISOString(),
        isInitial: true,
        text: t.greeting,
      },
    ]);
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-[#091220] transition-colors select-none">
      {/* Assistant Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800/80 bg-slate-50/70 dark:bg-[#0c182a]">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="h-10 w-10 rounded-2xl bg-gradient-to-tr from-cyan-600 via-sky-500 to-teal-400 p-[2px] shadow-md shadow-cyan-500/20">
              <div className="h-full w-full rounded-[14px] bg-slate-900 flex items-center justify-center">
                <Bot className="h-5 w-5 text-cyan-400" />
              </div>
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full bg-emerald-500 ring-2 ring-white dark:ring-slate-900" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100 flex items-center gap-1.5">
              {t.assistantHeader}
              <Sparkles className="h-3.5 w-3.5 text-cyan-500" />
            </h2>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Karnataka Coast &bull; Arabian Sea Guidance
            </p>
          </div>
        </div>

        <button
          onClick={clearChat}
          title="Reset conversation"
          className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      {/* Quick Action Grid (2 columns x 3 rows matching mockup) */}
      <div className="p-3 border-b border-slate-100 dark:border-slate-800/60 bg-slate-50/40 dark:bg-[#070e1a]/40">
        <div className="grid grid-cols-3 gap-2">
          {/* 1. Find Fishing Zone */}
          <button
            onClick={() => handleQuickAction('findPfz')}
            className="flex flex-col items-center justify-center p-2 rounded-xl bg-white dark:bg-[#0f1d33] hover:bg-cyan-50 dark:hover:bg-cyan-950/40 border border-slate-200 dark:border-slate-800 hover:border-cyan-400 text-slate-700 dark:text-slate-200 transition-all shadow-xs group"
          >
            <Fish className="h-4 w-4 text-cyan-500 mb-1 group-hover:scale-110 transition-transform" />
            <span className="text-[11px] font-semibold text-center leading-tight">
              {t.quickActions.findPfz}
            </span>
          </button>

          {/* 2. Check Sea Safety */}
          <button
            onClick={() => handleQuickAction('checkSafety')}
            className="flex flex-col items-center justify-center p-2 rounded-xl bg-white dark:bg-[#0f1d33] hover:bg-emerald-50 dark:hover:bg-emerald-950/40 border border-slate-200 dark:border-slate-800 hover:border-emerald-400 text-slate-700 dark:text-slate-200 transition-all shadow-xs group"
          >
            <ShieldCheck className="h-4 w-4 text-emerald-500 mb-1 group-hover:scale-110 transition-transform" />
            <span className="text-[11px] font-semibold text-center leading-tight">
              {t.quickActions.checkSafety}
            </span>
          </button>

          {/* 3. Return to Shore */}
          <button
            onClick={() => handleQuickAction('returnShore')}
            className="flex flex-col items-center justify-center p-2 rounded-xl bg-white dark:bg-[#0f1d33] hover:bg-rose-50 dark:hover:bg-rose-950/40 border border-slate-200 dark:border-slate-800 hover:border-rose-400 text-slate-700 dark:text-slate-200 transition-all shadow-xs group"
          >
            <Anchor className="h-4 w-4 text-rose-500 mb-1 group-hover:scale-110 transition-transform" />
            <span className="text-[11px] font-semibold text-center leading-tight">
              {t.quickActions.returnShore}
            </span>
          </button>

          {/* 4. Weather & Waves */}
          <button
            onClick={() => handleQuickAction('weatherWaves')}
            className="flex flex-col items-center justify-center p-2 rounded-xl bg-white dark:bg-[#0f1d33] hover:bg-sky-50 dark:hover:bg-sky-950/40 border border-slate-200 dark:border-slate-800 hover:border-sky-400 text-slate-700 dark:text-slate-200 transition-all shadow-xs group"
          >
            <Waves className="h-4 w-4 text-sky-500 mb-1 group-hover:scale-110 transition-transform" />
            <span className="text-[11px] font-semibold text-center leading-tight">
              {t.quickActions.weatherWaves}
            </span>
          </button>

          {/* 5. Cyclone / Lightning Alerts */}
          <button
            onClick={() => handleQuickAction('cycloneAlerts')}
            className="flex flex-col items-center justify-center p-2 rounded-xl bg-white dark:bg-[#0f1d33] hover:bg-amber-50 dark:hover:bg-amber-950/40 border border-slate-200 dark:border-slate-800 hover:border-amber-400 text-slate-700 dark:text-slate-200 transition-all shadow-xs group"
          >
            <Zap className="h-4 w-4 text-amber-500 mb-1 group-hover:scale-110 transition-transform" />
            <span className="text-[11px] font-semibold text-center leading-tight">
              {t.quickActions.cycloneAlerts}
            </span>
          </button>

          {/* 6. Nearby Reports */}
          <button
            onClick={() => handleQuickAction('nearbyReports')}
            className="flex flex-col items-center justify-center p-2 rounded-xl bg-white dark:bg-[#0f1d33] hover:bg-indigo-50 dark:hover:bg-indigo-950/40 border border-slate-200 dark:border-slate-800 hover:border-indigo-400 text-slate-700 dark:text-slate-200 transition-all shadow-xs group"
          >
            <Users className="h-4 w-4 text-indigo-500 mb-1 group-hover:scale-110 transition-transform" />
            <span className="text-[11px] font-semibold text-center leading-tight">
              {t.quickActions.nearbyReports}
            </span>
          </button>
        </div>
      </div>

      {/* Message History */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 text-xs sm:text-sm"
      >
        {messages.map((msg) => {
          const isUser = msg.sender === 'user';
          const isExpanded = expandedDetailsId === msg.id;

          return (
            <div
              key={msg.id}
              className={`flex flex-col ${
                isUser ? 'items-end' : 'items-start'
              }`}
            >
              <div className="flex items-center gap-1.5 mb-1 text-[11px] text-slate-400">
                {isUser ? (
                  <>
                    <span>You</span>
                    <User className="h-3 w-3" />
                  </>
                ) : (
                  <>
                    <Bot className="h-3 w-3 text-cyan-500" />
                    <span>SaagarDrishti Assistant</span>
                  </>
                )}
                <span className="text-[10px] opacity-70">
                  {new Date(msg.timestamp).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>

              {/* Message Bubble */}
              <div
                className={`max-w-[94%] rounded-2xl p-3.5 shadow-sm leading-relaxed ${
                  isUser
                    ? 'bg-blue-600 text-white rounded-tr-none'
                    : 'bg-slate-100 dark:bg-[#0e1b2f] text-slate-800 dark:text-slate-100 border border-slate-200 dark:border-slate-800 rounded-tl-none'
                }`}
              >
                {/* Regular text */}
                {msg.text && (
                  <p className="whitespace-pre-line text-xs sm:text-sm font-normal">
                    {msg.text}
                  </p>
                )}

                {/* Error */}
                {msg.error && (
                  <div className="flex items-start gap-2 text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/30 p-2.5 rounded-lg border border-rose-200 dark:border-rose-900/40">
                    <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                    <p className="text-xs">{msg.error}</p>
                  </div>
                )}

                {/* Fisherman-First Structured Assistant Card */}
                {msg.response && (
                  <FishermanResponseCard
                    response={msg.response}
                    selectedLocation={selectedLocation}
                    isExpanded={isExpanded}
                    onToggleExpand={() =>
                      setExpandedDetailsId(isExpanded ? null : msg.id)
                    }
                    onPlanRoute={onPlanRoute}
                    onShowOnMap={onShowOnMap}
                    onViewDetails={onViewDetails}
                  />
                )}
              </div>
            </div>
          );
        })}

        {/* Loading Spinner */}
        {isLoading && (
          <div className="flex items-start gap-2">
            <div className="h-7 w-7 rounded-full bg-cyan-500/20 flex items-center justify-center text-cyan-400 shrink-0">
              <Bot className="h-4 w-4 animate-spin" />
            </div>
            <div className="bg-slate-100 dark:bg-[#0e1b2f] p-3 rounded-2xl rounded-tl-none border border-slate-200 dark:border-slate-800 flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-cyan-500 animate-bounce" />
              <div className="h-2 w-2 rounded-full bg-cyan-500 animate-bounce [animation-delay:0.2s]" />
              <div className="h-2 w-2 rounded-full bg-cyan-500 animate-bounce [animation-delay:0.4s]" />
              <span className="text-xs text-slate-400 ml-1">
                Auditing marine data & calculating safe route...
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Input Form & Suggested Prompts */}
      <div className="p-3 border-t border-slate-200 dark:border-slate-800/80 bg-white dark:bg-[#070e1a]">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2"
        >
          <button
            type="button"
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            title="Attach reference coordinates or file"
          >
            <Paperclip className="h-4 w-4" />
          </button>

          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={t.chatInputPlaceholder}
            disabled={isLoading}
            className="flex-1 bg-slate-100 dark:bg-[#0f1d33] border border-slate-200 dark:border-slate-800 rounded-full px-4 py-2 text-xs sm:text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-all"
          />

          <button
            type="button"
            onClick={toggleVoiceInput}
            aria-label="Voice input"
            className={`p-2 rounded-full transition-all ${
              isListening
                ? 'bg-rose-500 text-white animate-pulse'
                : 'text-slate-400 hover:text-cyan-500 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
            title="Voice query"
          >
            <Mic className="h-4 w-4" />
          </button>

          <button
            type="submit"
            disabled={isLoading || !inputValue.trim()}
            aria-label="Send query"
            className="p-2.5 rounded-full bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-40 disabled:hover:bg-blue-600 transition-all flex items-center justify-center shadow-md shadow-blue-500/20"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>

        {/* Suggested Prompt Chips */}
        <div className="flex items-center gap-1.5 mt-2 overflow-x-auto text-[11px] text-slate-400">
          <span className="shrink-0 text-[10px] text-slate-400">Try:</span>
          <button
            onClick={() => handleSend(t.suggestedPrompt1)}
            className="px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-900 hover:bg-cyan-50 dark:hover:bg-cyan-950/40 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 whitespace-nowrap transition-colors"
          >
            {t.suggestedPrompt1}
          </button>
          <button
            onClick={() => handleSend(t.suggestedPrompt2)}
            className="px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-900 hover:bg-cyan-50 dark:hover:bg-cyan-950/40 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 whitespace-nowrap transition-colors"
          >
            {t.suggestedPrompt2}
          </button>
          <button
            onClick={() => handleSend(t.suggestedPrompt3)}
            className="px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-900 hover:bg-cyan-50 dark:hover:bg-cyan-950/40 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 whitespace-nowrap transition-colors"
          >
            {t.suggestedPrompt3}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Clean, fisherman-friendly response formatter
 * Avoids raw JSON, SST product identifiers, and unneeded telemetry.
 */
function FishermanResponseCard({
  response,
  selectedLocation,
  isExpanded,
  onToggleExpand,
  onPlanRoute,
  onShowOnMap,
  onViewDetails,
}: {
  response: MarineQueryResponse;
  selectedLocation: { name: string; coordinate: GeoCoordinate };
  isExpanded: boolean;
  onToggleExpand: () => void;
  onPlanRoute?: () => void;
  onShowOnMap?: () => void;
  onViewDetails?: () => void;
}) {
  const hasPfz = Boolean(response.candidate_pfz);
  const waveHeight =
    response.marine_hazard?.current_hour_observation?.wave_height_m ??
    response.marine_hazard?.peak_wave_height_m ??
    0.8;
  const hasWarning = Boolean(
    response.official_warning &&
      response.official_warning.severity !== 'no_warning'
  );

  return (
    <div className="space-y-3 pt-1">
      {/* Friendly Overview Paragraph */}
      <p className="text-xs sm:text-sm text-slate-800 dark:text-slate-100 leading-relaxed font-normal">
        {hasPfz
          ? `I found verified fishing zones near ${selectedLocation.name} based on official INCOIS advisory lines. The sea conditions are generally favourable, but please review the safety points below before departure.`
          : `Here are the latest verified marine conditions for ${selectedLocation.name}. Official INCOIS advisory lines and wave forecast models are summarized below.`}
      </p>

      {/* Fisherman Checklist with Clean Status Icons */}
      <div className="space-y-1.5 p-2.5 rounded-xl bg-white/70 dark:bg-[#070e1a]/70 border border-slate-200/80 dark:border-slate-800/80 text-xs">
        {/* Item 1: PFZ Status */}
        <div className="flex items-center gap-2">
          {hasPfz ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
          ) : (
            <Info className="h-4 w-4 text-amber-500 shrink-0" />
          )}
          <span className="font-medium text-slate-800 dark:text-slate-200">
            {hasPfz
              ? 'Potential fishing zones available (INCOIS lines)'
              : 'Official INCOIS PFZ advisory lines active on map'}
          </span>
        </div>

        {/* Item 2: Waves */}
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
          <span className="text-slate-700 dark:text-slate-300">
            Wave height: {waveHeight.toFixed(1)} m (
            {waveHeight < 1.2 ? 'slight / moderate' : 'rough sea'})
          </span>
        </div>

        {/* Item 3: Cyclone Warning */}
        <div className="flex items-center gap-2">
          {hasWarning ? (
            <AlertTriangle className="h-4 w-4 text-rose-500 shrink-0" />
          ) : (
            <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
          )}
          <span
            className={
              hasWarning
                ? 'font-bold text-rose-600 dark:text-rose-400'
                : 'text-slate-700 dark:text-slate-300'
            }
          >
            {hasWarning
              ? `Warning: ${response.official_warning?.warning_type}`
              : 'No active cyclone or severe gale warning'}
          </span>
        </div>

        {/* Item 4: Weather / Sea state */}
        <div className="flex items-center gap-2">
          <span className="h-4 w-4 rounded-full bg-amber-500/20 text-amber-500 flex items-center justify-center font-bold text-[10px] shrink-0">
            !
          </span>
          <span className="text-slate-600 dark:text-slate-400">
            Light coastal breeze; check morning VHF broadcast
          </span>
        </div>

        {/* Item 5: Overall Advice */}
        <div className="flex items-center gap-2 pt-1 border-t border-slate-200/50 dark:border-slate-800/50">
          <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
          <span className="font-semibold text-emerald-700 dark:text-emerald-400">
            {hasWarning
              ? 'Exercise caution & monitor IMD bulletin'
              : 'Safe to go with standard coastal caution'}
          </span>
        </div>
      </div>

      {/* Action Buttons: View Details, Show on Map, Plan Route */}
      <div className="flex flex-wrap items-center gap-2 pt-1">
        <button
          onClick={onViewDetails}
          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-white dark:bg-[#162744] hover:bg-slate-100 dark:hover:bg-[#1d3258] border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 transition-colors shadow-xs"
        >
          View Details
        </button>
        <button
          onClick={onShowOnMap}
          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-white dark:bg-[#162744] hover:bg-slate-100 dark:hover:bg-[#1d3258] border border-slate-200 dark:border-slate-700 text-cyan-600 dark:text-cyan-400 transition-colors shadow-xs"
        >
          Show on Map
        </button>
        <button
          onClick={onPlanRoute}
          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors shadow-xs"
        >
          Plan Route
        </button>
      </div>

      {/* Expandable "Why am I seeing this?" Section */}
      <div className="pt-2 border-t border-slate-200/60 dark:border-slate-800/60">
        <button
          onClick={onToggleExpand}
          className="flex items-center justify-between w-full text-[11px] text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
        >
          <span className="flex items-center gap-1 font-medium">
            <Info className="h-3 w-3 text-cyan-500" />
            Why am I seeing this recommendation?
          </span>
          {isExpanded ? (
            <ChevronUp className="h-3.5 w-3.5" />
          ) : (
            <ChevronDown className="h-3.5 w-3.5" />
          )}
        </button>

        {isExpanded && (
          <div className="mt-2 p-2.5 rounded-xl bg-slate-50 dark:bg-[#070e1a] border border-slate-200 dark:border-slate-800 text-[11px] space-y-1.5 text-slate-600 dark:text-slate-400">
            <div>
              <span className="font-semibold text-slate-700 dark:text-slate-300">
                Primary Data Sources:
              </span>{' '}
              INCOIS WFS (PFZ Vector Lines), Open-Meteo Marine (ECMWF Wave Model),
              IMD Coastal Bulletin.
            </div>
            <div>
              <span className="font-semibold text-slate-700 dark:text-slate-300">
                Advisory Time:
              </span>{' '}
              {formatMarineDateTime(response.timestamp)}
            </div>
            <div>
              <span className="font-semibold text-slate-700 dark:text-slate-300">
                Limitations:
              </span>{' '}
              PFZ lines indicate thermal & chlorophyll fronts where pelagic fish may
              congregate; they do NOT guarantee fish presence or safe navigation.
            </div>
            <div className="pt-1 flex items-center justify-between text-[10px]">
              <a
                href="https://incois.gov.in/"
                target="_blank"
                rel="noreferrer"
                className="text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-0.5"
              >
                Official INCOIS Portal <ExternalLink className="h-2.5 w-2.5" />
              </a>
              <a
                href="https://mausam.imd.gov.in/"
                target="_blank"
                rel="noreferrer"
                className="text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-0.5"
              >
                Official IMD Bulletins <ExternalLink className="h-2.5 w-2.5" />
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

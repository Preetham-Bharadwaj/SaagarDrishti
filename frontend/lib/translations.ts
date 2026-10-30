import { SupportedLanguage } from './types/marine';

export interface TranslationDictionary {
  appName: string;
  tagline: string;
  subTagline: string;
  greeting: string;
  assistantHeader: string;
  quickActions: {
    findPfz: string;
    checkSafety: string;
    returnShore: string;
    weatherWaves: string;
    cycloneAlerts: string;
    nearbyReports: string;
  };
  cards: {
    recommendedPfz: string;
    safetyAlerts: string;
    weatherForecast: string;
    nearestShore: string;
    viewRoute: string;
    viewDetails: string;
    viewForecast: string;
    planReturnRoute: string;
    highPotential: string;
    moderate: string;
    noMajorAlerts: string;
    activeWarning: string;
  };
  chatInputPlaceholder: string;
  suggestedPrompt1: string;
  suggestedPrompt2: string;
  suggestedPrompt3: string;
  liveLocation: string;
  safeWithCaution: string;
  cautionAdvised: string;
  doNotVenture: string;
}

export const TRANSLATIONS: Record<SupportedLanguage, TranslationDictionary> = {
  en: {
    appName: 'SaagarDrishti',
    tagline: 'AI-Powered Marine Intelligence',
    subTagline: 'Smarter Seas. Safer Decisions.',
    greeting:
      'Namaskara! 👋 I can help you find fishing zones, check sea conditions, give safety alerts and plan your route.',
    assistantHeader: 'Marine AI Assistant',
    quickActions: {
      findPfz: 'Find Fishing Zone',
      checkSafety: 'Check Sea Safety',
      returnShore: 'Return to Shore',
      weatherWaves: 'Weather & Waves',
      cycloneAlerts: 'Cyclone / Lightning Alerts',
      nearbyReports: 'Nearby Reports',
    },
    cards: {
      recommendedPfz: 'Recommended Fishing Zone',
      safetyAlerts: 'Safety Alerts',
      weatherForecast: 'Weather Forecast (Next 24 hrs)',
      nearestShore: 'Nearest Shore',
      viewRoute: 'View Route ↗',
      viewDetails: 'View Details',
      viewForecast: 'View Forecast',
      planReturnRoute: 'Plan Return Route',
      highPotential: 'High Potential',
      moderate: 'Moderate',
      noMajorAlerts: 'No Major Alerts',
      activeWarning: 'Active Marine Alert',
    },
    chatInputPlaceholder: 'Ask about fishing zones, weather, safety...',
    suggestedPrompt1: 'Nearest fishing zone',
    suggestedPrompt2: 'Is it safe tomorrow?',
    suggestedPrompt3: 'Return to shore',
    liveLocation: 'Live Location',
    safeWithCaution: 'Safe to go with caution',
    cautionAdvised: 'Caution advised in open waters',
    doNotVenture: 'Do NOT venture into sea',
  },
  kn: {
    appName: 'ಸಾಗರದೃಷ್ಟಿ',
    tagline: 'ಎಐ ಆಧಾರಿತ ಸಮುದ್ರ ಮಾಹಿತಿ ವ್ಯವಸ್ಥೆ',
    subTagline: 'ಬುದ್ಧಿವಂತ ಸಮುದ್ರ. ಸುರಕ್ಷಿತ ನಿರ್ಧಾರಗಳು.',
    greeting:
      'ನಮಸ್ಕಾರ! 👋 ನಾನು ನಿಮಗೆ ಮೀನುಗಾರಿಕೆ ವಲಯಗಳನ್ನು ಹುಡುಕಲು, ಸಮುದ್ರದ ಹವಾಮಾನ ತಿಳಿಯಲು ಮತ್ತು ಸುರಕ್ಷಿತ ಮಾರ್ಗ ಯೋಜಿಸಲು ಸಹಾಯ ಮಾಡುತ್ತೇನೆ.',
    assistantHeader: 'ಸಮುದ್ರ ಎಐ ಸಹಾಯಕ',
    quickActions: {
      findPfz: 'ಮೀನುಗಾರಿಕೆ ವಲಯ ಹುಡುಕಿ',
      checkSafety: 'ಸಮುದ್ರ ಸುರಕ್ಷತೆ ಪರಿಶೀಲಿಸಿ',
      returnShore: 'ದಡಕ್ಕೆ ಹಿಂದಿರುಗಿ',
      weatherWaves: 'ಹವಾಮಾನ ಮತ್ತು ಅಲೆಗಳು',
      cycloneAlerts: 'ಚಂಡಮಾರುತ ಎಚ್ಚರಿಕೆ',
      nearbyReports: 'ಸಮೀಪದ ವರದಿಗಳು',
    },
    cards: {
      recommendedPfz: 'ಸೂಚಿಸಲಾದ ಮೀನು ವಲಯ',
      safetyAlerts: 'ಸುರಕ್ಷತಾ ಎಚ್ಚರಿಕೆಗಳು',
      weatherForecast: 'ಹವಾಮಾನ ಮುನ್ಸೂಚನೆ (ಮುಂದಿನ 24 ಗಂಟೆ)',
      nearestShore: 'ಹತ್ತಿರದ ಬಂದರು / ದಡ',
      viewRoute: 'ಮಾರ್ಗ ವೀಕ್ಷಿಸಿ ↗',
      viewDetails: 'ವಿವರ ನೋಡಿ',
      viewForecast: 'ಮುನ್ಸೂಚನೆ ನೋಡಿ',
      planReturnRoute: 'ದಡದ ಮಾರ್ಗ ಯೋಜಿಸಿ',
      highPotential: 'ಹೆಚ್ಚಿನ ಸಂಭವನೀಯತೆ',
      moderate: 'ಮಧ್ಯಮ',
      noMajorAlerts: 'ಯಾವುದೇ ಗಂಭೀರ ಎಚ್ಚರಿಕೆಗಳಿಲ್ಲ',
      activeWarning: 'ಸಮುದ್ರ ಎಚ್ಚರಿಕೆ ಸಕ್ರಿಯವಾಗಿದೆ',
    },
    chatInputPlaceholder: 'ಮೀನುಗಾರಿಕೆ ವಲಯ, ಅಲೆಗಳು, ಸುರಕ್ಷತೆ ಬಗ್ಗೆ ಕೇಳಿ...',
    suggestedPrompt1: 'ಹತ್ತಿರದ ಮೀನುಗಾರಿಕೆ ವಲಯ',
    suggestedPrompt2: 'ನಾಳೆ ಸಮುದ್ರ ಸುರಕ್ಷಿತವೇ?',
    suggestedPrompt3: 'ದಡಕ್ಕೆ ಹಿಂತಿರುಗುವ ಮಾರ್ಗ',
    liveLocation: 'ನೇರ ಸ್ಥಳ',
    safeWithCaution: 'ಎಚ್ಚರಿಕೆಯೊಂದಿಗೆ ಹೋಗಬಹುದು',
    cautionAdvised: 'ತೆರೆದ ಸಮುದ್ರದಲ್ಲಿ ಜಾಗರೂಕತೆ ವಹಿಸಿ',
    doNotVenture: 'ಸಮುದ್ರಕ್ಕೆ ಇಳಿಯಬೇಡಿ (ನಿಷೇಧಿಸಲಾಗಿದೆ)',
  },
  ml: {
    appName: 'സാഗരദൃഷ്ടി',
    tagline: 'എഐ അധിഷ്ഠിത സമുദ്ര വിവരങ്ങൾ',
    subTagline: 'സുരക്ഷിതമായ കടൽ. മികച്ച തീരുമാനങ്ങൾ.',
    greeting:
      'നമസ്കാരം! 👋 മത്സ്യബന്ധന മേഖലകൾ കണ്ടെത്താനും കടൽ സാഹചര്യങ്ങൾ പരിശോധിക്കാനും സുരക്ഷിത യാത്ര പ്ലാൻ ചെയ്യാനും ഞാൻ സഹായിക്കാം.',
    assistantHeader: 'സമുദ്ര എഐ അസിസ്റ്റന്റ്',
    quickActions: {
      findPfz: 'മത്സ്യബന്ധന മേഖല',
      checkSafety: 'കടൽ സുരക്ഷ പരിശോധിക്കുക',
      returnShore: 'തീരത്തേക്ക് മടങ്ങുക',
      weatherWaves: 'കാലാവസ്ഥയും തിരമാലയും',
      cycloneAlerts: 'ചുഴലിക്കാറ്റ് മുന്നറിയിപ്പ്',
      nearbyReports: 'സമീപ റിപ്പോർട്ടുകൾ',
    },
    cards: {
      recommendedPfz: 'ശുപാർശ ചെയ്യുന്ന മത്സ്യമേഖല',
      safetyAlerts: 'സുരക്ഷാ മുന്നറിയിപ്പുകൾ',
      weatherForecast: 'കാലാവസ്ഥ പ്രവചനം (24 മണിക്കൂർ)',
      nearestShore: 'ഏറ്റവും അടുത്ത തീരം',
      viewRoute: 'റൂട്ട് കാണുക ↗',
      viewDetails: 'വിശദാംശങ്ങൾ കാണുക',
      viewForecast: 'പ്രവചനം കാണുക',
      planReturnRoute: 'തിരികെ റൂട്ട് പ്ലാൻ ചെയ്യുക',
      highPotential: 'കൂടുതൽ സാധ്യത',
      moderate: 'ഇടത്തരം',
      noMajorAlerts: 'പ്രത്യേക മുന്നറിയിപ്പുകൾ ഇല്ല',
      activeWarning: 'സമുദ്ര മുന്നറിയിപ്പ് നിലവിലുണ്ട്',
    },
    chatInputPlaceholder: 'മത്സ്യമേഖല, തിരമാലകൾ, സുരക്ഷ എന്നിവ ചോദിക്കുക...',
    suggestedPrompt1: 'അടുത്തുള്ള മത്സ്യമേഖല',
    suggestedPrompt2: 'നാളെ കടലിൽ പോകുന്നത് സുരക്ഷിതമാണോ?',
    suggestedPrompt3: 'തീരത്തേക്ക് മടങ്ങുക',
    liveLocation: 'തത്സമയ ലൊക്കേഷൻ',
    safeWithCaution: 'ജാഗ്രതയോടെ പോകാം',
    cautionAdvised: 'തുറന്ന കടലിൽ ജാഗ്രത പാലിക്കുക',
    doNotVenture: 'കടലിൽ പോകരുത്',
  },
  ta: {
    appName: 'சாகர்திருஷ்டி',
    tagline: 'செயற்கை நுண்ணறிவு கடல்சார் வழிகாட்டி',
    subTagline: 'பாதுகாப்பான கடல். சரியான முடிவுகள்.',
    greeting:
      'வணக்கம்! 👋 மீன்பிடி மண்டலங்களைக் கண்டறியவும், கடல் அலைகளை அறியவும், பாதுகாப்புடன் பயணிக்கவும் நான் உதவுகிறேன்.',
    assistantHeader: 'கடல்சார் AI உதவியாளர்',
    quickActions: {
      findPfz: 'மீன்பிடி மண்டலம் தேடு',
      checkSafety: 'கடல் பாதுகாப்பு காண்க',
      returnShore: 'கரைக்கு திரும்பு',
      weatherWaves: 'வானிலை & அலைகள்',
      cycloneAlerts: 'புயல் எச்சரிக்கை',
      nearbyReports: 'அருகிலுள்ள தகவல்கள்',
    },
    cards: {
      recommendedPfz: 'பரிந்துரைக்கப்பட்ட மீன்பிடி பகுதி',
      safetyAlerts: 'பாதுகாப்பு எச்சரிக்கைகள்',
      weatherForecast: 'வானிலை முன்னறிவிப்பு (24 மணிநேரம்)',
      nearestShore: 'அருகிலுள்ள துறைமுகம் / கரை',
      viewRoute: 'வழியைப் பார் ↗',
      viewDetails: 'விவரங்களைக் காண்க',
      viewForecast: 'முன்னறிவிப்பைப் பார்',
      planReturnRoute: 'கரை திரும்பும் வழி',
      highPotential: 'அதிக சாத்தியக்கூறு',
      moderate: 'மிதமான',
      noMajorAlerts: 'பெரிய எச்சரிக்கைகள் இல்லை',
      activeWarning: 'கடல் எச்சரிக்கை உள்ளது',
    },
    chatInputPlaceholder: 'மீன்பிடி பகுதி, அலைகள், வானிலை பற்றி கேளுங்கள்...',
    suggestedPrompt1: 'அருகிலுள்ள மீன்பிடி மண்டலம்',
    suggestedPrompt2: 'நாளை கடல் பயணம் பாதுகாப்பானதா?',
    suggestedPrompt3: 'கரை திரும்பும் வழி',
    liveLocation: 'நேரலை இடம்',
    safeWithCaution: 'எச்சரிக்கையுடன் செல்லலாம்',
    cautionAdvised: 'ஆழ்கடலில் கவனம் தேவை',
    doNotVenture: 'கடலுக்குள் செல்ல வேண்டாம்',
  },
  te: {
    appName: 'సాగరదృష్టి',
    tagline: 'AI ఆధారిత సముద్ర సమాచారం',
    subTagline: 'తెలివైన సముద్రం. సురక్షిత నిర్ణయాలు.',
    greeting:
      'నమస్కారం! 👋 చేపల వేట ప్రాంతాలను కనుగొనడానికి, సముద్ర వాతావరణం పరిశీలించడానికి, మరియు సురక్షిత మార్గ ప్రణాళికకు నేను సహాయం చేస్తాను.',
    assistantHeader: 'సముద్ర AI సహాయకుడు',
    quickActions: {
      findPfz: 'చేపల వేట ప్రాంతం',
      checkSafety: 'సముద్ర భద్రత చూడండి',
      returnShore: 'తీరానికి తిరిగి రండి',
      weatherWaves: 'వాతావరణం & అలలు',
      cycloneAlerts: 'తుఫాను హెచ్చరికలు',
      nearbyReports: 'సమీప నివేదికలు',
    },
    cards: {
      recommendedPfz: 'సిఫార్సు చేయబడిన చేపల ప్రాంతం',
      safetyAlerts: 'భద్రతా హెచ్చరికలు',
      weatherForecast: 'వాతావరణ సూచన (24 గంటలు)',
      nearestShore: 'సమీప తీరం / పోర్టు',
      viewRoute: 'మార్గం చూడండి ↗',
      viewDetails: 'వివరాలు చూడండి',
      viewForecast: 'సూచన చూడండి',
      planReturnRoute: 'తీర మార్గం ప్లాన్ చేయండి',
      highPotential: 'ఎక్కువ అవకాశం',
      moderate: 'మధ్యస్థం',
      noMajorAlerts: 'ప్రమాదకర హెచ్చరికలు లేవు',
      activeWarning: 'సముద్ర హెచ్చరిక అమల్లో ఉంది',
    },
    chatInputPlaceholder: 'చేపల వేట, అలల ఎత్తు, భద్రత గురించి అడగండి...',
    suggestedPrompt1: 'సమీప చేపల వేట ప్రాంతం',
    suggestedPrompt2: 'రేపు సముద్రం సురక్షితమేనా?',
    suggestedPrompt3: 'తీరానికి తిరిగి వెళ్ళే మార్గం',
    liveLocation: 'ప్రత్యక్ష స్థానం',
    safeWithCaution: 'జాగ్రత్తతో వెళ్లవచ్చు',
    cautionAdvised: 'సముద్రంలో జాగ్రత్త అవసరం',
    doNotVenture: 'సముద్రంలోకి వెళ్లవద్దు',
  },
};

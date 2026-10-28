import type { Metadata } from 'next';
import './globals.css';
import { ThemeProvider } from '../components/theme-provider';

export const metadata: Metadata = {
  title: 'SaagarDrishti — AI-Powered Marine Intelligence Platform',
  description:
    'Smarter Seas. Safer Decisions. Real-time marine hazard, ocean SST analytics, and verified fishing-zone intelligence for the Karnataka coastline.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark h-full antialiased" suppressHydrationWarning>
      <body className="h-full bg-slate-50 text-slate-900 dark:bg-[#060b13] dark:text-slate-100 transition-colors duration-200">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}

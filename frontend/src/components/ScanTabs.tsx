import type { ScanMode } from '@/types/security';

interface ScanTab {
  mode: ScanMode;
  label: string;
}

interface ScanTabsProps {
  tabs: ScanTab[];
  activeMode: ScanMode;
  onTabChange: (mode: ScanMode) => void;
}

export default function ScanTabs({ tabs, activeMode, onTabChange }: ScanTabsProps) {
  return (
    <div className="mb-5 grid grid-cols-3 gap-2 rounded-2xl border border-border bg-black/20 p-1.5">
      {tabs.map(({ mode, label }) => (
        <button
          key={mode}
          onClick={() => onTabChange(mode)}
          className={`rounded-xl px-3 py-2.5 text-xs font-semibold transition-colors sm:text-sm ${
            activeMode === mode
              ? 'bg-primary text-slate-950 shadow-[0_0_28px_rgba(77,227,208,0.22)]'
              : 'text-accent hover:bg-white/5 hover:text-foreground'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

interface AnalyzeButtonProps {
  disabled: boolean;
  isAnalyzing: boolean;
  onAnalyze: () => void;
}

export default function AnalyzeButton({ disabled, isAnalyzing, onAnalyze }: AnalyzeButtonProps) {
  return (
    <button
      onClick={onAnalyze}
      disabled={disabled || isAnalyzing}
      className="rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-slate-950 shadow-[0_0_24px_rgba(77,227,208,0.24)] transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400 disabled:shadow-none"
    >
      {isAnalyzing ? 'Analyzing...' : 'Analyze'}
    </button>
  );
}

interface AccessTokenInputProps {
  value: string;
  onChange: (value: string) => void;
}

export default function AccessTokenInput({ value, onChange }: AccessTokenInputProps) {
  return (
    <label className="flex min-w-64 flex-col gap-1.5">
      <span className="font-mono text-[10px] uppercase tracking-wider text-accent">
        Analysis access token
      </span>
      <input
        type="password"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete="off"
        placeholder="Required to run scans"
        aria-label="Analysis access token"
        className="field-surface rounded-xl px-3 py-2 font-mono text-xs text-foreground placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-primary/35"
      />
    </label>
  );
}

import type { ChangeEvent } from 'react';
import AnalyzeButton from './AnalyzeButton';

interface CodeScanInputProps {
  codeContent: string;
  fileName: string;
  canAnalyze: boolean;
  isAnalyzing: boolean;
  onAnalyze: () => void;
  onCodeChange: (value: string) => void;
  onFileUpload: (event: ChangeEvent<HTMLInputElement>) => void;
}

export default function CodeScanInput({
  codeContent,
  fileName,
  canAnalyze,
  isAnalyzing,
  onAnalyze,
  onCodeChange,
  onFileUpload,
}: CodeScanInputProps) {
  return (
    <>
      <div className="mb-3 flex flex-shrink-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <span className="font-mono text-xs uppercase text-accent">Paste code below or upload a .py file</span>
        <div className="flex flex-wrap items-center gap-3">
          {fileName && (
            <span className="rounded-full border border-secondary/30 bg-secondary/10 px-3 py-1 font-mono text-xs text-secondary">
              {fileName}
            </span>
          )}
          <input type="file" accept=".py" onChange={onFileUpload} className="hidden" id="py-upload" />
          <label htmlFor="py-upload" className="cursor-pointer rounded-xl border border-border bg-white/5 px-4 py-2.5 text-sm font-semibold text-foreground transition-colors hover:border-primary/45 hover:bg-primary/10">
            Open .py file
          </label>
          <AnalyzeButton disabled={!canAnalyze} isAnalyzing={isAnalyzing} onAnalyze={onAnalyze} />
        </div>
      </div>
      <textarea
        value={codeContent}
        onChange={(event) => onCodeChange(event.target.value)}
        placeholder="Paste Python code here, or use the button above to upload a .py file..."
        className="field-surface min-h-[360px] flex-1 w-full resize-none rounded-2xl p-4 font-mono text-sm leading-6 text-cyan-50 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-primary/35"
      />
    </>
  );
}

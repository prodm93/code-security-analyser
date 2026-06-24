import type { ChangeEvent } from 'react';
import AnalyzeButton from './AnalyzeButton';

interface ProjectScanInputProps {
  zipFile: File | null;
  canAnalyze: boolean;
  isAnalyzing: boolean;
  onAnalyze: () => void;
  onZipUpload: (event: ChangeEvent<HTMLInputElement>) => void;
}

export default function ProjectScanInput({
  zipFile,
  canAnalyze,
  isAnalyzing,
  onAnalyze,
  onZipUpload,
}: ProjectScanInputProps) {
  return (
    <>
      <div className="mb-3 flex flex-shrink-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <span className="font-mono text-xs uppercase text-accent">Upload a .zip file containing your project source code</span>
        <div className="flex flex-wrap items-center gap-3">
          {zipFile && (
            <span className="rounded-full border border-secondary/30 bg-secondary/10 px-3 py-1 font-mono text-xs text-secondary">
              {zipFile.name} ({(zipFile.size / 1024).toFixed(0)} KB)
            </span>
          )}
          <input type="file" accept=".zip" onChange={onZipUpload} className="hidden" id="zip-upload" />
          <label htmlFor="zip-upload" className="cursor-pointer rounded-xl border border-border bg-white/5 px-4 py-2.5 text-sm font-semibold text-foreground transition-colors hover:border-primary/45 hover:bg-primary/10">
            Open .zip file
          </label>
          <AnalyzeButton disabled={!canAnalyze} isAnalyzing={isAnalyzing} onAnalyze={onAnalyze} />
        </div>
      </div>
      <div className="field-surface flex min-h-[360px] flex-1 items-center justify-center rounded-2xl border-dashed">
        {zipFile ? (
          <div className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-primary/25 bg-primary/10 font-mono text-sm text-primary">.zip</div>
            <p className="text-lg font-semibold text-foreground">{zipFile.name}</p>
            <p className="mt-1 font-mono text-sm text-accent">{(zipFile.size / 1024).toFixed(0)} KB</p>
            <p className="mt-3 max-w-md text-xs text-accent">
              Scans with OpenGrep (code analysis) + Trivy (dependency CVEs, secrets, misconfigs)
            </p>
          </div>
        ) : (
          <div className="text-center text-accent">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-secondary/25 bg-secondary/10 font-mono text-sm text-secondary">src</div>
            <p className="text-sm text-foreground">Select a .zip file to analyze the full project</p>
            <p className="mt-2 text-xs">Both OpenGrep and Trivy will scan for vulnerabilities</p>
          </div>
        )}
      </div>
    </>
  );
}

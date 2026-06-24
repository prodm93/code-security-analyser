import AnalyzeButton from './AnalyzeButton';

interface ImageScanInputProps {
  imageName: string;
  canAnalyze: boolean;
  isAnalyzing: boolean;
  onAnalyze: () => void;
  onImageNameChange: (value: string) => void;
}

export default function ImageScanInput({
  imageName,
  canAnalyze,
  isAnalyzing,
  onAnalyze,
  onImageNameChange,
}: ImageScanInputProps) {
  return (
    <>
      <div className="mb-3 flex flex-shrink-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <span className="font-mono text-xs uppercase text-accent">Enter a container image name to scan with Trivy</span>
        <AnalyzeButton disabled={!canAnalyze} isAnalyzing={isAnalyzing} onAnalyze={onAnalyze} />
      </div>
      <div className="flex-1 flex flex-col">
        <input
          type="text"
          value={imageName}
          onChange={(event) => onImageNameChange(event.target.value)}
          placeholder="e.g. python:3.12-slim, node:20-alpine, nginx:latest"
          className="field-surface w-full rounded-2xl p-4 font-mono text-sm text-cyan-50 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-primary/35"
        />
        <div className="field-surface mt-3 flex min-h-[300px] flex-1 items-center justify-center rounded-2xl border-dashed">
          {imageName.trim() ? (
            <div className="text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-primary/25 bg-primary/10 font-mono text-sm text-primary">img</div>
              <p className="font-mono text-lg font-semibold text-foreground">{imageName}</p>
              <p className="mt-3 max-w-md text-xs text-accent">
                Trivy will scan for OS package CVEs, app dependencies, secrets, and misconfigs
              </p>
            </div>
          ) : (
            <div className="text-center text-accent">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-secondary/25 bg-secondary/10 font-mono text-sm text-secondary">ctr</div>
              <p className="text-sm text-foreground">Enter a Docker image name above</p>
              <p className="mt-2 text-xs">Trivy scans OS packages, dependencies, secrets, and misconfigurations</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

import type { AnalysisResultsProps } from '@/types/security';

function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'critical': return 'border-red-400/35 bg-red-500/15 text-red-200';
    case 'high': return 'border-orange-400/35 bg-orange-500/15 text-orange-200';
    case 'medium': return 'border-yellow-400/35 bg-yellow-500/15 text-yellow-100';
    case 'low': return 'border-emerald-400/35 bg-emerald-500/15 text-emerald-200';
    default: return 'border-slate-400/35 bg-slate-500/15 text-slate-200';
  }
}

export default function AnalysisResults({
  analysisResults,
  isAnalyzing,
  error
}: AnalysisResultsProps) {
  return (
    <section className="panel flex min-h-[520px] flex-col rounded-2xl p-5">
      <div className="mb-5 flex flex-shrink-0 items-center justify-between">
        <div>
          <p className="font-mono text-xs uppercase text-accent">Output stream</p>
          <h2 className="mt-1 text-xl font-semibold text-foreground">Results of Analysis</h2>
        </div>
        <div className={`h-2 w-2 rounded-full bg-primary shadow-[0_0_18px_rgba(77,227,208,0.9)] ${isAnalyzing ? 'animate-pulse' : ''}`} />
      </div>

      <div className="flex-1 overflow-auto">
        {error && (
          <div className="rounded-2xl border border-red-400/25 bg-red-500/10 p-4 text-sm text-red-200">
            <strong>Error:</strong> {error}
          </div>
        )}

        {!analysisResults && !error && (
          <div className="field-surface rounded-2xl p-6 text-center text-sm text-accent">
            {isAnalyzing ? (
              <div className="flex flex-col items-center gap-3">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary/20 border-t-primary" />
                <span>Scanning for vulnerabilities...</span>
              </div>
            ) : 'Upload and analyze code to see security assessment results here.'}
          </div>
        )}

        {analysisResults && (
          <div className="space-y-6">
            <div className="rounded-2xl border border-primary/20 bg-primary/10 p-4">
              <h3 className="mb-2 font-mono text-xs uppercase text-primary">Analysis Summary</h3>
              <p className="text-sm leading-6 text-cyan-50">{analysisResults.summary}</p>
            </div>

            {analysisResults.issues.length > 0 && (
              <div className="overflow-hidden rounded-2xl border border-border bg-black/20">
                <div className="border-b border-border bg-white/[0.035] px-4 py-3">
                  <h3 className="font-mono text-xs uppercase text-foreground">
                    Security Issues Found ({analysisResults.issues.length})
                  </h3>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-white/[0.045]">
                      <tr>
                        <th className="px-4 py-3 text-left font-mono text-[11px] font-medium uppercase text-accent">Issue</th>
                        <th className="px-4 py-3 text-left font-mono text-[11px] font-medium uppercase text-accent">Severity</th>
                        <th className="px-4 py-3 text-left font-mono text-[11px] font-medium uppercase text-accent">CVSS</th>
                        <th className="px-4 py-3 text-left font-mono text-[11px] font-medium uppercase text-accent">Description</th>
                        <th className="px-4 py-3 text-left font-mono text-[11px] font-medium uppercase text-accent">Vulnerable Code</th>
                        <th className="px-4 py-3 text-left font-mono text-[11px] font-medium uppercase text-accent">Recommended Fix</th>
                      </tr>
                    </thead>

                    <tbody className="divide-y divide-white/10">
                      {analysisResults.issues.map((issue, index) => (
                        <tr key={index} className="transition-colors hover:bg-white/[0.035]">
                          <td className="px-4 py-4 text-sm font-semibold text-foreground">{issue.title}</td>
                          <td className="px-4 py-4">
                            <span className={`inline-flex rounded-full border px-2.5 py-1 font-mono text-[11px] font-semibold ${getSeverityColor(issue.severity)}`}>
                              {issue.severity.toUpperCase()}
                            </span>
                          </td>
                          <td className="px-4 py-4 font-mono text-sm text-primary">{issue.cvss_score}</td>
                          <td className="max-w-xs px-4 py-4 text-sm leading-6 text-accent">{issue.description}</td>
                          <td className="max-w-xs overflow-hidden px-4 py-4 font-mono text-xs text-red-200">
                            <pre className="whitespace-pre-wrap break-words">{issue.code}</pre>
                          </td>
                          <td className="max-w-xs overflow-hidden px-4 py-4 font-mono text-xs text-emerald-200">
                            <pre className="whitespace-pre-wrap break-words">{issue.fix}</pre>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

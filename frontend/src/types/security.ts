export type ScanMode = 'code' | 'project' | 'image';

export interface SecurityIssue {
  title: string;
  description: string;
  code: string;
  fix: string;
  cvss_score: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
}

export interface AnalysisResponse {
  summary: string;
  issues: SecurityIssue[];
}

export interface AnalysisResultsProps {
  analysisResults: AnalysisResponse | null;
  isAnalyzing: boolean;
  error: string | null;
}

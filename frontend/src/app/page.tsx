'use client'

import { useState } from 'react';
import type { ChangeEvent } from 'react';
import type { ScanMode, AnalysisResponse } from '@/types/security';
import AnalysisResults from '@/components/AnalysisResults';
import AccessTokenInput from '@/components/AccessTokenInput';
import ScanTabs from '@/components/ScanTabs';
import CodeScanInput from '@/components/scan/CodeScanInput';
import ImageScanInput from '@/components/scan/ImageScanInput';
import ProjectScanInput from '@/components/scan/ProjectScanInput';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === 'development' && typeof window !== 'undefined' && window.location?.hostname === 'localhost'
    ? 'http://localhost:8000'
    : '');

const TABS: { mode: ScanMode; label: string }[] = [
  { mode: 'code', label: 'Python File' },
  { mode: 'project', label: 'Project (ZIP)' },
  { mode: 'image', label: 'Container Image' },
];

export default function Home() {
  const [scanMode, setScanMode] = useState<ScanMode>('code');
  const [accessToken, setAccessToken] = useState('');
  const [codeContent, setCodeContent] = useState('');
  const [fileName, setFileName] = useState('');
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [imageName, setImageName] = useState('');
  const [analysisResults, setAnalysisResults] = useState<AnalysisResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resetResults = () => {
    setAnalysisResults(null);
    setError(null);
  };

  const handleTabChange = (mode: ScanMode) => {
    setScanMode(mode);
    resetResults();
  };

  const handlePyFileUpload = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.name.endsWith('.py')) {
      setFileName(file.name);
      const reader = new FileReader();
      reader.onload = (e) => {
        setCodeContent(e.target?.result as string);
        resetResults();
      };
      reader.readAsText(file);
    } else {
      alert('Please select a Python (.py) file');
    }
  };

  const handleZipUpload = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.name.endsWith('.zip')) {
      setZipFile(file);
      resetResults();
    } else {
      alert('Please select a .zip file');
    }
  };

  const handleCodeChange = (value: string) => {
    setCodeContent(value);
    setFileName('');
    resetResults();
  };

  const handleImageNameChange = (value: string) => {
    setImageName(value);
    resetResults();
  };

  const canAnalyze = () => {
    if (!accessToken.trim()) return false;
    if (scanMode === 'code') return !!codeContent.trim();
    if (scanMode === 'project') return !!zipFile;
    if (scanMode === 'image') return !!imageName.trim();
    return false;
  };

  const handleAnalyze = async () => {
    if (!canAnalyze()) return;
    setIsAnalyzing(true);
    setError(null);

    try {
      let response: Response;
      const authorization = `Bearer ${accessToken.trim()}`;

      if (scanMode === 'code') {
        response = await fetch(`${API_BASE_URL}/api/analyze`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: authorization,
          },
          body: JSON.stringify({ code: codeContent }),
        });
      } else if (scanMode === 'project') {
        const formData = new FormData();
        formData.append('file', zipFile!);
        response = await fetch(`${API_BASE_URL}/api/analyze-project`, {
          method: 'POST',
          headers: { Authorization: authorization },
          body: formData,
        });
      } else {
        response = await fetch(`${API_BASE_URL}/api/analyze-image`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: authorization,
          },
          body: JSON.stringify({ image: imageName }),
        });
      }

      if (!response.ok) {
        const detail = await response.json().catch(() => null);
        throw new Error(detail?.detail || `HTTP error! status: ${response.status}`);
      }

      const results: AnalysisResponse = await response.json();
      setAnalysisResults(results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred during analysis');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <main className="relative min-h-screen overflow-hidden bg-background px-4 py-5 text-foreground sm:px-6 lg:px-8">
      <div className="cyber-grid pointer-events-none absolute inset-0 opacity-80" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/70 to-transparent" />

      <div className="relative mx-auto flex min-h-[calc(100vh-40px)] max-w-7xl flex-col">
        <header className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/10 px-3 py-1 font-mono text-[11px] uppercase text-primary">
              <span className="h-1.5 w-1.5 rounded-full bg-primary shadow-[0_0_14px_rgba(77,227,208,0.9)]" />
              OpenGrep / Trivy Console
            </div>
            <h1 className="text-3xl font-semibold text-foreground sm:text-4xl">Cybersecurity Analyst</h1>
            <p className="mt-2 max-w-2xl text-sm text-accent">
              Security analysis for Python files, source archives, and container images.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:items-end">
            <AccessTokenInput value={accessToken} onChange={setAccessToken} />
            <div className={`rounded-full border px-3 py-1.5 font-mono text-xs transition-colors ${
              isAnalyzing
                ? 'border-primary/40 bg-primary/15 text-primary'
                : 'border-secondary/25 bg-secondary/10 text-secondary'
            }`}>
              {isAnalyzing ? (
                <span className="inline-flex items-center gap-2">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary shadow-[0_0_10px_rgba(77,227,208,0.9)]" />
                  SCANNING
                </span>
              ) : 'STATUS: READY'}
            </div>
          </div>
        </header>

        <div className="grid flex-1 gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.25fr)]">
          <section className="panel flex min-h-[520px] flex-col rounded-2xl p-5">
            <ScanTabs tabs={TABS} activeMode={scanMode} onTabChange={handleTabChange} />

            <div className="flex-1 flex flex-col">
              {scanMode === 'code' && (
                <CodeScanInput
                  codeContent={codeContent}
                  fileName={fileName}
                  canAnalyze={canAnalyze()}
                  isAnalyzing={isAnalyzing}
                  onAnalyze={handleAnalyze}
                  onCodeChange={handleCodeChange}
                  onFileUpload={handlePyFileUpload}
                />
              )}

              {scanMode === 'project' && (
                <ProjectScanInput
                  zipFile={zipFile}
                  canAnalyze={canAnalyze()}
                  isAnalyzing={isAnalyzing}
                  onAnalyze={handleAnalyze}
                  onZipUpload={handleZipUpload}
                />
              )}

              {scanMode === 'image' && (
                <ImageScanInput
                  imageName={imageName}
                  canAnalyze={canAnalyze()}
                  isAnalyzing={isAnalyzing}
                  onAnalyze={handleAnalyze}
                  onImageNameChange={handleImageNameChange}
                />
              )}
            </div>
          </section>

          <AnalysisResults
            analysisResults={analysisResults}
            isAnalyzing={isAnalyzing}
            error={error}
          />
        </div>
      </div>
    </main>
  );
}

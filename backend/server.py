import os
import shutil
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv
from agents import Agent, Runner, trace

from auth import require_analysis_api_key
from context import (
    CODE_INSTRUCTIONS,
    PROJECT_INSTRUCTIONS,
    IMAGE_INSTRUCTIONS,
    get_code_prompt,
    get_project_prompt,
    get_image_prompt,
    enhance_summary,
)
from mcp_servers import create_scanner_server
from project_archives import (
    ProjectArchiveRejected,
    ProjectExpandedTooLarge,
    ProjectUploadTooLarge,
    extract_project_archive,
)
from resource_limits import (
    AnalysisCapacity,
    AnalysisCapacityExceeded,
    RequestBodyLimitMiddleware,
    ResourceLimits,
)

load_dotenv(override=True)

resource_limits = ResourceLimits.from_environment()
analysis_capacity = AnalysisCapacity(
    resource_limits.max_concurrent_analyses,
    resource_limits.queue_timeout_seconds,
)

app = FastAPI(title="Cybersecurity Analyzer API")

app.add_middleware(
    RequestBodyLimitMiddleware,
    path_limits=resource_limits.request_body_limits,
)

cors_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://frontend:3000",
]

if os.getenv("ENVIRONMENT") == "production":
    cors_origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    code: str


class ImageRequest(BaseModel):
    image: str


class SecurityIssue(BaseModel):
    title: str = Field(description="Brief title of the security vulnerability")
    description: str = Field(
        description="Detailed description of the security issue and its potential impact"
    )
    code: str = Field(
        description="The specific vulnerable code snippet that demonstrates the issue"
    )
    fix: str = Field(description="Recommended code fix or mitigation strategy")
    cvss_score: float = Field(
        description="CVSS score from 0.0 to 10.0 representing severity"
    )
    severity: str = Field(description="Severity level: critical, high, medium, or low")


class SecurityReport(BaseModel):
    summary: str = Field(description="Executive summary of the security analysis")
    issues: List[SecurityIssue] = Field(
        description="List of identified security vulnerabilities"
    )


def check_api_keys() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")


def sort_report(report: SecurityReport) -> SecurityReport:
    report.issues.sort(key=lambda issue: issue.cvss_score, reverse=True)
    return report


async def require_analysis_capacity() -> AsyncIterator[None]:
    try:
        async with analysis_capacity.reserve():
            yield
    except AnalysisCapacityExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail="Analysis capacity is currently full; retry shortly",
            headers={"Retry-After": "1"},
        ) from exc


# --- Code analysis (single .py file or pasted code) ---


@app.post(
    "/api/analyze",
    response_model=SecurityReport,
    dependencies=[
        Depends(require_analysis_api_key),
        Depends(require_analysis_capacity),
    ],
)
async def analyze_code(request: AnalyzeRequest) -> SecurityReport:
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="No code provided for analysis")
    check_api_keys()

    try:
        with trace("Code Analysis"):
            async with create_scanner_server() as scanners:
                agent = Agent(
                    name="Security Researcher",
                    instructions=CODE_INSTRUCTIONS,
                    model="gpt-4.1-mini",
                    mcp_servers=[scanners],
                    output_type=SecurityReport,
                )
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".py", delete=False
                ) as temp:
                    temp.write(request.code)
                    temp_path = temp.name
                try:
                    result = await Runner.run(
                        agent, input=get_code_prompt(request.code, temp_path)
                    )
                    report = sort_report(result.final_output_as(SecurityReport))
                    report.summary = enhance_summary(len(request.code), report.summary)
                    return report
                finally:
                    os.unlink(temp_path)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected {e=}, {type(e)=}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# --- Project analysis (zip upload) ---


@app.post(
    "/api/analyze-project",
    response_model=SecurityReport,
    dependencies=[
        Depends(require_analysis_api_key),
        Depends(require_analysis_capacity),
    ],
)
async def analyze_project(file: UploadFile = File(...)) -> SecurityReport:
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload a .zip file")
    check_api_keys()

    work_directory = Path(tempfile.mkdtemp(prefix="cyber_project_"))
    try:
        project_path = await extract_project_archive(
            file,
            work_directory,
            resource_limits.project_archive,
        )

        with trace("Project Analysis"):
            async with create_scanner_server() as scanners:
                agent = Agent(
                    name="Security Researcher",
                    instructions=PROJECT_INSTRUCTIONS,
                    model="gpt-4.1-mini",
                    mcp_servers=[scanners],
                    output_type=SecurityReport,
                )
                result = await Runner.run(
                    agent, input=get_project_prompt(str(project_path))
                )
                report = sort_report(result.final_output_as(SecurityReport))
                report.summary = f"Analyzed project '{file.filename}'. {report.summary}"
                return report
    except (ProjectUploadTooLarge, ProjectExpandedTooLarge) as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ProjectArchiveRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected {e=}, {type(e)=}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        await file.close()
        shutil.rmtree(work_directory, ignore_errors=True)


# --- Container image analysis ---


@app.post(
    "/api/analyze-image",
    response_model=SecurityReport,
    dependencies=[
        Depends(require_analysis_api_key),
        Depends(require_analysis_capacity),
    ],
)
async def analyze_image(request: ImageRequest) -> SecurityReport:
    if not request.image.strip():
        raise HTTPException(status_code=400, detail="No image name provided")
    check_api_keys()

    try:
        with trace("Image Analysis"):
            async with create_scanner_server() as scanners:
                agent = Agent(
                    name="Security Researcher",
                    instructions=IMAGE_INSTRUCTIONS,
                    model="gpt-4.1-mini",
                    mcp_servers=[scanners],
                    output_type=SecurityReport,
                )
                result = await Runner.run(
                    agent, input=get_image_prompt(request.image.strip())
                )
                report = sort_report(result.final_output_as(SecurityReport))
                report.summary = f"Analyzed container image '{request.image.strip()}'. {report.summary}"
                return report
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected {e=}, {type(e)=}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/health")
async def health():
    return {"message": "Cybersecurity Analyzer API"}


if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

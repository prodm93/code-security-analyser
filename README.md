# Agent-Assisted Software Security Analysis Platform

AI has let so many of us ship so fast, but...

Your ship likely has holes in it.

---

AI-generated code is everywhere, and it's getting better at looking correct while still being a security nightmare. I've spent enough time reviewing LLM output to know the pattern: the code compiles, it passes the smell test, and then you look closer and find hardcoded secrets, SQL injection waiting to happen, or dependencies pulled from who-knows-where with known CVEs. The models are confident about everything, including the stuff they get dangerously wrong.

Security analysis tooling hasn't kept up with this. Static analysis still thinks its job ends at the source code boundary. Dependency scanners, container scanners, infrastructure scanners—all talking past each other, dumping findings in formats that assume you have time to cross-reference everything manually. I wanted to see what it would look like to build something that actually treats security as a system-wide concern and does something useful with the output.

This is an infrastructure-complete, deployment-ready software security analysis platform. It's a full-stack build consisting of a FastAPI backend, a Next.js frontend exported as static assets and served from the same container, a custom MCP server that wraps OpenGrep and Trivy behind a unified scanning interface, and an OpenAI Agents SDK workflow that analyses, contextualises, and prioritises findings. Infrastructure is provisioned through Terraform for both Azure Container Apps and Google Cloud Run, with cloud-native secret management, cross-platform container builds, and automated CI included in the repository.

## Architecture

```text
Next.js UI
    │ API request
    ▼
FastAPI Backend
    │ starts agent run
    ▼
Analysis Agent (OpenAI Agents SDK)
    │ MCP tool call
    ▼
Custom MCP Server
    ├── OpenGrep ──► Static code findings
    └── Trivy ─────► Dependency / container / supply-chain findings
    │
    ▼
Normalised Findings ──► Analysis Agent ──► Structured Security Report
                                                │
                                                ▼
                                    FastAPI Backend ──► Next.js UI
```

The frontend sends scan requests to the FastAPI backend, which starts the analysis agent with access to the unified MCP server. The agent invokes the MCP scan tool; the server dispatches work to OpenGrep and Trivy and returns normalised findings. The agent then produces a structured report that FastAPI returns to the frontend.

## Why I Built It This Way

**Security beyond source code.** SAST is table stakes. Real vulnerabilities come from dependencies with critical CVEs, container images that haven't been patched, supply chain compromises, infrastructure misconfigurations. I wanted coverage across the whole delivery stack, not just the code I wrote. That's why Trivy sits alongside OpenGrep—not as an afterthought, but as a core part of the analysis pipeline. A SAST-only platform would miss a significant portion of the attack surface.

**Scanner replaceability.** Semgrep's licensing overhauls have been pulling features and rule sets behind Pro tiers with little warning, which makes any backend tightly coupled to it brittle by default. I went with OpenGrep to keep access to the rule ecosystem without waking up to find my scanner's core functionality paywalled. More importantly, findings are normalised before they hit the analysis layer, so the scanner itself is swappable without touching the rest of the system. If OpenGrep goes sideways too, I swap the scanner and the rest of the platform keeps working.

**A custom MCP server for unified scanning.** Rather than bolting scanners directly into the backend, I built a dedicated MCP server that exposes OpenGrep and Trivy through a standardised interface. The analysis agent uses one MCP interface instead of managing multiple scanner integrations, and consumes normalised findings without caring which tool produced them. This keeps scanner orchestration isolated from application logic, simplifies future scanner additions, and avoids tightly coupling the platform to any single security tool.

**Agent-assisted security analysis.** Security scanners are excellent at producing findings and considerably less helpful at connecting them. The platform uses an OpenAI Agents SDK workflow that consumes normalised findings from the MCP layer, correlates results across OpenGrep and Trivy, identifies recurring security themes spanning multiple layers of the stack, and generates consolidated security assessments with technical context and remediation guidance. Instead of treating each scanner as an isolated source of output, the platform produces a unified view of application security across source code, dependencies, containers, and supply-chain components.

**Single-container deployment.** I considered splitting the frontend and backend into separate deployments, but for a platform of this size it mostly introduced additional infrastructure to manage: separate hosting, routing, deployment coordination, environment configuration, and cross-service debugging. Exporting the Next.js frontend as static assets and serving it directly from FastAPI produces a single deployable artefact, simplifies promotion across environments, and keeps operational complexity aligned with the actual scale of the system.

**Terraform and multi-cloud deployment.** Infrastructure is defined entirely through Terraform and supports deployment to both Azure Container Apps and Google Cloud Run. The objective wasn't multi-cloud for its own sake; it was ensuring the application architecture remained portable and avoided unnecessary cloud-specific coupling. The same application can be deployed across providers without requiring changes to the application layer.

**Cross-platform builds by default.** Development happens on ARM64 hardware while deployment targets AMD64 cloud environments. Cross-platform container builds are baked into the workflow using Docker Buildx, producing reproducible images that behave consistently across local and cloud environments.

**Secrets without embedding.** This wasn't just about keeping credentials out of source control. I wanted the same container image to be deployable across local development, Azure Container Apps, and Google Cloud Run without modification. Secret injection is handled by Azure Key Vault or GCP Secret Manager at deployment time, keeping credential management in the infrastructure layer and allowing the application itself to remain environment-agnostic.

## Engineering Challenges

**Designing a scanner-agnostic analysis layer.** OpenGrep and Trivy operate at different layers of the stack and produce fundamentally different output formats. The custom MCP server normalises findings into a common schema before they reach the analysis workflow, allowing the agent layer to reason about security findings without being tightly coupled to any individual scanner implementation. That abstraction makes scanner replacement or expansion a deployment decision rather than an architectural rewrite.

**Scanner memory profiling under cloud constraints.** During early deployment testing, scanner processes were repeatedly being terminated with SIGKILL despite succeeding locally. The issue turned out not to be the application itself, but memory consumption associated with loading large scanner rule registries. I profiled scanner behaviour under cloud runtime constraints, validated actual resource requirements, and tuned deployment configuration around observed scanner characteristics rather than simply increasing container allocations.

**MCP compatibility management.** The custom MCP server became a critical integration boundary between the application and scanning layer. MCP compatibility is pinned explicitly rather than floating on latest releases, avoiding situations where upstream protocol changes silently break scanner orchestration or tool invocation behaviour.

**ARM64 to AMD64 deployment.** Development was performed on Apple Silicon while deployment targets expected AMD64 container images. Cross-platform builds were incorporated into the workflow from the outset using Docker Buildx, producing reproducible images that behave consistently across local and cloud environments.

**Relative URL routing in production.** Because the Next.js frontend is exported as static assets and served by FastAPI, frontend routing needed to work consistently whether the application was running locally or behind Azure Container Apps or Cloud Run. The frontend build was configured around deployment-agnostic asset paths and routing so deployment targets can change without requiring environment-specific frontend builds.

## Running Locally

```bash
cp .env.example .env

# Configure required API keys

docker buildx build --platform linux/amd64 -t security-platform .

docker run -p 8000:8000 --env-file .env security-platform
```

## Deployment

Infrastructure is defined entirely through Terraform. The same application can be deployed to either Azure Container Apps or Google Cloud Run using provider-specific variable files.

```bash
cd terraform/

terraform init

terraform apply -var-file="azure.tfvars"

# or

terraform apply -var-file="gcp.tfvars"
```

Secrets are injected through Azure Key Vault or GCP Secret Manager rather than embedded in container images or Terraform configuration.

## What's Next

The current deployment model provisions infrastructure into my own cloud accounts, but the provider-specific Terraform stacks are structured in a way that could support a BYOC (Bring Your Own Cloud) model. A future iteration would allow users to deploy the entire platform directly into their own Azure or GCP environments, keeping source code, scan results, and operational data within infrastructure they control.

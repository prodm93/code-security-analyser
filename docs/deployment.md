# Production deployment

Azure and GCP have separate, manual-only workflows:

- `Deploy Azure` targets the protected `azure-production` environment.
- `Deploy GCP` targets the protected `gcp-production` environment.

Neither workflow runs on pushes or pull requests. Both deploy only from `main`, default to a Terraform
plan, and are disabled until their repository-level enable variable is exactly `true`. An apply also
requires the cloud-specific confirmation phrase shown in the workflow form.

## Required safeguards

Before enabling either workflow:

1. Create its GitHub environment and restrict deployments to `main`.
2. Configure required reviewers for that environment.
3. Configure cloud OIDC trust for the environment-bound subject
   `repo:OWNER/REPOSITORY:environment:ENVIRONMENT`.
4. Create the remote Terraform state storage and grant the deployment identity access to it.
5. Add the environment variables listed below.
6. Only then create the repository variable `ENABLE_AZURE_DEPLOYMENT=true` or
   `ENABLE_GCP_DEPLOYMENT=true`.

The enable variable is a kill switch, not an authorization boundary. Environment protection rules and
cloud-side OIDC conditions provide that boundary. No long-lived cloud credentials belong in GitHub.

## Azure

Create the `azure-production` environment with these variables:

| Variable | Purpose |
| --- | --- |
| `AZURE_CLIENT_ID` | Federated deployment application's client ID |
| `AZURE_TENANT_ID` | Microsoft Entra tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Target subscription ID |
| `AZURE_TFSTATE_RESOURCE_GROUP` | Resource group containing remote state |
| `AZURE_TFSTATE_STORAGE_ACCOUNT` | Remote-state storage account |
| `AZURE_TFSTATE_CONTAINER` | Blob container for remote state |
| `AZURE_PROJECT_NAME` | Application and registry name prefix |
| `AZURE_RESOURCE_GROUP_NAME` | Existing application resource group |
| `AZURE_KEY_VAULT_ID` | Existing RBAC-enabled Key Vault resource ID |
| `AZURE_OPENAI_API_KEY_SECRET_ID` | Key Vault secret URI for the OpenAI API key |
| `AZURE_ANALYSIS_API_KEY_SECRET_ID` | Key Vault secret URI for the analysis bearer token |

The federated identity needs state-container data access and only the Azure control-plane permissions
required by the Terraform plan. Because the stack creates an RBAC assignment for the runtime identity,
the deployment identity must also be allowed to create that specific role assignment.

Run `Deploy Azure`, review the plan, then rerun with `apply` and the exact confirmation
`APPLY-AZURE-PRODUCTION`.

## GCP

Create the `gcp-production` environment with these variables:

| Variable | Purpose |
| --- | --- |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Full Workload Identity Provider resource name |
| `GCP_DEPLOY_SERVICE_ACCOUNT` | Deployment service-account email |
| `GCP_TFSTATE_BUCKET` | GCS bucket for remote state |
| `GCP_PROJECT_ID` | Target project ID |
| `GCP_REGION` | Cloud Run and Artifact Registry region |
| `GCP_SERVICE_NAME` | Cloud Run service and repository name |
| `GCP_OPENAI_API_KEY_SECRET_NAME` | Existing Secret Manager secret name |
| `GCP_ANALYSIS_API_KEY_SECRET_NAME` | Existing Secret Manager secret name for the bearer token |

The Workload Identity Provider must restrict principals to this repository and environment. The
deployment service account needs state-bucket access and only the project permissions required by the
Terraform plan, including the explicitly managed APIs, runtime identity, IAM bindings, Artifact
Registry, and Cloud Run resources.

Run `Deploy GCP`, review the plan, then rerun with `apply` and the exact confirmation
`APPLY-GCP-PRODUCTION`.

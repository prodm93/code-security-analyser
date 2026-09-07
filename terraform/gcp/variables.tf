variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run deployment"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Name of the Cloud Run service"
  type        = string
  default     = "cyber-analyzer"
}

variable "openai_api_key" {
  description = "OpenAI API key for the application"
  type        = string
  sensitive   = true
  default     = ""
}

variable "analysis_api_key" {
  description = "Bearer token required by analysis endpoints"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.analysis_api_key) >= 32
    error_message = "analysis_api_key must contain at least 32 characters."
  }
}

variable "allow_public_access" {
  description = "Grant unauthenticated network access to Cloud Run; application bearer authentication remains required"
  type        = bool
  default     = false
}

variable "semgrep_app_token" {
  description = "Semgrep app token for security scanning"
  type        = string
  sensitive   = true
  default     = ""
}

variable "docker_image_tag" {
  description = "Tag for the Docker image"
  type        = string
  default     = "latest"
}

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

variable "openai_api_key_secret_name" {
  description = "Name of an existing Secret Manager secret containing the OpenAI API key"
  type        = string

  validation {
    condition     = length(trimspace(var.openai_api_key_secret_name)) > 0
    error_message = "openai_api_key_secret_name must not be empty."
  }
}

variable "analysis_api_key_secret_name" {
  description = "Name of an existing Secret Manager secret containing the analysis bearer token"
  type        = string

  validation {
    condition     = length(trimspace(var.analysis_api_key_secret_name)) > 0
    error_message = "analysis_api_key_secret_name must not be empty."
  }
}

variable "allow_public_access" {
  description = "Grant unauthenticated network access to Cloud Run; application bearer authentication remains required"
  type        = bool
  default     = false
}

variable "docker_image_tag" {
  description = "Tag for the Docker image"
  type        = string
  default     = "latest"
}

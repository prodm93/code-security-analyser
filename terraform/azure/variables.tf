variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "cyber-analyzer"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus2"
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "cyber-analyzer-rg"
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
  description = "Expose Container App ingress externally; application bearer authentication remains required"
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

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

variable "key_vault_id" {
  description = "Resource ID of an existing RBAC-enabled Key Vault containing application secrets"
  type        = string

  validation {
    condition     = length(trimspace(var.key_vault_id)) > 0
    error_message = "key_vault_id must not be empty."
  }
}

variable "openai_api_key_secret_id" {
  description = "Versioned or versionless Key Vault secret URI containing the OpenAI API key"
  type        = string

  validation {
    condition     = length(trimspace(var.openai_api_key_secret_id)) > 0
    error_message = "openai_api_key_secret_id must not be empty."
  }
}

variable "analysis_api_key_secret_id" {
  description = "Versioned or versionless Key Vault secret URI containing the analysis bearer token"
  type        = string

  validation {
    condition     = length(trimspace(var.analysis_api_key_secret_id)) > 0
    error_message = "analysis_api_key_secret_id must not be empty."
  }
}

variable "allow_public_access" {
  description = "Expose Container App ingress externally; application bearer authentication remains required"
  type        = bool
  default     = false
}

variable "docker_image_tag" {
  description = "Tag for the Docker image"
  type        = string
  default     = "latest"
}

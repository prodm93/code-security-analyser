terraform {
  required_version = ">= 1.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

# Configure Azure Provider
provider "azurerm" {
  features {}
}

# Add a random acr_suffix to the acr name to make it globally unique.
resource "random_string" "acr_suffix" {
  length  = 6
  upper   = false
  lower   = true
  numeric = true
  special = false
}
locals {
  acr_basename = replace(var.project_name, "-", "") // only letters/numbers
  // keep base to <= 40 so base+6 <= 46 (under 50 char limit)
  acr_name = "${substr(local.acr_basename, 0, 40)}${random_string.acr_suffix.result}"
}

# Use existing resource group
data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}

# Use a dedicated runtime identity to read application secrets from Key Vault.
resource "azurerm_user_assigned_identity" "app" {
  name                = "${var.project_name}-runtime"
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name

  tags = {
    environment = terraform.workspace
    project     = var.project_name
  }
}

resource "azurerm_role_assignment" "key_vault_secrets" {
  scope                = var.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

# Create Azure Container Registry
resource "azurerm_container_registry" "acr" {
  name                = local.acr_name
  resource_group_name = data.azurerm_resource_group.main.name
  location            = data.azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = true

  tags = {
    environment = terraform.workspace
    project     = var.project_name
  }
}

# Configure Docker provider to use ACR
provider "docker" {
  registry_auth {
    address  = azurerm_container_registry.acr.login_server
    username = azurerm_container_registry.acr.admin_username
    password = azurerm_container_registry.acr.admin_password
  }
}

# Build and push Docker image
resource "docker_image" "app" {
  name = "${azurerm_container_registry.acr.login_server}/${var.project_name}:${var.docker_image_tag}"

  build {
    context    = "${path.module}/../.."
    dockerfile = "Dockerfile"
    platform   = "linux/amd64"
    no_cache   = true
  }
}

resource "docker_registry_image" "app" {
  name = docker_image.app.name

  depends_on = [docker_image.app]
}

# Create Log Analytics Workspace for monitoring
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.project_name}-logs"
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = {
    environment = terraform.workspace
    project     = var.project_name
  }
}

# Create Container App Environment
resource "azurerm_container_app_environment" "main" {
  name                       = "${var.project_name}-env"
  location                   = data.azurerm_resource_group.main.location
  resource_group_name        = data.azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  tags = {
    environment = terraform.workspace
    project     = var.project_name
  }
}

# Create Container App
resource "azurerm_container_app" "main" {
  name                         = var.project_name
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = data.azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  template {
    container {
      name   = "main"
      image  = docker_registry_image.app.name
      cpu    = 1.0
      memory = "2.0Gi"

      env {
        name        = "OPENAI_API_KEY"
        secret_name = "openai-api-key"
      }

      env {
        name        = "ANALYSIS_API_KEY"
        secret_name = "analysis-api-key"
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }


      env {
        name  = "PYTHONUNBUFFERED"
        value = "1"
      }
    }

    min_replicas = 0
    max_replicas = 1
  }

  ingress {
    external_enabled = var.allow_public_access
    target_port      = 8000

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  registry {
    server               = azurerm_container_registry.acr.login_server
    username             = azurerm_container_registry.acr.admin_username
    password_secret_name = "registry-password"
  }

  secret {
    name  = "registry-password"
    value = azurerm_container_registry.acr.admin_password
  }

  secret {
    name                = "openai-api-key"
    identity            = azurerm_user_assigned_identity.app.id
    key_vault_secret_id = var.openai_api_key_secret_id
  }

  secret {
    name                = "analysis-api-key"
    identity            = azurerm_user_assigned_identity.app.id
    key_vault_secret_id = var.analysis_api_key_secret_id
  }

  depends_on = [azurerm_role_assignment.key_vault_secrets]

  tags = {
    environment = terraform.workspace
    project     = var.project_name
  }
}

# Outputs
output "app_url" {
  value       = "https://${azurerm_container_app.main.ingress[0].fqdn}"
  description = "URL of the deployed application"
}

output "acr_login_server" {
  value       = azurerm_container_registry.acr.login_server
  description = "Azure Container Registry login server"
}

output "resource_group" {
  value       = data.azurerm_resource_group.main.name
  description = "Resource group name"
}

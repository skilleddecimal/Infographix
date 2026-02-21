# Infographix Infrastructure Variables

# =============================================================================
# General
# =============================================================================

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
  default     = "staging"

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be 'staging' or 'production'."
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# =============================================================================
# Networking
# =============================================================================

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# =============================================================================
# ECS / Containers
# =============================================================================

variable "backend_image" {
  description = "Docker image for backend"
  type        = string
  default     = "ghcr.io/infographix/backend:latest"
}

variable "frontend_image" {
  description = "Docker image for frontend"
  type        = string
  default     = "ghcr.io/infographix/frontend:latest"
}

variable "backend_cpu" {
  description = "CPU units for backend task"
  type        = number
  default     = 512
}

variable "backend_memory" {
  description = "Memory (MB) for backend task"
  type        = number
  default     = 1024
}

variable "backend_count" {
  description = "Number of backend tasks"
  type        = number
  default     = 2
}

variable "frontend_cpu" {
  description = "CPU units for frontend task"
  type        = number
  default     = 256
}

variable "frontend_memory" {
  description = "Memory (MB) for frontend task"
  type        = number
  default     = 512
}

variable "frontend_count" {
  description = "Number of frontend tasks"
  type        = number
  default     = 2
}

# =============================================================================
# Database (RDS)
# =============================================================================

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "Allocated storage (GB)"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "infographix"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "infographix"
}

# =============================================================================
# Cache (ElastiCache)
# =============================================================================

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_nodes" {
  description = "Number of cache nodes"
  type        = number
  default     = 1
}

# =============================================================================
# Application Configuration
# =============================================================================

variable "environment_variables" {
  description = "Environment variables for application"
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Secrets ARNs for application"
  type        = map(string)
  default     = {}
  sensitive   = true
}

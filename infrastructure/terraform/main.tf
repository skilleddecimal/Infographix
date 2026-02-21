# Infographix Infrastructure - Main Configuration
# Cloud-agnostic entry point for Terraform

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # Backend configuration - uncomment and configure for remote state
  # backend "s3" {
  #   bucket         = "infographix-terraform-state"
  #   key            = "terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "infographix-terraform-locks"
  # }
}

# =============================================================================
# Providers
# =============================================================================

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Infographix"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# =============================================================================
# Data Sources
# =============================================================================

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# =============================================================================
# Local Values
# =============================================================================

locals {
  name_prefix = "infographix-${var.environment}"

  common_tags = {
    Project     = "Infographix"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  azs = slice(data.aws_availability_zones.available.names, 0, 3)
}

# =============================================================================
# Random Resources
# =============================================================================

resource "random_password" "db_password" {
  length  = 32
  special = false
}

resource "random_password" "redis_password" {
  length  = 32
  special = false
}

# =============================================================================
# Modules
# =============================================================================

module "vpc" {
  source = "./modules/vpc"

  name_prefix = local.name_prefix
  environment = var.environment

  vpc_cidr           = var.vpc_cidr
  availability_zones = local.azs

  tags = local.common_tags
}

module "ecs" {
  source = "./modules/ecs"

  name_prefix = local.name_prefix
  environment = var.environment

  vpc_id          = module.vpc.vpc_id
  private_subnets = module.vpc.private_subnet_ids
  public_subnets  = module.vpc.public_subnet_ids

  backend_image  = var.backend_image
  frontend_image = var.frontend_image

  backend_cpu    = var.backend_cpu
  backend_memory = var.backend_memory
  backend_count  = var.backend_count

  frontend_cpu    = var.frontend_cpu
  frontend_memory = var.frontend_memory
  frontend_count  = var.frontend_count

  database_url = "postgresql://${var.db_username}:${random_password.db_password.result}@${module.rds.endpoint}/${var.db_name}"
  redis_url    = "redis://:${random_password.redis_password.result}@${module.elasticache.endpoint}:6379/0"

  environment_variables = var.environment_variables
  secrets               = var.secrets

  tags = local.common_tags
}

module "rds" {
  source = "./modules/rds"

  name_prefix = local.name_prefix
  environment = var.environment

  vpc_id          = module.vpc.vpc_id
  private_subnets = module.vpc.private_subnet_ids

  instance_class    = var.db_instance_class
  allocated_storage = var.db_allocated_storage

  database_name = var.db_name
  username      = var.db_username
  password      = random_password.db_password.result

  ecs_security_group_id = module.ecs.security_group_id

  tags = local.common_tags
}

module "elasticache" {
  source = "./modules/elasticache"

  name_prefix = local.name_prefix
  environment = var.environment

  vpc_id          = module.vpc.vpc_id
  private_subnets = module.vpc.private_subnet_ids

  node_type       = var.redis_node_type
  num_cache_nodes = var.redis_num_nodes

  auth_token = random_password.redis_password.result

  ecs_security_group_id = module.ecs.security_group_id

  tags = local.common_tags
}

# =============================================================================
# Outputs
# =============================================================================

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = module.ecs.alb_dns_name
}

output "ecs_cluster_name" {
  description = "ECS Cluster name"
  value       = module.ecs.cluster_name
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.rds.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = module.elasticache.endpoint
  sensitive   = true
}

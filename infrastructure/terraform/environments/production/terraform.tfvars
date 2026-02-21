# Production Environment Configuration

environment = "production"
aws_region  = "us-east-1"

# Networking
vpc_cidr = "10.1.0.0/16"

# ECS
backend_cpu    = 1024
backend_memory = 2048
backend_count  = 3

frontend_cpu    = 512
frontend_memory = 1024
frontend_count  = 2

# Database
db_instance_class    = "db.t3.medium"
db_allocated_storage = 100
db_name              = "infographix"
db_username          = "infographix"

# Cache
redis_node_type = "cache.t3.small"
redis_num_nodes = 2

# Application
environment_variables = {
  "LOG_LEVEL" = "INFO"
}

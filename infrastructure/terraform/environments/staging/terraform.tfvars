# Staging Environment Configuration

environment = "staging"
aws_region  = "us-east-1"

# Networking
vpc_cidr = "10.0.0.0/16"

# ECS
backend_cpu    = 512
backend_memory = 1024
backend_count  = 1

frontend_cpu    = 256
frontend_memory = 512
frontend_count  = 1

# Database
db_instance_class    = "db.t3.micro"
db_allocated_storage = 20
db_name              = "infographix_staging"
db_username          = "infographix"

# Cache
redis_node_type = "cache.t3.micro"
redis_num_nodes = 1

# Application
environment_variables = {
  "LOG_LEVEL" = "DEBUG"
}

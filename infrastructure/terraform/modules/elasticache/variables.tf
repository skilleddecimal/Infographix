# ElastiCache Module Variables

variable "name_prefix" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnets" {
  type = list(string)
}

variable "node_type" {
  type = string
}

variable "num_cache_nodes" {
  type = number
}

variable "auth_token" {
  type      = string
  sensitive = true
}

variable "ecs_security_group_id" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

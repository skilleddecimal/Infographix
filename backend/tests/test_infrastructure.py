"""Tests for infrastructure configuration files."""

import os
import pytest
import yaml


class TestDockerConfiguration:
    """Test Docker configuration files."""

    def test_dockerfile_backend_exists(self):
        """Backend Dockerfile should exist."""
        path = "infrastructure/docker/Dockerfile.backend"
        assert os.path.exists(path), f"Missing: {path}"

    def test_dockerfile_frontend_exists(self):
        """Frontend Dockerfile should exist."""
        path = "infrastructure/docker/Dockerfile.frontend"
        assert os.path.exists(path), f"Missing: {path}"

    def test_dockerfile_backend_has_healthcheck(self):
        """Backend Dockerfile should include health check."""
        with open("infrastructure/docker/Dockerfile.backend") as f:
            content = f.read()
        assert "HEALTHCHECK" in content

    def test_dockerfile_backend_runs_as_nonroot(self):
        """Backend Dockerfile should run as non-root user."""
        with open("infrastructure/docker/Dockerfile.backend") as f:
            content = f.read()
        assert "USER appuser" in content or "USER 1000" in content

    def test_dockerfile_frontend_has_nginx(self):
        """Frontend production Dockerfile should use nginx."""
        with open("infrastructure/docker/Dockerfile.frontend") as f:
            content = f.read()
        assert "nginx" in content.lower()


class TestDockerCompose:
    """Test Docker Compose configuration."""

    def test_docker_compose_exists(self):
        """docker-compose.yml should exist."""
        assert os.path.exists("docker-compose.yml")

    def test_docker_compose_valid_yaml(self):
        """docker-compose.yml should be valid YAML."""
        with open("docker-compose.yml") as f:
            config = yaml.safe_load(f)
        assert "services" in config

    def test_docker_compose_has_required_services(self):
        """docker-compose.yml should have required services."""
        with open("docker-compose.yml") as f:
            config = yaml.safe_load(f)

        required_services = ["backend", "frontend", "postgres", "redis"]
        for service in required_services:
            assert service in config["services"], f"Missing service: {service}"

    def test_docker_compose_has_healthchecks(self):
        """Services should have health checks."""
        with open("docker-compose.yml") as f:
            config = yaml.safe_load(f)

        # At least postgres and redis should have health checks
        postgres = config["services"]["postgres"]
        redis = config["services"]["redis"]

        assert "healthcheck" in postgres
        assert "healthcheck" in redis

    def test_docker_compose_prod_exists(self):
        """docker-compose.prod.yml should exist."""
        assert os.path.exists("docker-compose.prod.yml")


class TestNginxConfiguration:
    """Test nginx configuration."""

    def test_nginx_conf_exists(self):
        """nginx.conf should exist."""
        assert os.path.exists("infrastructure/docker/nginx/nginx.conf")

    def test_nginx_default_conf_exists(self):
        """default.conf should exist."""
        assert os.path.exists("infrastructure/docker/nginx/default.conf")

    def test_nginx_has_security_headers(self):
        """nginx should include security headers."""
        with open("infrastructure/docker/nginx/default.conf") as f:
            content = f.read()

        assert "X-Frame-Options" in content
        assert "X-Content-Type-Options" in content
        assert "X-XSS-Protection" in content

    def test_nginx_has_gzip(self):
        """nginx should enable gzip compression."""
        with open("infrastructure/docker/nginx/nginx.conf") as f:
            content = f.read()
        assert "gzip on" in content

    def test_nginx_has_rate_limiting(self):
        """nginx should have rate limiting."""
        with open("infrastructure/docker/nginx/nginx.conf") as f:
            content = f.read()
        assert "limit_req_zone" in content


class TestGitHubActions:
    """Test GitHub Actions workflows."""

    def test_ci_workflow_exists(self):
        """CI workflow should exist."""
        assert os.path.exists(".github/workflows/ci.yml")

    def test_deploy_workflow_exists(self):
        """Deploy workflow should exist."""
        assert os.path.exists(".github/workflows/deploy.yml")

    def test_ci_workflow_valid_yaml(self):
        """CI workflow should be valid YAML."""
        with open(".github/workflows/ci.yml") as f:
            config = yaml.safe_load(f)
        assert "jobs" in config

    def test_ci_workflow_has_test_job(self):
        """CI workflow should have test jobs."""
        with open(".github/workflows/ci.yml") as f:
            config = yaml.safe_load(f)

        jobs = config.get("jobs", {})
        assert "backend-test" in jobs or "test" in jobs

    def test_deploy_workflow_has_environments(self):
        """Deploy workflow should define environments."""
        with open(".github/workflows/deploy.yml") as f:
            content = f.read()

        assert "staging" in content.lower()
        assert "production" in content.lower()


class TestKubernetesManifests:
    """Test Kubernetes manifest files."""

    def test_k8s_base_exists(self):
        """Kubernetes base directory should exist."""
        assert os.path.isdir("infrastructure/k8s/base")

    def test_k8s_kustomization_exists(self):
        """kustomization.yaml should exist."""
        assert os.path.exists("infrastructure/k8s/base/kustomization.yaml")

    def test_k8s_has_deployments(self):
        """Kubernetes should have deployment manifests."""
        backend_path = "infrastructure/k8s/base/backend-deployment.yaml"
        frontend_path = "infrastructure/k8s/base/frontend-deployment.yaml"

        assert os.path.exists(backend_path)
        assert os.path.exists(frontend_path)

    def test_k8s_has_services(self):
        """Kubernetes should have service manifests."""
        assert os.path.exists("infrastructure/k8s/base/backend-service.yaml")
        assert os.path.exists("infrastructure/k8s/base/frontend-service.yaml")

    def test_k8s_has_ingress(self):
        """Kubernetes should have ingress manifest."""
        assert os.path.exists("infrastructure/k8s/base/ingress.yaml")

    def test_k8s_overlays_exist(self):
        """Kubernetes overlays should exist."""
        assert os.path.isdir("infrastructure/k8s/overlays/staging")
        assert os.path.isdir("infrastructure/k8s/overlays/production")


class TestMonitoringConfiguration:
    """Test monitoring configuration."""

    def test_prometheus_config_exists(self):
        """Prometheus configuration should exist."""
        assert os.path.exists("infrastructure/monitoring/prometheus/prometheus.yml")

    def test_prometheus_alerts_exist(self):
        """Prometheus alerts should exist."""
        assert os.path.exists("infrastructure/monitoring/prometheus/alerts.yml")

    def test_grafana_provisioning_exists(self):
        """Grafana provisioning should exist."""
        assert os.path.isdir("infrastructure/monitoring/grafana/provisioning")

    def test_monitoring_compose_exists(self):
        """Monitoring docker-compose should exist."""
        assert os.path.exists("infrastructure/monitoring/docker-compose.monitoring.yml")


class TestTerraformConfiguration:
    """Test Terraform configuration."""

    def test_terraform_main_exists(self):
        """main.tf should exist."""
        assert os.path.exists("infrastructure/terraform/main.tf")

    def test_terraform_variables_exists(self):
        """variables.tf should exist."""
        assert os.path.exists("infrastructure/terraform/variables.tf")

    def test_terraform_modules_exist(self):
        """Terraform modules should exist."""
        modules = ["vpc", "ecs", "rds", "elasticache"]
        for module in modules:
            path = f"infrastructure/terraform/modules/{module}"
            assert os.path.isdir(path), f"Missing module: {module}"

    def test_terraform_environments_exist(self):
        """Terraform environment configs should exist."""
        environments = ["staging", "production"]
        for env in environments:
            path = f"infrastructure/terraform/environments/{env}/terraform.tfvars"
            assert os.path.exists(path), f"Missing environment: {env}"

    def test_terraform_main_has_required_providers(self):
        """main.tf should have required providers."""
        with open("infrastructure/terraform/main.tf") as f:
            content = f.read()

        assert "required_providers" in content
        assert "aws" in content


class TestSecurityConfiguration:
    """Test security configuration in infrastructure."""

    def test_no_hardcoded_secrets_in_compose(self):
        """docker-compose files should not have hardcoded production secrets."""
        files_to_check = ["docker-compose.yml", "docker-compose.prod.yml"]

        sensitive_patterns = [
            "sk_live_",  # Stripe live keys
            "sk-ant-",   # Anthropic keys
        ]

        for file_path in files_to_check:
            if os.path.exists(file_path):
                with open(file_path) as f:
                    content = f.read()
                for pattern in sensitive_patterns:
                    assert pattern not in content, f"Found sensitive pattern in {file_path}"

    def test_secrets_use_environment_variables(self):
        """Production compose should use environment variables for secrets."""
        with open("docker-compose.prod.yml") as f:
            content = f.read()

        # Should reference environment variables
        assert "${" in content or ":-" in content

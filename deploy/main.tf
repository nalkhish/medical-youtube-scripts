terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_ecs_cluster" "stream_cluster" {
  name = "stream-cluster"
}

module "worker_task" {
  source = "./modules/ecs_fargate_worker"

  cluster_arn = aws_ecs_cluster.stream_cluster.arn

  task_name          = "stream-worker-pipeline"
  image_url          = "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/stream-worker-pipeline:latest"
  cpu                = 256
  memory             = 1024
  command            = ["python", "worker_pipeline.py"]
  task_role_arn      = var.task_role_arn
  execution_role_arn = var.execution_role_arn
  log_region         = var.aws_region

  env_vars = {
    SUPABASE_SERVICE_ROLE_KEY = var.supabase_service_role_key
    SUPABASE_URL              = var.supabase_url
    TOGETHER_API_KEY          = var.together_api_key
  }
}

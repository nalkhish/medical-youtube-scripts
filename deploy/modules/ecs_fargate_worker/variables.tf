variable "task_name" {
  type        = string
  description = "The name of the ECS task and family."
}

variable "image_url" {
  type        = string
  description = "The URL of the Docker image to run."
}

variable "cpu" {
  type        = number
  description = "CPU units for the task."
  default     = 256
}

variable "memory" {
  type        = number
  description = "Memory for the task."
  default     = 1024
}

variable "command" {
  type        = list(string)
  description = "The command to run in the container."
  default     = []
}

variable "task_role_arn" {
  type        = string
  description = "ARN of the IAM role for the task."
}

variable "execution_role_arn" {
  type        = string
  description = "ARN of the IAM role for ECS task execution."
}

variable "log_region" {
  type        = string
  description = "AWS region for CloudWatch logs."
}

variable "env_vars" {
  type        = map(string)
  description = "Environment variables for the ECS task."
  
  validation {
    condition     = length(var.env_vars) > 0
    error_message = "env_vars must not be empty. Please provide the required environment variables to ensure the task does not fast-fail at runtime."
  }
}

variable "cluster_arn" {
  type        = string
  description = "The ARN of the ECS cluster to run the task on."
}

variable "schedule_expression" {
  type        = string
  description = "The EventBridge cron or rate expression for triggering the task."
  default     = "rate(5 minutes)"
}

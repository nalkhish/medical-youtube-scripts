variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "aws_account_id" {
  type        = string
  description = "AWS Account ID"
}

variable "supabase_service_role_key" {
  type        = string
  description = "Supabase Service Role API Key"
}

variable "supabase_url" {
  type        = string
  description = "Supabase project URL"
}

variable "together_api_key" {
  type        = string
  description = "Together AI API Key"
}

variable "task_role_arn" {
  type        = string
  description = "ARN of the IAM role for the task"
}

variable "execution_role_arn" {
  type        = string
  description = "ARN of the IAM role for ECS task execution"
}

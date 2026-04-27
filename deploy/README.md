# Terraform Deployment Guide

To deploy the ECS Fargate worker using Terraform, you need to provide a few required input variables. This includes API keys for Supabase/Together AI, your AWS account ID, and two IAM Roles for ECS.

## 1. Create the IAM Roles

ECS Fargate requires two distinct IAM roles:
1. **Execution Role (`execution_role_arn`)**: Used by the ECS agent to pull your Docker image from ECR and push logs to CloudWatch.
2. **Task Role (`task_role_arn`)**: Used by your Python script if it needs to call other AWS services (like S3 or DynamoDB). Since this script only talks to external APIs (Supabase/Together AI), it doesn't need special permissions, but the role itself must exist.

### Creating the Execution Role
1. Go to the **IAM Console** -> **Roles** -> **Create role**.
2. Select **AWS service** -> **Elastic Container Service** -> **Elastic Container Service Task** (Allows ECS tasks to call AWS services on your behalf).
3. Click **Next**.
4. Search for and attach the managed policy: `AmazonECSTaskExecutionRolePolicy`.
5. Name it something like `ecsTaskExecutionRole` and create it.
6. Copy its ARN (e.g., `arn:aws:iam::123456789012:role/ecsTaskExecutionRole`).

### Creating the Task Role
1. Create another role exactly like above (AWS Service -> ECS -> ECS Task).
2. Skip attaching any policies (since the script doesn't currently use AWS resources).
3. Name it `streamWorkerTaskRole` and create it.
4. Copy its ARN.

## 2. Setting the Variables

Terraform needs these values to run. You can provide them in several ways:

### The Stream-Safe Way: Using Environment Variables

To ensure you never accidentally leak secrets on stream, **do not use a `.tfvars` file**. Instead, configure Terraform by prefixing the variable names with `TF_VAR_` and adding them to your `~/.bashrc` (or a dedicated `~/.secrets` file that you source). 

This way, the keys exist securely in your environment and never in your repository files:

```bash
# Add these to your ~/.bashrc or ~/.zshrc (which you keep closed on stream)
export TF_VAR_aws_account_id="123456789012"
export TF_VAR_supabase_url="https://xyz.supabase.co"
export TF_VAR_supabase_service_role_key="eyJhb..."
export TF_VAR_together_api_key="..."
export TF_VAR_execution_role_arn="arn:aws:iam::123456789012:role/ecsTaskExecutionRole"
export TF_VAR_task_role_arn="arn:aws:iam::123456789012:role/streamWorkerTaskRole"
```

Once added, run `source ~/.bashrc`. You can then freely run:

```bash
terraform plan
```
without any files containing secrets living in your project directory.

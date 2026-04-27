resource "aws_cloudwatch_log_group" "task_log_group" {
  name              = var.task_name
  retention_in_days = 14
}

resource "aws_ecs_task_definition" "task" {
  family                   = var.task_name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  task_role_arn            = var.task_role_arn
  execution_role_arn       = var.execution_role_arn
  cpu                      = var.cpu
  memory                   = var.memory

  container_definitions = jsonencode([
    {
      name      = var.task_name
      image     = var.image_url
      essential = true
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-region"        = var.log_region
          "awslogs-group"         = var.task_name
          "awslogs-stream-prefix" = "ecs"
        }
      }
      environment = [
        for k, v in var.env_vars : {
          name  = k
          value = v
        }
      ]
      command = var.command
    }
  ])

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
}

# -------------------------------------------------------------
# EventBridge Scheduler Configuration
# -------------------------------------------------------------

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_iam_role" "eventbridge_role" {
  name = "${var.task_name}-eventbridge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "eventbridge_policy" {
  name = "${var.task_name}-eventbridge-policy"
  role = aws_iam_role.eventbridge_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = "ecs:RunTask"
        Effect   = "Allow"
        Resource = aws_ecs_task_definition.task.arn
        Condition = {
          ArnEquals = {
            "ecs:cluster" = var.cluster_arn
          }
        }
      },
      {
        Action = "iam:PassRole"
        Effect = "Allow"
        Resource = [
          var.execution_role_arn,
          var.task_role_arn
        ]
      }
    ]
  })
}

resource "aws_cloudwatch_event_rule" "schedule_rule" {
  name                = "${var.task_name}-schedule"
  description         = "Triggers ${var.task_name} on a schedule"
  schedule_expression = var.schedule_expression
}

resource "aws_cloudwatch_event_target" "ecs_target" {
  rule      = aws_cloudwatch_event_rule.schedule_rule.name
  target_id = "${var.task_name}-target"
  arn       = var.cluster_arn
  role_arn  = aws_iam_role.eventbridge_role.arn

  ecs_target {
    task_definition_arn = aws_ecs_task_definition.task.arn
    task_count          = 1
    launch_type         = "FARGATE"

    network_configuration {
      subnets          = data.aws_subnets.default.ids
      assign_public_ip = true
    }
  }
}

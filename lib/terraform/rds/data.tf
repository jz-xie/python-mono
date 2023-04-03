data "aws_rds_engine_version" "postgresql" {
  engine  = var.aws_rds_engine_name
  version = var.aws_rds_engine_version
}

data "aws_secretsmanager_secret" "rds_secret" {
  name = "${var.app}/${var.environment}"
}

data "aws_secretsmanager_secret_version" "rds_secret" {
  secret_id = data.aws_secretsmanager_secret.rds_secret.id
}

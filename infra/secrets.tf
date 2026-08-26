resource "random_password" "db_password" {
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>?:" // RDS Postgres rejects /, @, " and space in passwords
}

resource "aws_secretsmanager_secret" "database_url" {
  name                    = "${var.project_name}-database-url"
  recovery_window_in_days = 0 // to force immediate deletion of the secret when terraform destroy is run (for demo project); don't do this for real systems
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id = aws_secretsmanager_secret.database_url.id
  // full connection string, not just the raw password — the app reads DATABASE_URL as one value, and ECS's `secrets`
  // injection can only inject a whole env var from a secret, not interpolate a secret into the middle of a string
  secret_string = "postgresql+psycopg://${aws_db_instance.main.username}:${random_password.db_password.result}@${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}"
}

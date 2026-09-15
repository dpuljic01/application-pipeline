resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

resource "aws_db_instance" "main" {
  identifier        = "${var.project_name}-db"
  allocated_storage = 20
  engine            = "postgres"
  engine_version    = "16"
  instance_class    = "db.t4g.micro" // free tier eligible

  db_name  = "app_pipeline_db"
  username = "app_pipeline_user"
  password = random_password.db_password.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  // Both must be set at creation — can't be retrofitted onto an existing
  // instance without a destructive replace. Flagged as a gap back on Day 13
  // ("fine for a demo DB with no real data"), fixed now because this
  // instance is about to hold real signups' data, not just demo data.
  storage_encrypted       = true
  backup_retention_period = 7 // daily automated backups, kept 7 days

  skip_final_snapshot = true // terraform destroy won't take a backup snapshot first — acceptable since the plan is to pg_dump real data out manually before any teardown, not rely on this
  publicly_accessible = false
  deletion_protection = false

  tags = {
    Name = "${var.project_name}-db"
  }
}

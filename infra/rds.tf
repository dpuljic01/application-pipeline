resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

resource "aws_db_instance" "main" {
  identifier              = "${var.project_name}-db"
  allocated_storage       = 20
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = "db.t4g.micro" // free tier eligible
  
  db_name                 = "app_pipeline_db"
  username                = "app_pipeline_user"
  password                = var.db_password

  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.rds.id]

  skip_final_snapshot     = true // terraform destroy won't take a backup snapshot first — fine for a demo DB with no real data to protect, not fine for production
  publicly_accessible     = false
  deletion_protection     = false

  tags = {
    Name = "${var.project_name}-db"
  }
}

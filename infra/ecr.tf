resource "aws_ecr_repository" "main" {
  name                 = "${var.project_name}-backend"
  image_tag_mutability = "IMMUTABLE" // prevent overwriting existing image tags

  image_scanning_configuration {
    scan_on_push = true // automatically scan images for vulnerabilities when pushed
  }

  tags = {
    Name = "${var.project_name}-backend"
  }
}


resource "aws_ecr_lifecycle_policy" "main" {
  repository = aws_ecr_repository.main.name

  policy = <<EOF
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Expire untagged images older than 30 days",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 30
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 2,
      "description": "Keep only the last 10 tagged images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
EOF

  depends_on = [aws_ecr_repository.main]
}
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
}

resource "aws_lb_target_group" "main" {
  name        = "${var.project_name}-tg"
  port        = 8000 // must match the container's portMappings in ecs.tf and the Dockerfile's uvicorn --port
  protocol    = "HTTP"
  target_type = "ip" // Fargate tasks are tracked by ENI IP, not instance ID — same reason aws_security_group.ecs attaches to the task directly
  vpc_id      = aws_vpc.main.id

  health_check {
    enabled  = true
    path     = "/api/health"
    protocol = "HTTP"
  }
}

resource "aws_lb_listener" "main" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }
}

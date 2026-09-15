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

  // Once HTTPS exists, plain HTTP should redirect rather than serve —
  // a Vercel-hosted (HTTPS) frontend calling this over HTTP would get
  // silently blocked by the browser as mixed content anyway.
  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

/*
Concept — ACM + DNS validation: AWS issues a free TLS certificate once you
prove you control the domain, by adding a CNAME record it hands you. Since
DNS for this domain lives at hosttech (not Route53), Terraform can't create
that validation record itself the way it could with aws_route53_record —
it has to be added by hand.

Apply sequence (do NOT apply this whole file in one shot):
  1. terraform apply -target=aws_acm_certificate.api
  2. terraform output acm_validation_record   → add that CNAME at hosttech
  3. Wait for DNS to propagate (same kind of wait as the SES DKIM records)
  4. terraform apply (the rest) — aws_acm_certificate_validation blocks
     until AWS confirms the record, then the HTTPS listener can reference
     the now-issued certificate.
*/
resource "aws_acm_certificate" "api" {
  domain_name       = "api.${var.domain_name}"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

output "acm_validation_record" {
  description = "Add this CNAME at hosttech to validate the ACM certificate"
  value = {
    name  = tolist(aws_acm_certificate.api.domain_validation_options)[0].resource_record_name
    type  = tolist(aws_acm_certificate.api.domain_validation_options)[0].resource_record_type
    value = tolist(aws_acm_certificate.api.domain_validation_options)[0].resource_record_value
  }
}

resource "aws_acm_certificate_validation" "api" {
  certificate_arn = aws_acm_certificate.api.arn
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.api.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }
}

output "alb_dns_name" {
  description = "Point api.<domain_name> at this via a CNAME at hosttech"
  value       = aws_lb.main.dns_name
}

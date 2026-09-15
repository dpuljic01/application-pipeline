/*
Concept — VPC: your own isolated slice of AWS network, defined by a CIDR block (an IP address range, e.g. 10.0.0.0/16 = 65,536 addresses).
Every other networking resource — subnets, gateways, security groups — lives inside this one VPC.

Concept — subnets & AZs: a subnet is a slice of the VPC's IP range, pinned to one Availability Zone (AZ) - Physically separate data centers within the region
Spreading across 2 AZs means one data center going down doesn't take everything out. We need 2 AZs specifically because the ALB requires subnets in at least 2 of them.

Concept — public vs. private subnet: the distinction is purely about routing (which we set up in a later piece, not on the subnet itself): 
    - "public" subnet has a route to an Internet Gateway (so resources there can be reached from the internet — that's where the ALB goes)
    - "private" subnet doesn't (RDS and the ECS tasks go here — no direct inbound internet access, only outbound via NAT)
*/

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-${count.index + 1}"
  }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.project_name}-private-${count.index + 1}"
  }
}


resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-nat-eip"
  }
}

/*
Concept — NAT instance vs. NAT Gateway: same job (give private-subnet
resources outbound-only internet access), different bill. The managed NAT
Gateway is ~$32-35/mo flat, before any data even moves through it — the
single biggest line item in this whole stack for a personal, low-traffic
project. A NAT instance is just a regular EC2 box doing the same routing
job in software (IP forwarding + NAT/masquerade) — t4g.nano runs ~$3/mo.
The trade: you own patching/updates on it, and it's a single instance (no
built-in HA the way the managed NAT Gateway has) — a real tradeoff, not a
free lunch, but a reasonable one for a side project, not a production SLA.
*/
data "aws_ami" "nat_instance" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-arm64"]
  }

  filter {
    name   = "architecture"
    values = ["arm64"]
  }
}

resource "aws_security_group" "nat_instance" {
  name        = "${var.project_name}-nat-instance-sg"
  description = "Allow traffic from the private subnets to route out through the NAT instance"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Allow all traffic from inside the VPC - this instance is the private subnets route to the internet"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  egress {
    description = "Allow all outbound traffic to the internet"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-nat-instance-sg"
  }
}

resource "aws_instance" "nat" {
  ami                    = data.aws_ami.nat_instance.id
  instance_type          = "t4g.nano" // cheapest Graviton/ARM burstable type — this box just forwards packets, it doesn't need real compute
  subnet_id              = aws_subnet.public[0].id
  vpc_security_group_ids = [aws_security_group.nat_instance.id]

  // Required for NAT: by default AWS drops any traffic not addressed
  // to/from the instance itself. A NAT instance's whole job is forwarding
  // traffic for *other* hosts (the private subnets), so that check has to
  // be disabled — this is the one setting a NAT Gateway doesn't require
  // you to know about, since AWS manages it internally there.
  source_dest_check = false

  user_data = <<-EOF
    #!/bin/bash
    set -e
    sysctl -w net.ipv4.ip_forward=1
    sed -i '/net.ipv4.ip_forward/d' /etc/sysctl.conf
    echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
    # AL2023 ships nftables by default but keeps the iptables-nft
    # compatibility shim, so plain iptables commands still work.
    iptables -t nat -A POSTROUTING ! -o lo -j MASQUERADE
    iptables-save > /etc/sysconfig/iptables 2>/dev/null || true
  EOF

  tags = {
    Name = "${var.project_name}-nat-instance"
  }
}

resource "aws_eip_association" "nat" {
  instance_id   = aws_instance.nat.id
  allocation_id = aws_eip.nat.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block           = "0.0.0.0/0"
    network_interface_id = aws_instance.nat.primary_network_interface_id
  }

  tags = {
    Name = "${var.project_name}-private-rt"
  }
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "Allow HTTP and HTTPS traffic to ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Allow HTTP traffic"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow HTTPS traffic"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-alb-sg"
  }
}

resource "aws_security_group" "ecs" {
  name        = "${var.project_name}-ecs-sg"
  description = "Allow traffic from ALB to ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Allow traffic from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ecs-sg"
  }
}

resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg"
  description = "Allow inbound Postgres traffic from ECS tasks only to RDS"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Allow traffic from ECS tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-rds-sg"
  }
}
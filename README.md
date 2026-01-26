# Application Pipeline

**Application Pipeline** is a lightweight, CRM‑style web application that turns a chaotic job search into a **clear, measurable pipeline**.

It is designed both as:

* a **real tool** you can use daily, and
* an **interview‑ready portfolio project** demonstrating clean architecture, AWS, and modern backend practices.

---

## Problem

Most job searches fail due to:

* inconsistent applications
* forgotten follow‑ups
* lost documents and links
* zero feedback loops (no idea what works)

Spreadsheets and Notion break down as volume increases.

**Application Pipeline** fixes this by treating a job search like a real sales pipeline.

---

## Solution

A simple, focused system to:

* track applications and outreach
* enforce clear stages and transitions
* centralize documents and notes
* enable reminders and follow‑ups
* surface patterns over time

Single‑user first. Designed for multi‑user later.

---

## Core Concepts

* Modular monolith (clean, scalable, interview‑friendly)
* Strong separation of concerns (API / Services / Domain / DB)
* AWS‑native authentication (Cognito)
* UUID‑based public identifiers
* Explicit dependency injection

See **`docs/application-pipeline-cheat-sheet.md`** for detailed architectural notes.

---

## 🏗️ Architecture Overview

```
frontend/        # Next.js (minimal auth + UI)
backend/
  api/           # FastAPI routers (HTTP only)
  services/      # Business logic
  domain/        # Core models & rules (framework‑free)
  db/            # SQLAlchemy models & repositories
  integrations/  # AWS / external services
  core/          # config, logging, shared utilities
infra/           # Terraform / IaC (later)
docs/            # Architecture & design notes
```

**Why a modular monolith?**

* Faster iteration than microservices
* Easier testing
* Clear mental model
* Can be split later if needed

---

## 🔐 Authentication

* AWS Cognito User Pool
* OAuth2 Authorization Code Flow
* JWT verification on backend
* `/me` endpoint to map Cognito users → internal users

Backend **never** trusts frontend claims.

---

## 🧪 Tech Stack

### Backend

* Python 3.11+
* FastAPI
* SQLAlchemy
* PostgreSQL
* AWS Cognito
* Docker

### Frontend (planned)

* Next.js
* TypeScript
* shadcn/ui

### Infrastructure (planned)

* AWS ECS (Fargate)
* RDS PostgreSQL
* S3
* EventBridge

---

## Getting Started (Local)

### Backend

```bash
cd backend
docker compose up -d
```

### Frontend (planned)

```bash
cd frontend
npm install
npm run dev
```

Environment variables are required for Cognito and DB access.

---

## Design Principles

* Explicit > implicit
* Boring tech > clever abstractions
* Business logic isolated from frameworks
* Every layer has one responsibility

If a piece of code is hard to explain, it’s probably in the wrong layer.

---

## Documentation

* `docs/application-pipeline-cheat-sheet.md` – core concepts & mental models
* More docs will be added as features grow

---

## Why This Project Matters

This project is intentionally designed to demonstrate:

* real‑world backend structure
* AWS authentication flows
* clean separation of concerns
* production‑grade thinking without over‑engineering

It reflects how modern backend systems are built in Swiss / EU companies.

---

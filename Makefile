BACKEND_DIR := backend
FRONTEND_DIR := frontend
VENV         := $(BACKEND_DIR)/.venv
PYTHON       := $(VENV)/bin/python
PIP          := $(VENV)/bin/pip
UVICORN      := $(VENV)/bin/uvicorn

.PHONY: install dev backend frontend migrate

install: ## Install all dependencies
	@echo "==> Installing backend dependencies"
	python3.13 -m venv $(VENV)
	$(PIP) install --upgrade pip -q
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt -q
	@echo "==> Installing frontend dependencies"
	cd $(FRONTEND_DIR) && npm install
	@echo "==> All dependencies installed"

migrate: ## Run Alembic migrations
	cd $(BACKEND_DIR) && ../$(VENV)/bin/alembic upgrade head

dev: migrate ## Start backend + frontend concurrently
	@echo "==> Starting AllocNCE (backend :8000 + frontend :5173)"
	@trap 'kill 0' INT; \
	(cd $(BACKEND_DIR) && $(UVICORN) main:app --reload --port 8000) & \
	(cd $(FRONTEND_DIR) && npm run dev) & \
	wait

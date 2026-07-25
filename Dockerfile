FROM python:3.13-slim

WORKDIR /app

# System deps for pdfplumber (poppler) and python-docx
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY backend/ ./

# Persistent volume mount point
RUN mkdir -p /app/data/uploads

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Les migrations doivent tourner au démarrage : main.py ne fait plus de
# create_all() (Alembic est seul maître du schéma), donc sans cette étape un
# conteneur neuf démarrerait sur un volume vide, sans aucune table.
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]

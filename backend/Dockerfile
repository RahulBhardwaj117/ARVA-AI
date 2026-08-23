FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend

WORKDIR /app

COPY pyproject.toml ./
RUN python -c "import subprocess, sys, tomllib; dependencies = tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']; subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--no-cache-dir', *dependencies])"

COPY backend ./backend
COPY scripts ./scripts
RUN pip install --no-cache-dir --no-deps .

EXPOSE 8000

CMD ["sh", "-c", "alembic -c backend/alembic.ini upgrade head && python scripts/seed_database.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

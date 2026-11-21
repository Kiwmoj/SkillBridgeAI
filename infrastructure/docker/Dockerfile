FROM python:3.12-slim
WORKDIR /app
COPY requirements-backend.txt .
RUN pip install --no-cache-dir -r requirements-backend.txt
COPY apps/__init__.py apps/__init__.py
COPY apps/backend apps/backend
COPY packages packages
COPY alembic.ini .
RUN useradd --system --create-home skillbridge \
    && mkdir /app/uploads \
    && chown skillbridge:skillbridge /app/uploads
USER skillbridge
EXPOSE 8000
CMD ["sh", "-c", "python -m alembic upgrade head && exec python -m uvicorn apps.backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

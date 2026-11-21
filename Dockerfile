FROM python:3.11-slim
WORKDIR /app
COPY requirements-backend.txt .
RUN pip install --no-cache-dir -r requirements-backend.txt
COPY backend backend
COPY alembic alembic
COPY alembic.ini .
RUN useradd --system --create-home skillbridge \
    && mkdir /app/uploads \
    && chown skillbridge:skillbridge /app/uploads
USER skillbridge
EXPOSE 8000
CMD ["sh", "-c", "python -m alembic upgrade head && exec python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

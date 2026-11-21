FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY pyproject.toml ./
COPY src/ ./src/
COPY alembic.ini ./
COPY alembic/ ./alembic/
RUN pip install --no-cache-dir '.[postgres]'
RUN useradd -u 10001 -m airr && chown -R airr:airr /app
USER airr
EXPOSE 8000
CMD ["uvicorn", "airr.asgi:app", "--host", "0.0.0.0", "--port", "8000"]

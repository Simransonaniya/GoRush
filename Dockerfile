<<<<<<< HEAD
FROM python:3.12-slim AS base
=======
FROM python:3.12-slim
>>>>>>> 443cf3b4165506c1ab3de92f7a0272091d790bfd

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
<<<<<<< HEAD
    gcc libpq-dev curl \
=======
    gcc libpq-dev \
>>>>>>> 443cf3b4165506c1ab3de92f7a0272091d790bfd
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

<<<<<<< HEAD
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

=======
EXPOSE 8000

>>>>>>> 443cf3b4165506c1ab3de92f7a0272091d790bfd
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

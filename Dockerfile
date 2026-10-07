FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn
COPY app.py .
ENV PORT=5000
EXPOSE 5000
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 --timeout 180 app:app"]

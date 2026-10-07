FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN addgroup --system app && adduser --system --ingroup app app
COPY --chown=app:app app.py .
USER app
ENV PORT=5000
EXPOSE 5000
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 --timeout 180 app:app"]

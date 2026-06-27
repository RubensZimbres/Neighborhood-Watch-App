FROM python:3.10-slim

WORKDIR /app

# Install dependencies first (Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Streamlit configuration for Cloud Run
ENV PORT=8080
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", \
  "--server.port=8080", \
  "--server.address=0.0.0.0", \
  "--server.headless=true", \
  "--browser.gatherUsageStats=false", \
  "--server.fileWatcherType=none"]

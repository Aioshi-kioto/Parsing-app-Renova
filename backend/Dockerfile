FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (required for some Python packages and Playwright)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (required for scrapers)
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Command to run the application will be overriden in docker-compose
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

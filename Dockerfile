FROM node:20.9.0-alpine3.18 AS builder
WORKDIR /app
COPY package*.json ./
#RUN npm ci
COPY . .
#RUN npm run build


FROM python:3.11.6-slim-bullseye

WORKDIR /app

# System dependencies, certificates, and ODBC driver
# Install curl and gnupg to add MS repository keys
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    dnsutils \
    openssl \
    gnupg2 \
    && rm -rf /var/lib/apt/lists/*

# Add Microsoft package repository for ODBC driver
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list

# Update and install MS ODBC driver 18 and unixodbc-dev
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
    msodbcsql18 \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Now install your Python dependencies.
# pyodbc is often used to connect to SQL Server via ODBC.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir open-interpreter==0.4.3 
    
RUN pip install diskcache==5.6.3

COPY --from=builder /app/backend ./backend
#COPY --from=builder /app/dist ./backend/static

# Any other steps remain unchanged
# Replace html.py after packages are installed
COPY html1.py /usr/local/lib/python3.11/site-packages/interpreter/core/computer/terminal/languages/html.py

# DNS and other steps as previously
RUN mkdir -p /etc/docker && \
    echo '{"dns": ["8.8.8.8", "8.8.4.4"]}' > /etc/docker/daemon.json

ENV NODE_ENV=production \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    MSSQL_URL='Driver={ODBC Driver 18 for SQL Server};Server=tcp:ems-sql-db.database.windows.net,1433;Database=GEN_AI_NEW;Uid=sqladminuser;Pwd=Password@123a;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'

RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers", "--forwarded-allow-ips", "*"]

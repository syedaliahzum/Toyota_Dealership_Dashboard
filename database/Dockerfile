# Database initialization Docker image
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    mysql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy database scripts and schema
COPY . .

# Create a startup script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "Waiting for MySQL to be ready..."\n\
until mysqladmin ping -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" --silent; do\n\
  echo "MySQL is unavailable - sleeping"\n\
  sleep 1\n\
done\n\
\n\
echo "MySQL is up - executing initialization scripts"\n\
\n\
# Run schema\n\
mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < schema.sql\n\
\n\
echo "Database initialization completed successfully"\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]

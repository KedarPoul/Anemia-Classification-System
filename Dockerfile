# -----------------------------
# Use a stable Python base image
# -----------------------------
FROM python:3.11-slim

# Create a non-root user for security
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Set the working directory
WORKDIR /app

# -----------------------------
# Install system dependencies
# -----------------------------
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 build-essential gcc g++ \
 && rm -rf /var/lib/apt/lists/*
USER user

# -----------------------------
# Copy requirements and install dependencies
# -----------------------------
COPY --chown=user requirements.txt ./
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# -----------------------------
# Copy application source code
# -----------------------------
COPY --chown=user . .

# -----------------------------
# Expose port and run app
# -----------------------------
EXPOSE 8080

# Use Railway's dynamic port ($PORT)
CMD gunicorn --bind 0.0.0.0:$PORT app:app

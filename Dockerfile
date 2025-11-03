# -----------------------------
# Force a stable, supported Python version
# -----------------------------
FROM python:3.11-slim

# Create a non-root user
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Set work directory
WORKDIR /app

# -----------------------------
# Install system dependencies
# -----------------------------
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 build-essential \
 && rm -rf /var/lib/apt/lists/*
USER user

# -----------------------------
# Copy requirements and install
# -----------------------------
COPY --chown=user requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# -----------------------------
# Copy app source
# -----------------------------
COPY --chown=user . .

# -----------------------------
# Expose port and launch
# -----------------------------
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]

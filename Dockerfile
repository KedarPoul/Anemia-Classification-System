# Use official lightweight Python 3.10 base image
FROM python:3.10-slim

# Create a non-root user
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# ✅ Install system dependencies (fixes LightGBM/libgomp and wheel builds)
USER root
RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*
USER user

# Copy requirements and install Python dependencies
COPY --chown=user requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY --chown=user . /app

# Expose app port
EXPOSE 7860

# Run Flask app with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app"]

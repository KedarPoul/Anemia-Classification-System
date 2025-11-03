# Use official lightweight Python base image
FROM python:3.9-slim

# Create a non-root user
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# ✅ Install system dependencies (fixes libgomp.so.1 error)
USER root
RUN apt-get update && apt-get install -y libgomp1 && rm -rf /var/lib/apt/lists/*
USER user

# Copy requirements and install Python dependencies
COPY --chown=user requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app source
COPY --chown=user . /app

# Expose port
EXPOSE 7860

# Run Flask app
CMD ["python", "app.py"]

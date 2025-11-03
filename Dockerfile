# Use Python 3.10 slim image for compatibility
FROM python:3.10-slim

# Create non-root user
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Install essential system libs for numpy/scikit-learn/lightgbm
USER root
RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*
USER user

# Copy requirements and install
COPY --chown=user requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY --chown=user . /app

# Expose app port
EXPOSE 7860

# Run app with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app"]

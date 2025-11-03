# Use an official lightweight Python image
FROM python:3.9-slim

# Create a non-root user (required by Hugging Face)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

# Copy and install dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY --chown=user . .

# Expose the port Hugging Face expects
EXPOSE 7860

# Run the Flask app
CMD ["python", "app.py"]

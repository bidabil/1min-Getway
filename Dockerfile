# Use a slim version of Python 3.10 for a small and secure image
FROM python:3.10-slim

# Prevent Python from writing .pyc files and ensure logs are sent straight to terminal
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
# build-essential is required for compiling some heavy-duty tokenizers (tiktoken, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Leverage Docker cache: install requirements before copying the source code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Create the logs directory and set permissions
# This ensures the container can write logs even when mounted as a volume
RUN mkdir -p logs && chmod 777 logs

# Expose the internal port used by the Flask application
EXPOSE 5001

# Run the application
# We use python main.py as the entry point
CMD ["python", "main.py"]
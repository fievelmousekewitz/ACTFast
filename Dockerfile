
FROM python:3.8.12-slim-bullseye
LABEL authors="jeffj"

# Set the working directory to /app

COPY requirements.txt .
# Copy the current directory contents into the container at /app
COPY . /app


WORKDIR /app
# Install dependencies for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*


# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Define the command to run the application
CMD ["uvicorn", "app.main:ACTFast", "--host", "0.0.0.0", "--port", "8080"]

HEALTHCHECK --interval=60s --timeout=30s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

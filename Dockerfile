FROM python:slim

WORKDIR /app

# Install requests library
RUN pip install --no-cache-dir requests

# Copy server.py from the current directory
COPY server.py .

# Set server.py as the entrypoint
ENTRYPOINT ["python", "server.py"]

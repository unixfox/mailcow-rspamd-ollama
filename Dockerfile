FROM python:slim

WORKDIR /app

# Copy requirements files
COPY requirements.txt .

# Install production dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy server.py from the current directory
COPY server.py .

# Set server.py as the entrypoint
ENTRYPOINT ["python", "server.py"]

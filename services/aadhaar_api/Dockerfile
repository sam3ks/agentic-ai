FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install uv (ultrafast pip replacement)
RUN pip install uv

# Use uv to install dependencies
COPY requirements.txt .
RUN uv pip install --no-cache --system -r requirements.txt

# Copy application files
COPY main.py .
COPY app ./app
COPY aadhaar_details.db .

# Start FastAPI server with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5002"]

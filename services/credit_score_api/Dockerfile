FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install uv (pip replacement)
RUN pip install uv

# Install dependencies using uv
COPY requirements.txt .
RUN uv pip install --no-cache --system -r requirements.txt

# Copy app code and database
COPY main.py .
COPY app ./app
COPY credit_scores.db .

# Run the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5001"]

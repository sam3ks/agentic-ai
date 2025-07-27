FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --default-timeout=300 --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5002

CMD ["python", "scripts/aadhaar_details_api.py"]

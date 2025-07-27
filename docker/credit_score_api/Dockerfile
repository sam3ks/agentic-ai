FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --default-timeout=300 --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5001

CMD ["python", "scripts/credit_score_api.py"]

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --default-timeout=300 --no-cache-dir -r requirements.txt

COPY . .

VOLUME ["/app/escalation_data"]

CMD ["python", "human_operator_dashboard.py"]

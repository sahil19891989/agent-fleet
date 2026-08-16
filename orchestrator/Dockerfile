FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
ENV BUS_BACKEND=pubsub
ENV CHAIN_BACKEND=firestore
EXPOSE 8080

CMD ["python", "orchestrator/server.py"]

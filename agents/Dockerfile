FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

# WORKER_AGENT_MODULE and WORKER_AGENT_CLASS are set per-service at deploy
# time (see deploy.sh), so this single Dockerfile builds all three workers.
CMD ["python", "agents/server.py"]

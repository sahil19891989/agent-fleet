FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
ENV BUS_BACKEND=cloudrun
ENV CHAIN_BACKEND=firestore
ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# Run as a module (not a script path) so /app stays on sys.path and
# `from orchestrator.orchestrator import ...` resolves correctly.
CMD ["python", "-m", "orchestrator.server"]

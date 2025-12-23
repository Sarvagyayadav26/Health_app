
# # Force rebuild on every deploy
# ARG CACHEBUST=2

# FROM python:3.11-slim

# WORKDIR /app

# RUN apt-get update && apt-get install -y \
#     build-essential \
#     && rm -rf /var/lib/apt/lists/*

# # Copy requirements with cache-bust
# ARG CACHEBUST
# COPY requirements1.txt .

# RUN pip install --upgrade pip

# # Install ALL Python deps (Groq + httpx pinned inside requirements)
# RUN pip install --no-cache-dir -r requirements1.txt

# # Copy project files
# ARG CACHEBUST
# COPY . .

# RUN mkdir -p data/docs

# EXPOSE 5001

# ENV PYTHONUNBUFFERED=1
# ENV PYTHONPATH=/app

# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD python -c "import requests; requests.get('http://localhost:5001/health')" || exit 1

# CMD ["sh", "-c", "uvicorn src.api.android_server:app --host 0.0.0.0 --port ${PORT}"]

# new dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements1.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements1.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 10000

# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#   CMD python -c "import requests; requests.get('http://localhost:10000/healthz')"


# CMD ["uvicorn","src.api.s:app","--host","0.0.0.0","--port","$PORT","--log-level","info","--access-log"]

CMD sh -c "uvicorn src.api.s:app --host 0.0.0.0 --port $PORT --log-level info --access-log --proxy-headers"





    
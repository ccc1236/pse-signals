FROM python:3.12-slim

# git needed for tvdatafeed install from GitHub
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .
COPY dashboard.html .

# Data directories (mount as volume for persistence)
RUN mkdir -p data/4h

EXPOSE 8050

# Default: run dashboard
CMD ["python", "dashboard.py"]

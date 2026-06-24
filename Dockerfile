FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get purge -y git && apt-get autoremove -y

COPY . .

EXPOSE 5000

CMD ["python", "index.py"]

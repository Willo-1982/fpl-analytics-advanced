
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends     build-essential libxml2-dev libxslt1-dev libjpeg62-turbo-dev zlib1g-dev  && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY pipeline ./pipeline
COPY alerts ./alerts
COPY configs ./configs
COPY data ./data
EXPOSE 8501
CMD ["streamlit","run","app/app.py","--server.address=0.0.0.0","--server.port=8501"]

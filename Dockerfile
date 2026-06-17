FROM python:3.11-slim

RUN apt-get update && apt-get install -y nano && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY ./src /app/src

CMD ["python", "src/main.py", "No_Desconhecido"]
FROM python:3.12-slim

# Не писать .pyc, не буферизовать stdout (логи сразу видны)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Сначала зависимости — этот слой кэшируется, пока requirements.txt не меняется
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Затем код приложения
COPY . .

EXPOSE 5000

CMD ["python", "serve.py"]

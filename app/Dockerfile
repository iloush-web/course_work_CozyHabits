FROM python:3.12-slim

# Не писать .pyc, не буферизовать stdout (логи сразу видны)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# tzdata — чтобы работала переменная TZ (часовые пояса), иначе контейнер в UTC
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

# Пути в COPY считаются от build context (корень проекта), а не от этого файла.
# Сначала зависимости - слой кэшируется, пока requirements.txt не меняется
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Затем код приложения
COPY . .

EXPOSE 5000

CMD ["python", "serve.py"]

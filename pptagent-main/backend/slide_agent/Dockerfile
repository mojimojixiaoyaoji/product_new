FROM python:3.12

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 LC_ALL=C.UTF-8 LANG=C.UTF-8

WORKDIR /app

RUN apt-get update && apt-get install -y supervisor && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

COPY . .

RUN mkdir -p /app/logs

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 10011 8001

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

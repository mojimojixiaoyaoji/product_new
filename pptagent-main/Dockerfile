# 使用包含 Python 3.12 和 Node.js 24 的基础镜像
FROM nikolaik/python-nodejs:python3.12-nodejs24

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    NODE_ENV=development

# 安装系统依赖和 supervisord
RUN apt-get update && apt-get install -y \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . /app/

# 安装 Python 依赖
RUN pip install --no-cache-dir -r /app/backend/requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/

# 安装前端依赖
WORKDIR /app/frontend
RUN npm install

# 创建日志目录
RUN mkdir -p /app/logs /var/log/supervisor

# 复制 supervisord 配置
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 只暴露前端端口 80（内部服务端口不对外开放）
EXPOSE 80

# 设置工作目录回到根目录
WORKDIR /app

# 启动 supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

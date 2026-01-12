# 1. 指定 Python 基础镜像
FROM python:3.11-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
    && rm -rf /var/lib/apt/lists/*

# 4. 先复制依赖文件，利用缓存加速
COPY ../requirements.txt requirements.txt

# 5. 安装 Python 包
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 7. 复制其余代码
COPY ../. .

# 8. 启动命令：直接运行 main.py
CMD ["python", "main.py"]
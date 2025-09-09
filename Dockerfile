FROM docker.1ms.run/library/python:3.12-slim

WORKDIR /app

# 复制需要的文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用程序代码
COPY . .

# 启动应用
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

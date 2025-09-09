#!/bin/sh

# 确保脚本在错误时退出
set -e

echo "正在初始化Ollama服务..."

# 等待Ollama服务启动
echo "等待Ollama服务启动..."
until curl -s http://localhost:11434/api/version > /dev/null 2>&1; do
  echo "Ollama服务尚未就绪，等待..."
  sleep 2
done
echo "Ollama服务已启动"

# 拉取嵌入式模型
echo "拉取嵌入式模型：nomic-embed-text..."
ollama pull nomic-embed-text:latest

# 完成
echo "Ollama初始化完成！"

# 将控制权交给原始的serve命令
exec ollama serve

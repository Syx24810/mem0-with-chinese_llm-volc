#!/bin/bash

echo "=== 启动记忆聊天助手 ==="
echo "(支持模型选择和记忆模式切换功能)"

# 检查Docker是否已安装
if ! command -v docker &> /dev/null; then
    echo "错误: 未检测到Docker，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: 未检测到docker-compose，请安装docker-compose"
    exit 1
fi

echo "1. 构建并启动服务..."
docker-compose up -d --build

echo "2. 等待服务启动..."
sleep 15

echo "3. 检查服务健康状态..."
echo "  - Qdrant数据库状态"
curl -s http://localhost:6333 > /dev/null || echo "  连接失败: 请等待Qdrant启动完成"

echo "  - Ollama服务状态"
curl -s http://localhost:11434/api/tags > /dev/null || echo "  连接失败: 请等待Ollama启动完成"

echo "4. 服务初始化中..."
sleep 5

echo "=== 服务已启动 ==="
echo "Web界面: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo ""
echo "功能:"
echo "- 模型选择: 可在网页界面选择不同模型"
echo "- 记忆模式: 可开启/关闭记忆功能进行对比"
echo ""
echo "使用Ctrl+C停止查看日志"
echo ""

# 显示日志
docker-compose logs -f
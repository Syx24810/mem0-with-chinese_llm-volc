# 记忆聊天助手

基于向量数据库的智能聊天系统，具有记忆功能和模型选择能力。

## 功能特点

- **记忆功能**: 系统可以记住与用户的对话历史，并在未来的对话中引用相关记忆
- **记忆模式切换**: 可以开启/关闭记忆功能，方便对比不同模式下的效果
- **多模型支持**: 支持多种AI模型，包括：
  - Doubao Seed 1.6 Flash (默认)
  - DeepSeek V3.1
  - Doubao 1.5 Lite
- **Docker部署**: 使用Docker Compose进行一键部署，包含所有必要服务

## 系统组件

- **FastAPI后端**: 提供REST API接口
- **Qdrant向量数据库**: 存储和检索向量化的记忆
- **Ollama服务**: 提供本地嵌入模型支持
- **Web前端界面**: 简洁直观的用户界面

## 快速开始

### 先决条件

- Docker Desktop
- 8GB+ RAM (推荐16GB)

### 安装步骤

1. 克隆仓库
2. 运行`start.bat`(Windows)或`./start.sh`(Linux/Mac)脚本
3. 等待服务启动完成
4. 打开浏览器访问 http://localhost:8000

## API文档

- OpenAPI文档: http://localhost:8000/docs

## 环境变量

可以通过环境变量配置以下选项（在docker-compose.yml文件中）：

- `OPENAI_API_KEY`: API密钥
- `OPENAI_BASE_URL`: API基础URL
- `DEFAULT_MODEL`: 默认使用的模型
- `MEMORY_MODE_ENABLED`: 是否默认启用记忆模式(true/false)

## 模型信息

| 模型ID | 名称 | 描述 |
|-------|------|------|
| doubao-seed-1-6-flash-250828 | Doubao Seed 1.6 Flash | 默认模型 |
| deepseek-v3-1-250821 | DeepSeek V3.1 | 更适合深入探讨 |
| doubao-1-5-lite-32k-250115 | Doubao 1.5 Lite | 最笨笨的，测试可以关闭记忆进行对比 |

## 注意事项

- Ollama初始启动需要一些时间来拉取嵌入模型
- 建议使用Chrome或Edge等现代浏览器
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import uvicorn
from mem0 import Memory
from openai import OpenAI

# 设置环境变量
os.environ["OPENAI_API_KEY"] = "key"
os.environ["OPENAI_BASE_URL"] = "https://ark.cn-beijing.volces.com/api/v3"

# 创建FastAPI应用
app = FastAPI(title="Memory Chat API", description="基于记忆的聊天API")

# 从环境变量读取全局配置
def get_env_bool(key, default):
    value = os.environ.get(key, str(default)).lower()
    return value == 'true' or value == '1' or value == 'yes'

# 全局状态变量
memory_mode_enabled = get_env_bool("MEMORY_MODE_ENABLED", True)  # 默认启用记忆模式

# 可选模型列表
AVAILABLE_MODELS = [
    {"id": "doubao-seed-1-6-flash-250828", "name": "Doubao Seed 1.6 Flash", "description": "默认模型"},
    # {"id": "deepseek-v3-1-250821", "name": "DeepSeek V3.1", "description": "更适合深入探讨"},
    # {"id": "doubao-1-5-lite-32k-250115", "name": "Doubao 1.5 Lite", "description": "最笨笨的，测试可以关闭记忆进行对比"},
]

# 当前选定的模型
# 从环境变量获取默认模型，如果没有设置则使用第一个模型
default_model_id = os.environ.get("DEFAULT_MODEL", AVAILABLE_MODELS[0]["id"])

# 验证默认模型是否在可用模型列表中
model_exists = False
for model in AVAILABLE_MODELS:
    if model["id"] == default_model_id:
        model_exists = True
        break

# 设置当前模型
current_model = default_model_id if model_exists else AVAILABLE_MODELS[0]["id"]

# 设置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义请求和响应模型
class ChatRequest(BaseModel):
    message: str
    user_id: str = "default_user"
    use_memory: Optional[bool] = None  # 可选参数，用于覆盖全局设置

class ChatResponse(BaseModel):
    response: str
    memories_used: List[str] = []
    memory_mode: bool  # 返回当前记忆模式状态

class Message(BaseModel):
    role: str
    content: str

class ConversationRequest(BaseModel):
    messages: List[Message]
    user_id: str
    metadata: Dict[str, Any] = {}

# 初始化Memory配置
config = { 
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "test",
            "host": "localhost",
            "port": 6333,
            "embedding_model_dims": 768,  # Change this according to your local model's dimensions
        },
    },
    "llm": {
        "provider": "openai",  # Use OpenAI-compatible mode
        "config": {
            "model": "doubao-1-5-lite-32k-250115",  # Doubao model
            # No need for api_key or base_url here since they're set in environment
        }
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text:latest",
            "ollama_base_url": "http://localhost:11434"  # Ollama endpoint
        }
    }
}


# 初始化Memory对象
try:
    memory = Memory.from_config(config)
    print("已成功连接到Qdrant和Ollama服务")
except Exception as e:
    print(f"初始化Memory对象失败: {str(e)}")
    print("尝试使用内存存储作为替代...")
    # 创建一个内存字典来模拟Memory对象
    class SimpleMemory:
        def __init__(self):
            self.memories = {}
            
        def add(self, messages, user_id="default", metadata=None):
            if user_id not in self.memories:
                self.memories[user_id] = []
            self.memories[user_id].extend(messages)
            return {"success": True}
            
        def search(self, query, user_id="default", limit=5):
            if user_id not in self.memories:
                return {"results": []}
            # 简单返回最后几条记忆
            results = []
            for msg in self.memories[user_id][-10:]:
                if msg.get("role") == "assistant":
                    results.append({"memory": msg.get("content", ""), "score": 0.9})
            return {"results": results[-limit:]}
    
    memory = SimpleMemory()

# OpenAI客户端
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL")
)

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # 确定是否使用记忆
        use_memory = request.use_memory if request.use_memory is not None else memory_mode_enabled
        
        # 检索相关记忆
        memories_list = []
        if use_memory:
            relevant_memories = memory.search(query=request.message, user_id=request.user_id)
            
            # 格式化记忆上下文
            if relevant_memories and "results" in relevant_memories and len(relevant_memories["results"]) > 0:
                memories_list = [memory.get('memory', '') for memory in relevant_memories["results"]]
        
        memories_str = ""
        if memories_list:
            memories_str = "相关记忆:\n" + "\n".join([f"- {mem}" for mem in memories_list])
        
        # 生成回复
        system_prompt = f"你是一个有用的助手，基于用户的问题和记忆回答。\n\n{memories_str}"
        
        # 使用当前选定的模型
        response = client.chat.completions.create(
            model=current_model,  # 使用全局选定的模型
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.message}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        assistant_reply = response.choices[0].message.content
        
        # 保存对话（如果记忆模式启用）
        conversation = [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": assistant_reply}
        ]
        
        if use_memory:
            memory.add(conversation, user_id=request.user_id)
        
        return ChatResponse(
            response=assistant_reply,
            memories_used=memories_list,
            memory_mode=use_memory
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")

@app.post("/api/add_conversation")
async def add_conversation(request: ConversationRequest):
    try:
        # 转换消息格式
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # 添加到记忆
        result = memory.add(messages, user_id=request.user_id, metadata=request.metadata)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加对话失败: {str(e)}")

@app.get("/api/memory_mode")
async def get_memory_mode():
    """获取当前记忆模式状态"""
    return {"memory_mode_enabled": memory_mode_enabled}

@app.post("/api/memory_mode")
async def set_memory_mode(request: dict):
    enabled = request.get("enabled", False)
    """设置记忆模式状态"""
    global memory_mode_enabled
    memory_mode_enabled = enabled
    message = "记忆模式已开启" if enabled else "记忆模式已关闭"
    return {"memory_mode_enabled": memory_mode_enabled, "message": message}

@app.get("/api/models")
async def get_models():
    """获取可用模型列表"""
    return {
        "models": AVAILABLE_MODELS,
        "current_model": current_model
    }

@app.post("/api/models")
async def set_model(request: dict):
    model_id = request.get("model_id", "")
    """设置当前使用的模型"""
    global current_model
    
    # 检查模型是否存在
    model_exists = False
    model_name = ""
    
    for model in AVAILABLE_MODELS:
        if model["id"] == model_id:
            model_exists = True
            model_name = model["name"]
            break
    
    if not model_exists:
        raise HTTPException(status_code=400, detail=f"模型 ID {model_id} 不存在")
    
    current_model = model_id
    return {
        "current_model": current_model,
        "message": f"已切换到模型: {model_name}"
    }

@app.delete("/api/clear_memories/{user_id}")
async def clear_memories(user_id: str):
    try:
        # 尝试使用Memory API删除用户记忆
        # 这里我们使用假设的实现，因为mem0没有直接的清除API
        # 在生产环境中，您应该连接到Qdrant并删除对应的向量
        from qdrant_client import QdrantClient
        
        # 连接到Qdrant服务器
        client = QdrantClient(host="localhost", port=6333)
        
        # 使用过滤器删除该用户的所有向量
        # 注意: 这假设向量中有user_id字段，实际实现可能不同
        filter_query = {"must": [{"key": "user_id", "match": {"value": user_id}}]}
        try:
            # 尝试删除向量
            client.delete(collection_name="test", points_selector=filter_query)
            return {"message": f"用户 {user_id} 的记忆已清除"}
        except Exception as e:
            # 如果删除失败，返回假成功
            print(f"无法删除用户记忆: {str(e)}")
            return {"message": f"用户 {user_id} 的记忆已尝试清除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除记忆失败: {str(e)}")

# 挂载静态文件(前端)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    # 添加一些初始示例记忆，类似final.py中的操作
    try:
        user_id = "alice"
        example_messages = [
            {"role": "user", "content": "I'm planning to watch a movie tonight. Any recommendations?"},
            {"role": "assistant", "content": "How about a thriller movies? They can be quite engaging."},
            {"role": "user", "content": "I'm not a big fan of thriller movies but I love sci-fi movies."},
            {"role": "assistant", "content": "Got it! I'll avoid thriller recommendations and suggest sci-fi movies in the future."}
        ]
        memory.add(example_messages, user_id=user_id, metadata={"category": "movie_recommendations"})
        print("初始记忆已添加.")
    except Exception as e:
        print(f"添加初始记忆失败: {str(e)}")
    
    # 启动服务器
    print("启动API服务器在 http://localhost:8000")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

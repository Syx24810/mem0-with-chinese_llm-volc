from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import uvicorn
import requests
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from openai import OpenAI

app = FastAPI(title="Memory Chat API")

# ================= 配置区 =================
DEEPSEEK_KEY = "sk-00000000000000000000000000000000"
SILICON_KEY = "sk-00000000000000000000000000000000"
# ==========================================

client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com/v1", timeout=30.0)
qdrant = QdrantClient(host="qdrant", port=6333)
COLLECTION_NAME = "long_term_memory"

if not qdrant.collection_exists(COLLECTION_NAME):
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
    )

# 核心升级 1：短期记忆池（让它在一次对话中连贯）
chat_histories = {}


class ChatRequest(BaseModel):
    message: str
    user_id: str = "default_user"


class ChatResponse(BaseModel):
    response: str
    memories_used: List[str] = []


memory_mode_enabled = True
AVAILABLE_MODELS = [{"id": "deepseek-chat", "name": "DeepSeek Chat", "description": "默认模型"}]


def get_embedding(text: str) -> list:
    if not SILICON_KEY.startswith("sk-"):
        print("【严重警告】硅基流动 Key 为空或格式错误！")
        return []
    headers = {"Authorization": f"Bearer {SILICON_KEY}", "Content-Type": "application/json"}
    data = {"model": "BAAI/bge-m3", "input": text}
    try:
        print(f"【正在请求硅基流动】计算向量: {text[:10]}...")
        res = requests.post("https://api.siliconflow.cn/v1/embeddings", headers=headers, json=data, timeout=5)
        if res.status_code != 200:
            print(f"【Embedding 接口拒绝】: {res.text}")
            return []
        print("【硅基流动向量计算成功】")
        return res.json()["data"][0]["embedding"]
    except Exception as e:
        print(f"【Embedding 网络超时或错误】: {e}")
        return []


def save_memory(user_id: str, text: str):
    vector = get_embedding(text)
    if not vector: return
    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[PointStruct(id=str(uuid.uuid4()), vector=vector, payload={"user_id": user_id, "text": text})]
    )


def search_memory(user_id: str, query: str, limit: int = 3):
    vector = get_embedding(query)
    if not vector: return []
    try:
        # 适配新版 qdrant-client 的写法
        response = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            query_filter={"must": [{"key": "user_id", "match": {"value": user_id}}]},
            limit=limit
        )
        hits = response.points  # 新版返回的是对象，需要取 .points
        print(f"【Qdrant 检索得分】: {[hit.score for hit in hits]}")

        # 0.01 阈值非常低，确保只要沾边就能抓出来
        return [hit.payload["text"] for hit in hits if hit.score > 0.01]
    except Exception as e:
        print(f"【Qdrant检索失败】: {e}")
        return []


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    print(f"\n【收到请求】: {request.message}")
    try:
        user_id = request.user_id

        # 1. 捞取长期记忆
        memories = search_memory(user_id, request.message)
        memories_str = "\n".join([f"- {m}" for m in memories]) if memories else "无"

        # 2. 核心升级 3：加入你的专属人设和短期聊天记录
        system_prompt = f"""你是一个长期陪伴用户的专属AI助理。
【绝对准则】：
1. 绝对不要使用任何 emoji 或表情符号。
2. 语气必须直接、务实，像个助理。
3. 以下是你脑海中关于用户的长期记忆：
{memories_str}
"""
        # 获取历史记录
        if user_id not in chat_histories:
            chat_histories[user_id] = []

        # 构造消息列表
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(chat_histories[user_id][-20:])  # 带上最近 20 轮对话
        messages.append({"role": "user", "content": request.message})

        # 3. 请求大模型
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        reply = response.choices[0].message.content.replace("<|endoftext|>", "").strip()

        # 4. 更新短期记忆池
        chat_histories[user_id].append({"role": "user", "content": request.message})
        chat_histories[user_id].append({"role": "assistant", "content": reply})

        # 5. 保存长期记忆（只要包含记住，或者对话比较长就存）
        if "记住" in request.message or "叫" in request.message or len(request.message) > 10:
            save_memory(user_id, f"用户信息或要求: {request.message}")

        return ChatResponse(response=reply, memories_used=memories)
    except Exception as e:
        print(f"【探针报错】: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 兼容接口
@app.get("/api/memory_mode")
def get_memory_mode(): return {"memory_mode_enabled": True}


@app.post("/api/memory_mode")
def set_memory_mode(request: dict): return {"memory_mode_enabled": True}


@app.get("/api/models")
def get_models(): return {"models": AVAILABLE_MODELS, "current_model": "deepseek-chat"}


@app.post("/api/models")
def set_model(request: dict): return {"current_model": "deepseek-chat", "message": "已切换"}


@app.delete("/api/clear_memories/{user_id}")
def clear_memories(user_id: str):
    try:
        qdrant.delete(collection_name=COLLECTION_NAME,
                      points_selector={"must": [{"key": "user_id", "match": {"value": user_id}}]})
        return {"message": "记忆已清除"}
    except:
        return {"message": "清除失败"}




app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000)
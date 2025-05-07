import json
import datetime
from fastapi import FastAPI, HTTPException , Request
from pydantic import BaseModel
from typing import List, Dict

from core.inferencer import Inferencer
import llm_tools.math
import llm_tools.eth

# 设置 API 密钥
API_KEY = "123"

# 初始化 Inferencer
print("Initializing Inferencer...")
tools = []
tools.extend(llm_tools.math.math_tools)
tools.extend(llm_tools.eth.eth_tools)

inferencer = Inferencer(
    model_config={"model_name": "Qwen/Qwen3-1.7B"},
    tools=tools,
    thinking=True
)
print("Inferencer initialized.")

# FastAPI 应用
app = FastAPI(
    title="Custom Inferencer API",
    description="Qwen3 + Tools for Open WebUI",
    version="1.0.0"
)

# 输入数据结构
class ChatInput(BaseModel):
    messages: List[Dict[str, str]]
    api_key: str

# 推理接口：同时兼容 2 个路径
@app.post("/infer")
@app.post("/infer/chat/completions")
async def infer_openai_compatible(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    print("🔥 OpenAI-style messages:", messages)

    if not messages:
        raise HTTPException(status_code=400, detail="Missing messages")

    if not any(msg["role"] == "system" for msg in messages):
        messages.insert(0, {
            "role": "system",
            "content": f"You are a helpful assistant with tools. {datetime.datetime.now()}"
        })

    response = inferencer.infer(messages)
    return {"choices": [{"message": response[-1]}]}

# 模型列表接口（无需密钥）
@app.get("/infer/models")
async def list_models():
    return {"models": ["Qwen/Qwen3-1.7B"]}

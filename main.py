import json
import datetime
from fastapi import FastAPI, HTTPException , Request
from pydantic import BaseModel
from typing import List, Dict
import re
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
    last_msg = response[-1]

    # 回溯本轮消息，找到最近一次 function_call
    function_call_info = ""
    for msg in reversed(response):
        if "function_call" in msg and msg["function_call"]:
            func_name = msg["function_call"].get("name", "")
            args = msg["function_call"].get("arguments", {})
            function_call_info = f"[This answer used Function Call: {func_name} Parameter: {json.dumps(args, ensure_ascii=False)}]"
            break

    # 提取思考和正式回答
    content = last_msg.get("content") or ""
    think_match = re.search(r"<think>(.*?)</think>", content, flags=re.DOTALL)
    thinking = think_match.group(1).strip() if think_match else ""
    # 去除 <think>...</think> 和 <|im_end|>
    answer = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    answer = answer.replace("<|im_end|>", "").strip()

    content = ""
    if function_call_info:
        content += function_call_info + "\n\n"
    if thinking:
        content += "💡Model thinking：\n" + thinking.strip() + "\n\n"
    if answer:
        content += "🤖Model answer:\n" + answer.strip()

    last_msg = {
        "role": "assistant",
        "content": content.strip()
    }
    return {"choices": [{"message": last_msg}]}

# 模型列表接口（无需密钥）
@app.get("/infer/models")
async def list_models():
    return {"models": ["Qwen/Qwen3-1.7B"]}

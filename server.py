#!/usr/bin/env python3
"""
openai-unlimited server
Run: python server.py
URL: http://localhost:12434/v1
Key: openai-unlimited-local
"""

import sys, subprocess, json, uuid, time

for pkg in ["fastapi", "uvicorn[standard]", "httpx"]:
    try:
        __import__(pkg.split("[")[0])
    except ImportError:
        print(f"Installing {pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, httpx

HOST    = "0.0.0.0"
PORT    = 12434
API_KEY = "openai-unlimited-local"

UPSTREAM   = "https://android.chat.openai.com/backend-anon/conversation"
MODELS_URL = "https://android.chat.openai.com/backend-anon/models"

DEVICE_ID = str(uuid.uuid4())

HEADERS = {
    "accept":        "text/event-stream",
    "content-type":  "application/json",
    "oai-device-id": DEVICE_ID,
    "oai-language":  "en-US",
    "origin":        "https://chatgpt.com",
    "referer":       "https://chatgpt.com/",
    "user-agent":    "ChatGPT/1.2026.069 (Android 14; Mobile; rv:0)",
}

_models_cache = {"data": None, "ts": 0}

app = FastAPI(title="openai-unlimited", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def check_auth(request: Request):
    auth = request.headers.get("authorization", "")
    token = auth.split(" ", 1)[1].strip() if auth.startswith("Bearer ") else ""
    if token != API_KEY:
        raise HTTPException(401, detail=f"Use: Authorization: Bearer {API_KEY}")


async def get_models() -> list:
    now = time.time()
    if _models_cache["data"] and now - _models_cache["ts"] < 60:
        return _models_cache["data"]
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(MODELS_URL, headers=HEADERS)
            if r.status_code == 200:
                models = r.json().get("models", [])
                _models_cache["data"] = models
                _models_cache["ts"] = now
                return models
    except Exception:
        pass
    return [
        {"slug": "auto"}, {"slug": "gpt-5"}, {"slug": "gpt-5-mini"},
        {"slug": "gpt-4o"}, {"slug": "gpt-4o-mini"}, {"slug": "o3"}, {"slug": "o4-mini"},
    ]


def build_upstream_body(messages: list, model: str) -> dict:
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
        tag = {"system": "[SYSTEM]", "assistant": "[ASSISTANT]"}.get(role, "[USER]")
        parts.append(f"{tag}\n{content}")
    return {
        "action": "next",
        "messages": [{
            "id": str(uuid.uuid4()),
            "author": {"role": "user"},
            "content": {"content_type": "text", "parts": ["\n\n".join(parts)]},
        }],
        "parent_message_id": str(uuid.uuid4()),
        "model": model,
        "history_and_training_disabled": True,
    }


async def do_stream(messages, model, req_id, created):
    upstream = build_upstream_body(messages, model)
    prev = ""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0)) as client:
            async with client.stream("POST", UPSTREAM, headers=HEADERS, json=upstream) as resp:
                if resp.status_code not in (200, 201):
                    raw = await resp.aread()
                    yield f"data: {json.dumps({'error':{'message':f'Upstream {resp.status_code}: {raw.decode()[:200]}','type':'upstream_error'}})}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        break
                    try:
                        ev = json.loads(payload)
                    except Exception:
                        continue
                    msg  = ev.get("message") or {}
                    role = (msg.get("author") or {}).get("role", "")
                    if role != "assistant":
                        continue
                    pts = (msg.get("content") or {}).get("parts") or []
                    if not pts or not isinstance(pts[0], str):
                        continue
                    full  = pts[0]
                    delta = full[len(prev):]
                    prev  = full
                    if not delta:
                        continue
                    yield f"data: {json.dumps({'id':req_id,'object':'chat.completion.chunk','created':created,'model':model,'choices':[{'index':0,'delta':{'role':'assistant','content':delta},'finish_reason':None}]})}\n\n"

    except httpx.ConnectError:
        yield f"data: {json.dumps({'error':{'message':'Cannot reach upstream. Check internet.','type':'connection_error'}})}\n\n"
    except httpx.TimeoutException:
        yield f"data: {json.dumps({'error':{'message':'Upstream timed out.','type':'timeout'}})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error':{'message':str(e),'type':'server_error'}})}\n\n"

    yield f"data: {json.dumps({'id':req_id,'object':'chat.completion.chunk','created':created,'model':model,'choices':[{'index':0,'delta':{},'finish_reason':'stop'}]})}\n\n"
    yield "data: [DONE]\n\n"


@app.get("/")
async def root():
    return {"server": "openai-unlimited", "base_url": f"http://localhost:{PORT}/v1",
            "api_key": API_KEY, "docs": f"http://localhost:{PORT}/docs"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/v1/models")
async def list_models(request: Request):
    check_auth(request)
    models = await get_models()
    now = int(time.time())
    return {
        "object": "list",
        "data": [
            {"id": m.get("slug", "unknown"), "object": "model",
             "created": now, "owned_by": "openai-unlimited"}
            for m in models
        ],
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    check_auth(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    messages = body.get("messages")
    if not messages or not isinstance(messages, list):
        raise HTTPException(400, "'messages' is required")

    model     = body.get("model", "auto")
    streaming = bool(body.get("stream", False))
    req_id    = f"chatcmpl-{uuid.uuid4().hex}"
    created   = int(time.time())

    if streaming:
        return StreamingResponse(
            do_stream(messages, model, req_id, created),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache",
                     "X-Accel-Buffering": "no",
                     "Connection": "keep-alive"},
        )

    text = ""
    async for chunk in do_stream(messages, model, req_id, created):
        if not chunk.startswith("data: "):
            continue
        p = chunk[6:].strip()
        if p == "[DONE]":
            break
        try:
            d = json.loads(p)
            text += (d.get("choices") or [{}])[0].get("delta", {}).get("content", "") or ""
        except Exception:
            pass

    pt = sum(len(str(m.get("content", "")).split()) for m in messages)
    ct = len(text.split())
    return JSONResponse({
        "id": req_id, "object": "chat.completion", "created": created, "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct},
    })


if __name__ == "__main__":
    print(f"""
\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557
\u2551  openai-unlimited  \u2713  running                    \u2551
\u2560\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2563
\u2551  Base URL \u2192  http://localhost:{PORT}/v1         \u2551
\u2551  API Key  \u2192  {API_KEY}  \u2551
\u2551  Docs     \u2192  http://localhost:{PORT}/docs       \u2551
\u2560\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2563
\u2551  curl http://localhost:12434/health                \u2551
\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d
""")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")

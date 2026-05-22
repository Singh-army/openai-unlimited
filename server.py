#!/usr/bin/env python3
"""
openai-unlimited — Local OpenAI-compatible API Server
======================================================
Run  :  python server.py
URL  :  http://127.0.0.1:12434/v1
Key  :  openai-unlimited-local
Docs :  http://127.0.0.1:12434/docs
"""

import sys, subprocess

# ── Auto-install ───────────────────────────────────────────────────────────────────────────────
for pkg in ["fastapi", "uvicorn[standard]", "httpx"]:
    try:
        __import__(pkg.split("[")[0])
    except ImportError:
        print(f"📦 Installing {pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

import json, uuid, time, asyncio
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, httpx

# ── Constants ─────────────────────────────────────────────────────────────────────────────
HOST      = "127.0.0.1"
PORT      = 12434
API_KEY   = "openai-unlimited-local"

# Same endpoint the PowerShell script uses — Android mobile endpoint
UPSTREAM  = "https://android.chat.openai.com/backend-anon/conversation"
MODELS_URL = "https://android.chat.openai.com/backend-anon/models"

DEVICE_ID = str(uuid.uuid4())

HEADERS = {
    "accept":          "text/event-stream",
    "content-type":    "application/json",
    "oai-device-id":   DEVICE_ID,
    "oai-language":    "en-US",
    "origin":          "https://chatgpt.com",
    "referer":         "https://chatgpt.com/",
    # Android mobile user-agent — same as the PS1 script
    "user-agent":      "ChatGPT/1.2026.069 (Android 14; Mobile; rv:0)",
}

# ── App ─────────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="openai-unlimited",
    description="Local OpenAI-compatible API — no key, no paywall. Base URL: http://127.0.0.1:12434/v1 | API Key: openai-unlimited-local",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Cache for models ────────────────────────────────────────────────────────────────────────────
_models_cache: dict = {"data": None, "fetched_at": 0}

# ── Auth ───────────────────────────────────────────────────────────────────────────────────
def auth(request: Request):
    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(401, f"Missing auth. Use:  Authorization: Bearer {API_KEY}")
    if header.split(" ", 1)[1].strip() != API_KEY:
        raise HTTPException(401, f"Wrong API key. Use: {API_KEY}")

# ── Fetch real model list from upstream ────────────────────────────────────────────────
async def fetch_models() -> dict:
    now = time.time()
    if _models_cache["data"] and now - _models_cache["fetched_at"] < 60:
        return _models_cache["data"]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(MODELS_URL, headers=HEADERS)
            if r.status_code == 200:
                data = r.json()
                _models_cache["data"] = data
                _models_cache["fetched_at"] = now
                return data
    except Exception:
        pass
    # Fallback static list
    return {
        "models": [
            {"slug": "auto",        "title": "Auto"},
            {"slug": "gpt-5",       "title": "GPT-5"},
            {"slug": "gpt-5-mini",  "title": "GPT-5 Mini"},
            {"slug": "gpt-4o",      "title": "GPT-4o"},
            {"slug": "gpt-4o-mini", "title": "GPT-4o Mini"},
            {"slug": "o3",          "title": "o3"},
            {"slug": "o4-mini",     "title": "o4-mini"},
        ],
        "default_model_slug": "auto",
    }

# ── Build upstream conversation body ────────────────────────────────────────────────────
def build_body(messages: list, model: str, parent_id: Optional[str] = None) -> dict:
    # Merge all messages into a single prompt (same as PS1 Convert-MessagesToPrompt)
    lines = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
        if role == "system":
            lines.append(f"[SYSTEM]\n{content}")
        elif role == "user":
            lines.append(f"[USER]\n{content}")
        elif role == "assistant":
            lines.append(f"[ASSISTANT]\n{content}")

    prompt = "\n\n".join(lines)
    msg_id = str(uuid.uuid4())
    pid    = parent_id or str(uuid.uuid4())

    return {
        "action": "next",
        "messages": [{
            "id":      msg_id,
            "author":  {"role": "user"},
            "content": {"content_type": "text", "parts": [prompt]},
        }],
        "parent_message_id":            pid,
        "model":                        model,
        "history_and_training_disabled": True,
    }

# ── Routes ──────────────────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Info"])
async def root():
    return {
        "name":     "openai-unlimited",
        "version":  "1.0.0",
        "base_url": f"http://{HOST}:{PORT}/v1",
        "api_key":  API_KEY,
        "docs":     f"http://{HOST}:{PORT}/docs",
        "endpoints": ["/health", "/v1/models", "/v1/chat/completions"],
    }

@app.get("/health", tags=["Info"])
async def health():
    return {"status": "ok", "server": "openai-unlimited", "port": PORT}

@app.get("/v1/models", tags=["Models"])
async def list_models(request: Request):
    auth(request)
    raw   = await fetch_models()
    models = raw.get("models", [])
    now   = int(time.time())
    return {
        "object": "list",
        "data": [
            {
                "id":       m.get("slug", m.get("id", "unknown")),
                "object":   "model",
                "created":  now,
                "owned_by": "openai-unlimited",
            }
            for m in models
        ],
    }

@app.post("/v1/chat/completions", tags=["Chat"])
async def chat_completions(request: Request):
    auth(request)

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON body")

    messages = body.get("messages")
    if not messages or not isinstance(messages, list):
        raise HTTPException(400, "'messages' array is required")

    model      = body.get("model", "auto")
    do_stream  = bool(body.get("stream", False))
    cid        = f"chatcmpl-{uuid.uuid4().hex}"
    created    = int(time.time())
    upstream_b = build_body(messages, model)

    # ── Stream generator ──────────────────────────────────────────────────────────────────
    async def stream_gen():
        prev = ""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0)) as client:
                async with client.stream("POST", UPSTREAM, headers=HEADERS, json=upstream_b) as resp:
                    if resp.status_code not in (200, 201):
                        body_text = await resp.aread()
                        err = {"error": {"message": f"Upstream HTTP {resp.status_code}: {body_text.decode()[:300]}", "type": "upstream_error"}}
                        yield f"data: {json.dumps(err)}\n\n"
                        yield "data: [DONE]\n\n"
                        return

                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        payload = line[6:]
                        if payload.strip() == "[DONE]":
                            break
                        try:
                            ev = json.loads(payload)
                        except json.JSONDecodeError:
                            continue

                        # Parse same way as PS1 — message.content.parts[0]
                        msg   = ev.get("message") or {}
                        role  = (msg.get("author") or {}).get("role", "")
                        if role != "assistant":
                            continue
                        parts = (msg.get("content") or {}).get("parts") or []
                        if not parts or not isinstance(parts[0], str):
                            continue

                        full  = parts[0]
                        if full == prev:
                            continue
                        delta = full[len(prev):]
                        prev  = full

                        chunk = {
                            "id": cid, "object": "chat.completion.chunk",
                            "created": created, "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"role": "assistant", "content": delta},
                                "finish_reason": None,
                            }],
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"

        except httpx.ConnectError:
            err = {"error": {"message": "Cannot reach upstream — check your internet connection.", "type": "connection_error"}}
            yield f"data: {json.dumps(err)}\n\n"
        except httpx.TimeoutException:
            err = {"error": {"message": "Upstream timed out after 120s.", "type": "timeout_error"}}
            yield f"data: {json.dumps(err)}\n\n"
        except Exception as e:
            err = {"error": {"message": str(e), "type": "server_error"}}
            yield f"data: {json.dumps(err)}\n\n"

        # Final stop chunk
        yield f"data: {json.dumps({'id':cid,'object':'chat.completion.chunk','created':created,'model':model,'choices':[{'index':0,'delta':{},'finish_reason':'stop'}]})}\n\n"
        yield "data: [DONE]\n\n"

    if do_stream:
        return StreamingResponse(
            stream_gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
        )

    # Non-streaming: collect
    full_text = ""
    async for raw_chunk in stream_gen():
        if not raw_chunk.startswith("data: "):
            continue
        p = raw_chunk[6:].strip()
        if p == "[DONE]":
            break
        try:
            d = json.loads(p)
            delta_c = (d.get("choices") or [{}])[0].get("delta", {}).get("content", "")
            full_text += (delta_c or "")
        except Exception:
            continue

    pt = sum(len(str(m.get("content", "")).split()) for m in messages)
    ct = len(full_text.split())
    return JSONResponse({
        "id": cid, "object": "chat.completion", "created": created, "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": full_text}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct},
    })

# ── Main ────────────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════════════╗
║          openai-unlimited  v1.0.0   ✓ running            ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  Base URL →  http://{HOST}:{PORT}/v1               ║
║  API Key  →  {API_KEY}         ║
║  Docs     →  http://{HOST}:{PORT}/docs             ║
║                                                          ║
║  Quick test:                                             ║
║    curl http://127.0.0.1:12434/health                    ║
║                                                          ║
║  Press Ctrl+C to stop                                    ║
╚══════════════════════════════════════════════════════════╝
""")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")

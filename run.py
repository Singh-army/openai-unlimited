#!/usr/bin/env python3
"""
openai-unlimited  —  free GPT in your terminal + Cursor API
────────────────────────────────────────────────────────────
  python run.py             → terminal coding agent
  python run.py --server    → API server for Cursor / MCP
  python run.py --both      → agent + server together

Cursor settings:
  Base URL : http://localhost:12434/v1
  API Key  : openai-unlimited-local
"""

import sys, os, subprocess, json, uuid, time, re, threading, argparse, shutil, glob

# ── auto-install ──────────────────────────────────────────────────────────────
def _install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

for _pkg in ["httpx", "fastapi", "uvicorn[standard]"]:
    try:
        __import__(_pkg.split("[")[0])
    except ImportError:
        print(f"  installing {_pkg}…", flush=True)
        _install(_pkg)

import httpx

# ── upstream config ───────────────────────────────────────────────────────────
UPSTREAM   = "https://android.chat.openai.com/backend-anon/conversation"
MODELS_URL = "https://android.chat.openai.com/backend-anon/models"
DEVICE_ID  = str(uuid.uuid4())
UA_HEADERS = {
    "accept":        "text/event-stream",
    "content-type":  "application/json",
    "oai-device-id": DEVICE_ID,
    "oai-language":  "en-US",
    "origin":        "https://chatgpt.com",
    "referer":       "https://chatgpt.com/",
    "user-agent":    "ChatGPT/1.2026.069 (Android 14; Mobile; rv:0)",
}

# ── colours ───────────────────────────────────────────────────────────────────
C = {
    "reset":  "\033[0m",
    "bold":   "\033[1m",
    "dim":    "\033[2m",
    "green":  "\033[92m",
    "cyan":   "\033[96m",
    "yellow": "\033[93m",
    "red":    "\033[91m",
    "blue":   "\033[94m",
    "purple": "\033[95m",
}

def c(color, text): return f"{C[color]}{text}{C['reset']}"
def banner():
    print(c("cyan", """
  ╔══════════════════════════════════════════╗
  ║   openai-unlimited  ·  coding agent      ║
  ║   free GPT · file access · shell exec    ║
  ╚══════════════════════════════════════════╝"""))

# ── upstream streaming ────────────────────────────────────────────────────────
def _build_payload(messages, model="auto"):
    parts = []
    for m in messages:
        role    = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
        tag = {"system": "[SYSTEM]", "assistant": "[ASSISTANT]"}.get(role, "[USER]")
        parts.append(f"{tag}\n{content}")
    return {
        "action": "next",
        "messages": [{
            "id":      str(uuid.uuid4()),
            "author":  {"role": "user"},
            "content": {"content_type": "text", "parts": ["\n\n".join(parts)]},
        }],
        "parent_message_id":             str(uuid.uuid4()),
        "model":                         model,
        "history_and_training_disabled": True,
    }

def stream_reply(messages, model="auto", print_live=True):
    payload = _build_payload(messages, model)
    full    = ""
    try:
        with httpx.Client(timeout=httpx.Timeout(120, connect=15)) as client:
            with client.stream("POST", UPSTREAM, headers=UA_HEADERS, json=payload) as resp:
                if resp.status_code not in (200, 201):
                    err = resp.read().decode()[:300]
                    print(c("red", f"\n  upstream error {resp.status_code}: {err}"))
                    return ""
                prev = ""
                for line in resp.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:]
                    if raw.strip() == "[DONE]":
                        break
                    try:
                        ev   = json.loads(raw)
                        msg  = ev.get("message") or {}
                        role = (msg.get("author") or {}).get("role", "")
                        if role != "assistant":
                            continue
                        pts  = (msg.get("content") or {}).get("parts") or []
                        if not pts or not isinstance(pts[0], str):
                            continue
                        text  = pts[0]
                        delta = text[len(prev):]
                        prev  = text
                        full  = text
                        if delta and print_live:
                            print(c("green", delta), end="", flush=True)
                    except Exception:
                        pass
    except httpx.ConnectError:
        print(c("red", "\n  cannot reach upstream — check internet"))
    except httpx.TimeoutException:
        print(c("red", "\n  request timed out"))
    except Exception as e:
        print(c("red", f"\n  error: {e}"))
    if print_live:
        print()
    return full

# ── file tools ────────────────────────────────────────────────────────────────
MAX_FILE_BYTES = 64_000

def read_file(path):
    try:
        path = os.path.expanduser(path)
        size = os.path.getsize(path)
        if size > MAX_FILE_BYTES:
            return f"[file too large: {size} bytes — showing first 60000 chars]\n" + open(path, errors="replace").read(60000)
        return open(path, errors="replace").read()
    except Exception as e:
        return f"[error reading {path}: {e}]"

def write_file(path, content):
    try:
        path = os.path.expanduser(path)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True, f"wrote {len(content)} chars to {path}"
    except Exception as e:
        return False, str(e)

def list_files(pattern="**/*", base="."):
    try:
        base  = os.path.expanduser(base)
        paths = glob.glob(os.path.join(base, pattern), recursive=True)
        files = [p for p in paths if os.path.isfile(p)]
        result = []
        for f in sorted(files)[:200]:
            rel  = os.path.relpath(f, base)
            size = os.path.getsize(f)
            result.append(f"{rel}  ({size} B)")
        return "\n".join(result) if result else "no files found"
    except Exception as e:
        return f"error: {e}"

def run_shell(cmd, cwd=None, timeout=30):
    try:
        out = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=cwd or os.getcwd()
        )
        result = ""
        if out.stdout.strip():
            result += out.stdout
        if out.stderr.strip():
            result += "\n[stderr]\n" + out.stderr
        return result.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"[timed out after {timeout}s]"
    except Exception as e:
        return f"[error: {e}]"

# ── auto-apply file changes from model reply ──────────────────────────────────
BLOCK_PATTERN = re.compile(r"```(?:\w+)?\s*\n([\s\S]*?)```", re.DOTALL)
PATH_COMMENT  = re.compile(r"^(?:#|//|--|--)\s*([^\s].+\.\w+)\s*$")

def extract_and_apply_files(reply: str, cwd: str):
    applied = []
    blocks  = list(BLOCK_PATTERN.finditer(reply))
    for blk in blocks:
        before    = reply[:blk.start()].rstrip()
        last_line = before.split("\n")[-1].strip()
        m = PATH_COMMENT.match(last_line)
        if m:
            path    = os.path.join(cwd, m.group(1).strip())
            content = blk.group(1)
            ok, msg = write_file(path, content)
            if ok:
                applied.append(m.group(1).strip())
                print(c("yellow", f"  ✓ wrote  {m.group(1).strip()}"))
    return applied

# ── SYSTEM PROMPT ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are an expert coding agent running in a terminal.

CAPABILITIES YOU HAVE:
- Read any file the user mentions (they will paste content or ask you to reference it)
- Write files — when writing code, ALWAYS put the filename as a comment on the line
  immediately before each code block, like:
    # path/to/file.py
    ```python
    ...code...
    ```
  The agent will auto-apply these files to disk.
- Run shell commands — wrap in a shell block like:
    ```shell
    npm install
    ```
  The agent will run these and show you the output.
- Make multi-file edits, refactors, explain bugs, write tests.

RULES:
- Always show the filename before a code block so it can be auto-saved.
- Be concise, don't repeat yourself.
- When fixing bugs, show only the changed parts unless the file is short.
- Never add placeholder comments like "# ... rest of file". Write complete, working code.
"""

# ── terminal agent ────────────────────────────────────────────────────────────
def run_agent():
    banner()
    cwd     = os.getcwd()
    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    model   = "auto"

    print(c("dim", f"  cwd: {cwd}"))
    print(c("dim",  "  commands: /read <file>  /ls [dir]  /sh <cmd>  /model <name>  /clear  /exit"))
    print(c("dim",  "  tip: mention a filename and it auto-reads it; model writes files + runs shell"))
    print()

    while True:
        try:
            raw = input(c("blue", "you › ")).strip()
        except (EOFError, KeyboardInterrupt):
            print(c("dim", "\n  bye"))
            break

        if not raw:
            continue

        if raw.lower() in ("/exit", "/quit", "exit", "quit"):
            print(c("dim", "  bye")); break

        if raw.lower() == "/clear":
            history = [{"role": "system", "content": SYSTEM_PROMPT}]
            print(c("dim", "  context cleared")); continue

        if raw.lower().startswith("/model "):
            model = raw.split(None, 1)[1].strip()
            print(c("dim", f"  model → {model}")); continue

        if raw.lower().startswith("/read "):
            path    = raw.split(None, 1)[1].strip()
            content = read_file(os.path.join(cwd, path))
            snippet = content[:300] + ("…" if len(content) > 300 else "")
            print(c("dim", f"\n  [{path}]:\n{snippet}\n"))
            history.append({"role": "user",
                             "content": f"Here is the file `{path}`:\n```\n{content}\n```"})
            continue

        if raw.lower().startswith("/ls"):
            parts = raw.split(None, 1)
            base  = parts[1].strip() if len(parts) > 1 else cwd
            print(c("dim", "\n" + list_files(base=base) + "\n")); continue

        if raw.lower().startswith("/sh "):
            cmd    = raw.split(None, 1)[1].strip()
            result = run_shell(cmd, cwd=cwd)
            print(c("dim", f"\n{result}\n")); continue

        # auto-inject local file references
        user_msg  = raw
        file_refs = re.findall(
            r'(?:^|\s)([\w./\\-]+\.(?:py|js|ts|jsx|tsx|html|css|json|yaml|yml|md|txt|sh|bat|env|toml|rs|go|java|cpp|c|h))',
            raw
        )
        injected = []
        for ref in file_refs:
            full = os.path.join(cwd, ref)
            if os.path.isfile(full) and ref not in injected:
                content  = read_file(full)
                user_msg += f"\n\n[content of {ref}]:\n```\n{content}\n```"
                injected.append(ref)

        history.append({"role": "user", "content": user_msg})

        print(c("purple", "\nagent › "), end="", flush=True)
        reply = stream_reply(history, model=model)

        if not reply:
            history.pop(); continue

        history.append({"role": "assistant", "content": reply})

        # auto-apply files
        extract_and_apply_files(reply, cwd)

        # auto-run shell blocks
        shell_blocks = re.findall(
            r"```(?:shell|bash|sh|cmd|powershell)\s*\n([\s\S]*?)```", reply
        )
        for cmd in shell_blocks:
            cmd = cmd.strip()
            if not cmd: continue
            ans = input(c("yellow", f"\n  run? $ {cmd[:80]}  [y/N] ")).strip().lower()
            if ans == "y":
                out = run_shell(cmd, cwd=cwd)
                print(c("dim", out))
                history.append({"role": "user",
                                 "content": f"[shell output of `{cmd}`]:\n{out}"})
        print()


# ── API server (Cursor / MCP / any OpenAI client) ─────────────────────────────
API_KEY  = "openai-unlimited-local"
API_PORT = 12434

def run_server():
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import StreamingResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn

    _cache = {"data": None, "ts": 0}
    srv    = FastAPI(title="openai-unlimited", version="1.0.0")
    srv.add_middleware(CORSMiddleware, allow_origins=["*"],
                       allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    def auth(req: Request):
        token = req.headers.get("authorization", "").removeprefix("Bearer ").strip()
        if token != API_KEY:
            raise HTTPException(401, f"Use: Authorization: Bearer {API_KEY}")

    async def _models():
        now = time.time()
        if _cache["data"] and now - _cache["ts"] < 60:
            return _cache["data"]
        try:
            async with httpx.AsyncClient(timeout=10) as cl:
                r = await cl.get(MODELS_URL, headers=UA_HEADERS)
                if r.status_code == 200:
                    _cache["data"] = r.json().get("models", [])
                    _cache["ts"]   = now
                    return _cache["data"]
        except Exception:
            pass
        return [{"slug": s} for s in ["auto","gpt-5","gpt-5-mini","gpt-4o","gpt-4o-mini","o3","o4-mini"]]

    @srv.get("/"); async def root(): return {"base_url": f"http://localhost:{API_PORT}/v1", "api_key": API_KEY}
    @srv.get("/health"); async def health(): return {"status": "ok"}

    @srv.get("/v1/models")
    async def list_models(req: Request):
        auth(req)
        data = await _models()
        ts   = int(time.time())
        return {"object": "list", "data": [
            {"id": m.get("slug","?"), "object": "model", "created": ts,
             "owned_by": "openai-unlimited"} for m in data
        ]}

    async def _sse(msgs, model, rid, ts):
        upstream = _build_payload(msgs, model)
        prev     = ""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=15)) as cl:
                async with cl.stream("POST", UPSTREAM, headers=UA_HEADERS, json=upstream) as resp:
                    if resp.status_code not in (200, 201):
                        raw = await resp.aread()
                        yield f"data: {json.dumps({'error':{'message':f'upstream {resp.status_code}'}})}\n\n"
                        yield "data: [DONE]\n\n"; return
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "): continue
                        pay = line[6:]
                        if pay.strip() == "[DONE]": break
                        try:
                            ev   = json.loads(pay)
                            msg  = ev.get("message") or {}
                            role = (msg.get("author") or {}).get("role","")
                            if role != "assistant": continue
                            pts  = (msg.get("content") or {}).get("parts") or []
                            if not pts or not isinstance(pts[0], str): continue
                            full  = pts[0]; delta = full[len(prev):]; prev = full
                            if not delta: continue
                            yield f"data: {json.dumps({'id':rid,'object':'chat.completion.chunk','created':ts,'model':model,'choices':[{'index':0,'delta':{'role':'assistant','content':delta},'finish_reason':None}]})}\n\n"
                        except Exception: pass
        except Exception as e:
            yield f"data: {json.dumps({'error':{'message':str(e)}})}\n\n"
        yield f"data: {json.dumps({'id':rid,'object':'chat.completion.chunk','created':ts,'model':model,'choices':[{'index':0,'delta':{},'finish_reason':'stop'}]})}\n\n"
        yield "data: [DONE]\n\n"

    @srv.post("/v1/chat/completions")
    async def chat(req: Request):
        auth(req)
        body  = await req.json()
        msgs  = body.get("messages") or []
        if not msgs: raise HTTPException(400, "'messages' required")
        model  = body.get("model", "auto")
        stream = bool(body.get("stream", False))
        rid    = f"chatcmpl-{uuid.uuid4().hex}"
        ts     = int(time.time())
        if stream:
            return StreamingResponse(_sse(msgs, model, rid, ts),
                                     media_type="text/event-stream",
                                     headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})
        text = ""
        async for chunk in _sse(msgs, model, rid, ts):
            if not chunk.startswith("data: "): continue
            p = chunk[6:].strip()
            if p == "[DONE]": break
            try: text += (json.loads(p).get("choices") or [{}])[0].get("delta",{}).get("content","") or ""
            except Exception: pass
        pt = sum(len(str(m.get("content","")).split()) for m in msgs)
        ct = len(text.split())
        return JSONResponse({"id":rid,"object":"chat.completion","created":ts,"model":model,
            "choices":[{"index":0,"message":{"role":"assistant","content":text},"finish_reason":"stop"}],
            "usage":{"prompt_tokens":pt,"completion_tokens":ct,"total_tokens":pt+ct}})

    print(c("cyan", f"""
  ╔══════════════════════════════════════════╗
  ║  openai-unlimited  API  ✓  running       ║
  ╠══════════════════════════════════════════╣
  ║  Base URL → http://localhost:{API_PORT}/v1  ║
  ║  API Key  → {API_KEY}  ║
  ╚══════════════════════════════════════════╝"""))
    uvicorn.run(srv, host="0.0.0.0", port=API_PORT, log_level="warning")


# ── entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="openai-unlimited — free GPT terminal agent + Cursor API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python run.py              → terminal coding agent
  python run.py --server     → API server only (Cursor / MCP)
  python run.py --both       → agent + server together
        """
    )
    ap.add_argument("--server", action="store_true", help="start API server")
    ap.add_argument("--both",   action="store_true", help="agent + server")
    args = ap.parse_args()

    if args.both:
        t = threading.Thread(target=run_server, daemon=True)
        t.start(); time.sleep(1)
        run_agent()
    elif args.server:
        run_server()
    else:
        run_agent()

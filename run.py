#!/usr/bin/env python3
"""
openai-unlimited  —  free GPT in your terminal + OpenAI API + MCP server
─────────────────────────────────────────────────────────────────────────
  python run.py              → terminal coding agent
  python run.py --server     → OpenAI-compatible API (Cursor / LiteLLM)
  python run.py --mcp        → MCP server via stdio (Cursor MCP / Claude Desktop)
  python run.py --mcp-http   → MCP server via HTTP SSE (remote agents)
  python run.py --all        → everything at once

Cursor MCP config  (~/.cursor/mcp.json):
  {
    "mcpServers": {
      "openai-unlimited": {
        "command": "python",
        "args": ["<full-path>/run.py", "--mcp"]
      }
    }
  }

OpenAI API config:
  Base URL : http://localhost:12434/v1
  API Key  : openai-unlimited-local
"""

import sys, os, subprocess, json, uuid, time, re, threading, argparse, glob

# ── auto-install ──────────────────────────────────────────────────────────────
def _pip(*pkgs):
    for pkg in pkgs:
        try:
            __import__(pkg.split("[")[0].replace("-","_"))
        except ImportError:
            print(f"  installing {pkg}…", flush=True)
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

_pip("httpx", "fastapi", "uvicorn[standard]", "mcp[cli]")

import httpx

# ── upstream ──────────────────────────────────────────────────────────────────
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
C = {"reset":"\033[0m","bold":"\033[1m","dim":"\033[2m","green":"\033[92m",
     "cyan":"\033[96m","yellow":"\033[93m","red":"\033[91m","blue":"\033[94m","purple":"\033[95m"}
def c(col, txt): return f"{C[col]}{txt}{C['reset']}"

# ── GPT core ──────────────────────────────────────────────────────────────────
def _payload(messages, model="auto"):
    parts = []
    for m in messages:
        role    = m.get("role","user")
        content = m.get("content","")
        if isinstance(content, list):
            content = " ".join(p.get("text","") for p in content if isinstance(p,dict))
        tag = {"system":"[SYSTEM]","assistant":"[ASSISTANT]"}.get(role,"[USER]")
        parts.append(f"{tag}\n{content}")
    return {"action":"next","messages":[{
        "id":str(uuid.uuid4()),"author":{"role":"user"},
        "content":{"content_type":"text","parts":["\n\n".join(parts)]},
    }],"parent_message_id":str(uuid.uuid4()),"model":model,
      "history_and_training_disabled":True}

def gpt(messages, model="auto", live=False):
    """Blocking GPT call. Returns full reply string."""
    full, prev = "", ""
    try:
        with httpx.Client(timeout=httpx.Timeout(120,connect=15)) as cl:
            with cl.stream("POST", UPSTREAM, headers=UA_HEADERS, json=_payload(messages,model)) as r:
                if r.status_code not in (200,201):
                    return f"[upstream error {r.status_code}]"
                for line in r.iter_lines():
                    if not line.startswith("data: "): continue
                    raw = line[6:]
                    if raw.strip()=="[DONE]": break
                    try:
                        ev = json.loads(raw)
                        msg = ev.get("message") or {}
                        if (msg.get("author") or {}).get("role","") != "assistant": continue
                        pts = (msg.get("content") or {}).get("parts") or []
                        if not pts or not isinstance(pts[0],str): continue
                        full = pts[0]; delta = full[len(prev):]; prev = full
                        if delta and live: print(c("green",delta), end="", flush=True)
                    except Exception: pass
    except httpx.ConnectError: return "[cannot reach upstream — check internet]"
    except httpx.TimeoutException: return "[timed out]"
    except Exception as e: return f"[error: {e}]"
    if live: print()
    return full

# ── file / shell tools (shared by agent + MCP) ────────────────────────────────
MAX_READ = 64_000

def tool_read_file(path: str) -> str:
    try:
        path = os.path.expanduser(path)
        size = os.path.getsize(path)
        content = open(path, errors="replace").read(MAX_READ)
        note = f"[truncated to {MAX_READ} bytes]\n" if size > MAX_READ else ""
        return note + content
    except Exception as e: return f"[error: {e}]"

def tool_write_file(path: str, content: str) -> str:
    try:
        path = os.path.expanduser(path)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        open(path,"w",encoding="utf-8").write(content)
        return f"wrote {len(content)} chars → {path}"
    except Exception as e: return f"[error: {e}]"

def tool_list_files(directory: str = ".") -> str:
    try:
        base  = os.path.expanduser(directory)
        files = [p for p in glob.glob(os.path.join(base,"**/*"),recursive=True) if os.path.isfile(p)]
        lines = [f"{os.path.relpath(f,base)}  ({os.path.getsize(f)} B)" for f in sorted(files)[:300]]
        return "\n".join(lines) if lines else "no files found"
    except Exception as e: return f"[error: {e}]"

def tool_run_shell(command: str, cwd: str = ".") -> str:
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True,
                           timeout=30, cwd=cwd or os.getcwd())
        out = r.stdout.strip()
        err = r.stderr.strip()
        parts = []
        if out: parts.append(out)
        if err: parts.append(f"[stderr]\n{err}")
        return "\n".join(parts) or "(no output)"
    except subprocess.TimeoutExpired: return "[timed out after 30s]"
    except Exception as e: return f"[error: {e}]"

def tool_chat(message: str, model: str = "auto") -> str:
    return gpt([{"role":"user","content":message}], model=model)

# ── MCP server (stdio transport — for Cursor MCP & Claude Desktop) ────────────
def run_mcp_stdio():
    """Expose tools via MCP stdio protocol. Add to mcp.json and Cursor picks it up."""
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types
    import asyncio

    server = Server("openai-unlimited")

    @server.list_tools()
    async def list_tools():
        return [
            types.Tool(
                name="chat",
                description="Send a message to GPT (gpt-5, gpt-4o, auto, etc.) and get a reply. Free, no API key needed.",
                inputSchema={"type":"object","properties":{
                    "message":{"type":"string","description":"Your message or coding question"},
                    "model":{"type":"string","description":"Model to use: auto, gpt-5, gpt-4o, gpt-4o-mini, o3, o4-mini","default":"auto"}
                },"required":["message"]}
            ),
            types.Tool(
                name="read_file",
                description="Read a file from the local filesystem and return its contents.",
                inputSchema={"type":"object","properties":{
                    "path":{"type":"string","description":"Absolute or relative file path"}
                },"required":["path"]}
            ),
            types.Tool(
                name="write_file",
                description="Write content to a file on the local filesystem. Creates parent directories if needed.",
                inputSchema={"type":"object","properties":{
                    "path":{"type":"string","description":"File path to write to"},
                    "content":{"type":"string","description":"Content to write"}
                },"required":["path","content"]}
            ),
            types.Tool(
                name="list_files",
                description="List all files in a directory recursively.",
                inputSchema={"type":"object","properties":{
                    "directory":{"type":"string","description":"Directory path to list","default":"."}
                },"required":[]}
            ),
            types.Tool(
                name="run_shell",
                description="Run a shell command and return stdout + stderr.",
                inputSchema={"type":"object","properties":{
                    "command":{"type":"string","description":"Shell command to execute"},
                    "cwd":{"type":"string","description":"Working directory","default":"."}
                },"required":["command"]}
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        import asyncio
        try:
            if name == "chat":
                result = await asyncio.to_thread(tool_chat,
                    arguments.get("message",""),
                    arguments.get("model","auto"))
            elif name == "read_file":
                result = await asyncio.to_thread(tool_read_file, arguments["path"])
            elif name == "write_file":
                result = await asyncio.to_thread(tool_write_file,
                    arguments["path"], arguments["content"])
            elif name == "list_files":
                result = await asyncio.to_thread(tool_list_files,
                    arguments.get("directory","."))
            elif name == "run_shell":
                result = await asyncio.to_thread(tool_run_shell,
                    arguments["command"], arguments.get("cwd","."))
            else:
                result = f"unknown tool: {name}"
        except Exception as e:
            result = f"[error: {e}]"
        return [types.TextContent(type="text", text=str(result))]

    async def _run():
        async with stdio_server() as (r, w):
            await server.run(r, w, server.create_initialization_options())

    import asyncio
    asyncio.run(_run())


# ── MCP server (HTTP/SSE transport — for remote agents) ───────────────────────
MCP_HTTP_PORT = 12435

def run_mcp_http():
    """Expose tools via MCP over HTTP SSE. Point any MCP client to http://localhost:12435/sse"""
    from mcp.server import Server
    from mcp.server.sse import SseServerTransport
    from mcp import types
    import asyncio
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import JSONResponse
    import uvicorn

    server = Server("openai-unlimited")

    @server.list_tools()
    async def list_tools():
        return [
            types.Tool(name="chat",
                description="Chat with GPT-5/4o for free. No API key.",
                inputSchema={"type":"object","properties":{
                    "message":{"type":"string"},
                    "model":{"type":"string","default":"auto"}
                },"required":["message"]}),
            types.Tool(name="read_file",
                description="Read a local file.",
                inputSchema={"type":"object","properties":{
                    "path":{"type":"string"}
                },"required":["path"]}),
            types.Tool(name="write_file",
                description="Write content to a local file.",
                inputSchema={"type":"object","properties":{
                    "path":{"type":"string"},"content":{"type":"string"}
                },"required":["path","content"]}),
            types.Tool(name="list_files",
                description="List files in a directory.",
                inputSchema={"type":"object","properties":{
                    "directory":{"type":"string","default":"."}
                },"required":[]}),
            types.Tool(name="run_shell",
                description="Run a shell command.",
                inputSchema={"type":"object","properties":{
                    "command":{"type":"string"},"cwd":{"type":"string","default":"."}
                },"required":["command"]}),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        try:
            if name=="chat":         result = await asyncio.to_thread(tool_chat,       arguments.get("message",""), arguments.get("model","auto"))
            elif name=="read_file":  result = await asyncio.to_thread(tool_read_file,  arguments["path"])
            elif name=="write_file": result = await asyncio.to_thread(tool_write_file, arguments["path"], arguments["content"])
            elif name=="list_files": result = await asyncio.to_thread(tool_list_files, arguments.get("directory","."))
            elif name=="run_shell":  result = await asyncio.to_thread(tool_run_shell,  arguments["command"], arguments.get("cwd","."))
            else: result = f"unknown tool: {name}"
        except Exception as e:
            result = f"[error: {e}]"
        return [types.TextContent(type="text", text=str(result))]

    sse = SseServerTransport("/messages")

    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as (r, w):
            await server.run(r, w, server.create_initialization_options())

    async def handle_messages(scope, receive, send):
        await sse.handle_post_message(scope, receive, send)

    async def root(request):
        return JSONResponse({"mcp": "openai-unlimited", "sse": f"http://localhost:{MCP_HTTP_PORT}/sse",
                             "tools": ["chat","read_file","write_file","list_files","run_shell"]})

    app = Starlette(routes=[
        Route("/", root),
        Route("/sse", handle_sse),
        Mount("/messages", app=handle_messages),
    ])

    print(c("cyan", f"""
  ╔══════════════════════════════════════════╗
  ║  openai-unlimited  MCP HTTP  ✓ running   ║
  ╠══════════════════════════════════════════╣
  ║  SSE  → http://localhost:{MCP_HTTP_PORT}/sse      ║
  ║  Tools: chat · read_file · write_file    ║
  ║         list_files · run_shell           ║
  ╚══════════════════════════════════════════╝"""))
    uvicorn.run(app, host="0.0.0.0", port=MCP_HTTP_PORT, log_level="warning")


# ── OpenAI-compatible API server ──────────────────────────────────────────────
API_KEY  = "openai-unlimited-local"
API_PORT = 12434
_mcache  = {"data": None, "ts": 0}

def run_api_server():
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import StreamingResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn, asyncio

    srv = FastAPI(title="openai-unlimited")
    srv.add_middleware(CORSMiddleware, allow_origins=["*"],
                       allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    def auth(req):
        tok = req.headers.get("authorization","").removeprefix("Bearer ").strip()
        if tok != API_KEY: raise HTTPException(401, f"Use: Bearer {API_KEY}")

    async def _models():
        now = time.time()
        if _mcache["data"] and now-_mcache["ts"]<60: return _mcache["data"]
        try:
            async with httpx.AsyncClient(timeout=10) as cl:
                r = await cl.get(MODELS_URL, headers=UA_HEADERS)
                if r.status_code==200:
                    _mcache["data"]=r.json().get("models",[]); _mcache["ts"]=now
                    return _mcache["data"]
        except Exception: pass
        return [{"slug":s} for s in ["auto","gpt-5","gpt-5-mini","gpt-4o","gpt-4o-mini","o3","o4-mini"]]

    @srv.get("/")
    async def root():
        return {"base_url": f"http://localhost:{API_PORT}/v1", "api_key": API_KEY}

    @srv.get("/health")
    async def health():
        return {"status": "ok"}

    @srv.get("/v1/models")
    async def list_models(req: Request):
        auth(req); data=await _models(); ts=int(time.time())
        return {"object":"list","data":[{"id":m.get("slug","?"),"object":"model",
            "created":ts,"owned_by":"openai-unlimited"} for m in data]}

    async def _sse(msgs, model, rid, ts):
        up = _payload(msgs, model); prev=""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(120,connect=15)) as cl:
                async with cl.stream("POST",UPSTREAM,headers=UA_HEADERS,json=up) as resp:
                    if resp.status_code not in (200,201):
                        yield f"data: {json.dumps({'error':{'message':f'upstream {resp.status_code}'}})}\n\n"
                        yield "data: [DONE]\n\n"; return
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "): continue
                        pay=line[6:]
                        if pay.strip()=="[DONE]": break
                        try:
                            ev=json.loads(pay); msg=ev.get("message") or {}
                            if (msg.get("author") or {}).get("role","")!="assistant": continue
                            pts=(msg.get("content") or {}).get("parts") or []
                            if not pts or not isinstance(pts[0],str): continue
                            full=pts[0]; delta=full[len(prev):]; prev=full
                            if not delta: continue
                            yield f"data: {json.dumps({'id':rid,'object':'chat.completion.chunk','created':ts,'model':model,'choices':[{'index':0,'delta':{'role':'assistant','content':delta},'finish_reason':None}]})}\n\n"
                        except Exception: pass
        except Exception as e:
            yield f"data: {json.dumps({'error':{'message':str(e)}})}\n\n"
        yield f"data: {json.dumps({'id':rid,'object':'chat.completion.chunk','created':ts,'model':model,'choices':[{'index':0,'delta':{},'finish_reason':'stop'}]})}\n\n"
        yield "data: [DONE]\n\n"

    @srv.post("/v1/chat/completions")
    async def chat(req: Request):
        auth(req); body=await req.json()
        msgs=body.get("messages") or []
        if not msgs: raise HTTPException(400,"'messages' required")
        model=body.get("model","auto"); stream=bool(body.get("stream",False))
        rid=f"chatcmpl-{uuid.uuid4().hex}"; ts=int(time.time())
        if stream:
            return StreamingResponse(_sse(msgs,model,rid,ts), media_type="text/event-stream",
                headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})
        text=""
        async for chunk in _sse(msgs,model,rid,ts):
            if not chunk.startswith("data: "): continue
            p=chunk[6:].strip()
            if p=="[DONE]": break
            try: text+=(json.loads(p).get("choices") or [{}])[0].get("delta",{}).get("content","") or ""
            except Exception: pass
        pt=sum(len(str(m.get("content","")).split()) for m in msgs); ct=len(text.split())
        return JSONResponse({"id":rid,"object":"chat.completion","created":ts,"model":model,
            "choices":[{"index":0,"message":{"role":"assistant","content":text},"finish_reason":"stop"}],
            "usage":{"prompt_tokens":pt,"completion_tokens":ct,"total_tokens":pt+ct}})

    print(c("cyan", f"""
  ╔══════════════════════════════════════════╗
  ║  openai-unlimited  API  ✓ running        ║
  ╠══════════════════════════════════════════╣
  ║  Base URL → http://localhost:{API_PORT}/v1  ║
  ║  API Key  → {API_KEY}  ║
  ╚══════════════════════════════════════════╝"""))
    uvicorn.run(srv, host="0.0.0.0", port=API_PORT, log_level="warning")


# ── terminal coding agent ─────────────────────────────────────────────────────
SYSTEM = """\
You are an expert coding agent in a terminal.
When writing files, ALWAYS put the filename as a comment on the line before the code block:
  # path/to/file.py
  ```python
  ...code...
  ```
The agent auto-saves these to disk.
For shell commands use ```shell blocks — user is asked [y/N] before they run.
Write complete, working code. Never use placeholder comments like '# rest of file'.
"""

BLOCK_RE    = re.compile(r"```(?:\w+)?\s*\n([\s\S]*?)```", re.DOTALL)
PATH_CMT_RE = re.compile(r"^(?:#|//|--)\s*(\S.+\.\w+)\s*$")
FILE_RE     = re.compile(r'(?:^|\s)([\w./\\-]+\.(?:py|js|ts|jsx|tsx|html|css|json|yaml|yml|md|txt|sh|bat|toml|rs|go|java|cpp|c|h))')

def auto_apply(reply, cwd):
    for blk in BLOCK_RE.finditer(reply):
        last = reply[:blk.start()].rstrip().split("\n")[-1].strip()
        m = PATH_CMT_RE.match(last)
        if m:
            result = tool_write_file(os.path.join(cwd, m.group(1)), blk.group(1))
            print(c("yellow", f"  ✓ {result}"))

def run_agent():
    print(c("cyan","""
  ╔══════════════════════════════════════════╗
  ║   openai-unlimited  ·  coding agent      ║
  ║   free GPT · file access · shell exec    ║
  ╚══════════════════════════════════════════╝"""))
    cwd     = os.getcwd()
    history = [{"role":"system","content":SYSTEM}]
    model   = "auto"
    print(c("dim", f"  cwd: {cwd}"))
    print(c("dim",  "  /read <f>  /ls [dir]  /sh <cmd>  /model <m>  /clear  /exit"))
    print()

    while True:
        try: raw = input(c("blue","you › ")).strip()
        except (EOFError, KeyboardInterrupt): print(c("dim","\n  bye")); break
        if not raw: continue
        if raw.lower() in ("/exit","/quit","exit","quit"): print(c("dim","  bye")); break
        if raw.lower()=="/clear":
            history=[{"role":"system","content":SYSTEM}]; print(c("dim","  cleared")); continue
        if raw.lower().startswith("/model "):
            model=raw.split(None,1)[1].strip(); print(c("dim",f"  model → {model}")); continue
        if raw.lower().startswith("/read "):
            path=raw.split(None,1)[1].strip()
            content=tool_read_file(os.path.join(cwd,path))
            print(c("dim",f"\n  [{path}]:\n{content[:300]}{'…' if len(content)>300 else ''}\n"))
            history.append({"role":"user","content":f"File `{path}`:\n```\n{content}\n```"}); continue
        if raw.lower().startswith("/ls"):
            parts=raw.split(None,1); base=parts[1].strip() if len(parts)>1 else cwd
            print(c("dim","\n"+tool_list_files(base)+"\n")); continue
        if raw.lower().startswith("/sh "):
            cmd=raw.split(None,1)[1].strip()
            print(c("dim","\n"+tool_run_shell(cmd,cwd)+"\n")); continue

        msg = raw
        for ref in FILE_RE.findall(raw):
            full=os.path.join(cwd,ref)
            if os.path.isfile(full):
                msg+=f"\n\n[{ref}]:\n```\n{tool_read_file(full)}\n```"

        history.append({"role":"user","content":msg})
        print(c("purple","\nagent › "),end="",flush=True)
        reply=gpt(history, model=model, live=True)
        if not reply: history.pop(); continue
        history.append({"role":"assistant","content":reply})

        auto_apply(reply, cwd)

        for cmd in re.findall(r"```(?:shell|bash|sh|cmd|powershell)\s*\n([\s\S]*?)```",reply):
            cmd=cmd.strip()
            if not cmd: continue
            if input(c("yellow",f"\n  run? $ {cmd[:80]}  [y/N] ")).strip().lower()=="y":
                out=tool_run_shell(cmd,cwd); print(c("dim",out))
                history.append({"role":"user","content":f"[shell: `{cmd}`]\n{out}"})
        print()


# ── entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="openai-unlimited — free GPT · terminal agent · OpenAI API · MCP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python run.py               terminal coding agent
  python run.py --server      OpenAI-compatible API server (Cursor / LiteLLM)
  python run.py --mcp         MCP server via stdio  (add to mcp.json)
  python run.py --mcp-http    MCP server via HTTP SSE  (remote agents)
  python run.py --all         agent + API server + MCP HTTP
        """
    )
    ap.add_argument("--server",   action="store_true", help="OpenAI API server")
    ap.add_argument("--mcp",      action="store_true", help="MCP server (stdio)")
    ap.add_argument("--mcp-http", action="store_true", help="MCP server (HTTP SSE)")
    ap.add_argument("--all",      action="store_true", help="agent + API + MCP HTTP")
    args = ap.parse_args()

    if args.mcp:
        run_mcp_stdio()
    elif args.all:
        threading.Thread(target=run_api_server, daemon=True).start()
        threading.Thread(target=run_mcp_http,   daemon=True).start()
        time.sleep(1)
        run_agent()
    elif args.mcp_http:
        run_mcp_http()
    elif args.server:
        run_api_server()
    else:
        run_agent()

# ⚡ openai-unlimited — Free GPT API · Terminal · MCP Server · No Key Ever

> **Drop-in OpenAI API replacement. Use GPT-5, GPT-4o, o3 and more — free, local, zero config.**  
> Works as a terminal agent, Cursor/VS Code backend, MCP server for coding agents, or plain HTTP API.

[![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)](https://python.org)
[![OpenAI Compatible](https://img.shields.io/badge/OpenAI_API-compatible-orange)](#-api-server--http)
[![MCP](https://img.shields.io/badge/MCP-stdio_%2B_SSE-brightgreen)](#-mcp-server)
[![Cursor](https://img.shields.io/badge/Cursor_IDE-ready-purple)](#-cursor-ide)
[![License](https://img.shields.io/badge/License-MIT-green)](#)

```bash
# one-line install & run
git clone https://github.com/Singh-army/openai-unlimited && cd openai-unlimited && python run.py
```

Dependencies install automatically. No `.env`. No account. No API key.

---

## 📋 Table of Contents

- [All Run Modes](#-all-run-modes)
- [Model Picker](#-model-picker)
- [Terminal Coding Agent](#-terminal-coding-agent)
- [API Server (HTTP)](#-api-server--http)
- [MCP Server (Cursor / Claude Desktop)](#-mcp-server)
- [Cursor IDE Setup](#-cursor-ide-setup)
- [VS Code + Continue](#-vs-code--continue)
- [Python / Node.js SDK](#-python--nodejs-sdk)
- [LangChain / LiteLLM / n8n](#-langchain--litellm--n8n)
- [All-in-One Mode](#-all-in-one-mode)
- [Available Tools (MCP)](#-mcp-tools)
- [Requirements](#-requirements)

---

## 🚀 All Run Modes

| Command | What starts | Port |
|---|---|---|
| `python run.py` | Terminal coding agent | — |
| `python run.py --server` | OpenAI-compatible HTTP API | `12434` |
| `python run.py --mcp` | MCP server via **stdio** (Cursor MCP / Claude Desktop) | stdio |
| `python run.py --mcp-http` | MCP server via **HTTP SSE** (n8n / LangChain / remote) | `12435` |
| `python run.py --all` | **Everything at once** — agent + API + MCP HTTP | `12434` + `12435` |

---

## 🧠 Model Picker

Every mode lets you choose the model freely. Here are all available models:

| Model ID | Description | Best for |
|---|---|---|
| `auto` | Best available — auto-selected ✅ **default** | Everything |
| `gpt-5` | Latest GPT-5 | Complex code, reasoning |
| `gpt-5-mini` | GPT-5, faster + lighter | Quick tasks |
| `gpt-4o` | Multimodal powerhouse | Code + vision |
| `gpt-4o-mini` | Small, fast, cheap-tier | Simple completions |
| `o3` | Deep reasoning model | Hard problems, math |
| `o4-mini` | Fast reasoning | Step-by-step logic |

### How to switch model in each mode

**Terminal agent — runtime command:**
```
you › /model gpt-5
you › /model o3
you › /model gpt-4o-mini
```

**API server — per request (in JSON body):**
```json
{ "model": "gpt-5", "messages": [...] }
```

**MCP stdio — per tool call:**
```json
{ "name": "chat", "arguments": { "message": "hello", "model": "o3" } }
```

**Python SDK:**
```python
client.chat.completions.create(model="gpt-5", messages=[...])
```

**curl:**
```bash
curl http://localhost:12434/v1/models \
  -H "Authorization: Bearer openai-unlimited-local"
# returns live list of all available models
```

---

## 🤖 Terminal Coding Agent

Like Aider or Claude Code — but free, no setup, works offline-first.

```bash
python run.py
```

```
  ╔══════════════════════════════════════════╗
  ║   openai-unlimited  ·  coding agent      ║
  ║   free GPT · file access · shell exec    ║
  ╚══════════════════════════════════════════╝
  cwd: /your/project
  /read <f>  /ls [dir]  /sh <cmd>  /model <m>  /clear  /exit

you › fix the bug in app.py
you › write a FastAPI server in server.py
you › /model gpt-5
you › add tests for auth.py using pytest
you › /sh npm install
you › /read config.json
```

### Agent superpowers

| Feature | How it works |
|---|---|
| **Auto file read** | Mention `app.py` in your message → it reads it automatically |
| **Auto file write** | Agent puts `# path/file.py` before a code block → saved to disk ✅ |
| **Shell execution** | Agent wraps commands in ` ```shell ``` ` → asks `[y/N]` before running |
| **Conversation memory** | Full history kept across turns in the same session |
| **Model switch** | `/model gpt-5` anytime mid-conversation |

### All slash commands

```
/read <file>      inject file contents into context
/ls [dir]         list all files in directory (default: cwd)
/sh <command>     run a shell command and show output
/model <name>     switch model — gpt-5, gpt-4o, o3, auto ...
/clear            clear conversation history (keep system prompt)
/exit             quit
```

---

## 🌐 API Server — HTTP

Start once, use from anywhere on your machine.

```bash
python run.py --server
```

```
  ╔══════════════════════════════════════════╗
  ║  openai-unlimited  API  ✓ running        ║
  ╠══════════════════════════════════════════╣
  ║  Base URL → http://localhost:12434/v1    ║
  ║  API Key  → openai-unlimited-local       ║
  ╚══════════════════════════════════════════╝
```

### Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/v1/chat/completions` | POST | Chat completions (streaming + non-streaming) |
| `/v1/models` | GET | List all available models |
| `/health` | GET | Health check |

### curl — non-streaming

```bash
curl http://localhost:12434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer openai-unlimited-local" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Write a Python hello world"}],
    "stream": false
  }'
```

### curl — streaming (like ChatGPT)

```bash
curl http://localhost:12434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer openai-unlimited-local" \
  -d '{
    "model": "gpt-5",
    "messages": [{"role": "user", "content": "Explain async/await"}],
    "stream": true
  }'
```

### List available models

```bash
curl http://localhost:12434/v1/models \
  -H "Authorization: Bearer openai-unlimited-local"
```

---

## 🔌 MCP Server

Exposes 5 tools over **two transports** — pick what your tool supports.

### Transport 1 — stdio (Cursor MCP, Claude Desktop, any MCP client)

```bash
python run.py --mcp
```

**Add to `~/.cursor/mcp.json`:**

```json
{
  "mcpServers": {
    "openai-unlimited": {
      "command": "python",
      "args": ["/full/path/to/run.py", "--mcp"]
    }
  }
}
```

> Replace `/full/path/to/run.py` with the actual absolute path on your machine.

**Add to Claude Desktop (`claude_desktop_config.json`):**

```json
{
  "mcpServers": {
    "openai-unlimited": {
      "command": "python",
      "args": ["/full/path/to/run.py", "--mcp"]
    }
  }
}
```

---

### Transport 2 — HTTP SSE (n8n, LangChain, remote agents)

```bash
python run.py --mcp-http
```

```
  ╔══════════════════════════════════════════╗
  ║  openai-unlimited  MCP HTTP  ✓ running   ║
  ╠══════════════════════════════════════════╣
  ║  SSE  → http://localhost:12435/sse       ║
  ╚══════════════════════════════════════════╝
```

Point any SSE-based MCP client to: `http://localhost:12435/sse`

---

## 🔧 MCP Tools

All 5 tools available in both stdio and HTTP transports:

| Tool | Input | What it does |
|---|---|---|
| `chat` | `message`, `model` (optional) | Send a message to GPT, get reply |
| `read_file` | `path` | Read any local file |
| `write_file` | `path`, `content` | Write/create a local file |
| `list_files` | `directory` (optional) | List files recursively |
| `run_shell` | `command`, `cwd` (optional) | Execute a shell command |

**Example MCP tool call:**
```json
{
  "name": "chat",
  "arguments": {
    "message": "Write a Python Flask server with auth",
    "model": "gpt-5"
  }
}
```

```json
{
  "name": "run_shell",
  "arguments": {
    "command": "pytest tests/ -v",
    "cwd": "/my/project"
  }
}
```

---

## 🖥️ Cursor IDE Setup

### Option A — API backend (Cursor AI uses it)

1. Start: `python run.py --server`
2. Open Cursor → **Settings** (`Ctrl+,`) → **Models**
3. Set **Override OpenAI Base URL** → `http://localhost:12434/v1`
4. Set **OpenAI API Key** → `openai-unlimited-local`
5. **Add Custom Model** → type `gpt-5` (or `auto`, `gpt-4o`, `o3`)
6. Click **Verify** ✅

### Option B — MCP server (tools in Cursor Agent)

1. Edit `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "openai-unlimited": {
      "command": "python",
      "args": ["/full/path/to/run.py", "--mcp"]
    }
  }
}
```
2. Restart Cursor
3. In Cursor Agent — you'll see tools: `chat`, `read_file`, `write_file`, `list_files`, `run_shell`

### Option C — Both at once

```bash
python run.py --all
```
API on `:12434` + MCP HTTP on `:12435` + terminal agent — all running together.

---

## 🟦 VS Code + Continue

Install the [Continue extension](https://marketplace.visualstudio.com/items?itemName=Continue.continue), then add to `~/.continue/config.json`:

```json
{
  "models": [
    {
      "title": "GPT-5 Free",
      "provider": "openai",
      "model": "gpt-5",
      "apiBase": "http://localhost:12434/v1",
      "apiKey": "openai-unlimited-local"
    },
    {
      "title": "GPT-4o Free",
      "provider": "openai",
      "model": "gpt-4o",
      "apiBase": "http://localhost:12434/v1",
      "apiKey": "openai-unlimited-local"
    },
    {
      "title": "o3 Free",
      "provider": "openai",
      "model": "o3",
      "apiBase": "http://localhost:12434/v1",
      "apiKey": "openai-unlimited-local"
    }
  ]
}
```

All 3 models show up as separate options in the Continue model dropdown.

---

## 🐍 Python / Node.js SDK

### Python (openai package)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:12434/v1",
    api_key="openai-unlimited-local",
)

# pick any model
for model in ["gpt-5", "gpt-4o", "o3", "auto"]:
    res = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "hello"}],
    )
    print(f"{model}: {res.choices[0].message.content}")
```

### Python — streaming

```python
stream = client.chat.completions.create(
    model="gpt-5",
    messages=[{"role": "user", "content": "Write a REST API"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

### Node.js / TypeScript

```ts
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "http://localhost:12434/v1",
  apiKey: "openai-unlimited-local",
});

const res = await client.chat.completions.create({
  model: "gpt-5",   // or gpt-4o, o3, auto
  messages: [{ role: "user", content: "Explain MCP protocol" }],
});
console.log(res.choices[0].message.content);
```

---

## 🔗 LangChain / LiteLLM / n8n

### LangChain (Python)

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-5",
    openai_api_base="http://localhost:12434/v1",
    openai_api_key="openai-unlimited-local",
)
print(llm.invoke("Write a Python web scraper").content)
```

### LiteLLM proxy

```yaml
# litellm_config.yaml
model_list:
  - model_name: gpt-5-free
    litellm_params:
      model: openai/gpt-5
      api_base: http://localhost:12434/v1
      api_key: openai-unlimited-local
  - model_name: gpt-4o-free
    litellm_params:
      model: openai/gpt-4o
      api_base: http://localhost:12434/v1
      api_key: openai-unlimited-local
```

```bash
litellm --config litellm_config.yaml
```

### n8n (HTTP Request node)

```
URL    : http://localhost:12435/sse   (MCP transport)
  — or —
URL    : http://localhost:12434/v1/chat/completions
Method : POST
Header : Authorization: Bearer openai-unlimited-local
Body   : { "model": "gpt-4o", "messages": [...] }
```

### Aider

```bash
export OPENAI_API_BASE=http://localhost:12434/v1
export OPENAI_API_KEY=openai-unlimited-local
aider --model gpt-4o
```

---

## ⚡ All-in-One Mode

Runs the terminal agent + API server + MCP HTTP server all together:

```bash
python run.py --all
```

```
  API  → http://localhost:12434/v1   (Cursor, IDE, SDK)
  MCP  → http://localhost:12435/sse  (n8n, agents, LangChain)
  Agent → interactive terminal
```

This is the recommended mode when you want everything available without juggling multiple terminals.

---

## ⚙️ Requirements

| Requirement | Detail |
|---|---|
| Python | 3.8 or higher |
| Internet | Required (proxies to upstream) |
| OS | Windows / macOS / Linux |
| Packages | Auto-installed on first run |

Packages auto-installed: `httpx`, `fastapi`, `uvicorn`, `mcp[cli]`

No Docker. No Node. No `.env`. No account.

---

## ⭐ Star this if it saved you money

[![Star](https://img.shields.io/github/stars/Singh-army/openai-unlimited?style=social)](https://github.com/Singh-army/openai-unlimited/stargazers)

**Share with devs who hate paying for API keys 👇**

---

> ⚠️ Not affiliated with OpenAI. For personal and educational use only.

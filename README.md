# openai-unlimited

> **Free GPT-5 in your terminal — coding agent · OpenAI API · MCP server.**  
> No login. No API key. No paywall. No account.

[![Python](https://img.shields.io/badge/python-3.8%2B-blue?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![OpenAI Compatible](https://img.shields.io/badge/OpenAI%20API-compatible-412991?logo=openai&logoColor=white)]()
[![MCP](https://img.shields.io/badge/MCP-stdio%20%2B%20HTTP-orange)]()

> ⚠️ Not affiliated with OpenAI. Uses the same anonymous endpoint the ChatGPT web app uses internally.

---

## ✨ What it does

| Mode | Command | Use case |
|---|---|---|
| **Coding agent** | `unlimitedai` | Chat, write files, run shell cmds in terminal |
| **OpenAI API server** | `unlimitedai --server` | Drop-in for Cursor, VS Code, LangChain, any SDK |
| **MCP stdio** | `unlimitedai --mcp` | Cursor MCP agent, Claude Desktop |
| **MCP HTTP SSE** | `unlimitedai --mcp-http` | n8n, remote agents, HTTP-based MCP clients |
| **Everything** | `unlimitedai --all` | All three servers + agent in one terminal |

---

## 🚀 Install

```bash
git clone https://github.com/Singh-army/openai-unlimited
cd openai-unlimited
pip install -e .
```

After install, `unlimitedai` is available **globally** — open any terminal, any folder, and just type it.

---

## 🤖 Mode 1 — Terminal Coding Agent

```bash
unlimitedai
```

```
╔══════════════════════════════════════════════╗
║   openai-unlimited  ·  coding agent          ║
║   free GPT · file access · shell exec        ║
╚══════════════════════════════════════════════╝

  cwd   : /your/project
  model : auto  (change: /model <name>)
  models: auto  gpt-5  gpt-5-mini  gpt-4o  gpt-4o-mini  o3  o4-mini
  cmds  : /read <f>  /ls [dir]  /sh <cmd>  /model <m>  /clear  /exit

you › _
```

### Agent commands

| Command | What it does |
|---|---|
| `/model gpt-5` | Switch model mid-conversation |
| `/models` | List all available models |
| `/read src/app.py` | Load a file into context |
| `/ls ./src` | List files in a directory |
| `/sh npm run build` | Run a shell command manually |
| `/clear` | Reset conversation history |
| `/exit` | Quit |

### Smart auto-features
- **Mention a filename** (`fix main.py`) → file is auto-loaded into context
- **Code blocks with `# path/to/file` above** → auto-saved to disk
- **Shell blocks** → agent asks `[y/N]` before running

---

## 🌐 Mode 2 — OpenAI-Compatible API Server

```bash
unlimitedai --server
```

```
╔══════════════════════════════════════════════╗
║  openai-unlimited  API  ✓ live               ║
╠══════════════════════════════════════════════╣
║  Base URL → http://localhost:12434/v1        ║
║  API Key  → openai-unlimited-local           ║
║  Models   → auto · gpt-5 · gpt-4o · o3 ...  ║
╚══════════════════════════════════════════════╝
```

### Quick settings (copy-paste into any tool)

```
Base URL : http://localhost:12434/v1
API Key  : openai-unlimited-local
```

---

### Cursor

`Cursor Settings → Models → OpenAI API Key → Override`:
```
API Base URL : http://localhost:12434/v1
API Key      : openai-unlimited-local
```

Or add to `~/.cursor/mcp.json` for MCP agent mode (see Mode 3 below).

---

### VS Code + Continue

`.continue/config.json`:
```json
{
  "models": [
    {
      "title": "GPT-5 (free)",
      "provider": "openai",
      "model": "gpt-5",
      "apiBase": "http://localhost:12434/v1",
      "apiKey": "openai-unlimited-local"
    },
    {
      "title": "o3 (free)",
      "provider": "openai",
      "model": "o3",
      "apiBase": "http://localhost:12434/v1",
      "apiKey": "openai-unlimited-local"
    },
    {
      "title": "GPT-4o mini (free)",
      "provider": "openai",
      "model": "gpt-4o-mini",
      "apiBase": "http://localhost:12434/v1",
      "apiKey": "openai-unlimited-local"
    }
  ]
}
```

---

### Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:12434/v1",
    api_key="openai-unlimited-local",
)

# streaming
stream = client.chat.completions.create(
    model="gpt-5",   # gpt-5 · gpt-4o · o3 · o4-mini · gpt-5-mini · auto
    messages=[{"role": "user", "content": "write a binary search in Python"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

---

### Node.js / TypeScript

```typescript
import OpenAI from "openai";

const ai = new OpenAI({
  baseURL: "http://localhost:12434/v1",
  apiKey:  "openai-unlimited-local",
});

const res = await ai.chat.completions.create({
  model:    "gpt-5",
  messages: [{ role: "user", content: "explain async/await" }],
});
console.log(res.choices[0].message.content);
```

---

### curl

```bash
# list available models
curl http://localhost:12434/v1/models \
  -H "Authorization: Bearer openai-unlimited-local"

# chat completion
curl http://localhost:12434/v1/chat/completions \
  -H "Authorization: Bearer openai-unlimited-local" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5","messages":[{"role":"user","content":"hello"}]}'

# streaming
curl http://localhost:12434/v1/chat/completions \
  -H "Authorization: Bearer openai-unlimited-local" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5","messages":[{"role":"user","content":"hello"}],"stream":true}'
```

---

### LangChain

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-5",
    openai_api_base="http://localhost:12434/v1",
    openai_api_key="openai-unlimited-local",
)
print(llm.invoke("write a SQL query for top 10 customers by revenue"))
```

---

### LiteLLM proxy

`litellm_config.yaml`:
```yaml
model_list:
  - model_name: gpt-5
    litellm_params:
      model: openai/gpt-5
      api_base: http://localhost:12434/v1
      api_key: openai-unlimited-local
  - model_name: o3
    litellm_params:
      model: openai/o3
      api_base: http://localhost:12434/v1
      api_key: openai-unlimited-local
```

---

### Aider

```bash
export OPENAI_API_BASE=http://localhost:12434/v1
export OPENAI_API_KEY=openai-unlimited-local
aider --model gpt-5
```

---

## 🔌 Mode 3 — MCP Server (stdio)

```bash
unlimitedai --mcp
```

Connects via stdio. Used by Cursor MCP, Claude Desktop, and any MCP-compatible client.

### Cursor `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "openai-unlimited": {
      "command": "unlimitedai",
      "args": ["--mcp"]
    }
  }
}
```

### Claude Desktop `claude_desktop_config.json`

```json
{
  "mcpServers": {
    "openai-unlimited": {
      "command": "unlimitedai",
      "args": ["--mcp"]
    }
  }
}
```

### MCP tools

| Tool | Input | Description |
|---|---|---|
| `chat` | `message`, `model` | Chat with GPT — pick any model |
| `read_file` | `path` | Read a local file into context |
| `write_file` | `path`, `content` | Write content to a local file |
| `list_files` | `directory` | List all files in a directory |
| `run_shell` | `command`, `cwd` | Run a shell command |

**Example tool call:**
```json
{
  "tool": "chat",
  "arguments": {
    "message": "refactor this function to use async/await",
    "model": "o3"
  }
}
```

---

## 🌍 Mode 4 — MCP HTTP SSE (remote agents)

```bash
unlimitedai --mcp-http
```

```
  SSE endpoint → http://localhost:12435/sse
  Same 5 tools as stdio MCP above
```

Use in n8n, Zapier, or any HTTP-based MCP client.

---

## ⚡ Mode 5 — Everything at once

```bash
unlimitedai --all
```

Starts API (`:12434`) + MCP HTTP (`:12435`) in background threads, then opens the coding agent in the foreground.

---

## 🧠 Models

| Model | Best for |
|---|---|
| `auto` | Let GPT pick the best model (default) |
| `gpt-5` | Most capable, complex tasks |
| `gpt-5-mini` | Fast + very capable |
| `gpt-4o` | Balanced, multimodal |
| `gpt-4o-mini` | Lightweight, fastest |
| `o3` | Deep reasoning, math, hard code |
| `o4-mini` | Reasoning, fast |

Switch model anywhere:
```bash
# agent
/model o3

# API
"model": "gpt-5"

# MCP tool arg
"model": "o3"

# SDK
model="gpt-4o"
```

---

## 📋 Requirements

- Python 3.8+
- Internet connection
- Dependencies auto-installed on first run (`httpx`, `fastapi`, `uvicorn`, `mcp`)

Or install manually:
```bash
pip install -r requirements.txt
```

---

## 📁 Files

```
openai-unlimited/
├── run.py            ← everything (agent + API + MCP)
├── setup.py          ← registers `unlimitedai` CLI command
├── pyproject.toml    ← build config
├── requirements.txt  ← httpx fastapi uvicorn mcp
├── server.py         ← legacy redirect → run.py
└── README.md
```

---

## License

MIT — see [LICENSE](LICENSE)

# openai-unlimited

Free GPT in your terminal — coding agent, OpenAI-compatible API, MCP server.  
No login. No API key. No paywall.

> **Not affiliated with OpenAI.** Uses the same anonymous endpoint the ChatGPT web app uses.

---

## Install once — use everywhere

```bash
git clone https://github.com/Singh-army/openai-unlimited
cd openai-unlimited
pip install -e .
```

That's it. You now have the `unlimitedai` command globally in your terminal.

---

## Usage

```
unlimitedai                 →  terminal coding agent  (default)
unlimitedai --server        →  OpenAI API  on localhost:12434/v1
unlimitedai --mcp           →  MCP server  via stdio (Cursor / Claude Desktop)
unlimitedai --mcp-http      →  MCP server  via HTTP SSE on localhost:12435
unlimitedai --all           →  agent + API + MCP HTTP all at once
```

---

## Modes

### 1 · Terminal Coding Agent (default)

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

you › write a fastapi hello world server
agent › ...streams response, auto-saves files, asks before running shell cmds...
```

**Commands inside the agent:**

| Command | What it does |
|---|---|
| `/model gpt-5` | Switch model mid-conversation |
| `/models` | List all available models |
| `/read src/main.py` | Load file into context |
| `/ls ./src` | List files in a directory |
| `/sh npm run build` | Run a shell command manually |
| `/clear` | Clear conversation history |
| `/exit` | Quit |

**Auto-features:**
- Mentions of `file.py` in your prompt → file auto-loaded into context
- Code blocks with a `# path/to/file` comment above → auto-saved to disk
- Shell blocks → agent asks `[y/N]` before running

---

### 2 · OpenAI-Compatible API Server

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

**Settings to paste into any tool:**

```
Base URL : http://localhost:12434/v1
API Key  : openai-unlimited-local
```

#### Cursor (API backend)

`Cursor Settings → Models → Add Model`:
```
Base URL : http://localhost:12434/v1
API Key  : openai-unlimited-local
Model    : gpt-5
```

#### VS Code + Continue

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
    }
  ]
}
```

#### Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:12434/v1",
    api_key="openai-unlimited-local",
)

# choose any model
response = client.chat.completions.create(
    model="gpt-5",          # or: gpt-4o, o3, o4-mini, gpt-5-mini, auto
    messages=[{"role": "user", "content": "write a binary search in Python"}],
    stream=True,
)
for chunk in response:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

#### Node.js / TypeScript

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

#### curl

```bash
# list models
curl http://localhost:12434/v1/models \
  -H "Authorization: Bearer openai-unlimited-local"

# chat
curl http://localhost:12434/v1/chat/completions \
  -H "Authorization: Bearer openai-unlimited-local" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-5",
    "messages": [{"role":"user","content":"hello"}],
    "stream": false
  }'
```

#### LangChain

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-5",
    openai_api_base="http://localhost:12434/v1",
    openai_api_key="openai-unlimited-local",
)
print(llm.invoke("write a SQL query for top 10 customers"))
```

#### LiteLLM

```yaml
# litellm_config.yaml
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

#### Aider

```bash
export OPENAI_API_BASE=http://localhost:12434/v1
export OPENAI_API_KEY=openai-unlimited-local
aider --model gpt-5
```

---

### 3 · MCP Server — stdio (Cursor MCP / Claude Desktop)

```bash
unlimitedai --mcp
```

**Cursor** `~/.cursor/mcp.json`:
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

**Claude Desktop** `claude_desktop_config.json`:
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

**MCP tools exposed:**

| Tool | Description |
|---|---|
| `chat` | Send a message to GPT (pick model in `model` arg) |
| `read_file` | Read a local file into context |
| `write_file` | Write content to a local file |
| `list_files` | List files in a directory recursively |
| `run_shell` | Run a shell command, returns stdout + stderr |

**Example MCP call:**
```json
{
  "tool": "chat",
  "arguments": {
    "message": "refactor this function to use async/await",
    "model": "gpt-5"
  }
}
```

---

### 4 · MCP Server — HTTP SSE (remote agents / n8n)

```bash
unlimitedai --mcp-http
```

```
  SSE endpoint → http://localhost:12435/sse
```

Use in n8n, Zapier, or any HTTP-based MCP client.

---

### 5 · Everything at once

```bash
unlimitedai --all
```

Starts the API server (port 12434) + MCP HTTP (port 12435) in background threads, then opens the terminal agent in the foreground.

---

## Available Models

| Model | Best for |
|---|---|
| `auto` | Let GPT pick (default) |
| `gpt-5` | Best quality, complex reasoning |
| `gpt-5-mini` | Fast + capable |
| `gpt-4o` | Multimodal, balanced |
| `gpt-4o-mini` | Fastest, lightweight tasks |
| `o3` | Deep reasoning, math, code |
| `o4-mini` | Reasoning, fast |

Switch model any time:
- **Agent:** `/model o3`
- **API:** `"model": "o3"` in request body
- **MCP:** `"model": "o3"` in tool arguments

---

## Requirements

- Python 3.8+
- Internet connection (routes through ChatGPT anonymous endpoint)
- Dependencies auto-installed on first run: `httpx fastapi uvicorn mcp`

---

## License

MIT

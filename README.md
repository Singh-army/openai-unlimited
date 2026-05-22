# ⚡ GPT-Free — Free GPT-5 API · No Key · No Login · No Paywall

> **Use GPT-5, GPT-4o, o3 and more — for free, from your terminal or any IDE — no OpenAI account needed.**

[![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](#)
[![Works with Cursor](https://img.shields.io/badge/Cursor_IDE-compatible-purple)](#cursor-ide)
[![Works with VS Code](https://img.shields.io/badge/VS_Code-compatible-blue)](#vs-code--continue)
[![OpenAI Compatible](https://img.shields.io/badge/OpenAI_API-compatible-orange)](#api-server)

---

## 🚀 One-line start

```bash
git clone https://github.com/Singh-army/openai-unlimited && cd openai-unlimited && python run.py
```

Deps install automatically. No config. No `.env`. No API key.

---

## What is this?

**openai-unlimited** is a free, local OpenAI-compatible API server + terminal coding agent.

- ✅ Works as a **drop-in replacement** for `openai.api_base` in any project
- ✅ Plug into **Cursor, VS Code (Continue), Windsurf, Aider, LiteLLM, n8n** — anything that accepts a base URL
- ✅ **Terminal coding agent** — reads your files, writes code, runs shell commands
- ✅ Access **GPT-5, GPT-5-mini, GPT-4o, o3, o4-mini** — all free
- ✅ Streams tokens live — same feel as ChatGPT
- ✅ Single Python file — no Docker, no Node, no setup

---

## 📦 Modes

| Command | What it does |
|---|---|
| `python run.py` | 🤖 Terminal coding agent |
| `python run.py --server` | 🌐 API server (for IDE / MCP / agents) |
| `python run.py --both` | ⚡ Agent + server simultaneously |

---

## 🤖 Terminal Coding Agent

Like **Aider** or **Claude CLI** — but free and zero config.

```
$ python run.py

  ╔══════════════════════════════════════════╗
  ║   openai-unlimited  ·  coding agent      ║
  ║   free GPT · file access · shell exec    ║
  ╚══════════════════════════════════════════╝

you › fix the bug in app.py
you › write a REST API in server.js
you › add TypeScript types to utils.ts
you › explain what main.py does
you › write tests for auth.py
```

**Agent superpowers:**
- 📁 Mention any filename → auto-reads it into context
- 💾 Model writes `# path/file.py` above a code block → **auto-saved to disk**
- 🔧 Model suggests a shell command → asks `[y/N]` before running
- 🔄 Full conversation memory across turns

**Slash commands:**
```
/read <file>     inject a file into context
/ls [dir]        list project files
/sh <command>    run a shell command
/model <name>    switch model (gpt-5, gpt-4o, o3 ...)
/clear           clear conversation history
/exit            quit
```

---

## 🌐 API Server

Start it once, use everywhere:

```bash
python run.py --server
```

```
Base URL : http://localhost:12434/v1
API Key  : openai-unlimited-local
```

### Test with curl

```bash
curl http://localhost:12434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer openai-unlimited-local" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"hello"}],"stream":false}'
```

### Use in Python (drop-in replacement)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:12434/v1",
    api_key="openai-unlimited-local",
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Write a Python hello world"}],
)
print(response.choices[0].message.content)
```

### Use in Node.js

```js
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "http://localhost:12434/v1",
  apiKey: "openai-unlimited-local",
});

const res = await client.chat.completions.create({
  model: "gpt-4o",
  messages: [{ role: "user", content: "Hello!" }],
});
console.log(res.choices[0].message.content);
```

---

## 🖥️ Cursor IDE

1. `python run.py --server` (keep terminal open)
2. Cursor → **Settings** → **Models**
3. **Override OpenAI Base URL** → `http://localhost:12434/v1`
4. **OpenAI API Key** → `openai-unlimited-local`
5. **Add Custom Model** → `auto` (or `gpt-4o`, `gpt-5`)
6. Click **Verify** ✅

> Use **Chat mode** (`Ctrl+L`) for best results.

---

## 🟦 VS Code + Continue

Add to `~/.continue/config.json`:

```json
{
  "models": [{
    "title": "GPT-Free (local)",
    "provider": "openai",
    "model": "gpt-4o",
    "apiBase": "http://localhost:12434/v1",
    "apiKey": "openai-unlimited-local"
  }]
}
```

---

## 🤝 MCP / Agent config

```json
{
  "openai": {
    "baseURL": "http://localhost:12434/v1",
    "apiKey": "openai-unlimited-local"
  }
}
```

Compatible with: **LiteLLM · LangChain · LlamaIndex · n8n · Flowise · Aider · Anything OpenAI-SDK-based**

---

## 🧠 Available Models

| Model | Notes |
|---|---|
| `auto` | Picks the best available (recommended) |
| `gpt-5` | Latest GPT-5 |
| `gpt-5-mini` | Fast + efficient |
| `gpt-4o` | Multimodal |
| `gpt-4o-mini` | Small & fast |
| `o3` | Reasoning model |
| `o4-mini` | Fast reasoning |

---

## ⚙️ Requirements

- Python 3.8+
- Internet connection
- That's it — deps install automatically

---

## ⭐ If this helped you, star the repo!

[![Star this repo](https://img.shields.io/github/stars/Singh-army/openai-unlimited?style=social)](https://github.com/Singh-army/openai-unlimited/stargazers)

**Share it with devs who hate paying for API keys 👇**

---

> ⚠️ Not affiliated with OpenAI. For personal and educational use only.

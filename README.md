# openai-unlimited

Free GPT in your terminal + OpenAI-compatible API server — no key, no login, no paywall.

## Quick start

```bash
git clone https://github.com/Singh-army/openai-unlimited
cd openai-unlimited
python run.py
```

Dependencies install automatically on first run.

## Modes

| Command | What it does |
|---|---|
| `python run.py` | Terminal coding agent — reads/writes files, runs shell |
| `python run.py --server` | API server for Cursor / MCP / any OpenAI client |
| `python run.py --both` | Agent + server at the same time |

## Terminal agent

Just talk to it like a senior dev:

```
you › fix the bug in app.py
you › write a REST API in server.js
you › /read config.json     ← inject file into context
you › /ls                   ← list project files
you › /sh npm install       ← run a shell command
you › /model gpt-4o         ← switch model
you › /clear                ← clear context
```

When the model writes code with a filename comment above the block, it is **auto-saved to disk**.
Shell blocks are shown with a `[y/N]` prompt before running.

## Cursor IDE

1. Run `python run.py --server` (keep the terminal open)
2. Open Cursor → Settings → Models
3. Set **Override OpenAI Base URL**: `http://localhost:12434/v1`
4. Set **OpenAI API Key**: `openai-unlimited-local`
5. Add custom model: `auto` (or `gpt-4o`, `gpt-5`, etc.)
6. Click **Verify** ✓

## MCP / other agents

```json
{
  "openai": {
    "baseURL": "http://localhost:12434/v1",
    "apiKey": "openai-unlimited-local"
  }
}
```

## Models

`auto` · `gpt-5` · `gpt-5-mini` · `gpt-4o` · `gpt-4o-mini` · `o3` · `o4-mini`

---

> Not affiliated with OpenAI. For personal / educational use only.

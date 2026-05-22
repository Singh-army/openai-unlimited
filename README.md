# openai-unlimited

Local OpenAI-compatible API server. No login, no API key, no paywall.
Works with **any** tool that accepts a custom OpenAI endpoint.

```
Base URL : http://127.0.0.1:12434/v1
API Key  : openai-unlimited-local
```

---

## Requirements

- Python 3.8+
- Internet connection

---

## Start the server

**Windows:**
```cmd
python server.py
```
or double-click `start.bat`

**Linux / macOS:**
```bash
bash start.sh
```
or:
```bash
python3 server.py
```

> deps auto-install on first run (`fastapi`, `uvicorn`, `httpx`)

---

## Test with curl

```bash
# Health check (no auth needed)
curl http://127.0.0.1:12434/health

# List models
curl http://127.0.0.1:12434/v1/models \
  -H "Authorization: Bearer openai-unlimited-local"

# Chat
curl http://127.0.0.1:12434/v1/chat/completions \
  -H "Authorization: Bearer openai-unlimited-local" \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"Hello!"}]}'

# Streaming
curl http://127.0.0.1:12434/v1/chat/completions \
  -H "Authorization: Bearer openai-unlimited-local" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5","messages":[{"role":"user","content":"Hello!"}],"stream":true}'
```

---

## Python usage

```bash
pip install openai
```

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:12434/v1",
    api_key="openai-unlimited-local",
)

# Non-streaming
res = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(res.choices[0].message.content)

# Streaming
stream = client.chat.completions.create(
    model="gpt-5",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

---

## IDE Integration

### Cursor
`Settings > Models > OpenAI`:
```
Base URL : http://127.0.0.1:12434/v1
API Key  : openai-unlimited-local
```

### VS Code — Continue.dev
`~/.continue/config.json`:
```json
{
  "models": [{
    "title": "openai-unlimited",
    "provider": "openai",
    "model": "auto",
    "apiBase": "http://127.0.0.1:12434/v1",
    "apiKey": "openai-unlimited-local"
  }]
}
```

### MCP Agent
```json
{
  "mcpServers": {
    "openai-unlimited": {
      "baseURL": "http://127.0.0.1:12434/v1",
      "apiKey": "openai-unlimited-local",
      "model": "auto"
    }
  }
}
```

---

## Node.js

```js
import OpenAI from "openai";
const client = new OpenAI({
  baseURL: "http://127.0.0.1:12434/v1",
  apiKey: "openai-unlimited-local",
});
const res = await client.chat.completions.create({
  model: "auto",
  messages: [{ role: "user", content: "Hello!" }],
});
console.log(res.choices[0].message.content);
```

---

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Server info |
| GET | `/health` | No | Health check |
| GET | `/v1/models` | Yes | List models |
| POST | `/v1/chat/completions` | Yes | Chat (stream + non-stream) |
| GET | `/docs` | No | Swagger UI |

---

## Interactive Docs

Open after starting server:
```
http://127.0.0.1:12434/docs
```

---

## Notes
- Windows, Linux, macOS supported
- Not affiliated with OpenAI

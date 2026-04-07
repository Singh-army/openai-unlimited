# openai-unlimited

`openai-unlimited` is a Windows terminal and local API wrapper for the anonymous chat flow.

This project is **beta**.

- terminal works
- model selection works
- local API works
- current flow is free while the anonymous endpoint stays available
- upstream changes can break compatibility at any time
- no extra install needed beyond Windows PowerShell

This project is not affiliated with OpenAI.

## What You Get

- 1-click start
- 1-click stop
- terminal chat
- model selection from live available models
- local OpenAI-compatible API for apps and editors
- local session continuity and saved device id

## Start

Double-click:

```text
start_openai_unlimited.cmd
```

Or run:

```powershell
.\start_openai_unlimited.cmd
```

## Stop

Double-click:

```text
stop_openai_unlimited.cmd
```

Or run:

```powershell
.\stop_openai_unlimited.cmd
```

## Terminal Commands

- `/help`
- `/models`
- `/categories`
- `/model <slug>`
- `/state`
- `/new`
- `/device-reset`
- `/exit`

Use `/models` to see live model choices, then `/model <slug>` to switch.

## Current Model Slugs

These are the current live slugs seen by the terminal:

- `auto`
- `gpt-5-3`
- `gpt-5-2`
- `gpt-5-1`
- `gpt-5`
- `gpt-5-mini`

Examples:

```text
/model auto
/model gpt-5-3
/model gpt-5-mini
```

The live list can change upstream. Use `/models` for the latest available slugs, tool flags, and token limits.

## Local API

- base URL: `http://127.0.0.1:12434/v1`
- bearer key: `openai-unlimited-local`
- endpoints:
- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`

Example:

```powershell
$headers = @{ Authorization = "Bearer openai-unlimited-local" }
Invoke-RestMethod `
  -Uri "http://127.0.0.1:12434/v1/chat/completions" `
  -Headers $headers `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"model":"auto","messages":[{"role":"user","content":"Reply with OK only."}],"stream":false}'
```

## Use In Editors And Tools

You can use `openai-unlimited` in tools that support a custom OpenAI-compatible endpoint.

It can be used in a similar way to Ollama in apps that let you set:

- custom base URL
- custom bearer key
- model name from `/v1/models`

It is not an Ollama server. It is a local OpenAI-compatible endpoint.

## Important Limits

- beta project
- Windows-first setup
- depends on current anonymous endpoint behavior
- model list can change without notice
- some upstream tools and flags may stop working without warning

## Local Data

Runtime state is stored locally in:

```text
openai_unlimited_terminal_data/
```

That folder can contain local state, cache, and session continuity data. It is ignored by Git.

## Credits

Credits: [Shannsingh.com](https://shannsingh.com)

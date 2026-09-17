# Universal LLM Proxy for Claude Code & Desktop
**Developed by Mahesh Kumar Dey** 🚀

This is a powerful, lightweight proxy server that allows you to use **ANY LLM Provider** (OpenAI, NVIDIA NIM, Google Gemini, Groq, Together AI, Ollama, etc.) seamlessly within **Claude Desktop** and the **Claude Code CLI**.

It acts as a Universal Translator: it accepts Anthropic API requests (including native tool calling, streaming, and vision), translates them to standard OpenAI API format, fetches responses from your chosen provider, and translates them back to Anthropic format on-the-fly.

## ✨ Features
- **Multi-Model & Multi-Provider:** Configure multiple models (NVIDIA, Gemini, OpenAI, Groq, Ollama) in `config.yaml` and switch between them directly from Claude Desktop's UI dropdown!
- **Dynamic Routing:** Automatically routes each chat request to the specific provider base URL and API key corresponding to the selected model.
- **Universal Compatibility:** Run Claude Code CLI with ANY OpenAI-compatible API endpoint.
- **Full Tool Calling Support:** Seamlessly translates Claude Code's Anthropic function/tool calls into native OpenAI tool calls (and translates responses back).
- **Keep-Alive System:** Prevents Claude Desktop from timing out during slow cold-starts (perfect for heavy models like NVIDIA GLM-5.3 or Llama 3.1).
- **Passthrough Mode:** Can also act as a standard Anthropic proxy if you want to route official Claude traffic.

---

## 🚀 How to Setup

### 1. Install Requirements
Make sure you have Python installed, then install the required packages:
```bash
pip install -r requirements.txt
```

### 2. Configure Your Models & Providers
Edit `config.yaml` to set your desired models and API keys. All models configured under `models:` will appear in Claude Desktop's model dropdown menu!

```yaml
# config.yaml
server:
  host: "127.0.0.1"
  port: 4000
  api_key: "sk-proxy-universal-1234"

default_model: "nvidia-glm-5.3-flash"

models:
  - id: "nvidia-glm-5.3-flash"
    display_name: "NVIDIA GLM-5.3 Flash"
    type: "openai"
    base_url: "https://integrate.api.nvidia.com/v1"
    api_key: "nvapi-YOUR_KEY"
    model: "z-ai/glm-5.3-flash"

  - id: "gemini-2.5-flash"
    display_name: "Google Gemini 2.5 Flash"
    type: "openai"
    base_url: "https://generativelanguage.googleapis.com/v1beta/openai/"
    api_key: "AIzaSy_YOUR_KEY"
    model: "gemini-2.5-flash"

  - id: "openai-gpt-4o"
    display_name: "OpenAI GPT-4o"
    type: "openai"
    base_url: "https://api.openai.com/v1"
    api_key: "sk-YOUR_KEY"
    model: "gpt-4o"
```

### 3. Start the Server
Run the provided batch script or start it manually:
```bash
start.bat
# OR
python proxy.py
```
*The proxy will start on `http://127.0.0.1:4000`*

---

## 💻 How to use with Claude Code (CLI)
You can force Claude Code to use this proxy instead of official Anthropic servers by setting environment variables:

**For PowerShell:**
```powershell
$env:ANTHROPIC_BASE_URL="http://127.0.0.1:4000"
$env:ANTHROPIC_API_KEY="sk-proxy-universal-1234"
claude
```

**For Bash / Mac / Linux:**
```bash
export ANTHROPIC_BASE_URL="http://127.0.0.1:4000"
export ANTHROPIC_API_KEY="sk-proxy-universal-1234"
claude
```

---

## 🖥️ How to use with Claude Desktop
Open your Claude Desktop configuration file:
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Add the proxy details inside the `"env"` block:
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:4000/v1",
    "ANTHROPIC_API_KEY": "sk-proxy-universal-1234"
  }
}
```
*Restart Claude Desktop completely. All configured models from `config.yaml` will now appear in your Claude Desktop model selector dropdown!*

---
**Created with ❤️ by Mahesh Kumar Dey**
- 🐙 GitHub: [mdey0108](https://github.com/mdey0108/)
- 🌐 Portfolio: [mdey0108.github.io](https://mdey0108.github.io/)

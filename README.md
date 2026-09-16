# Universal LLM Proxy for Claude Code & Desktop
**Developed by Mahesh Kumar Dey** 🚀

This is a powerful, lightweight proxy server that allows you to use **ANY LLM Provider** (OpenAI, NVIDIA NIM, Groq, Together AI, Ollama, etc.) seamlessly within **Claude Desktop** and the **Claude Code CLI**.

It acts as a Universal Translator: it accepts Anthropic API requests (including native tool calling, streaming, and vision), translates them to the standard OpenAI API format, fetches the response from your chosen provider, and translates it back to Anthropic's format on-the-fly.

## ✨ Features
- **Universal Compatibility:** Run Claude Code with ANY OpenAI-compatible API endpoint.
- **Full Tool Calling Support:** Seamlessly translates Claude Code's Anthropic function/tool calls into native OpenAI tool calls (and translates the responses back).
- **Keep-Alive System:** Prevents Claude Desktop from timing out during slow cold-starts (perfect for heavy models like NVIDIA's GLM-5.3 or Llama 3.1).
- **Passthrough Mode:** Can also act as a standard Anthropic proxy if you just want to route official Claude traffic.
- **Developer Crafted:** Built and optimized by Mahesh Kumar Dey for ultimate flexibility and speed.

---

## 🚀 How to Setup

### 1. Install Requirements
Make sure you have Python installed, then install the required packages:
```bash
pip install -r requirements.txt
```

### 2. Configure Your Provider
Edit `config.yaml` to set your desired LLM API. 
You can use NVIDIA, Groq, OpenAI, Ollama, or any other provider!

```yaml
# config.yaml
provider:
  type: "openai"
  base_url: "https://api.groq.com/openai/v1"
  api_key: "gsk_your_groq_api_key"
  model: "llama-3.1-70b-versatile"
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
You can force Claude Code to use this proxy instead of the official Anthropic servers by setting two environment variables before running it.

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
*Note: The API key here is just for local proxy authentication. Your real API key stays safe inside `config.yaml`.*

---

## 🖥️ How to use with Claude Desktop
Open your Claude Desktop configuration file.
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Add the proxy details inside the `"env"` block:
```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:4000/v1",
    "ANTHROPIC_API_KEY": "sk-proxy-universal-1234"
  },
  "mcpServers": {
    // your existing MCP servers...
  }
}
```
*Restart Claude Desktop completely for the changes to take effect.*

---
**Created with ❤️ by Mahesh Kumar Dey**
- 🐙 GitHub: [mdey0108](https://github.com/mdey0108/)
- 🌐 Portfolio: [mdey0108.github.io](https://mdey0108.github.io/)

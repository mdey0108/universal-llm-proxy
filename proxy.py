"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    Universal LLM Proxy Server                                ║
║                    Developed by Mahesh Kumar Dey                             ║
║                                                                              ║
║  Use ANY LLM provider inside Claude Desktop App & Claude Code CLI.           ║
║  Translates between Anthropic Messages API ↔ OpenAI Chat Completions API.    ║
║                                                                              ║
║  All models appear as Claude Sonnet / Claude Opus to the client.             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import time
import uuid
import sys
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import httpx
import yaml
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse

# Fix Windows console encoding — cp1252 can't handle Unicode
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Console Colors
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class C:
    """ANSI color codes for beautiful console output."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    # Colors
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    # Backgrounds
    BG_GREEN  = "\033[42m"
    BG_BLUE   = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN   = "\033[46m"


def banner():
    """Print startup banner."""
    print(f"""
{C.CYAN}{C.BOLD}+==============================================================+
|           Universal LLM Proxy Server                         |
|                                                              |
|   Use ANY LLM in Claude Desktop & Claude Code                |
+==============================================================+{C.RESET}
""")


def log_info(msg: str):
    print(f"  {C.CYAN}[i]{C.RESET}  {msg}")

def log_success(msg: str):
    print(f"  {C.GREEN}[+]{C.RESET}  {msg}")

def log_warn(msg: str):
    print(f"  {C.YELLOW}[!]{C.RESET}  {C.YELLOW}{msg}{C.RESET}")

def log_error(msg: str):
    print(f"  {C.RED}[x]{C.RESET}  {C.RED}{msg}{C.RESET}")

def log_request(method: str, path: str, detail: str = ""):
    ts = time.strftime("%H:%M:%S")
    extra = f"  {C.DIM}{detail}{C.RESET}" if detail else ""
    print(f"  {C.DIM}{ts}{C.RESET}  {C.MAGENTA}{C.BOLD}{method}{C.RESET} {C.WHITE}{path}{C.RESET}{extra}")

def log_proxy(direction: str, msg: str):
    arrow = f"{C.BLUE}->{C.RESET}" if direction == "out" else f"{C.GREEN}<-{C.RESET}"
    print(f"         {arrow}  {msg}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Configuration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONFIG_PATH = Path(__file__).parent / "config.yaml"

def load_config() -> dict:
    """Load configuration from config.yaml."""
    if not CONFIG_PATH.exists():
        log_error(f"Config file not found: {CONFIG_PATH}")
        log_info("Please create config.yaml — see README.md for examples.")
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Validate required fields
    required = {
        "server.host": config.get("server", {}).get("host"),
        "server.port": config.get("server", {}).get("port"),
        "server.api_key": config.get("server", {}).get("api_key"),
        "provider.type": config.get("provider", {}).get("type"),
        "provider.base_url": config.get("provider", {}).get("base_url"),
        "provider.api_key": config.get("provider", {}).get("api_key"),
        "provider.model": config.get("provider", {}).get("model"),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        log_error(f"Missing config fields: {', '.join(missing)}")
        sys.exit(1)

    return config


config = load_config()
SERVER = config["server"]
PROVIDER = config["provider"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Claude Model Definitions (what Claude Desktop sees)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CLAUDE_MODELS = [
    {
        "id": "claude-sonnet-4-20250514",
        "display_name": "Claude Sonnet 4",
        "created_at": "2025-05-14T00:00:00Z",
    },
    {
        "id": "claude-opus-4-20250918",
        "display_name": "Claude Opus 4",
        "created_at": "2025-09-18T00:00:00Z",
    },
    {
        "id": "claude-3-5-sonnet-20241022",
        "display_name": "Claude 3.5 Sonnet",
        "created_at": "2024-10-22T00:00:00Z",
    },
    {
        "id": "claude-3-opus-20240229",
        "display_name": "Claude 3 Opus",
        "created_at": "2024-02-29T00:00:00Z",
    },
    {
        "id": "claude-3-5-haiku-20241022",
        "display_name": "Claude 3.5 Haiku",
        "created_at": "2024-10-22T00:00:00Z",
    },
]

# The model name we report back in responses
DEFAULT_RESPONSE_MODEL = "claude-sonnet-4-20250514"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Translation: Anthropic → OpenAI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _extract_text_from_content(content) -> str:
    """Extract plain text from Anthropic content (string or list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "image":
                    # Convert image blocks to a placeholder description
                    parts.append("[Image provided]")
        return "\n".join(parts) if parts else ""
    return str(content)


def anthropic_to_openai(body: dict) -> dict:
    """
    Convert an Anthropic Messages API request to an OpenAI Chat Completions request.

    Anthropic format:
    {
        "model": "claude-...",
        "max_tokens": 1024,
        "system": "You are helpful",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": true,
        "temperature": 0.7,
        "top_p": 1.0
    }

    OpenAI format:
    {
        "model": "gpt-4o",
        "max_tokens": 1024,
        "messages": [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"}
        ],
        "stream": true,
        "temperature": 0.7,
        "top_p": 1.0
    }
    """
    openai_messages = []

    # Handle system prompt — Anthropic has it as top-level, OpenAI as a message
    system = body.get("system")
    if system:
        if isinstance(system, list):
            # Anthropic system can be a list of content blocks
            system_text = _extract_text_from_content(system)
        else:
            system_text = str(system)
        if system_text.strip():
            openai_messages.append({"role": "system", "content": system_text})

    # Convert messages
    for msg in body.get("messages", []):
        role = msg.get("role", "user")
        content = msg.get("content")

        # Convert content blocks to plain text for OpenAI
        if isinstance(content, list):
            # Check for tool_use or tool_result blocks
            has_tool_use = any(isinstance(b, dict) and b.get("type") == "tool_use" for b in content)
            has_tool_result = any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content)

            if has_tool_use:
                # Assistant message with tool calls
                text_content = ""
                tool_calls = []
                for b in content:
                    if b.get("type") == "text":
                        text_content += b.get("text", "") + "\n"
                    elif b.get("type") == "tool_use":
                        tool_calls.append({
                            "id": b.get("id"),
                            "type": "function",
                            "function": {
                                "name": b.get("name"),
                                "arguments": json.dumps(b.get("input", {}))
                            }
                        })
                
                openai_msg = {"role": "assistant"}
                if text_content.strip():
                    openai_msg["content"] = text_content.strip()
                else:
                    openai_msg["content"] = None
                    
                if tool_calls:
                    openai_msg["tool_calls"] = tool_calls
                openai_messages.append(openai_msg)
                continue
                
            elif has_tool_result:
                # User message with tool results
                for b in content:
                    if b.get("type") == "text":
                        openai_messages.append({"role": "user", "content": b.get("text", "")})
                    elif b.get("type") == "tool_result":
                        res_content = b.get("content", "")
                        if isinstance(res_content, list):
                            res_content = _extract_text_from_content(res_content)
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": b.get("tool_use_id"),
                            "content": str(res_content)
                        })
                continue

            # Check if there are image blocks — convert to OpenAI vision format
            has_images = any(
                isinstance(b, dict) and b.get("type") == "image"
                for b in content
            )
            if has_images:
                openai_content = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            openai_content.append({
                                "type": "text",
                                "text": block.get("text", "")
                            })
                        elif block.get("type") == "image":
                            source = block.get("source", {})
                            if source.get("type") == "base64":
                                media_type = source.get("media_type", "image/png")
                                data = source.get("data", "")
                                openai_content.append({
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{media_type};base64,{data}"
                                    }
                                })
                            elif source.get("type") == "url":
                                openai_content.append({
                                    "type": "image_url",
                                    "image_url": {
                                        "url": source.get("url", "")
                                    }
                                })
                    elif isinstance(block, str):
                        openai_content.append({"type": "text", "text": block})
                openai_messages.append({"role": role, "content": openai_content})
            else:
                # Text-only content blocks — flatten to string
                text = _extract_text_from_content(content)
                openai_messages.append({"role": role, "content": text})
        elif isinstance(content, str):
            openai_messages.append({"role": role, "content": content})
        else:
            openai_messages.append({"role": role, "content": str(content) if content else ""})

    # Build OpenAI request
    openai_body = {
        "model": PROVIDER["model"],
        "messages": openai_messages,
    }

    # Map tools
    tools = body.get("tools")
    if tools:
        openai_tools = []
        for t in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": t.get("name"),
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {})
                }
            })
        openai_body["tools"] = openai_tools

    tool_choice = body.get("tool_choice")
    if tool_choice:
        t_type = tool_choice.get("type")
        if t_type == "auto":
            openai_body["tool_choice"] = "auto"
        elif t_type == "any":
            openai_body["tool_choice"] = "required"
        elif t_type == "tool":
            openai_body["tool_choice"] = {
                "type": "function",
                "function": {"name": tool_choice.get("name")}
            }

    # Map parameters
    if "max_tokens" in body:
        openai_body["max_tokens"] = body["max_tokens"]
    if "temperature" in body:
        openai_body["temperature"] = body["temperature"]
    if "top_p" in body:
        openai_body["top_p"] = body["top_p"]
    if "stop_sequences" in body:
        openai_body["stop"] = body["stop_sequences"]
    if body.get("stream"):
        openai_body["stream"] = True
        # Request usage in stream for token counting
        openai_body["stream_options"] = {"include_usage": True}

    return openai_body


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Translation: OpenAI → Anthropic (Non-Streaming)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _map_finish_reason(reason: str | None) -> str:
    """Map OpenAI finish_reason to Anthropic stop_reason."""
    mapping = {
        "stop": "end_turn",
        "length": "max_tokens",
        "content_filter": "end_turn",
        "tool_calls": "tool_use",
        "function_call": "tool_use",
    }
    return mapping.get(reason or "", "end_turn")


def openai_to_anthropic(openai_response: dict, requested_model: str) -> dict:
    """
    Convert an OpenAI Chat Completions response to an Anthropic Messages response.

    OpenAI format:
    {
        "id": "chatcmpl-...",
        "choices": [{"message": {"role": "assistant", "content": "Hi!"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    }

    Anthropic format:
    {
        "id": "msg_...",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "Hi!"}],
        "model": "claude-sonnet-4-20250514",
        "stop_reason": "end_turn",
        "stop_sequence": null,
        "usage": {"input_tokens": 10, "output_tokens": 5}
    }
    """
    choice = openai_response.get("choices", [{}])[0]
    message = choice.get("message", {})
    usage = openai_response.get("usage", {})

    content_text = message.get("content", "") or ""
    content_blocks = [{"type": "text", "text": content_text}]

    # Handle tool calls if present
    tool_calls = message.get("tool_calls", [])
    if tool_calls:
        for tc in tool_calls:
            func = tc.get("function", {})
            try:
                tool_input = json.loads(func.get("arguments", "{}"))
            except json.JSONDecodeError:
                tool_input = {"raw": func.get("arguments", "")}
            content_blocks.append({
                "type": "tool_use",
                "id": tc.get("id", f"toolu_{uuid.uuid4().hex[:24]}"),
                "name": func.get("name", "unknown"),
                "input": tool_input,
            })

    return {
        "id": f"msg_{uuid.uuid4().hex[:24]}",
        "type": "message",
        "role": "assistant",
        "content": content_blocks,
        "model": requested_model if requested_model in [m["id"] for m in CLAUDE_MODELS] else DEFAULT_RESPONSE_MODEL,
        "stop_reason": _map_finish_reason(choice.get("finish_reason")),
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Translation: OpenAI → Anthropic (Streaming SSE)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def stream_openai_to_anthropic(
    openai_stream: AsyncGenerator,
    requested_model: str,
) -> AsyncGenerator[str, None]:
    """
    Translate an OpenAI streaming response into Anthropic SSE events.

    OpenAI SSE format:
        data: {"choices": [{"delta": {"content": "Hello"}}]}
        data: [DONE]

    Anthropic SSE format:
        event: message_start
        data: {"type": "message_start", "message": {...}}

        event: content_block_start
        data: {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}

        event: content_block_delta
        data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello"}}

        event: content_block_stop
        data: {"type": "content_block_stop", "index": 0}

        event: message_delta
        data: {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 5}}

        event: message_stop
        data: {"type": "message_stop"}
    """

    # Track state
    output_tokens = 0
    input_tokens = 0
    finish_reason = None
    has_content = False
    
    is_text_block_open = True
    active_tool_calls = set()

    # 4. Process OpenAI stream chunks
    async for chunk_data in openai_stream:
        if not chunk_data:
            continue

        # Parse OpenAI chunk
        try:
            chunk = json.loads(chunk_data)
        except json.JSONDecodeError:
            continue

        # Extract usage from the final chunk (if stream_options.include_usage was set)
        if chunk.get("usage"):
            usage = chunk["usage"]
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

        choices = chunk.get("choices", [])
        if not choices:
            continue

        choice = choices[0]
        delta = choice.get("delta", {})
        
        # --- Handle Text Content ---
        content = delta.get("content")
        # Support reasoning models (GLM-5.3, DeepSeek) that send 'reasoning_content'
        if not content and "reasoning_content" in delta:
            content = delta.get("reasoning_content")

        if content:
            if not is_text_block_open:
                # Edge case: text after tool calls. Unlikely in OpenAI, but just ignore or handle.
                pass
            else:
                has_content = True
                output_tokens += 1  # Rough approximation
                delta_event = {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {
                        "type": "text_delta",
                        "text": content,
                    },
                }
                yield f"event: content_block_delta\ndata: {json.dumps(delta_event)}\n\n"

        # --- Handle Tool Calls ---
        tool_calls = delta.get("tool_calls")
        if tool_calls:
            if is_text_block_open:
                # Close the text block
                yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"
                is_text_block_open = False
                
            for tc in tool_calls:
                idx = tc.get("index", 0)
                anthropic_idx = idx + 1  # offset by 1 because text is 0

                # If this is the start of a new tool call
                if tc.get("id"):
                    # If we are starting a new one, and there was a previous one, close the previous one
                    if anthropic_idx - 1 in active_tool_calls:
                        yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': anthropic_idx - 1})}\n\n"
                        active_tool_calls.remove(anthropic_idx - 1)
                        
                    start_block = {
                        "type": "content_block_start",
                        "index": anthropic_idx,
                        "content_block": {
                            "type": "tool_use",
                            "id": tc.get("id"),
                            "name": tc.get("function", {}).get("name", "")
                        }
                    }
                    yield f"event: content_block_start\ndata: {json.dumps(start_block)}\n\n"
                    active_tool_calls.add(anthropic_idx)

                # If there are arguments streaming
                args = tc.get("function", {}).get("arguments")
                if args:
                    delta_event = {
                        "type": "content_block_delta",
                        "index": anthropic_idx,
                        "delta": {
                            "type": "input_json_delta",
                            "partial_json": args
                        }
                    }
                    yield f"event: content_block_delta\ndata: {json.dumps(delta_event)}\n\n"

        fr = choice.get("finish_reason")
        if fr:
            finish_reason = fr

    # 5. Emit remaining content_block_stops
    if is_text_block_open:
        yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"
        is_text_block_open = False
        
    for idx in list(active_tool_calls):
        yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': idx})}\n\n"
        active_tool_calls.remove(idx)

    # 6. Emit message_delta
    # Map finish_reason properly (tool_calls -> tool_use)
    if finish_reason == "tool_calls":
        anthropic_stop_reason = "tool_use"
    else:
        anthropic_stop_reason = _map_finish_reason(finish_reason)
        
    message_delta = {
        "type": "message_delta",
        "delta": {
            "stop_reason": anthropic_stop_reason,
            "stop_sequence": None,
        },
        "usage": {
            "output_tokens": output_tokens,
        },
    }
    yield f"event: message_delta\ndata: {json.dumps(message_delta)}\n\n"

    # 7. Emit message_stop
    yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# OpenAI Stream Reader
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def read_openai_sse(response: httpx.Response) -> AsyncGenerator[str, None]:
    """Read SSE events from an OpenAI streaming response and yield data payloads."""
    async for line in response.aiter_lines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                return
            yield data


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FastAPI Application
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Shared HTTP client
http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Manage HTTP client lifecycle."""
    global http_client
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=30.0))
    log_success("HTTP client ready (timeout: 300s)")
    yield
    if http_client:
        await http_client.aclose()


app = FastAPI(
    title="""
Universal LLM Proxy Server for Claude Code & Desktop
Developed by mdey0
---------------------------------------------------
This proxy seamlessly translates Anthropic API calls into OpenAI API calls,
allowing Claude Code and Claude Desktop to use ANY LLM provider.
""",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────────────────────────
# Auth middleware
# ─────────────────────────────────────────────────────────────────────────────

def verify_auth(request: Request) -> bool:
    """Verify the incoming request has a valid API key."""
    expected = SERVER["api_key"]

    # Check x-api-key header (Anthropic style)
    api_key = request.headers.get("x-api-key")
    if api_key and api_key.strip() == expected.strip():
        return True

    # Check Authorization: Bearer header (OpenAI style)
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer ") and auth[7:].strip() == expected.strip():
        return True

    # Also accept Authorization without Bearer prefix
    if auth and auth.strip() == expected.strip():
        return True

    return False


# ─────────────────────────────────────────────────────────────────────────────
# GET /v1/models — Return fake Claude models
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/v1/models")
async def list_models(request: Request):
    """Return a list of Claude models so Claude Desktop shows the right options."""
    log_request("GET", "/v1/models")

    if not verify_auth(request):
        return JSONResponse(status_code=401, content={"error": {"message": "Invalid API key"}})

    models_data = []
    for m in CLAUDE_MODELS:
        models_data.append({
            "id": m["id"],
            "object": "model",
            "created": int(time.time()),
            "owned_by": "anthropic",
            "display_name": m["display_name"],
            "type": "model",
        })

    log_proxy("out", f"Returning {len(models_data)} Claude model(s)")
    return JSONResponse(content={"data": models_data, "object": "list"})


# ─────────────────────────────────────────────────────────────────────────────
# POST /v1/messages — Main proxy endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/v1/messages")
async def create_message(request: Request):
    """
    Receive Anthropic Messages API request from Claude Desktop/Code,
    translate and forward to the configured backend provider.
    """
    # Auth check
    if not verify_auth(request):
        log_warn("Unauthorized request rejected")
        return JSONResponse(
            status_code=401,
            content={
                "type": "error",
                "error": {
                    "type": "authentication_error",
                    "message": "Invalid API key. Check your proxy api_key in config.yaml.",
                },
            },
        )

    # Parse request body
    try:
        body = await request.json()
    except Exception as e:
        log_error(f"Failed to parse request body: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "type": "error",
                "error": {"type": "invalid_request_error", "message": str(e)},
            },
        )

    requested_model = body.get("model", DEFAULT_RESPONSE_MODEL)
    is_streaming = body.get("stream", False)

    log_request(
        "POST", "/v1/messages",
        f"model={requested_model}  stream={is_streaming}  max_tokens={body.get('max_tokens', '?')}"
    )

    # ── Intercept Claude Desktop 'Test Connection' ──
    # Claude Desktop sends a max_tokens=1, stream=False request to test the connection.
    # On slow backends (like GLM-5.3 cold start), this non-streaming test times out.
    if not is_streaming and body.get("max_tokens") == 1:
        log_proxy("in", f"← Intercepted Claude 'Test connection' probe. Returning mock success.")
        return JSONResponse(content={
            "id": f"msg_{uuid.uuid4().hex[:24]}",
            "type": "message",
            "role": "assistant",
            "model": requested_model,
            "content": [{"type": "text", "text": "Connection successful!"}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 5}
        })

    # ── Route based on provider type ──
    provider_type = PROVIDER["type"].lower()

    if provider_type == "anthropic":
        # Passthrough — forward as-is to Anthropic-compatible backend
        return await _proxy_anthropic(body, requested_model, is_streaming)
    elif provider_type == "openai":
        # Translate — convert to OpenAI format and back
        return await _proxy_openai(body, requested_model, is_streaming)
    else:
        log_error(f"Unknown provider type: {provider_type}")
        return JSONResponse(
            status_code=500,
            content={
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": f"Unknown provider type '{provider_type}'. Use 'openai' or 'anthropic'.",
                },
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# Proxy: OpenAI-compatible backends
# ─────────────────────────────────────────────────────────────────────────────

async def _proxy_openai(body: dict, requested_model: str, is_streaming: bool):
    """Translate Anthropic request → OpenAI, forward, translate response back."""
    openai_body = anthropic_to_openai(body)

    base_url = PROVIDER["base_url"].rstrip("/")
    url = f"{base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {PROVIDER['api_key']}",
        "Content-Type": "application/json",
    }

    log_proxy("out", f"→ {C.BLUE}{PROVIDER['model']}{C.RESET} @ {C.DIM}{base_url}{C.RESET}")

    try:
        if is_streaming:
            # ── Streaming mode ──
            async def generate():
                # ── MUST send message_start first before any pings! ──
                message_start = {
                    "type": "message",
                    "id": f"msg_{uuid.uuid4().hex[:24]}",
                    "role": "assistant",
                    "content": [],
                    "model": requested_model,
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": 0, "output_tokens": 0}
                }
                yield f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': message_start})}\n\n"
                
                content_block_start = {
                    "type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}
                }
                yield f"event: content_block_start\ndata: {json.dumps(content_block_start)}\n\n"

                req = http_client.build_request(
                    "POST", url,
                    headers=headers,
                    json=openai_body,
                    timeout=httpx.Timeout(300.0, connect=30.0)
                )
                
                task = asyncio.create_task(http_client.send(req, stream=True))
                
                # Keep client alive while waiting for backend (useful for slow cold starts)
                while not task.done():
                    done, pending = await asyncio.wait([task], timeout=10.0)
                    if not done:
                        yield 'event: ping\ndata: {"type": "ping"}\n\n'
                
                try:
                    response = task.result()
                except Exception as e:
                    log_error(f"Backend connection error: {e}")
                    error_json = json.dumps({"type": "error", "error": {"type": "api_error", "message": f"Backend error: {str(e)}"}})
                    yield f'event: error\ndata: {error_json}\n\n'
                    return

                if response.status_code != 200:
                    error_body = await response.aread()
                    await response.aclose()
                    error_text = error_body.decode("utf-8", errors="replace")
                    log_error(f"Backend error {response.status_code}: {error_text[:200]}")
                    error_json = json.dumps({"type": "error", "error": {"type": "api_error", "message": f"Backend error {response.status_code}: {error_text[:200]}"}})
                    yield f'event: error\ndata: {error_json}\n\n'
                    return

                log_proxy("in", f"← Streaming response from backend...")
                try:
                    openai_sse = read_openai_sse(response)
                    async for event in stream_openai_to_anthropic(openai_sse, requested_model):
                        yield event
                finally:
                    await response.aclose()

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        else:
            # ── Non-streaming mode ──
            response = await http_client.post(url, headers=headers, json=openai_body)

            if response.status_code != 200:
                error_text = response.text
                log_error(f"Backend error {response.status_code}: {error_text[:200]}")
                return _make_anthropic_error(response.status_code, error_text)

            openai_response = response.json()
            anthropic_response = openai_to_anthropic(openai_response, requested_model)

            log_proxy("in", f"← {C.GREEN}OK{C.RESET}  tokens: in={anthropic_response['usage']['input_tokens']} out={anthropic_response['usage']['output_tokens']}")

            return JSONResponse(content=anthropic_response)

    except httpx.ConnectError as e:
        log_error(f"Connection failed: {e}")
        return _make_anthropic_error(502, f"Cannot connect to backend: {PROVIDER['base_url']}")
    except httpx.ReadTimeout as e:
        log_error(f"Read timeout: {e}")
        return _make_anthropic_error(504, "Backend read timeout")
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        return _make_anthropic_error(500, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Proxy: Anthropic-compatible backends (passthrough)
# ─────────────────────────────────────────────────────────────────────────────

async def _proxy_anthropic(body: dict, requested_model: str, is_streaming: bool):
    """Forward request as-is to an Anthropic-compatible backend."""
    base_url = PROVIDER["base_url"].rstrip("/")
    url = f"{base_url}/messages"

    # Override model name with configured model
    body["model"] = PROVIDER["model"]

    headers = {
        "x-api-key": PROVIDER["api_key"],
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    log_proxy("out", f"→ {C.BLUE}{PROVIDER['model']}{C.RESET} @ {C.DIM}{base_url}{C.RESET}  (passthrough)")

    try:
        if is_streaming:
            async def generate():
                req = http_client.build_request(
                    "POST", url, 
                    headers=headers, 
                    json=body,
                    timeout=httpx.Timeout(300.0, connect=30.0)
                )
                
                task = asyncio.create_task(http_client.send(req, stream=True))
                
                # Keep client alive while waiting for backend
                while not task.done():
                    done, pending = await asyncio.wait([task], timeout=10.0)
                    if not done:
                        yield 'event: ping\ndata: {"type": "ping"}\n\n'
                
                try:
                    response = task.result()
                except Exception as e:
                    log_error(f"Backend connection error: {e}")
                    error_json = json.dumps({"type": "error", "error": {"type": "api_error", "message": f"Backend error: {str(e)}"}})
                    yield f'event: error\ndata: {error_json}\n\n'
                    return

                if response.status_code != 200:
                    error_body = await response.aread()
                    await response.aclose()
                    error_text = error_body.decode("utf-8", errors="replace")
                    log_error(f"Backend error {response.status_code}: {error_text[:200]}")
                    error_json = json.dumps({"type": "error", "error": {"type": "api_error", "message": f"Backend error {response.status_code}: {error_text[:200]}"}})
                    yield f'event: error\ndata: {error_json}\n\n'
                    return

                log_proxy("in", f"← Streaming passthrough...")
                try:
                    async for line in response.aiter_lines():
                        # Rewrite model name in message_start events
                        if "message_start" in line and PROVIDER["model"] in line:
                            line = line.replace(PROVIDER["model"], requested_model)
                        yield line + "\n"
                finally:
                    await response.aclose()

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            response = await http_client.post(url, headers=headers, json=body)

            if response.status_code != 200:
                log_error(f"Backend error {response.status_code}: {response.text[:200]}")
                return _make_anthropic_error(response.status_code, response.text)

            result = response.json()
            # Rewrite model name
            result["model"] = requested_model
            log_proxy("in", f"← {C.GREEN}OK{C.RESET}  (passthrough)")
            return JSONResponse(content=result)

    except httpx.ConnectError as e:
        log_error(f"Connection failed: {e}")
        return _make_anthropic_error(502, f"Cannot connect to backend: {base_url}")
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        return _make_anthropic_error(500, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Error Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_anthropic_error(status_code: int, message: str) -> JSONResponse:
    """Create an Anthropic-format error response."""
    error_types = {
        400: "invalid_request_error",
        401: "authentication_error",
        403: "permission_error",
        404: "not_found_error",
        429: "rate_limit_error",
        500: "api_error",
        502: "api_error",
        503: "overloaded_error",
        504: "api_error",
    }
    return JSONResponse(
        status_code=status_code,
        content={
            "type": "error",
            "error": {
                "type": error_types.get(status_code, "api_error"),
                "message": message[:2000],
            },
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
async def health():
    return {
        "status": "ok",
        "service": "Universal LLM Proxy",
        "provider": PROVIDER["type"],
        "model": PROVIDER["model"],
        "base_url": PROVIDER["base_url"],
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Entry Point
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    banner()

    log_info(f"Provider:  {C.BOLD}{PROVIDER['type'].upper()}{C.RESET}")
    log_info(f"Backend:   {C.CYAN}{PROVIDER['base_url']}{C.RESET}")
    log_info(f"Model:     {C.GREEN}{PROVIDER['model']}{C.RESET}")
    log_info(f"Proxy Key: {C.DIM}{SERVER['api_key'][:10]}...{C.RESET}")
    print()

    log_success(f"Proxy starting on {C.BOLD}http://{SERVER['host']}:{SERVER['port']}{C.RESET}")
    print()

    # Claude Desktop config hint
    print(f"  {C.YELLOW}[>] Claude Desktop Config:{C.RESET}")
    print(f"     Edit: {C.DIM}%APPDATA%\\Claude\\claude_desktop_config.json{C.RESET}")
    print(f"""     {C.DIM}{{
       "env": {{
         "ANTHROPIC_BASE_URL": "http://127.0.0.1:{SERVER['port']}/v1",
         "ANTHROPIC_API_KEY": "{SERVER['api_key']}"
       }}
     }}{C.RESET}""")
    print()

    # Claude Code hint
    print(f"  {C.YELLOW}[>] Claude Code CLI:{C.RESET}")
    print(f"     {C.DIM}$env:ANTHROPIC_BASE_URL=\"http://127.0.0.1:{SERVER['port']}\"{C.RESET}")
    print(f"     {C.DIM}$env:ANTHROPIC_API_KEY=\"{SERVER['api_key']}\"{C.RESET}")
    print(f"     {C.DIM}claude{C.RESET}")
    print()

    print(f"  {C.DIM}{'-' * 56}{C.RESET}")
    print(f"  {C.CYAN}Waiting for requests...{C.RESET}")
    print()

    uvicorn.run(
        app,
        host=SERVER["host"],
        port=int(SERVER["port"]),
        log_level="warning",  # Keep uvicorn quiet — we handle our own logging
    )

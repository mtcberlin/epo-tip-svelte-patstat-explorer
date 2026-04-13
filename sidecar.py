"""Minimal PATSTAT BigQuery API sidecar for the SvelteKit Patent Navigator."""

import asyncio
import json
import os
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from epo.tipdata.patstat import PatstatClient
import uvicorn

app = FastAPI(title="PATSTAT Sidecar")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

client = PatstatClient(env="PROD")

CONFIG_DIR = Path.home() / ".patent-navigator"
CONFIG_FILE = CONFIG_DIR / "config.json"

MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8082/mcp")

MAX_AGENT_ITERATIONS = 15

SYSTEM_PROMPT = """You are a PATSTAT SQL expert. The user asks questions about patent data.
You generate Google BigQuery standard SQL (NOT legacy SQL).

IMPORTANT — you have MCP tools for schema discovery. Use them, do NOT guess table/column names.

## Mandatory workflow (follow this order):
1. Call `list_tables` FIRST to see available tables — do NOT query INFORMATION_SCHEMA or run SHOW TABLES
2. Call `get_table_schema` for each relevant table to get exact column names and types
3. Build your SQL query using the exact schema you discovered
4. Call `execute_query` to run it and verify it works
5. Respond with ONLY the final working SQL query — no explanation, no markdown fences

## Rules:
- NEVER query INFORMATION_SCHEMA, SHOW TABLES, or any metadata tables — use the MCP tools instead
- Only SELECT queries, always with LIMIT (max 500)
- For applicants: JOIN tls207_pers_appln with applt_seq_nr > 0
- For inventors: JOIN tls207_pers_appln with invt_seq_nr > 0
- Person names are uppercase in PATSTAT
- Use appln_filing_year (not appln_filing_date) for year filtering
- Use COUNT(DISTINCT docdb_family_id) for patent family counts
- Be efficient — minimize tool calls, get schema first then write SQL

## Your final response must be ONLY the SQL query, nothing else.
"""


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def _save_config(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


# --- MCP tool conversion ---

def _mcp_tools_to_anthropic(mcp_tools) -> list[dict]:
    """Convert MCP tool objects to Anthropic API tool format."""
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.inputSchema,
        }
        for t in mcp_tools
    ]


# --- Agentic loop (fully async) ---

async def _run_agentic_loop(
    question: str,
    history: list[dict],
    api_key: str,
    model: str,
    mcp_tools: list[dict],
    mcp_call_tool,  # async callable(name, args) -> str
) -> AsyncGenerator[dict, None]:
    """Run the agentic loop. Yields step dicts for SSE streaming.

    Steps: {event: "mcp_connected"|"tool_call"|"tool_result"|"result"|"error", data: {...}}
    """
    if not api_key:
        yield {"event": "error", "data": {"message": "No API key configured."}}
        return

    try:
        import anthropic
    except ImportError:
        yield {"event": "error", "data": {"message": "anthropic package not installed."}}
        return

    try:
        ai_client = anthropic.Anthropic(api_key=api_key)
    except Exception as e:
        yield {"event": "error", "data": {"message": str(e)}}
        return

    # Signal MCP connection to frontend
    if mcp_tools:
        yield {
            "event": "mcp_connected",
            "data": {
                "server": "mtc.berlin PATSTAT MCP Server",
                "tools": [t["name"] for t in mcp_tools],
                "tool_count": len(mcp_tools),
            },
        }

    # Build initial messages
    messages = []
    for entry in history:
        messages.append({"role": entry["role"], "content": entry["content"]})
    messages.append({"role": "user", "content": question})

    for iteration in range(MAX_AGENT_ITERATIONS):
        try:
            kwargs = {
                "model": model,
                "max_tokens": 4096,
                "system": SYSTEM_PROMPT,
                "messages": messages,
            }
            if mcp_tools:
                kwargs["tools"] = mcp_tools

            response = await asyncio.to_thread(ai_client.messages.create, **kwargs)
        except anthropic.AuthenticationError:
            yield {"event": "error", "data": {"message": "Invalid API key."}}
            return
        except Exception as e:
            yield {"event": "error", "data": {"message": str(e)}}
            return

        # Process response content blocks
        has_tool_use = False
        assistant_content = []
        tool_results = []

        for block in response.content:
            assistant_content.append(block)

            if block.type == "tool_use":
                has_tool_use = True

                yield {
                    "event": "tool_call",
                    "data": {"name": block.name, "input": block.input, "iteration": iteration + 1},
                }

                # Call MCP tool (async — stays in the same event loop)
                try:
                    result_text = await mcp_call_tool(block.name, block.input)
                except Exception as e:
                    result_text = f"Tool error: {e}"

                yield {
                    "event": "tool_result",
                    "data": {
                        "name": block.name,
                        "result": result_text[:2000],
                        "iteration": iteration + 1,
                    },
                }

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })

        if has_tool_use:
            messages.append({
                "role": "assistant",
                "content": [_block_to_dict(b) for b in assistant_content],
            })
            messages.append({
                "role": "user",
                "content": tool_results,
            })
        else:
            text_parts = [b.text for b in response.content if b.type == "text"]
            final_text = _extract_sql("\n".join(text_parts))

            # Model sometimes stops without echoing the SQL (it already ran it via execute_query).
            # Fall back to the last execute_query tool call so the client always has runnable SQL.
            if not final_text:
                final_text = _extract_last_sql_from_messages(messages) or ""

            if not final_text:
                yield {
                    "event": "error",
                    "data": {"message": "Agent finished without producing any SQL."},
                }
                return

            yield {
                "event": "result",
                "data": {"text": final_text, "iterations": iteration + 1},
            }
            return

    # Max iterations — try to extract SQL from the last execute_query call
    last_sql = _extract_last_sql_from_messages(messages)
    if last_sql:
        yield {
            "event": "result",
            "data": {"text": last_sql, "iterations": MAX_AGENT_ITERATIONS},
        }
    else:
        yield {
            "event": "error",
            "data": {"message": f"Max iterations ({MAX_AGENT_ITERATIONS}) reached without final answer."},
        }


import re

def _extract_sql(text: str) -> str:
    """Extract SQL from text that may contain markdown fences or explanation."""
    text = text.strip()
    # Try to extract from markdown code fences
    fence_match = re.search(r'```(?:sql)?\s*\n?(.*?)```', text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    # If the text starts with SELECT, it's likely pure SQL
    if re.match(r'^\s*SELECT\b', text, re.IGNORECASE):
        # Take everything up to the first non-SQL line
        lines = text.split('\n')
        sql_lines = []
        for line in lines:
            # Stop at lines that look like natural language explanation
            if sql_lines and re.match(r'^(This|Note|The|I |You |Would|Here)', line.strip()):
                break
            sql_lines.append(line)
        return '\n'.join(sql_lines).strip().rstrip(';')
    return text


def _extract_last_sql_from_messages(messages: list[dict]) -> str | None:
    """Try to find the last execute_query SQL from the conversation history."""
    for msg in reversed(messages):
        content = msg.get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "execute_query":
                    sql = block.get("input", {}).get("query", "")
                    if sql and re.match(r'^\s*SELECT\b', sql, re.IGNORECASE):
                        return sql
    return None


def _block_to_dict(block) -> dict:
    """Convert an Anthropic content block to a dict for message history."""
    if block.type == "text":
        return {"type": "text", "text": block.text}
    elif block.type == "tool_use":
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
    return {"type": "text", "text": str(block)}


# --- MCP client — single persistent session per request ---

async def _create_mcp_session():
    """Create an MCP client session. Returns (session, cleanup) tuple."""
    from mcp.client.streamable_http import streamablehttp_client
    from mcp import ClientSession

    # We need to manage the context managers manually for persistent sessions
    transport_cm = streamablehttp_client(MCP_URL)
    read, write, _ = await transport_cm.__aenter__()
    session = ClientSession(read, write)
    await session.__aenter__()
    await session.initialize()

    async def cleanup():
        try:
            await session.__aexit__(None, None, None)
        except Exception:
            pass
        try:
            await transport_cm.__aexit__(None, None, None)
        except Exception:
            pass

    return session, cleanup


async def _get_mcp_tools_and_caller():
    """Connect to MCP, return (tools, call_tool_fn, cleanup_fn).

    Keeps a single session alive for the duration of the agentic loop.
    """
    try:
        session, cleanup = await _create_mcp_session()
        tools_result = await session.list_tools()
        tools = _mcp_tools_to_anthropic(tools_result.tools)

        async def call_tool(name: str, arguments: dict) -> str:
            try:
                result = await session.call_tool(name, arguments)
                return "\n".join(c.text for c in result.content if hasattr(c, "text"))
            except Exception as e:
                return f"MCP tool call failed: {e}"

        return tools, call_tool, cleanup
    except Exception as e:
        async def noop():
            pass
        return [], None, noop


# --- Pydantic models ---

class QueryRequest(BaseModel):
    sql: str


class NlToSqlRequest(BaseModel):
    question: str
    history: list[dict] = []


class SettingsUpdate(BaseModel):
    api_key: str | None = None
    model: str | None = None


class CoOccurrenceRequest(BaseModel):
    where_clause: str
    cpc_prefix: str | None = None


# --- Endpoints ---

@app.post("/api/co-occurrence")
async def co_occurrence(req: CoOccurrenceRequest):
    """Return CPC section co-occurrence matrix for patents matching the WHERE clause."""
    cpc_filter = ""
    if req.cpc_prefix:
        escaped = req.cpc_prefix.replace("'", "''")
        cpc_filter = f"AND (c1.cpc_class_symbol LIKE '{escaped}%' OR c2.cpc_class_symbol LIKE '{escaped}%')"

    sql = f"""
        SELECT
            SUBSTR(c1.cpc_class_symbol, 1, 1) AS section1,
            SUBSTR(c2.cpc_class_symbol, 1, 1) AS section2,
            COUNT(DISTINCT a.docdb_family_id) AS family_count
        FROM tls201_appln a
        JOIN tls207_pers_appln pa ON a.appln_id = pa.appln_id
        JOIN tls206_person p ON pa.person_id = p.person_id
        JOIN tls224_appln_cpc c1 ON a.appln_id = c1.appln_id
        JOIN tls224_appln_cpc c2 ON a.appln_id = c2.appln_id
        WHERE {req.where_clause}
          AND c1.cpc_class_symbol < c2.cpc_class_symbol
          {cpc_filter}
        GROUP BY section1, section2
        HAVING family_count >= 1
        ORDER BY family_count DESC
    """
    try:
        result = client.sql_query(sql, use_legacy_sql=False)
        return list(result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/patent/{appln_id}")
async def patent_detail(appln_id: int):
    """Return detailed information for a single patent application."""
    basic = client.sql_query(f"""
        SELECT
            a.appln_id, a.appln_auth, a.appln_nr, a.appln_kind,
            a.appln_filing_date, a.appln_filing_year,
            a.docdb_family_id, a.granted,
            t.appln_title AS title, t.appln_title_lg AS title_lang,
            ab.appln_abstract AS abstract
        FROM tls201_appln a
        LEFT JOIN tls202_appln_title t ON a.appln_id = t.appln_id AND t.appln_title_lg = 'en'
        LEFT JOIN tls203_appln_abstr ab ON a.appln_id = ab.appln_id
        WHERE a.appln_id = {appln_id}
        LIMIT 1
    """, use_legacy_sql=False)

    if not basic:
        raise HTTPException(status_code=404, detail="Patent not found")

    applicants = list(client.sql_query(f"""
        SELECT p.person_name, p.person_ctry_code
        FROM tls207_pers_appln pa
        JOIN tls206_person p ON pa.person_id = p.person_id
        WHERE pa.appln_id = {appln_id} AND pa.applt_seq_nr > 0
        ORDER BY pa.applt_seq_nr
    """, use_legacy_sql=False))

    cpc_rows = list(client.sql_query(f"""
        SELECT DISTINCT cpc_class_symbol
        FROM tls224_appln_cpc
        WHERE appln_id = {appln_id}
        ORDER BY cpc_class_symbol
    """, use_legacy_sql=False))

    result = dict(basic[0])
    result["applicants"] = [dict(a) for a in applicants]
    result["cpc_codes"] = [r["cpc_class_symbol"] for r in cpc_rows]
    return result


@app.get("/api/health")
async def health():
    try:
        result = client.sql_query("SELECT 1 AS ok", use_legacy_sql=False)
        return {"ok": True, "message": f"BigQuery connected, returned {len(result)} row(s)"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


@app.post("/api/query")
async def query(req: QueryRequest):
    try:
        result = client.sql_query(req.sql, use_legacy_sql=False)
        return list(result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/settings")
async def get_settings():
    config = _load_config()
    api_key = config.get("api_key", "")
    return {
        "has_api_key": bool(api_key),
        "api_key_preview": f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "",
        "model": config.get("model", "claude-sonnet-4-20250514"),
    }


@app.post("/api/settings")
async def update_settings(req: SettingsUpdate):
    config = _load_config()
    if req.api_key is not None:
        config["api_key"] = req.api_key
    if req.model is not None:
        config["model"] = req.model
    _save_config(config)
    return {"ok": True}


@app.post("/api/nl-to-sql")
async def nl_to_sql(req: NlToSqlRequest):
    """Agentic NL-to-SQL via MCP tools. Returns SSE stream of steps."""
    config = _load_config()
    api_key = config.get("api_key", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="No API key configured. Open Settings to add your Anthropic API key.")

    model = config.get("model", "claude-sonnet-4-20250514")

    # Connect to MCP — one persistent session for the whole request
    mcp_tools, mcp_call_tool, mcp_cleanup = await _get_mcp_tools_and_caller()

    async def generate():
        try:
            async for step in _run_agentic_loop(
                question=req.question,
                history=req.history,
                api_key=api_key,
                model=model,
                mcp_tools=mcp_tools,
                mcp_call_tool=mcp_call_tool or (lambda n, a: "MCP not available"),
            ):
                yield f"data: {json.dumps(step)}\n\n"
            yield "data: {\"event\": \"done\"}\n\n"
        finally:
            await mcp_cleanup()

    return StreamingResponse(generate(), media_type="text/event-stream")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 52081))
    uvicorn.run(app, host="127.0.0.1", port=port)

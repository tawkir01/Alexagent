import asyncio
import socket

import httpx
import pytest
import uvicorn
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from backend.config import settings
from backend.academic import initialize_database
from backend.mcp_server import create_app
from backend.tools import create_mcp_server


@pytest.fixture
async def mcp_server_url():
    initialize_database()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]

    server = uvicorn.Server(
        uvicorn.Config(
            create_app(),
            host="127.0.0.1",
            port=port,
            lifespan="on",
            log_level="error",
        )
    )
    server_task = asyncio.create_task(server.serve())
    for _ in range(100):
        if server.started:
            break
        if server_task.done():
            await server_task
        await asyncio.sleep(0.05)
    assert server.started, "MCP server did not start"
    try:
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        server.should_exit = True
        await server_task


async def test_mcp_initialization_and_tool_discovery(mcp_server_url):
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {settings.mcp_bearer_token}"},
    ) as http_client:
        async with streamable_http_client(mcp_server_url, http_client=http_client) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                initialized = await session.initialize()
                assert initialized.serverInfo.name == "CampusFlow"
                tools = await session.list_tools()
                assert {tool.name for tool in tools.tools} == {
                    "list_upcoming_deadlines",
                    "detect_deadline_changes_and_conflicts",
                    "get_academic_change_history",
                    "record_academic_update",
                    "publish_signature_demo_notice",
                    "simulate_academic_workload",
                    "propose_revised_study_plan",
                    "search_academic_sources",
                    "propose_study_plan",
                }


async def test_mcp_tools_return_source_cited_deadline_data(mcp_server_url):
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {settings.mcp_bearer_token}"},
    ) as http_client:
        async with streamable_http_client(mcp_server_url, http_client=http_client) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                deadlines = await session.call_tool("list_upcoming_deadlines", {})
                assert len(deadlines.structuredContent["assignments"]) == 4
                changes = await session.call_tool("detect_deadline_changes_and_conflicts", {})
                assert changes.structuredContent["changes"][0]["status"] == "verified"
                assert changes.structuredContent["conflicts"] == []
                demo_notice = await session.call_tool("publish_signature_demo_notice", {})
                assert demo_notice.structuredContent["created"] is True
                history = await session.call_tool("get_academic_change_history", {})
                assert any(event["status"] == "disputed" for event in history.structuredContent["history"])
                update = await session.call_tool("record_academic_update", {
                    "record_key": "exam:CS301:midterm",
                    "record_kind": "examination_date",
                    "record_value": "2026-11-07",
                    "source_id": "NOTICE-CAMPUS-78",
                    "source_title": "Updated CS301 midterm notice",
                    "source_type": "notice",
                    "content": "The CS301 midterm date has changed to November 7.",
                })
                assert update.structuredContent["change"]["entity_type"] == "examination"
                sim = await session.call_tool("simulate_academic_workload", {"lost_hours_tomorrow": 2})
                assert sim.structuredContent["scenario"]["lost_hours_tomorrow"] == 2
                revised = await session.call_tool("propose_revised_study_plan", {"lost_hours_tomorrow": 2})
                assert revised.structuredContent["status"] == "pending"
                search = await session.call_tool("search_academic_sources", {"query": "DBMS deadline"})
                assert search.structuredContent["count"] >= 2
                assert all("source_id" in source for source in search.structuredContent["sources"])


async def test_mcp_input_validation_and_pending_study_plan(mcp_server_url):
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {settings.mcp_bearer_token}"},
    ) as http_client:
        async with streamable_http_client(mcp_server_url, http_client=http_client) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                invalid = await session.call_tool("search_academic_sources", {"query": "x"})
                assert invalid.isError
                result = await session.call_tool("propose_study_plan", {})
                assert result.structuredContent["status"] == "pending"


async def test_mcp_bearer_permission_check(mcp_server_url):
    async with httpx.AsyncClient() as client:
        response = await client.get(mcp_server_url)
    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized"}


def test_server_factory_initializes():
    server = create_mcp_server()
    assert server.name == "CampusFlow"

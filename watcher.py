import asyncio
import os
import re
import sys
import time
import traceback
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.config import (
    ENABLE_POWERBI_REFRESH,
    EXCEL_FILE,
    EXCEL_SAVE_WAIT_SECONDS,
    POWERBI_MCP_EXE,
    POWERBI_REFRESH_TYPE,
    WATCHER_DEBOUNCE_SECONDS,
)

# The dashboard itself reads the Excel source through FastAPI.
# If ENABLE_POWERBI_REFRESH=true, this watcher also triggers a
# Power BI Desktop semantic-model refresh through the local MCP server.

last_event = 0.0


def log(message):
    print(
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}",
        flush=True,
    )


def result_text(result):
    output = []
    for item in getattr(result, "content", []) or []:
        output.append(getattr(item, "text", str(item)))
    return "\n".join(output)


async def refresh_powerbi():
    if not ENABLE_POWERBI_REFRESH:
        log("Power BI refresh is disabled. Dashboard will use the updated Excel data.")
        return

    if not POWERBI_MCP_EXE:
        raise RuntimeError(
            "POWERBI_MCP_EXE is empty. Set it in .env or set "
            "ENABLE_POWERBI_REFRESH=false."
        )

    if not POWERBI_MCP_EXE.exists():
        raise RuntimeError(
            f"Power BI MCP executable not found: {POWERBI_MCP_EXE}"
        )

    server_params = StdioServerParameters(
        command=str(POWERBI_MCP_EXE),
        args=["--start", "--accept-eula"],
        env=os.environ.copy(),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = (await session.list_tools()).tools
            names = {tool.name for tool in tools}

            if (
                "connection_operations" not in names
                or "model_operations" not in names
            ):
                raise RuntimeError(
                    "Required Power BI MCP tools are missing."
                )

            result = await session.call_tool(
                "connection_operations",
                arguments={
                    "request": {
                        "operation": "ListLocalInstances"
                    }
                },
            )

            text = result_text(result)
            ports = re.findall(
                r"localhost:\d+",
                text,
                flags=re.IGNORECASE,
            )

            if not ports:
                raise RuntimeError(
                    "No open Power BI Desktop instance found. "
                    "Open the PBIX file first."
                )

            selected = ports[0]
            log(f"Power BI Desktop instance: {selected}")

            await session.call_tool(
                "connection_operations",
                arguments={
                    "request": {
                        "operation": "Connect",
                        "dataSource": selected,
                    }
                },
            )

            log("Connected to Power BI Desktop.")

            result = await session.call_tool(
                "model_operations",
                arguments={
                    "request": {
                        "operation": "RefreshWithXMLA",
                        "refreshType": POWERBI_REFRESH_TYPE,
                    }
                },
            )

            text = result_text(result)

            if text:
                log("Power BI refresh response:")
                print(text, flush=True)
            else:
                log("Power BI refresh request completed with no text payload.")


def process(path):
    global last_event

    try:
        if Path(path).resolve() != EXCEL_FILE.resolve():
            return
    except Exception:
        return

    now = time.time()

    if now - last_event < WATCHER_DEBOUNCE_SECONDS:
        return

    last_event = now

    log("=" * 70)
    log("EXCEL CHANGE DETECTED")
    log(f"File: {path}")
    log("Waiting for Excel to finish saving...")
    time.sleep(EXCEL_SAVE_WAIT_SECONDS)

    try:
        asyncio.run(refresh_powerbi())
    except Exception:
        log("POWER BI REFRESH FAILED")
        traceback.print_exc()


class Handler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory:
            process(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            process(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            process(event.dest_path)


def main():
    if not EXCEL_FILE.exists():
        print(f"Excel source not found: {EXCEL_FILE}")
        print("Set EXCEL_FILE in .env to your workbook.")
        sys.exit(1)

    log("INSIGHTFORGE EXCEL WATCHER")
    log(f"Watching: {EXCEL_FILE}")
    log(f"Power BI refresh enabled: {ENABLE_POWERBI_REFRESH}")
    log(f"Debounce: {WATCHER_DEBOUNCE_SECONDS}s")
    log("Press Ctrl+C to stop.")

    observer = Observer()
    observer.schedule(
        Handler(),
        str(EXCEL_FILE.parent),
        recursive=False,
    )
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("Stopping watcher...")
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()

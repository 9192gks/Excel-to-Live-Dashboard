import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

APP_NAME = os.getenv("APP_NAME", "InsightForge")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

excel_env = os.getenv("EXCEL_FILE", "data/sample_financial_data.xlsx")
EXCEL_FILE = Path(excel_env)
if not EXCEL_FILE.is_absolute():
    EXCEL_FILE = PROJECT_ROOT / EXCEL_FILE

ENABLE_POWERBI_REFRESH = os.getenv("ENABLE_POWERBI_REFRESH", "false").lower() in {
    "1", "true", "yes", "y", "on"
}
powerbi_mcp_env = os.getenv("POWERBI_MCP_EXE", "").strip()
POWERBI_MCP_EXE = Path(powerbi_mcp_env).expanduser() if powerbi_mcp_env else None

POWERBI_REFRESH_TYPE = os.getenv("POWERBI_REFRESH_TYPE", "Full")
WATCHER_DEBOUNCE_SECONDS = int(os.getenv("WATCHER_DEBOUNCE_SECONDS", "15"))
EXCEL_SAVE_WAIT_SECONDS = int(os.getenv("EXCEL_SAVE_WAIT_SECONDS", "4"))
DASHBOARD_REFRESH_SECONDS = int(os.getenv("DASHBOARD_REFRESH_SECONDS", "5"))

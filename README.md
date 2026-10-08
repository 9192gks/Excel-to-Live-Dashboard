# InsightForge — Part 2

A lightweight, local analytics automation project that turns an Excel workbook into a self-updating HTML dashboard.

The dashboard HTML used in this project was originally generated with Claude in Part 1. Part 2 removes the need to regenerate the HTML and instead makes the existing dashboard consume fresh data from a local FastAPI API.

## Architecture

```text
                    INSIGHTFORGE PART 2

                  Excel Workbook
                       │
                       ▼
                Python Watcher
                       │
             detects file changes
                       │
             ┌─────────┴─────────┐
             │                   │
             ▼                   ▼
       FastAPI /api/data    Power BI MCP
             │               (optional)
             ▼                   │
       HTML Dashboard       Power BI Desktop
```

### Current dashboard data path

```text
Excel → FastAPI → HTML Dashboard
```

The dashboard polls `/api/data` every few seconds, so changes in the Excel workbook appear without manually refreshing the browser.

### Optional Power BI path

When `ENABLE_POWERBI_REFRESH=true`:

```text
Excel → Watcher → Power BI MCP → Power BI Desktop refresh
```

The Power BI refresh is deliberately optional because Power BI Desktop and the local MCP executable are machine-specific.

## Features

- Local FastAPI API
- Excel/`.xlsx` ingestion with Pandas + OpenPyXL
- File change monitoring with Watchdog
- Existing Claude-generated HTML dashboard
- Automatic browser-side refresh
- Optional Power BI Desktop semantic-model refresh through the Power BI Modeling MCP
- No Power BI Service required
- No cloud hosting required
- Configurable paths through `.env`

## Requirements

For the basic dashboard:

- Windows
- Python 3.10+
- An Excel workbook with these fields:

```text
Date / Order Date
Segment
Product
Country
Discount Band
Sales
Profit
Units Sold
```

For optional Power BI refresh:

- Power BI Desktop
- A PBIX file open in Power BI Desktop
- Power BI Modeling MCP installed locally

## Quick start

### 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/InsightForge-Part2.git
cd InsightForge-Part2
```

### 2. Run

Double-click:

```text
START_DASHBOARD.bat
```

The script creates a virtual environment, installs dependencies, starts FastAPI, starts the watcher, and opens the dashboard.

Dashboard:

```text
http://127.0.0.1:8000/dashboard.html
```

API:

```text
http://127.0.0.1:8000/api/data
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## Using your own Excel file

Copy:

```text
.env.example
```

to:

```text
.env
```

Then change:

```env
EXCEL_FILE=C:\Path\To\Your\Workbook.xlsx
```

Relative paths also work:

```env
EXCEL_FILE=data/my_workbook.xlsx
```

Do not commit `.env`.

## Power BI MCP setup

If you want Excel changes to also trigger a Power BI Desktop refresh:

1. Install the Power BI Modeling MCP.
2. Open your PBIX in Power BI Desktop.
3. Copy `.env.example` to `.env`.
4. Set:

```env
ENABLE_POWERBI_REFRESH=true
```

5. Set the local MCP executable path:

```env
POWERBI_MCP_EXE=C:\Users\YOUR_USERNAME\.vscode\extensions\...\powerbi-modeling-mcp.exe
```

6. Start the project.

When the Excel file is saved, `watcher.py` detects the change and sends a refresh request to the local Power BI Desktop instance.

## Important

The Power BI MCP executable path is intentionally not hard-coded into the GitHub project. Every machine can have a different Windows username, VS Code extension path, and MCP installation location.

## Project structure

```text
InsightForge-Part2/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   └── dashboard.html
│
├── data/
│   └── sample_financial_data.xlsx
│
├── watcher.py
├── requirements.txt
├── .env.example
├── .gitignore
├── START_DASHBOARD.bat
├── README.md
└── LICENSE
```

## How it works

### 1. Excel

The workbook is the source file.

### 2. Watcher

`watcher.py` uses Watchdog to monitor the Excel file.

When the file changes, it waits briefly for Excel to finish saving and then optionally triggers the Power BI refresh.

### 3. FastAPI

`app/main.py` reads the workbook and exposes:

```text
GET /api/data
```

### 4. HTML dashboard

`dashboard.html` requests `/api/data` and renders:

- KPIs
- Monthly trend
- Profit margin
- Segment analysis
- Product analysis
- Geography
- Discounts
- Insights

It automatically checks for updated data.

## Part 2 → Part 3

Part 2:

```text
Excel
  ↓
Python
  ↓
FastAPI
  ↓
Claude-generated HTML dashboard
```

The planned next step is:

```text
Excel
  ↓
Python Watcher
  ↓
Power BI Desktop Semantic Model
  ↓
DAX / semantic-model query
  ↓
FastAPI
  ↓
HTML Dashboard
```

That makes the Power BI semantic model the single source of truth while keeping the dashboard as the presentation layer.

## Security

Do not commit:

- real company data
- confidential Excel workbooks
- `.env`
- credentials
- database files
- machine-specific paths

The included workbook is synthetic demo data.

## License

MIT

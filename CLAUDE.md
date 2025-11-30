# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TrendRadar is a Chinese hot news aggregation and monitoring tool that collects trending topics from 11+ platforms (Zhihu, Weibo, Douyin, Bilibili, etc.) and pushes filtered notifications via multiple channels (WeChat Work, Feishu, DingTalk, Telegram, Email, ntfy, Bark, Slack).

**Current Version:** 3.4.1 (main.py), MCP Server: 1.0.3

## Common Commands

```bash
# Run the main crawler
python main.py

# Run MCP server (stdio mode - for AI clients)
python -m mcp_server.server

# Run MCP server (HTTP mode for development)
python mcp_server/server.py

# Start local HTTP server for viewing output
./start-http.sh  # macOS/Linux
start-http.bat   # Windows

# Install dependencies
pip install -r requirements.txt

# Docker deployment
cd docker && docker-compose up -d
```

## Architecture

### Core Components

```
TrendRadar/
├── main.py                 # Main crawler script (192KB, single-file architecture)
│                           # Contains: config loading, API fetching, news processing,
│                           # notification sending, HTML/TXT report generation
├── mcp_server/             # MCP (Model Context Protocol) server for AI analysis
│   ├── server.py           # FastMCP 2.0 server with 14 AI tools
│   ├── tools/              # MCP tool implementations
│   │   ├── analytics.py    # Trend analysis, sentiment analysis
│   │   ├── data_query.py   # Basic news queries
│   │   ├── search_tools.py # Full-text search, cross-platform comparison
│   │   ├── config_mgmt.py  # Configuration management
│   │   └── system.py       # System status, data statistics
│   ├── services/           # Data services
│   │   ├── data_service.py # News data loading and parsing
│   │   ├── parser_service.py # Text file parsing
│   │   └── cache_service.py  # Query caching
│   └── utils/              # Utilities (date parsing, error handling)
├── config/
│   ├── config.yaml         # Main configuration (platforms, weights, notifications)
│   └── frequency_words.txt # Keyword filters (one per line, supports +/!/@ modifiers)
├── output/                 # Generated reports organized by date
│   └── YYYY年MM月DD日/
│       ├── txt/            # Raw text snapshots
│       └── html/           # HTML reports
└── docker/                 # Docker deployment files
```

### Data Flow

1. **Fetch**: `main.py` fetches hot news from newsnow API for configured platforms
2. **Filter**: News filtered by keywords in `frequency_words.txt`
3. **Rank**: Custom weighting algorithm (rank 60%, frequency 30%, hotness 10%)
4. **Output**: Generates TXT snapshots and HTML reports in `output/`
5. **Notify**: Pushes to configured channels (webhooks/email)

### Report Modes

- `daily`: Daily summary of all matching news
- `current`: Current trending items only
- `incremental`: Only new items since last run (no duplicates)

### Keyword Syntax (frequency_words.txt)

```
keyword      # Basic match
+required    # Must contain (AND logic)
!excluded   # Exclude term
keyword@5    # Limit to 5 results for this keyword
```

Blank lines separate keyword groups for independent statistics.

## Configuration Priority

Environment variables override `config/config.yaml` values. Key env vars:
- `REPORT_MODE`, `ENABLE_CRAWLER`, `ENABLE_NOTIFICATION`
- `FEISHU_WEBHOOK_URL`, `DINGTALK_WEBHOOK_URL`, `WEWORK_WEBHOOK_URL`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- `EMAIL_FROM`, `EMAIL_PASSWORD`, `EMAIL_TO`
- `BARK_URL`, `SLACK_WEBHOOK_URL`, `NTFY_TOPIC`

## MCP Server Tools

The MCP server provides 14 tools for AI-powered news analysis:
- `resolve_date_range`: Parse natural language dates (recommended to call first)
- `get_news_list`, `get_latest_news`: Basic queries
- `search_news`, `find_similar_news`: Full-text search
- `analyze_sentiment`, `detect_trending`: Analytics
- `compare_platforms`, `get_platform_stats`: Cross-platform analysis

## GitHub Actions

Workflow: `.github/workflows/crawler.yml`
- Runs hourly by default (`0 * * * *` UTC)
- Commits output changes automatically
- Webhook secrets stored in GitHub Secrets (not in config files)

## Key Patterns

- Single-file main script for easy deployment
- Beijing timezone (Asia/Shanghai) for all timestamps
- Output directory structure: `output/YYYY年MM月DD日/{txt,html}/`
- Batch message splitting for platform limits (DingTalk 20KB, Feishu 30KB, etc.)
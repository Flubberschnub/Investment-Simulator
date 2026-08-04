# MCP and scheduling

MCP is supervisory, not the market-timing runtime. It can read status, pause operation, and resume simulation or shadow mode. It cannot place orders or resume live mode.

Use an external process scheduler only for backtests, token-health checks, and shadow reports. A ChatGPT scheduled task is not a low-latency trading engine.

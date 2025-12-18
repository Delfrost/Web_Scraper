import sys
import asyncio
import uvicorn

if __name__ == "__main__":
    # 1. Force Windows to use the ProactorEventLoop (Required for Playwright)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # 2. Run Uvicorn directly
    # distinct from main.py so we control the startup
    # reload=False is CRITICAL here to prevent the loop settings from being lost in a subprocess
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
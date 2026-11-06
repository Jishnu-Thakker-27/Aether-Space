"""
Aether Space Server Entry Point
Runs the high-performance FastAPI application using Uvicorn.
Supports:
    python server.py [port]
    python main.py [port]
    uvicorn main:app --reload --port 8000
"""

import os
import sys
import uvicorn
from main import app

if __name__ == "__main__":
    # Support port as CLI arg: e.g. python server.py 8000
    port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else int(os.getenv("PORT", 8000))
    print(f"\n=================================================================")
    print(f"🚀 Aether Space — FastAPI + Vite Full-Stack Assistant")
    print(f"👉 Local Access URL: http://127.0.0.1:{port}")
    print(f"📖 Swagger API Docs:  http://127.0.0.1:{port}/docs")
    print(f"⚡ Vite Dev URL:      http://localhost:5173 (run 'npm run dev')")
    print(f"=================================================================\n")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

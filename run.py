import os
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    print(f"Starting GoRush AI Chatbot Backend on http://{host}:{port} ...")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)


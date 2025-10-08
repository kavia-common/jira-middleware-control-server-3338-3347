# Deprecated minimal app. Prefer app.main:app as the primary application.
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

legacy_app = FastAPI(title="Legacy App (Deprecated)")

legacy_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@legacy_app.get("/")
def health_check():
    return {"message": "Healthy", "note": "Use app.main:app for full MCP server."}

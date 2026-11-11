from fastapi import FastAPI
from app.routers import health, billing, conversations, knowledge, chat

app = FastAPI(
    title="Backend & AI Chatbot Developer API",
    description="Sistem Chatbot Layanan Digital dengan Policy Gate & Safety Controls",
    version="1.0.0"
)

# Register Routers
app.include_router(health.router)
app.include_router(chat.router)        # Endpoint /chat baru
app.include_router(billing.router)
app.include_router(conversations.router)
app.include_router(knowledge.router)

@app.get("/")
def root():
    return {
        "message": "Welcome to Backend & AI Chatbot API",
        "docs_url": "/docs"
    }
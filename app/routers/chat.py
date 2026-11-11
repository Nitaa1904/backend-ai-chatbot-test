import sqlite3
from fastapi import APIRouter, Depends
from app.database import get_db
from app.models import ChatRequest, ChatResponse
from app.services.chatbot import process_chat_message

router = APIRouter(prefix="/chat", tags=["Chatbot"])

@router.post("", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest, conn: sqlite3.Connection = Depends(get_db)):
    """ Endpoint utama Chatbot dengan Policy Gate & Isolasi Klien """
    return process_chat_message(
        conn=conn,
        client_id=req.client_id,
        conversation_id=req.conversation_id,
        message=req.message
    )
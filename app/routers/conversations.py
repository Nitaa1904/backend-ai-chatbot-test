import sqlite3
from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_db
from app.models import ConversationDetailResponse

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation_history(conversation_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """Mengambil riwayat percakapan beserta seluruh pesan."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM conversations WHERE conversation_id = ?", (conversation_id,))
    conv = cursor.fetchone()
    
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation ID '{conversation_id}' tidak ditemukan."
        )

    cursor.execute(
        "SELECT * FROM chat_messages WHERE conversation_id = ? ORDER BY turn_index ASC", 
        (conversation_id,)
    )
    messages = cursor.fetchall()

    conv_dict = dict(conv)
    conv_dict['messages'] = [dict(m) for m in messages]
    return conv_dict

@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """Menghapus sesi percakapan beserta seluruh pesannya (Cascading delete)."""
    cursor = conn.cursor()
    cursor.execute("SELECT conversation_id FROM conversations WHERE conversation_id = ?", (conversation_id,))
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation ID '{conversation_id}' tidak ditemukan."
        )

    cursor.execute("DELETE FROM conversations WHERE conversation_id = ?", (conversation_id,))
    conn.commit()
    
    return {
        "status": "success",
        "message": f"Sesi percakapan '{conversation_id}' beserta pesannya telah dihapus."
    }
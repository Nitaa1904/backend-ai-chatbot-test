import sqlite3
from typing import List
from fastapi import APIRouter, Depends, status
from app.database import get_db
from app.models import KnowledgeBaseResponse, KnowledgeBaseCreate

router = APIRouter(prefix="/knowledge-bases", tags=["Knowledge Base"])

@router.get("", response_model=List[KnowledgeBaseResponse])
def get_all_knowledge_bases(conn: sqlite3.Connection = Depends(get_db)):
    """Menampilkan seluruh isi Knowledge Base."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM knowledge_bases")
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@router.post("", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
def create_knowledge_base(item: KnowledgeBaseCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Menambahkan informasi baru ke Knowledge Base."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO knowledge_bases (category, keyword_triggers, title, content)
        VALUES (?, ?, ?, ?)
    """, (item.category, item.keyword_triggers, item.title, item.content))
    conn.commit()
    
    new_id = cursor.lastrowid
    return {**item.model_dump(), "id": new_id}
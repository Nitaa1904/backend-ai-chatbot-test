import sqlite3
from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_db

router = APIRouter(tags=["Health"])

@router.get("/health")
def check_health(conn: sqlite3.Connection = Depends(get_db)):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        return {
            "status": "healthy",
            "database": "connected",
            "message": "Server FastAPI dan Database SQLite berjalan dengan baik."
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection error: {str(e)}"
        )
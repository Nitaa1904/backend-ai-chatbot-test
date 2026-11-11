import os
import uuid
import sqlite3
from typing import Dict, Any, Tuple, Optional
from google import genai
from google.genai import types
from fastapi import HTTPException, status

# Inisialisasi Google Gemini SDK
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
client_ai = None
if GEMINI_API_KEY:
    try:
        client_ai = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Warning: Gemini Client failed to initialize: {e}")

FALLBACK_RESPONSE = (
    "Mohon maaf kak, informasi tersebut belum tersedia di sistem kami. "
    "Tim support kami akan membantu memberikan informasi lebih lanjut."
)

# 1. Intent Detection sederhanakan dengan Keyword Rules & Fallback
def detect_intent_and_policy(user_message: str) -> Tuple[str, bool]:
    msg_lower = user_message.lower()
    
    # Intent Aktivasi Service (Harus lewat Policy Gate)
    activation_keywords = ["aktif", "aktivasi", "sambung domain", "go live", "onlinekan"]
    if any(k in msg_lower for k in activation_keywords):
        return "activation_request", True

    # Intent Pembayaran / Rekening
    payment_keywords = ["bayar", "rekening", "transfer", "bca", "mandiri", "bri"]
    if any(k in msg_lower for k in payment_keywords):
        return "payment_info", False

    # Intent Tagihan
    billing_keywords = ["tagihan", "sisa", "lunas", "invoice", "biaya"]
    if any(k in msg_lower for k in billing_keywords):
        return "billing_info", False

    return "general_query", False


# 2. Knowledge Base Search
def search_knowledge_base(conn: sqlite3.Connection, query: str) -> Optional[str]:
    cursor = conn.cursor()
    cursor.execute("SELECT keyword_triggers, content FROM knowledge_bases")
    rows = cursor.fetchall()

    query_lower = query.lower()
    for row in rows:
        triggers = [t.strip().lower() for t in row["keyword_triggers"].split(",")]
        if any(trigger in query_lower for trigger in triggers if trigger):
            return row["content"]
    return None


# 3. Main Chat Engine Process
def process_chat_message(conn: sqlite3.Connection, client_id: str, conversation_id: Optional[str], message: str) -> Dict[str, Any]:
    cursor = conn.cursor()

    # --- ISOLASI & VALIDASI CLIENT_ID ---
    cursor.execute("SELECT client_name FROM clients WHERE client_id = ?", (client_id,))
    client_row = cursor.fetchone()
    if not client_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client ID '{client_id}' tidak valid atau tidak terdaftar."
        )

    # --- PENGELOLAAN CONVERSATION SESSION ---
    if conversation_id:
        # Cek apakah percakapan ada dan milik client_id tersebut (ISOLATION CHECK)
        cursor.execute("SELECT client_id FROM conversations WHERE conversation_id = ?", (conversation_id,))
        conv_row = cursor.fetchone()
        if not conv_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation ID '{conversation_id}' tidak ditemukan."
            )
        if conv_row["client_id"] != client_id:
            # Cegah kebocoran data percakapan antar-klien (TC-08 / TC-10)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akses ditolak: Percakapan ini milik klien lain."
            )
    else:
        # Buat percakapan baru
        conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
        cursor.execute(
            "INSERT INTO conversations (conversation_id, client_id) VALUES (?, ?)",
            (conversation_id, client_id)
        )
        conn.commit()

    # --- INTENT & POLICY GATE CHECK ---
    intent, is_activation = detect_intent_and_policy(message)
    reply = ""

    # Cek manipulasi status pembayaran via chat (TC-05 & TC-06)
    msg_lower = message.lower()
    if "sudah transfer" in msg_lower or "ubah status" in msg_lower or "tandai invoice" in msg_lower or "override" in msg_lower:
        reply = (
            "Mohon maaf, perubahan status pembayaran tidak dapat dilakukan langsung melalui percakapan chatbot. "
            "Silakan lakukan konfirmasi pembayaran melalui menu konfirmasi resmi backend agar dapat diverifikasi oleh tim kami."
        )

    # POLICY GATE: Cek Tagihan DB jika meminta Aktivasi Service (TC-03 & TC-04)
    elif is_activation:
        cursor.execute("SELECT invoice_no, total_amount, amount_paid, payment_status FROM invoices WHERE client_id = ?", (client_id,))
        invoices = cursor.fetchall()
        
        has_unpaid = False
        total_remaining = 0

        for inv in invoices:
            rem = inv["total_amount"] - inv["amount_paid"]
            if inv["payment_status"] != "paid" or rem > 0:
                has_unpaid = True
                total_remaining += rem

        if has_unpaid:
            reply = (
                f"Mohon maaf kak {client_row['client_name']}, permintaan aktivasi layanan belum dapat diproses "
                f"karena masih terdapat sisa tagihan sebesar Rp{total_remaining:,}. "
                "Silakan lakukan pelunasan terlebih dahulu."
            )
        else:
            reply = (
                f"Terima kasih kak {client_row['client_name']}. Seluruh tagihan Anda telah LUNAS. "
                "Permintaan aktivasi layanan telah kami teruskan ke tim teknis terkait dan akan diproses maksimal 1x24 jam."
            )

    # KB RETRIEVAL & LLM / FALLBACK GENERATION
    else:
        kb_content = search_knowledge_base(conn, message)
        
        if kb_content:
            # Jika ada API Key & Client AI aktif, gunakan Gemini untuk generate respons natural
            if client_ai and GEMINI_API_KEY:
                try:
                    system_instruction = (
                        "Anda adalah AI Customer Service yang ramah dan profesional. "
                        "Jawablah pertanyaan pengguna HANYA berdasarkan konteks fakta berikut. "
                        "Jangan menambah fakta atau janji di luar konteks yang diberikan.\n"
                        f"Konteks Fakta: {kb_content}"
                    )
                    response = client_ai.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=message,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.2,
                        )
                    )
                    reply = response.text.strip()
                except Exception as e:
                    print(f"Gemini API Exception (Fallback to DB Content): {e}")
                    reply = kb_content
            else:
                reply = kb_content
        else:
            # GENERAL FALLBACK (TC-07)
            reply = FALLBACK_RESPONSE

    # --- SAVE CONVERSATION TO DATABASE ---
    # Hitung turn index saat ini
    cursor.execute("SELECT COUNT(*) as count FROM chat_messages WHERE conversation_id = ?", (conversation_id,))
    turn_count = cursor.fetchone()["count"]

    # Simpan Pesan User
    cursor.execute("""
        INSERT INTO chat_messages (conversation_id, turn_index, sender, message_text, detected_intent)
        VALUES (?, ?, 'user', ?, ?)
    """, (conversation_id, turn_count + 1, message, intent))

    # Simpan Pesan Assistant
    cursor.execute("""
        INSERT INTO chat_messages (conversation_id, turn_index, sender, message_text, detected_intent)
        VALUES (?, ?, 'assistant', ?, ?)
    """, (conversation_id, turn_count + 2, reply, intent))

    # Update updated_at di tabel conversations
    cursor.execute("UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE conversation_id = ?", (conversation_id,))
    conn.commit()

    return {
        "conversation_id": conversation_id,
        "client_id": client_id,
        "reply": reply,
        "detected_intent": intent
    }
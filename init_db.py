import sqlite3
from app.database import DB_NAME

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Enable Foreign Keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Tabel clients
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        client_id TEXT PRIMARY KEY,
        client_name TEXT NOT NULL,
        company_name TEXT,
        phone_number TEXT NOT NULL,
        official_domain TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Tabel invoices
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        invoice_no TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        service_type TEXT NOT NULL,
        package_name TEXT NOT NULL,
        total_amount INTEGER NOT NULL,
        amount_paid INTEGER NOT NULL DEFAULT 0,
        payment_status TEXT NOT NULL CHECK(payment_status IN ('unpaid', 'half_paid', 'paid')),
        due_date DATE,
        FOREIGN KEY (client_id) REFERENCES clients(client_id) ON DELETE CASCADE
    );
    """)

    # 3. Tabel knowledge_bases
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_bases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        keyword_triggers TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL
    );
    """)

    # 4. Tabel conversations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        conversation_id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(client_id) ON DELETE CASCADE
    );
    """)

    # 5. Tabel chat_messages
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        turn_index INTEGER NOT NULL,
        sender TEXT NOT NULL CHECK(sender IN ('user', 'assistant')),
        message_text TEXT NOT NULL,
        detected_intent TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
    );
    """)

    # Indexing untuk efisiensi query
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_client ON invoices(client_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_client ON conversations(client_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON chat_messages(conversation_id);")

    # SEED DATA
    # Clean up existing seed data to allow fresh rerun
    cursor.execute("DELETE FROM chat_messages;")
    cursor.execute("DELETE FROM conversations;")
    cursor.execute("DELETE FROM knowledge_bases;")
    cursor.execute("DELETE FROM invoices;")
    cursor.execute("DELETE FROM clients;")

    # Insert Clients
    cursor.executemany("""
    INSERT INTO clients (client_id, client_name, company_name, phone_number, official_domain)
    VALUES (?, ?, ?, ?, ?)
    """, [
        ('CLI-001', 'Budi Santoso', 'PT Makmur Sentosa', '6281234567801', 'makmursentosa.com'),
        ('CLI-002', 'Rani Wijaya', 'Toko Berkah Rani', '6281234567802', 'tokorani.id'),
        ('CLI-003', 'Hendra Tan', 'CV Solusi Digital', '6281234567803', 'solusidigital.co.id')
    ])

    # Insert Invoices
    cursor.executemany("""
    INSERT INTO invoices (invoice_no, client_id, service_type, package_name, total_amount, amount_paid, payment_status)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [
        ('INV-2026-001', 'CLI-001', 'website', 'Gold Website', 1600000, 800000, 'half_paid'),
        ('INV-2026-002', 'CLI-002', 'seo', 'SEO Domestik', 600000, 600000, 'paid'),
        ('INV-2026-003', 'CLI-003', 'website', 'Platinum Website', 3000000, 0, 'unpaid')
    ])

    # Insert Knowledge Bases
    cursor.executemany("""
    INSERT INTO knowledge_bases (category, keyword_triggers, title, content)
    VALUES (?, ?, ?, ?)
    """, [
        ('rekening', 'rekening, transfer, bayar, bca, mandiri, bri', 'Rekening Pembayaran', 
         'Data rekening pembayaran resmi untuk keperluan simulasi: BCA: 111-222-333 a.n. PT Contoh Digital.'),
        ('layanan', 'seo, paket seo, ranking google, search engine', 'Informasi Layanan SEO', 
         'Paket SEO Domestik: Rp600.000 per bulan. Paket SEO Internasional: Rp2.200.000 per bulan.'),
        ('kebijakan', 'revisi, edit web, perbaikan, ganti foto', 'Kebijakan Revisi', 
         'Setiap pembuatan website mendapatkan maksimal 3 kali revisi gratis dalam waktu 1 bulan setelah pelunasan. Revisi berikutnya dapat dikenakan biaya tambahan.'),
        ('operasional', 'sambung domain, online, go live, domain resmi', 'Kebijakan Aktivasi Layanan', 
         'Aktivasi domain utama hanya dapat diproses jika tagihan terkait telah berstatus lunas. Estimasi proses aktivasi adalah 1x24 jam.')
    ])

    conn.commit()
    conn.close()
    print("Database SQLite berhasil dibuat dan di-seed!")

if __name__ == "__main__":
    init_db()
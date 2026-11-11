# Dokumen Analisis Studi Kasus Debugging & Arsitektur

## Kasus 1 — Kebocoran Konteks Antar-Klien

### 1. Kemungkinan Penyebab Utama

Pada framework backend berbasis Python asynchronous seperti FastAPI/Uvicorn, kebocoran konteks antar-klien umumnya disebabkan oleh:

- **Global Mutable State / Singleton Module-Level Variable**: Menggunakan variabel global (misal `current_client` atau list `chat_history`) untuk menyimpan state per-request. Dalam execution model asyncio, request yang datang hampir bersamaan akan saling menimpa nilai variabel global tersebut.
- **Shared Memory Scope**: Instansiasi objek AI Client atau Session Memory yang dibagikan ke seluruh koneksi tanpa mengisolasinya berdasarkan ID unik session/klien.

### 2. Pengelolaan State dan Session yang Tepat

- **Stateless Router/Service**: Menjaga layer API dan Service tetap _stateless_. State percakapan tidak disimpan dalam memori aplikasi, melainkan persisten di database SQLite (`conversations` & `chat_messages`).
- **Dependency Injection**: Menggunakan sistem `Depends()` FastAPI untuk membuat instance koneksi database atau context handler terisolasi per-request.
- **Explicit Parameter Passing**: Mengirimkan `client_id` dan `conversation_id` secara eksplisit melalui signature method dari layer router ke service layer.

### 3. Memastikan Konteks Klien Tidak Tercampur

- **Strict Tenant Isolation**: Sebelum memproses percakapan atau mengembalikan data invoice, backend wajib melakukan verifikasi kepemilikan (`ownership check`):
  ```python
  if conversation.client_id != request.client_id:
      raise HTTPException(status_code=403, detail="Access denied")
  ```

* **Database Query Filtering**: Seluruh query SQL untuk pembacaan riwayat chat atau billing wajib menyertakan klausa `WHERE client_id = ?`.

---

## Kasus 2 — Prompt Injection dan Manipulasi Data

### 1. Mengapa Instruksi Prompt Injection Memengaruhi Respons LLM?

LLM bekerja dengan menerima rangkaian teks (_prompt_) dan memprediksi kelanjutan teks terbaik berdasarkan urutan probabilitas. Jika instruksi pengembang (_system prompt_) dan input pengguna (_user prompt_) digabungkan langsung menjadi satu string tanpa batasan ketat, LLM dapat terkecoh dan menganggap instruksi pengguna sebagai perintah tingkat sistem (_Instruction Following Hijacking_).

### 2. Memisahkan Pengambilan Keputusan Backend dengan Generasi Jawaban LLM

- **Deterministic Business Policy (Policy Gate)**: Keputusan bisnis (seperti perubahan status invoice `PAID`/`UNPAID`, pengecekan sisa tagihan, atau izin aktivasi domain) **100% diputuskan oleh kode Python dan database SQLite**, bukan oleh jawaban LLM.
- **LLM sebagai Representation Layer**: LLM hanya difungsikan untuk memformat jawaban secara alami (_natural language generation_) atau merekap informasi dari _knowledge base_ yang sudah divalidasi.

### 3. Memastikan Instruksi Pengguna Tidak Mengubah Data Tagihan

- **No Write-Access Tools for LLM**: LLM tidak diberikan akses perkakas (_function calling_) untuk eksekusi query `UPDATE` atau `DELETE` pada database.
- **Strict Endpoint Separation**: Perubahan status tagihan atau konfirmasi pembayaran hanya dapat dilakukan via endpoint khusus backend `POST /billing/confirm-payment` yang memiliki skema validasi Pydantic v2 dan aturan otorisasi tersendiri.
- **Keyword & Pattern Filtering**: Menolak klaim pembayaran atau instruksi manipulasi status di layer backend sebelum memanggil API LLM.

---

## Kasus 3 — LLM Provider Timeout & Rate Limit (HTTP 429)

### 1. Penanganan Timeout dan Kegagalan Provider

- **Timeout Configuration**: Menetapkan batas waktu timeout yang ketat (misal 5 detik) pada panggilan API LLM agar request client tidak terbengkalai.
- **Retry Mechanism dengan Exponential Backoff**: Menggunakan library `tenacity` untuk melakukan retry otomatis ketika menghadapi HTTP rate limit (429) atau error sementara (5xx).

### 2. Strategi Fallback agar Chatbot Tetap Merespons

- **Graceful Degradation / Direct Retrieval Fallback**: Jika pemanggilan Gemini API gagal (timeout, quota limit, atau network error), backend secara otomatis mengambil jawaban langsung dari tabel `knowledge_bases` (SQL keyword matching) tanpa menghentikan proses HTTP.
- **General Fallback Message**: Jika informasi tidak ditemukan baik di LLM maupun DB, sistem mengembalikan pesan standar tanpa melempar error status 500:
  > _"Mohon maaf kak, informasi tersebut belum tersedia di sistem kami. Tim support kami akan membantu memberikan informasi lebih lanjut."_

### 3. Mencegah Satu Kegagalan Provider Mengganggu Keseluruhan Layanan

- **Circuit Breaker Pattern**: Mengisolasi kegagalan integrasi AI agar tidak membuat server FastAPI menumpuk _unhandled exceptions_.
- **Async Non-Blocking I/O**: Memastikan pemanggilan API LLM dilakukan secara asinkron atau dalam threadpool terpisah sehingga event loop FastAPI tetap responsif melayani endpoint lain.

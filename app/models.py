import re
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

# --- Payment Confirmation Validation ---
class PaymentConfirmationRequest(BaseModel):
    client_id: str = Field(..., description="ID Klien wajib diisi")
    invoice_no: str = Field(..., description="Nomor invoice format INV-YYYY-NNN")
    nominal_transfer: int = Field(..., gt=0, description="Nominal transfer harus integer positif")
    bank_tujuan: str = Field(..., description="Pilihan bank: BCA, MANDIRI, atau BRI")
    nama_rekening_pengirim: str = Field(..., description="Minimal 3 karakter non-spasi")

    @field_validator('invoice_no')
    @classmethod
    def validate_invoice_no(cls, v: str) -> str:
        pattern = r"^INV-\d{4}-\d{3}$"
        if not re.match(pattern, v):
            raise ValueError("Format invoice_no harus sesuai dengan pola INV-YYYY-NNN (misal: INV-2026-001)")
        return v

    @field_validator('bank_tujuan')
    @classmethod
    def validate_bank_tujuan(cls, v: str) -> str:
        allowed = ["BCA", "MANDIRI", "BRI"]
        uppercase_v = v.upper()
        if uppercase_v not in allowed:
            raise ValueError(f"Bank tujuan harus salah satu dari: {', '.join(allowed)}")
        return uppercase_v

    @field_validator('nama_rekening_pengirim')
    @classmethod
    def validate_nama_rekening(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 3:
            raise ValueError("Nama rekening pengirim minimal 3 karakter non-spasi")
        return cleaned


# --- Response Schemas ---
class ClientResponse(BaseModel):
    client_id: str
    client_name: str
    company_name: Optional[str] = None
    phone_number: str
    official_domain: Optional[str] = None

class InvoiceResponse(BaseModel):
    invoice_no: str
    client_id: str
    service_type: str
    package_name: str
    total_amount: int
    amount_paid: int
    remaining_amount: int
    payment_status: str
    due_date: Optional[str] = None

class BillingSummaryResponse(BaseModel):
    client: ClientResponse
    invoices: List[InvoiceResponse]
    total_paid: int
    total_remaining: int

class KnowledgeBaseCreate(BaseModel):
    category: str
    keyword_triggers: str
    title: str
    content: str

class KnowledgeBaseResponse(KnowledgeBaseCreate):
    id: int

class ChatMessageResponse(BaseModel):
    id: int
    conversation_id: str
    turn_index: int
    sender: str
    message_text: str
    detected_intent: Optional[str] = None
    created_at: str

class ConversationDetailResponse(BaseModel):
    conversation_id: str
    client_id: str
    created_at: str
    updated_at: str
    messages: List[ChatMessageResponse]

# --- Chat Models ---
class ChatRequest(BaseModel):
    client_id: str = Field(..., description="ID Klien yang mengirim pesan")
    conversation_id: Optional[str] = Field(None, description="ID Percakapan (opsional, akan dibuat otomatis jika kosong)")
    message: str = Field(..., description="Pesan dari pengguna")

class ChatResponse(BaseModel):
    conversation_id: str
    client_id: str
    reply: str
    detected_intent: str
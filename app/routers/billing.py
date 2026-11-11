import sqlite3
from fastapi import APIRouter, Depends
from app.database import get_db
from app.models import BillingSummaryResponse, PaymentConfirmationRequest
from app.services.billing import get_client_billing_summary, process_payment_confirmation

router = APIRouter(prefix="/billing", tags=["Billing"])

@router.get("/{client_id}", response_model=BillingSummaryResponse)
def get_billing_info(client_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """Mengambil informasi tagihan klien, total bayar, dan total sisa tagihan."""
    return get_client_billing_summary(conn, client_id)

@router.post("/confirm-payment")
def confirm_payment(req: PaymentConfirmationRequest, conn: sqlite3.Connection = Depends(get_db)):
    """ Endpoint validasi konfirmasi pembayaran (Pydantic v2 + DB Validation) """
    return process_payment_confirmation(conn, req)
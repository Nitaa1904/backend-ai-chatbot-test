import sqlite3
from typing import Dict, Any, List
from fastapi import HTTPException, status
from app.models import PaymentConfirmationRequest

def get_client_billing_summary(conn: sqlite3.Connection, client_id: str) -> Dict[str, Any]:
    # 1. Cek keberadaan Client
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
    client = cursor.fetchone()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Klien dengan client_id '{client_id}' tidak ditemukan."
        )

    # 2. Ambil seluruh Tagihan
    cursor.execute("SELECT * FROM invoices WHERE client_id = ?", (client_id,))
    invoices_rows = cursor.fetchall()

    invoices = []
    total_paid = 0
    total_remaining = 0

    for row in invoices_rows:
        tot_amount = row['total_amount']
        amt_paid = row['amount_paid']
        status_db = row['payment_status']
        remaining = tot_amount - amt_paid

        # Konsistensi data nominal
        if remaining < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Data tagihan tidak konsisten: amount_paid melebih total_amount pada invoice {row['invoice_no']}."
            )

        # Konsistensi status pembayaran
        if status_db == 'paid' and remaining != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Status tagihan tidak konsisten: status 'paid' tapi sisa tagihan {remaining} pada invoice {row['invoice_no']}."
            )
        elif status_db == 'unpaid' and amt_paid != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Status tagihan tidak konsisten: status 'unpaid' tapi amount_paid > 0 pada invoice {row['invoice_no']}."
            )

        total_paid += amt_paid
        total_remaining += remaining

        invoice_dict = dict(row)
        invoice_dict['remaining_amount'] = remaining
        invoices.append(invoice_dict)

    return {
        "client": dict(client),
        "invoices": invoices,
        "total_paid": total_paid,
        "total_remaining": total_remaining
    }

def process_payment_confirmation(conn: sqlite3.Connection, req: PaymentConfirmationRequest) -> Dict[str, Any]:
    cursor = conn.cursor()

    # Validasi 1: Cek apakah client_id terdaftar
    cursor.execute("SELECT client_id FROM clients WHERE client_id = ?", (req.client_id,))
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client ID '{req.client_id}' tidak terdaftar."
        )

    # Validasi 2: Cek apakah invoice_no terdaftar dan milik client tersebut
    cursor.execute("SELECT * FROM invoices WHERE invoice_no = ?", (req.invoice_no,))
    invoice = cursor.fetchone()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice '{req.invoice_no}' tidak ditemukan."
        )

    if invoice['client_id'] != req.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Invoice '{req.invoice_no}' bukan milik Client ID '{req.client_id}'."
        )

    # Validasi 3: Cek konsistensi nominal pembayaran
    remaining = invoice['total_amount'] - invoice['amount_paid']
    if remaining == 0 or invoice['payment_status'] == 'paid':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invoice '{req.invoice_no}' sudah berstatus LUNAS (paid)."
        )

    if req.nominal_transfer > remaining:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nominal transfer (Rp{req.nominal_transfer:,}) melebihi sisa tagihan (Rp{remaining:,})."
        )

    return {
        "status": "success",
        "message": "Konfirmasi pembayaran diterima dan sedang dalam verifikasi.",
        "details": {
            "invoice_no": req.invoice_no,
            "nominal_transfer": req.nominal_transfer,
            "remaining_before": remaining,
            "bank_tujuan": req.bank_tujuan
        }
    }
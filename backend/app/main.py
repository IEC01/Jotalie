from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import blink, rates, services
from .config import settings
from .db import SessionLocal, Sms, Transfer, Withdrawal, init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Jotali API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TransferIn(BaseModel):
    sender_name: str = Field(min_length=1, max_length=60)
    recipient_phone: str = Field(pattern=r"^\+?\d{8,15}$")
    amount_xof: int = Field(ge=500, le=1_000_000)


def transfer_out(t: Transfer) -> dict:
    return {"id": t.id, "status": t.status, "invoice": t.invoice, "amount_xof": t.amount_xof,
            "amount_sats": t.amount_sats, "rate_xof_per_btc": t.rate_xof_per_btc}


@app.get("/rate")
async def rate():
    r = await rates.btc_xof_rate()
    return {"xof_per_btc": r, "xof_per_sat": r / 100_000_000}


@app.post("/transfers")
async def create_transfer(body: TransferIn, db: Session = Depends(get_db)):
    rate_ = await rates.btc_xof_rate()                      # taux figé ici
    sats = rates.xof_to_sats(body.amount_xof, rate_)
    invoice = await blink.create_invoice(sats, f"Jotali: {body.sender_name} -> {body.recipient_phone}")
    t = Transfer(sender_name=body.sender_name, recipient_phone=body.recipient_phone,
                 amount_xof=body.amount_xof, amount_sats=sats, rate_xof_per_btc=rate_, invoice=invoice)
    db.add(t)
    db.commit()
    return transfer_out(t)


@app.get("/transfers/{transfer_id}")
async def get_transfer(transfer_id: int, db: Session = Depends(get_db)):
    t = db.get(Transfer, transfer_id)
    if not t:
        raise HTTPException(404, "Transfert introuvable")
    await services.settle_if_paid(db, t)  # le frontend interroge cette route (polling)
    return transfer_out(t)


@app.post("/dev/transfers/{transfer_id}/simulate-paid")
def simulate_paid(transfer_id: int, db: Session = Depends(get_db)):
    """Démo uniquement : marque la facture comme payée (actif seulement si BLINK_MOCK=true)."""
    if not settings.blink_mock:
        raise HTTPException(403, "Disponible uniquement en mode mock")
    t = db.get(Transfer, transfer_id)
    if not t:
        raise HTTPException(404, "Transfert introuvable")
    blink.mock_mark_paid(t.invoice)
    return {"ok": True}


@app.get("/phones/{phone}/sms")
def sms_inbox(phone: str, db: Session = Depends(get_db)):
    rows = db.query(Sms).filter(Sms.phone == phone).order_by(Sms.id.desc()).all()
    return [{"id": s.id, "body": s.body, "at": s.created_at.isoformat()} for s in rows]


@app.post("/ussd", response_class=PlainTextResponse)
def ussd(phoneNumber: str = Form(...), text: str = Form(""), sessionId: str = Form(""),
         serviceCode: str = Form(""), db: Session = Depends(get_db)):
    """Format Africa's Talking : réponse 'CON ...' (suite) ou 'END ...' (fin)."""
    w = services.get_wallet(db, phoneNumber)
    db.commit()
    parts = text.split("*") if text else []
    if not parts:
        return "CON Jotali\n1. Solde\n2. Retirer\n3. Historique"
    choice = parts[0]
    if choice == "1":
        return f"END Solde: {w.balance_xof} FCFA"
    if choice == "2":
        if len(parts) == 1:
            return "CON Retirer vers:\n1. Wave\n2. Orange Money"
        provider = {"1": "Wave", "2": "Orange Money"}.get(parts[1])
        if not provider:
            return "END Choix invalide."
        if len(parts) == 2:
            return f"CON Montant en FCFA (solde {w.balance_xof}):"
        try:
            amount = int(parts[2])
        except ValueError:
            return "END Montant invalide."
        return "END " + services.withdraw(db, phoneNumber, amount, provider)
    if choice == "3":
        rows = (db.query(Transfer).filter(Transfer.recipient_phone == phoneNumber, Transfer.status == "paid")
                .order_by(Transfer.id.desc()).limit(3).all())
        if not rows:
            return "END Aucune operation."
        return "END " + "\n".join(f"+{r.amount_xof} FCFA de {r.sender_name}" for r in rows)
    return "END Choix invalide."

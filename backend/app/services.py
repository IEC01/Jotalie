from sqlalchemy.orm import Session

from . import blink
from .db import Sms, Transfer, Wallet, Withdrawal


def send_sms(db: Session, phone: str, body: str) -> None:
    """Simulé : écrit en base. Remplacer par Africa's Talking / Twilio si disponible."""
    db.add(Sms(phone=phone, body=body))


def get_wallet(db: Session, phone: str) -> Wallet:
    w = db.get(Wallet, phone)
    if not w:
        w = Wallet(phone=phone, balance_xof=0)
        db.add(w)
        db.flush()
    return w


async def settle_if_paid(db: Session, t: Transfer) -> Transfer:
    """Crédite le solde UNE seule fois quand la facture est payée (idempotent)."""
    if t.status == "pending" and await blink.is_paid(t.invoice):
        t.status = "paid"
        w = get_wallet(db, t.recipient_phone)
        w.balance_xof += t.amount_xof  # montant FCFA figé à la création
        send_sms(db, t.recipient_phone,
                 f"Jotali: vous avez recu {t.amount_xof} FCFA de {t.sender_name}. Composez *123# pour votre solde.")
        db.commit()
    return t


def withdraw(db: Session, phone: str, amount_xof: int, provider: str) -> str:
    w = get_wallet(db, phone)
    if amount_xof <= 0 or amount_xof > w.balance_xof:
        return "Solde insuffisant."
    w.balance_xof -= amount_xof
    db.add(Withdrawal(phone=phone, amount_xof=amount_xof, provider=provider))
    send_sms(db, phone, f"Jotali: retrait de {amount_xof} FCFA vers {provider} effectue (simule).")
    db.commit()
    return f"Retrait de {amount_xof} FCFA vers {provider} effectue."

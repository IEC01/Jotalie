"""Parcours complet en mode mock : python tests_smoke.py"""
import os
os.environ["BLINK_MOCK"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as c:
    t = c.post("/transfers", json={"sender_name": "Awa", "recipient_phone": "221770000000", "amount_xof": 25000}).json()
    print("facture:", t["invoice"][:16], "...", t["amount_sats"], "sats", t["status"])
    c.post(f"/dev/transfers/{t['id']}/simulate-paid")
    assert c.get(f"/transfers/{t['id']}").json()["status"] == "paid"
    assert c.get(f"/transfers/{t['id']}").json()["status"] == "paid"  # idempotent
    print("SMS:", c.get("/phones/221770000000/sms").json()[0]["body"])
    u = lambda txt: c.post("/ussd", data={"phoneNumber": "221770000000", "text": txt}).text
    print(u("")); print(u("1")); print(u("2*1*10000")); print(u("1"))
    assert u("1") == "END Solde: 15000 FCFA"
print("OK")

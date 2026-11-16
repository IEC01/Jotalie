"""Client minimal Blink (GraphQL). Mode mock pour développer et démontrer sans réseau.

À VÉRIFIER dans la doc Blink (dev.blink.sv) : noms exacts des mutations/requêtes,
et l'URL signet/staging pour tester sans vrais fonds.
"""
import secrets
import httpx

from .config import settings

CREATE_INVOICE = """
mutation Create($input: LnInvoiceCreateInput!) {
  lnInvoiceCreate(input: $input) {
    invoice { paymentRequest paymentHash }
    errors { message }
  }
}"""

PAYMENT_STATUS = """
query Status($input: LnInvoicePaymentStatusInput!) {
  lnInvoicePaymentStatus(input: $input) { status errors { message } }
}"""

_mock_paid: set[str] = set()


async def _gql(query: str, variables: dict) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            settings.blink_api_url,
            json={"query": query, "variables": variables},
            headers={"X-API-KEY": settings.blink_api_key},
        )
        r.raise_for_status()
        return r.json()["data"]


async def create_invoice(amount_sats: int, memo: str) -> str:
    if settings.blink_mock:
        return "lnbc" + secrets.token_hex(24)  # fausse facture
    data = await _gql(CREATE_INVOICE, {"input": {
        "walletId": settings.blink_btc_wallet_id, "amount": amount_sats, "memo": memo}})
    res = data["lnInvoiceCreate"]
    if res["errors"]:
        raise RuntimeError(res["errors"][0]["message"])
    return res["invoice"]["paymentRequest"]


async def is_paid(invoice: str) -> bool:
    if settings.blink_mock:
        return invoice in _mock_paid
    data = await _gql(PAYMENT_STATUS, {"input": {"paymentRequest": invoice}})
    return data["lnInvoicePaymentStatus"]["status"] == "PAID"


def mock_mark_paid(invoice: str) -> None:
    _mock_paid.add(invoice)

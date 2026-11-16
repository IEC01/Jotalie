import httpx

# Le FCFA (XOF) est arrimé à l'euro : 1 EUR = 655,957 XOF (parité fixe).
XOF_PER_EUR = 655.957
FALLBACK_BTC_EUR = 85000.0  # utilisé hors-ligne / si l'API de taux échoue


async def btc_xof_rate() -> int:
    """Prix d'1 BTC en FCFA, via BTC/EUR (CoinGecko) x parité fixe."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin", "vs_currencies": "eur"},
            )
            r.raise_for_status()
            btc_eur = float(r.json()["bitcoin"]["eur"])
    except Exception:
        btc_eur = FALLBACK_BTC_EUR
    return int(btc_eur * XOF_PER_EUR)


def xof_to_sats(amount_xof: int, rate_xof_per_btc: int) -> int:
    return max(1, round(amount_xof / rate_xof_per_btc * 100_000_000))

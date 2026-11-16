# Jotali

Envoyer de l'argent au pays, aussi simplement qu'un SMS. Transferts Bitcoin Lightning pour la diaspora sénégalaise
(Dakar Bitcoin Days Hackathon #4).

## Lancer le backend (mode démo, sans réseau)

    cd backend
    pip install -r requirements.txt
    cp .env.example .env
    uvicorn app.main:app --reload
    python tests_smoke.py      # parcours complet automatisé

Docs interactives : http://localhost:8000/docs

## Endpoints

| Route | Rôle |
|---|---|
| GET /rate | Taux BTC/FCFA (via BTC/EUR x parité fixe 655,957) |
| POST /transfers | Crée un transfert + facture Lightning, taux figé |
| GET /transfers/{id} | Statut (crédite le solde une seule fois si payé) |
| POST /dev/transfers/{id}/simulate-paid | Démo : simule le paiement (mode mock) |
| GET /phones/{phone}/sms | Boîte SMS (pour le simulateur de téléphone) |
| POST /ussd | Webhook USSD au format Africa's Talking |

## Passer en réel avec Blink

Dans `.env` : `BLINK_MOCK=false`, `BLINK_API_KEY`, `BLINK_BTC_WALLET_ID`
(et l'URL signet/staging pour tester sans vrais fonds). Vérifier les requêtes GraphQL dans `app/blink.py` avec la doc Blink.

## Limites du MVP (à dire franchement)

Portefeuille custodial, SMS/USSD simulés, retrait mobile money simulé.

import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";

const API = import.meta.env.VITE_API || "http://127.0.0.1:8000";
const fmt = (n) => new Intl.NumberFormat("fr-FR").format(n);

async function api(path, options) {
  const r = await fetch(API + path, options);
  if (!r.ok) throw new Error((await r.text()) || r.status);
  return r;
}

/* ---------- Côté diaspora (web) ---------- */
function SendPanel({ phone, setPhone }) {
  const [sender, setSender] = useState("Awa");
  const [amount, setAmount] = useState(25000);
  const [rate, setRate] = useState(null);
  const [transfer, setTransfer] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api("/rate").then((r) => r.json()).then((d) => setRate(d.xof_per_btc)).catch(() => {});
  }, []);

  // Suivi du paiement : on interroge le backend toutes les 2 s
  useEffect(() => {
    if (!transfer || transfer.status === "paid") return;
    const id = setInterval(() => {
      api(`/transfers/${transfer.id}`).then((r) => r.json()).then(setTransfer).catch(() => {});
    }, 2000);
    return () => clearInterval(id);
  }, [transfer]);

  const estSats = rate ? Math.round((amount / rate) * 1e8) : null;

  async function submit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const r = await api("/transfers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sender_name: sender, recipient_phone: phone, amount_xof: Number(amount) }),
      });
      setTransfer(await r.json());
    } catch (err) {
      setError("Impossible de créer le transfert. Le backend tourne-t-il ? " + err.message);
    }
    setLoading(false);
  }

  const simulate = () => api(`/dev/transfers/${transfer.id}/simulate-paid`, { method: "POST" }).catch(() => {});

  return (
    <section className="panel">
      <h2>Côté diaspora <span className="tag">web</span></h2>
      {!transfer && (
        <form onSubmit={submit}>
          <label>Votre prénom
            <input value={sender} onChange={(e) => setSender(e.target.value)} required />
          </label>
          <label>Téléphone du bénéficiaire (Sénégal)
            <input value={phone} onChange={(e) => setPhone(e.target.value)} pattern="\+?\d{8,15}" required />
          </label>
          <label>Montant à envoyer (FCFA)
            <input type="number" min="500" max="1000000" step="500" value={amount} onChange={(e) => setAmount(e.target.value)} required />
          </label>
          <p className="hint">
            {estSats ? <>Équivalent actuel : <b>≈ {fmt(estSats)} sats</b></> : "Chargement du taux…"}
          </p>
          <button className="primary" disabled={loading}>{loading ? "Création…" : "Envoyer via Lightning"}</button>
          {error && <p className="error">{error}</p>}
        </form>
      )}

      {transfer && transfer.status !== "paid" && (
        <div className="invoice">
          <p>Payez <b>{fmt(transfer.amount_sats)} sats</b> pour envoyer <b>{fmt(transfer.amount_xof)} FCFA</b> à {phone}.</p>
          <div className="qr"><QRCodeSVG value={`lightning:${transfer.invoice}`} size={200} /></div>
          <p className="mono">{transfer.invoice.slice(0, 28)}…</p>
          <p className="hint">En attente du paiement…</p>
          <button className="ghost" onClick={simulate}>Simuler le paiement (démo)</button>
        </div>
      )}

      {transfer && transfer.status === "paid" && (
        <div className="success">
          <h3>Paiement confirmé</h3>
          <p>{fmt(transfer.amount_xof)} FCFA envoyés à {phone}. Regardez le téléphone à droite.</p>
          <button className="primary" onClick={() => setTransfer(null)}>Nouvel envoi</button>
        </div>
      )}
    </section>
  );
}

/* ---------- Côté Dakar (téléphone simple : SMS + USSD) ---------- */
function PhonePanel({ phone }) {
  const [sms, setSms] = useState([]);
  const [ussd, setUssd] = useState(null); // { text, screen, ended }
  const [reply, setReply] = useState("");

  useEffect(() => {
    const load = () => api(`/phones/${phone}/sms`).then((r) => r.json()).then(setSms).catch(() => {});
    load();
    const id = setInterval(load, 2000);
    return () => clearInterval(id);
  }, [phone]);

  async function call(text) {
    const body = new URLSearchParams({ phoneNumber: phone, text, sessionId: "demo", serviceCode: "*123#" });
    const out = await (await api("/ussd", { method: "POST", body })).text();
    setUssd({ text, screen: out.slice(4), ended: out.startsWith("END") });
    setReply("");
  }

  const answer = (e) => {
    e.preventDefault();
    if (!reply) return;
    call(ussd.text ? `${ussd.text}*${reply}` : reply);
  };

  return (
    <section className="panel dark">
      <h2>Côté Dakar <span className="tag">téléphone simple</span></h2>
      <div className="phone">
        <div className="screen">
          <h4>SMS reçus</h4>
          {sms.length === 0 && <p className="muted">Aucun message.</p>}
          {sms.slice(0, 3).map((m) => <div className="bubble" key={m.id}>{m.body}</div>)}
        </div>
        <div className="screen">
          <h4>USSD</h4>
          {!ussd && <button className="primary" onClick={() => call("")}>Composer *123#</button>}
          {ussd && (
            <>
              <pre>{ussd.screen}</pre>
              {!ussd.ended ? (
                <form onSubmit={answer} className="row">
                  <input value={reply} onChange={(e) => setReply(e.target.value)} placeholder="Votre choix" autoFocus />
                  <button className="primary">Envoyer</button>
                </form>
              ) : (
                <button className="ghost" onClick={() => setUssd(null)}>Fermer</button>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}

export default function App() {
  const [phone, setPhone] = useState("221770000000");
  return (
    <main>
      <header>
        <h1>Jotali</h1>
        <p>Envoyer de l'argent au pays, aussi simplement qu'un SMS.</p>
      </header>
      <div className="grid">
        <SendPanel phone={phone} setPhone={setPhone} />
        <PhonePanel phone={phone} />
      </div>
      <footer>MVP : portefeuille custodial, SMS/USSD et retrait mobile money simulés.</footer>
    </main>
  );
}

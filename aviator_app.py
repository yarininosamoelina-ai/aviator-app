import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import hashlib
import secrets

# =========================================================
#  APPLICATION SIMULATEUR AVIATOR — ÉDUCATIF
#  Aucune prédiction. Aucun pari réel. Argent fictif.
# =========================================================

st.set_page_config(page_title="Aviator Simulator", page_icon="🛩️", layout="wide")

st.title("🛩️ Simulateur Aviator — Éducatif")
st.error(
    "⚠️ **Aucun algorithme ne peut prédire Aviator.** "
    "Cette application simule des stratégies avec de l'argent fictif. "
    "Ne l'utilisez jamais pour parier réellement."
)

# ---------- MOTEUR ----------
def crash_point(rtp=0.97):
    u = np.random.random()
    return float("inf") if u == 0 else max(1.0, round(rtp / (1 - u), 2))

def crash_provably_fair(server_seed, client_seed, nonce, rtp=0.97):
    h = hashlib.sha256(f"{server_seed}-{client_seed}-{nonce}".encode()).hexdigest()
    u = int(h[:13], 16) / float(16**13)
    return float("inf") if u == 0 else max(1.0, round(rtp / (1 - u), 2))

def calcul_mise(strategie, mise_base, pertes, bankroll):
    if strategie == "Cashout fixe":
        return mise_base
    if strategie == "Martingale":
        return mise_base * (2 ** pertes)
    if strategie == "Fibonacci":
        fib = [1, 1]
        while len(fib) <= pertes:
            fib.append(fib[-1] + fib[-2])
        return mise_base * fib[pertes]
    if strategie == "D'Alembert":
        return mise_base + pertes * mise_base
    if strategie == "Mise proportionnelle":
        return max(0.01, round(bankroll * 0.02, 2))
    return mise_base

def simuler(bankroll, mise_base, nb_manches, strategie, cible, rtp):
    bankrolls, crashes, mises, gains = [bankroll], [], [], []
    mise, pertes = mise_base, 0
    for i in range(nb_manches):
        if bankroll < mise:
            break
        crash = crash_point(rtp)
        crashes.append(crash)
        mises.append(round(mise, 2))
        if crash >= cible:
            gain = mise * (cible - 1)
            bankroll += gain
            pertes = 0
        else:
            gain = -mise
            bankroll -= mise
            pertes += 1
        gains.append(round(gain, 2))
        bankrolls.append(round(bankroll, 2))
        mise = round(calcul_mise(strategie, mise_base, pertes, bankroll), 2)
        if mise < 0.01:
            mise = 0.01
    return bankrolls, crashes, mises, gains

def monte_carlo(nb_sims, bankroll, mise_base, nb_manches, strategie, cible, rtp):
    finals, ruines = [], 0
    for _ in range(nb_sims):
        b, c, m, g = simuler(bankroll, mise_base, nb_manches, strategie, cible, rtp)
        finals.append(b[-1])
        if b[-1] < mise_base:
            ruines += 1
    return {
        "moyenne": float(np.mean(finals)),
        "mediane": float(np.median(finals)),
        "min": float(np.min(finals)),
        "max": float(np.max(finals)),
        "ruine": ruines / nb_sims,
        "finales": finals,
    }

# ---------- INTERFACE ----------
onglets = st.tabs(["🎮 Simulation", "🎲 Monte Carlo", "📊 Comparaison", "🔐 Provably Fair"])

# ========== ONGLET 1 : SIMULATION ==========
with onglets[0]:
    st.header("Simulation manche par manche")

    col1, col2, col3 = st.columns(3)
    with col1:
        bankroll = st.number_input("Bankroll initiale (€)", 1.0, 100000.0, 100.0, 10.0)
        mise = st.number_input("Mise de base (€)", 0.1, 1000.0, 1.0, 0.1)
    with col2:
        manches = st.slider("Nombre de manches", 10, 1000, 100)
        cible = st.number_input("Cible de cashout (x)", 1.01, 100.0, 1.5, 0.1)
    with col3:
        strategie = st.selectbox(
            "Stratégie",
            ["Cashout fixe", "Martingale", "Fibonacci", "D'Alembert", "Mise proportionnelle"]
        )
        rtp = st.slider("RTP", 0.90, 1.00, 0.97, 0.01)

    if st.button("▶️ Lancer la simulation", type="primary"):
        b, c, m, g = simuler(bankroll, mise, manches, strategie, cible, rtp)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Bankroll finale", f"{b[-1]:.2f} €", f"{b[-1] - bankroll:+.2f} €")
        k2.metric("Manches jouées", len(c))
        k3.metric("Ruine ?", "Oui" if b[-1] < mise else "Non")
        k4.metric("Espérance par mise", f"{(rtp-1)*100:.2f} %")

        fig = go.Figure()
        fig.add_trace(go.Scatter(y=b, mode="lines+markers", name="Bankroll",
                                 line=dict(color="royalblue", width=2)))
        fig.add_hline(y=bankroll, line_dash="dash", line_color="gray",
                      annotation_text="Bankroll initiale")
        fig.update_layout(title="Évolution de la bankroll",
                          xaxis_title="Manche", yaxis_title="€", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            fig_h = px.histogram(x=c, nbins=40, title="Distribution des crashs",
                                 labels={"x": "Crash (x)", "y": "Fréquence"})
            st.plotly_chart(fig_h, use_container_width=True)
        with c2:
            fig_p = px.scatter(x=c, y=g, title="Gain par manche vs Crash",
                               labels={"x": "Crash (x)", "y": "Gain (€)"})
            fig_p.add_hline(y=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_p, use_container_width=True)

        df = pd.DataFrame({
            "Manche": range(1, len(c) + 1),
            "Mise (€)": m,
            "Crash": [f"{x:.2f}x" for x in c],
            "Gain (€)": g,
            "Bankroll (€)": b[1:],
        })
        st.subheader("Détail des manches")
        st.dataframe(df, use_container_width=True, height=300)
        st.download_button("⬇️ Télécharger CSV", df.to_csv(index=False).encode(),
                           "aviator_simulation.csv", "text/csv")

# ========== ONGLET 2 : MONTE CARLO ==========
with onglets[1]:
    st.header("🎲 Monte Carlo — Probabilité de ruine")
    st.write("Simule des milliers de parties pour estimer le risque réel.")

    c1, c2, c3 = st.columns(3)
    with c1:
        mc_bankroll = st.number_input("Bankroll (€)", 1.0, 100000.0, 100.0, key="mc_b")
        mc_mise = st.number_input("Mise (€)", 0.1, 1000.0, 1.0, key="mc_m")
    with c2:
        mc_manches = st.slider("Manches/partie", 10, 1000, 100, key="mc_n")
        mc_cible = st.number_input("Cible (x)", 1.01, 100.0, 1.5, key="mc_c")
    with c3:
        mc_strat = st.selectbox("Stratégie",
            ["Cashout fixe", "Martingale", "Fibonacci", "D'Alembert", "Mise proportionnelle"],
            key="mc_s")
        mc_sims = st.slider("Simulations", 100, 5000, 1000, 100)

    if st.button("🎲 Lancer Monte Carlo", type="primary"):
        with st.spinner(f"Calcul de {mc_sims} parties..."):
            r = monte_carlo(mc_sims, mc_bankroll, mc_mise, mc_manches,
                            mc_strat, mc_cible, 0.97)

        k1, k2, k3 = st.columns(3)
        k1.metric("Bankroll moyenne", f"{r['moyenne']:.2f} €")
        k2.metric("Bankroll médiane", f"{r['mediane']:.2f} €")
        k3.metric("Probabilité de ruine", f"{r['ruine']*100:.2f} %",
                  delta_color="inverse")

        k4, k5, k6 = st.columns(3)
        k4.metric("Minimum", f"{r['min']:.2f} €")
        k5.metric("Maximum", f"{r['max']:.2f} €")
        k6.metric("Espérance/mise", "-3.00 %")

        fig = px.histogram(x=r["finales"], nbins=60,
                           title=f"Distribution des bankrolls finales ({mc_sims} parties)",
                           labels={"x": "Bankroll finale (€)", "y": "Fréquence"})
        fig.add_vline(x=mc_bankroll, line_dash="dash", line_color="red",
                      annotation_text="Bankroll initiale")
        st.plotly_chart(fig, use_container_width=True)

        st.info(
            f"Sur {mc_sims} parties avec la stratégie **{mc_strat}**, "
            f"tu finis ruiné dans **{r['ruine']*100:.1f} %** des cas. "
            "L'espérance reste négative quelle que soit la stratégie."
        )

# ========== ONGLET 3 : COMPARAISON ==========
with onglets[2]:
    st.header("📊 Comparer les stratégies côte à côte")

    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        cmp_bankroll = st.number_input("Bankroll (€)", 1.0, 100000.0, 100.0, key="cmp_b")
        cmp_mise = st.number_input("Mise (€)", 0.1, 1000.0, 1.0, key="cmp_m")
    with cc2:
        cmp_manches = st.slider("Manches", 10, 1000, 100, key="cmp_n")
        cmp_cible = st.number_input("Cible (x)", 1.01, 100.0, 1.5, key="cmp_c")
    with cc3:
        cmp_strats = st.multiselect(
            "Stratégies à comparer",
            ["Cashout fixe", "Martingale", "Fibonacci", "D'Alembert", "Mise proportionnelle"],
            default=["Cashout fixe", "Martingale", "Fibonacci"]
        )

    if st.button("📊 Comparer", type="primary") and cmp_strats:
        resultats = {}
        fig = go.Figure()
        for s in cmp_strats:
            b, c, m, g = simuler(cmp_bankroll, cmp_mise, cmp_manches, s, cmp_cible, 0.97)
            resultats[s] = b
            fig.add_trace(go.Scatter(y=b, mode="lines", name=s, line=dict(width=2)))

        fig.add_hline(y=cmp_bankroll, line_dash="dash", line_color="gray")
        fig.update_layout(title="Comparaison des stratégies",
                          xaxis_title="Manche", yaxis_title="€", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        rows = [{
            "Stratégie": s,
            "Bankroll finale": f"{b[-1]:.2f} €",
            "Profit": f"{b[-1] - cmp_bankroll:+.2f} €",
            "Ruine": "Oui" if b[-1] < cmp_mise else "Non",
        } for s, b in resultats.items()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ========== ONGLET 4 : PROVABLY FAIR ==========
with onglets[3]:
    st.header("🔐 Vérification Provably Fair")
    st.markdown(
        "Aviator publie un **hash SHA-256** avant la manche, puis révèle le **seed secret** après. "
        "Tu peux ainsi vérifier que le résultat n'a pas été modifié."
    )

    pf1, pf2 = st.columns(2)
    with pf1:
        client_seed = st.text_input("Client seed", "mon_seed_123")
    with pf2:
        nonce = st.number_input("Nonce (n° de manche)", 0, 1_000_000, 0)

    if st.button("🔐 Générer une manche vérifiable", type="primary"):
        server_seed = secrets.token_hex(16)
        commit = hashlib.sha256(server_seed.encode()).hexdigest()
        crash = crash_provably_fair(server_seed, client_seed, nonce)

        st.markdown("#### 1️⃣ Commit (avant la manche)")
        st.code(f"SHA-256(server_seed) = {commit}")

        st.markdown("#### 2️⃣ Résultat calculé")
        st.metric("Point de crash", f"{crash}x")

        st.markdown("#### 3️⃣ Reveal (après la manche)")
        st.code(f"server_seed = {server_seed}")

        verif = hashlib.sha256(server_seed.encode()).hexdigest()
        if verif == commit:
            st.success("✅ Vérifié : le hash correspond. Le résultat était bien fixé à l'avance.")
        else:
            st.error("❌ Incohérence détectée.")

st.markdown("---")
st.caption(
    "⚠️ Outil éducatif. Aucune prédiction possible. RTP < 100 % = perte moyenne à long terme. "
    "Jouez responsable. France : 09 74 75 13 13."
)

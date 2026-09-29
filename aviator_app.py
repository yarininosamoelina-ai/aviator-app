import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import hashlib
import secrets
from collections import Counter

# =========================================================
#  SIMULATEUR AVIATOR — ÉDUCATIF
#  Aucune prédiction possible. Outil d'analyse statistique.
# =========================================================

st.set_page_config(page_title="Aviator Analyzer", page_icon="🛩️", layout="wide")
st.title("🛩️ Aviator Analyzer — Éducatif")
st.error(
    "⚠️ **Aucun algorithme ne peut prédire Aviator.** "
    "Cette application calcule des probabilités mathématiques. "
    "Elle ne prédit pas les tours futurs."
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
onglets = st.tabs([
    "🎮 Simulation",
    "🎲 Monte Carlo",
    "📊 Comparaison",
    "📐 Calculateur",
    "📈 Analyse de série",
    "🔐 Provably Fair",
])

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
        fig.add_hline(y=bankroll, line_dash="dash", line_color="gray")
        fig.update_layout(title="Évolution de la bankroll",
                          xaxis_title="Manche", yaxis_title="€")
        st.plotly_chart(fig, use_container_width=True)

        df = pd.DataFrame({
            "Manche": range(1, len(c) + 1),
            "Mise (€)": m,
            "Crash": [f"{x:.2f}x" for x in c],
            "Gain (€)": g,
            "Bankroll (€)": b[1:],
        })
        st.dataframe(df, use_container_width=True, height=300)
        st.download_button("⬇️ CSV", df.to_csv(index=False).encode(),
                           "simulation.csv", "text/csv")

# ========== ONGLET 2 : MONTE CARLO ==========
with onglets[1]:
    st.header("🎲 Monte Carlo — Probabilité de ruine")

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
        k3.metric("Probabilité de ruine", f"{r['ruine']*100:.2f} %")

        fig = px.histogram(x=r["finales"], nbins=60,
                           title=f"Distribution des bankrolls finales ({mc_sims} parties)")
        fig.add_vline(x=mc_bankroll, line_dash="dash", line_color="red")
        st.plotly_chart(fig, use_container_width=True)

# ========== ONGLET 3 : COMPARAISON ==========
with onglets[2]:
    st.header("📊 Comparer les stratégies")

    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        cmp_bankroll = st.number_input("Bankroll (€)", 1.0, 100000.0, 100.0, key="cmp_b")
        cmp_mise = st.number_input("Mise (€)", 0.1, 1000.0, 1.0, key="cmp_m")
    with cc2:
        cmp_manches = st.slider("Manches", 10, 1000, 100, key="cmp_n")
        cmp_cible = st.number_input("Cible (x)", 1.01, 100.0, 1.5, key="cmp_c")
    with cc3:
        cmp_strats = st.multiselect(
            "Stratégies",
            ["Cashout fixe", "Martingale", "Fibonacci", "D'Alembert", "Mise proportionnelle"],
            default=["Cashout fixe", "Martingale", "Fibonacci"]
        )

    if st.button("📊 Comparer", type="primary") and cmp_strats:
        fig = go.Figure()
        for s in cmp_strats:
            b, c, m, g = simuler(cmp_bankroll, cmp_mise, cmp_manches, s, cmp_cible, 0.97)
            fig.add_trace(go.Scatter(y=b, mode="lines", name=s))
        fig.update_layout(title="Comparaison des stratégies",
                          xaxis_title="Manche", yaxis_title="€")
        st.plotly_chart(fig, use_container_width=True)

# ========== ONGLET 4 : CALCULATEUR DE PROBABILITÉS ==========
with onglets[3]:
    st.header("📐 Calculateur de probabilités")
    st.markdown("""
    Cette section calcule la **probabilité mathématique exacte** qu'un tour atteigne un multiplicateur donné.

    **Formule officielle** (issue du système provably fair) :

    `P(crash ≥ X) = RTP / X`

    Où **RTP** est le Retour au Joueur (généralement 0.97, soit 97%).
    """)

    calc_col1, calc_col2 = st.columns([1, 2])
    with calc_col1:
        multiplicateur = st.number_input("Multiplicateur cible (x)", 1.01, 10000.0, 2.04, 0.01)
        rtp_calc = st.slider("RTP utilisé", 0.90, 1.00, 0.97, 0.01, key="rtp_calc")

    with calc_col2:
        proba = rtp_calc / multiplicateur
        proba_pct = proba * 100
        cote = 1 / proba if proba > 0 else float("inf")
        un_sur = f"1 sur {cote:.0f}"

        st.metric("Probabilité d'atteindre ce multiplicateur", f"{proba_pct:.4f} %")
        st.metric("Soit environ", un_sur)
        st.metric("Espérance mathématique par mise", f"{(rtp_calc - 1) * 100:.2f} %")

    st.markdown("---")
    st.subheader("📊 Tableau des probabilités pour différents multiplicateurs")

    multiplicateurs_table = [1.1, 1.5, 2.0, 2.04, 3.0, 5.0, 10.0, 20.0, 50.0, 100.0]
    rows = []
    for m in multiplicateurs_table:
        p = rtp_calc / m
        rows.append({
            "Multiplicateur": f"{m:.2f}x",
            "Probabilité d'atteindre": f"{p*100:.4f} %",
            "Cote (1 sur X)": f"1 sur {1/p:.1f}" if p > 0 else "∞",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("🧮 Calculateur inversé : à partir d'un multiplicateur observé")
    st.markdown(
        "Si tu as vu un tour à **X** sur Bet, la probabilité qu'il **se reproduise au prochain tour** "
        "est exactement la même que s'il n'était jamais tombé :"
    )
    m_observe = st.number_input("Multiplicateur observé (ex: 2.04)", 1.01, 10000.0, 2.04, 0.01, key="m_obs")
    p_obs = rtp_calc / m_observe
    st.info(
        f"**Probabilité que {m_observe}x retombe au prochain tour** : {p_obs*100:.4f} % "
        f"(soit environ 1 sur {1/p_obs:.0f} tours).\n\n"
        f"⚠️ **Le fait qu'il soit tombé il y a 5 minutes ne change RIEN.** "
        "Chaque tour est indépendant."
    )

# ========== ONGLET 5 : ANALYSE DE SÉRIE ==========
with onglets[4]:
    st.header("📈 Analyse de série de tours passés")
    st.markdown("""
    Colle une liste de tours passés (récupérés sur Bet ou ailleurs) pour voir pourquoi
    **aucun pattern ne prédit le futur**.
    """)

    serie_texte = st.text_area(
        "Liste des tours (séparés par virgule, espace ou saut de ligne)",
        value="1.20, 1.50, 2.04, 1.10, 3.50, 1.05, 1.85, 2.04, 1.30, 5.20, 1.15, 1.95, 2.04, 1.40",
        height=120
    )

    if st.button("🔍 Analyser la série", type="primary"):
        try:
            # Nettoyage et parsing
            import re
            texte_nettoye = re.sub(r"[,\s\n]+", " ", serie_texte.strip())
            valeurs = [float(x) for x in texte_nettoye.split() if x]
            valeurs = [v for v in valeurs if v >= 1.0]

            if len(valeurs) < 5:
                st.warning("Il faut au moins 5 valeurs pour analyser.")
            else:
                st.success(f"✅ {len(valeurs)} tours analysés.")

                # Statistiques de base
                st.subheader("📊 Statistiques descriptives")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Moyenne", f"{np.mean(valeurs):.2f}x")
                c2.metric("Médiane", f"{np.median(valeurs):.2f}x")
                c3.metric("Minimum", f"{np.min(valeurs):.2f}x")
                c4.metric("Maximum", f"{np.max(valeurs):.2f}x")

                # Histogramme
                fig = px.histogram(x=valeurs, nbins=30,
                                   title="Distribution des multiplicateurs observés",
                                   labels={"x": "Multiplicateur", "y": "Fréquence"})
                st.plotly_chart(fig, use_container_width=True)

                # Recherche d'un multiplicateur spécifique
                st.subheader("🎯 Recherche d'un multiplicateur spécifique")
                m_cible = st.number_input("Multiplicateur à retrouver", 1.01, 10000.0, 2.04, 0.01, key="m_serie")
                occurrences = [i+1 for i, v in enumerate(valeurs) if abs(v - m_cible) < 0.05]

                if occurrences:
                    st.info(
                        f"Le multiplicateur **{m_cible}x** apparaît aux positions : "
                        f"**{', '.join(map(str, occurrences))}** "
                        f"(soit {len(occurrences)} fois sur {len(valeurs)} tours)."
                    )
                    # Calcul des écarts entre occurrences
                    if len(occurrences) > 1:
                        ecarts = [occurrences[i+1] - occurrences[i] for i in range(len(occurrences)-1)]
                        st.write(f"**Écarts entre les apparitions** : {ecarts}")
                        st.write(f"**Écart moyen** : {np.mean(ecarts):.1f} tours")
                        st.warning(
                            "⚠️ **Ces écarts ne sont PAS prédictifs.** Ils varient énormément d'une série à l'autre. "
                            "La prochaine apparition peut survenir dans 1 tour, 100 tours, ou jamais."
                        )
                else:
                    st.warning(f"Le multiplicateur {m_cible}x n'apparaît pas dans cette série (tolérance 0.05).")

                # Test d'indépendance : le tour précédent influence-t-il le suivant ?
                st.subheader("🔬 Test d'indépendance")
                st.markdown("""
                **Question** : après un tour ≥ 2x, le tour suivant a-t-il plus de chances d'être ≥ 2x ?
                Si Aviator était prédictible, on verrait une corrélation. Regardons les faits.
                """)

                seuil = 2.0
                suites = []
                for i in range(len(valeurs) - 1):
                    if valeurs[i] >= seuil:
                        suites.append(valeurs[i+1] >= seuil)

                if suites:
                    proba_conditionnelle = sum(suites) / len(suites)
                    proba_theorique = rtp_calc / seuil
                    st.write(f"**Nombre de cas où un tour ≥ {seuil}x est suivi d'un autre tour ≥ {seuil}x** : {sum(suites)} / {len(suites)}")
                    st.write(f"**Probabilité observée après un gros tour** : {proba_conditionnelle*100:.2f} %")
                    st.write(f"**Probabilité théorique (indépendante)** : {proba_theorique*100:.2f} %")
                    ecart = abs(proba_conditionnelle - proba_theorique) * 100
                    if ecart < 10:
                        st.success(
                            f"✅ L'écart est de {ecart:.2f} points. **Aucune corrélation détectable.** "
                            "Les tours sont bien indépendants."
                        )
                    else:
                        st.info(
                            f"L'écart est de {ecart:.2f} points. **C'est du bruit statistique** "
                            "(échantillon trop petit). Avec plus de données, l'écart se réduirait à 0."
                        )
                else:
                    st.warning(f"Aucun tour ≥ {seuil}x trouvé dans la série pour tester la condition.")

                # Conclusion
                st.markdown("---")
                st.error(
                    "🚫 **Conclusion** : Aucun pattern dans cette série ne permet de prédire le prochain tour. "
                    "Chaque manche est indépendante et déterminée à l'avance par le serveur. "
                    "Les 'prédicteurs' vendus en ligne exploitent cette illusion."
                )

        except Exception as e:
            st.error(f"Erreur de parsing : {e}")

# ========== ONGLET 6 : PROVABLY FAIR ==========
with onglets[5]:
    st.header("🔐 Vérification Provably Fair")
    st.markdown(
        "Aviator publie un **hash SHA-256** avant la manche, puis révèle le **seed secret** après."
    )

    pf1, pf2 = st.columns(2)
    with pf1:
        client_seed = st.text_input("Client seed", "mon_seed_123")
    with pf2:
        nonce = st.number_input("Nonce", 0, 1_000_000, 0)

    if st.button("🔐 Générer une manche vérifiable", type="primary"):
        server_seed = secrets.token_hex(16)
        commit = hashlib.sha256(server_seed.encode()).hexdigest()
        crash = crash_provably_fair(server_seed, client_seed, nonce)

        st.markdown("#### 1️⃣ Commit")
        st.code(f"SHA-256(server_seed) = {commit}")
        st.markdown("#### 2️⃣ Résultat")
        st.metric("Crash", f"{crash}x")
        st.markdown("#### 3️⃣ Reveal")
        st.code(f"server_seed = {server_seed}")

        if hashlib.sha256(server_seed.encode()).hexdigest() == commit:
            st.success("✅ Vérifié : le résultat était fixé à l'avance.")

st.markdown("---")
st.caption(
    "⚠️ Outil éducatif. Aucune prédiction possible. RTP < 100 % = perte moyenne. "
    "Jouez responsable. France : 09 74 75 13 13."
                      )

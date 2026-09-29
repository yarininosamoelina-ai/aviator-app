import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import hashlib
import secrets
import re

# =========================================================
#  SIMULATEUR AVIATOR — ÉDUCATIF
#  Aucune prédiction possible. Outil d'analyse statistique.
# =========================================================

st.set_page_config(page_title="Aviator Analyzer", page_icon="🛩️", layout="wide")
st.title("🛩️ Aviator Analyzer — Éducatif")
st.error(
    "⚠️ **Aucun algorithme ne peut prédire Aviator.** "
    "Cette application calcule des probabilités. Elle ne prédit pas les tours futurs."
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
    "⏳ Simulateur d'attente",
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

# ========== ONGLET 4 : CALCULATEUR ==========
with onglets[3]:
    st.header("📐 Calculateur de probabilités")
    st.markdown("""
    **Formule officielle** : `P(crash ≥ X) = RTP / X`
    """)

    calc_col1, calc_col2 = st.columns([1, 2])
    with calc_col1:
        multiplicateur = st.number_input("Multiplicateur cible (x)", 1.01, 10000.0, 2.04, 0.01)
        rtp_calc = st.slider("RTP utilisé", 0.90, 1.00, 0.97, 0.01, key="rtp_calc")

    with calc_col2:
        proba = rtp_calc / multiplicateur
        st.metric("Probabilité d'atteindre ce multiplicateur", f"{proba*100:.4f} %")
        st.metric("Soit environ", f"1 sur {1/proba:.0f}")
        st.metric("Espérance par mise", f"{(rtp_calc - 1) * 100:.2f} %")

    st.markdown("---")
    st.subheader("📊 Tableau des probabilités")

    multiplicateurs_table = [1.1, 1.5, 2.0, 2.04, 3.0, 5.0, 10.0, 20.0, 50.0, 100.0]
    rows = []
    for m in multiplicateurs_table:
        p = rtp_calc / m
        rows.append({
            "Multiplicateur": f"{m:.2f}x",
            "Probabilité d'atteindre": f"{p*100:.4f} %",
            "Cote": f"1 sur {1/p:.1f}",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ========== ONGLET 5 : SIMULATEUR D'ATTENTE ==========
with onglets[4]:
    st.header("⏳ Simulateur d'attente")
    st.markdown("""
    Tu veux savoir **combien de temps il faut attendre** pour qu'un multiplicateur précis revienne ?
    Cet outil simule des milliers de parties pour te montrer la **réalité mathématique** :
    le temps d'attente est **totalement imprévisible**.

    👉 **Entre un multiplicateur** (ex : 2.04x) et observe la distribution.
    """)

    att_col1, att_col2 = st.columns([1, 2])
    with att_col1:
        m_cible = st.number_input("Multiplicateur recherché (x)", 1.01, 100.0, 2.04, 0.01, key="att_m")
        nb_sims_att = st.slider("Nombre de parties simulées", 100, 5000, 1000, 100, key="att_sims")
        max_attente = st.slider("Limite d'attente max (tours)", 10, 500, 100, 10, key="att_max")

    proba_theorique = 0.97 / m_cible

    with att_col2:
        st.metric("Probabilité à chaque tour", f"{proba_theorique*100:.2f} %")
        st.metric("Attente moyenne théorique", f"{1/proba_theorique:.1f} tours")

    if st.button("⏳ Simuler les temps d'attente", type="primary"):
        with st.spinner("Simulation en cours..."):
            temps_attente = []
            non_trouves = 0

            for _ in range(nb_sims_att):
                trouve = False
                for tour in range(1, max_attente + 1):
                    crash = crash_point(0.97)
                    if crash >= m_cible:
                        temps_attente.append(tour)
                        trouve = True
                        break
                if not trouve:
                    non_trouves += 1

            if not temps_attente:
                st.error("Aucune occurrence trouvée. Essaie avec un multiplicateur plus bas.")
            else:
                temps_attente = np.array(temps_attente)

                st.markdown("### 📊 Résultats de la simulation")

                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Attente moyenne observée", f"{temps_attente.mean():.1f} tours")
                k2.metric("Attente médiane", f"{np.median(temps_attente):.0f} tours")
                k3.metric("Attente minimum", f"{temps_attente.min()} tour(s)")
                k4.metric("Attente maximum", f"{temps_attente.max()} tours")

                st.markdown(f"**Sur {nb_sims_att} parties simulées :**")
                st.write(f"- Le multiplicateur **{m_cible}x** est apparu dans les {max_attente} premiers tours : **{len(temps_attente)} fois**")
                st.write(f"- Il n'est **pas apparu** dans les {max_attente} premiers tours : **{non_trouves} fois**")
                st.write(f"- Attente la plus longue observée : **{temps_attente.max()} tours**")
                st.write(f"- Attente la plus courte : **{temps_attente.min()} tour**")

                # Histogramme
                fig = px.histogram(x=temps_attente, nbins=40,
                                   title=f"Distribution du temps d'attente pour {m_cible}x",
                                   labels={"x": "Nombre de tours avant apparition", "y": "Fréquence"})
                fig.add_vline(x=float(temps_attente.mean()), line_dash="dash",
                              line_color="red", annotation_text="Moyenne")
                st.plotly_chart(fig, use_container_width=True)

                # Explication
                st.markdown("---")
                st.markdown("### 🎯 Que retenir ?")

                ecart_type = temps_attente.std()
                st.warning(f"""
                **Regarde bien l'écart entre le minimum et le maximum :**
                - Attente la plus courte : **{temps_attente.min()} tour(s)**
                - Attente la plus longue : **{temps_attente.max()} tours**
                - Écart-type : **{ecart_type:.1f} tours**

                Si tu cherches `{m_cible}x` après l'avoir vu, tu peux très bien le retrouver :
                - ✅ **Dès le tour suivant** (chance)
                - ❌ **Après {temps_attente.max()} tours ou plus** (pas de chance)

                **Il n'y a AUCUN moyen de savoir à l'avance.** L'écart est gigantesque.
                """)

                st.error(
                    "🚫 **Conclusion** : Le temps d'attente varie énormément d'une situation à l'autre. "
                    "Aucune application ne peut prédire 'l'heure probable' d'un tour. "
                    "Toutes celles qui le prétendent sont des arnaques."
                )

                # Comparaison avec ce qu'un "prédicteur" annoncerait
                st.markdown("---")
                st.markdown("### 🔍 Test : un 'prédicteur' pourrait-il deviner ?")
                st.markdown(f"""
                Imaginons qu'un site te dise : *"Le prochain {m_cible}x arrivera dans X tours"*.

                Voici, sur {len(temps_attente)} apparitions réelles, ce qui s'est passé :

                - S'il avait dit **"dans 1 tour"** → il aurait eu raison **{(temps_attente == 1).sum()/len(temps_attente)*100:.1f} % du temps**
                - S'il avait dit **"dans {int(np.median(temps_attente))} tours"** → **{(temps_attente == np.median(temps_attente)).sum()/len(temps_attente)*100:.1f} % du temps**
                - S'il avait dit **"dans 10 tours"** → **{(temps_attente == 10).sum()/len(temps_attente)*100:.1f} % du temps**

                Aucune prédiction fixe ne fonctionne. Le "prédicteur" n'aurait raison qu'**une fois sur {int(len(temps_attente)/(temps_attente == int(np.median(temps_attente))).sum()) if (temps_attente == int(np.median(temps_attente))).sum() > 0 else 'X'}**, au mieux.
                """)

# ========== ONGLET 6 : ANALYSE DE SÉRIE ==========
with onglets[5]:
    st.header("📈 Analyse de série de tours passés")

    serie_texte = st.text_area(
        "Liste des tours (séparés par virgule, espace ou saut de ligne)",
        value="1.20, 1.50, 2.04, 1.10, 3.50, 1.05, 1.85, 2.04, 1.30, 5.20, 1.15, 1.95, 2.04, 1.40",
        height=120
    )

    if st.button("🔍 Analyser la série", type="primary"):
        try:
            texte_nettoye = re.sub(r"[,\s\n]+", " ", serie_texte.strip())
            valeurs = [float(x) for x in texte_nettoye.split() if x]
            valeurs = [v for v in valeurs if v >= 1.0]

            if len(valeurs) < 5:
                st.warning("Il faut au moins 5 valeurs.")
            else:
                st.success(f"✅ {len(valeurs)} tours analysés.")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Moyenne", f"{np.mean(valeurs):.2f}x")
                c2.metric("Médiane", f"{np.median(valeurs):.2f}x")
                c3.metric("Minimum", f"{np.min(valeurs):.2f}x")
                c4.metric("Maximum", f"{np.max(valeurs):.2f}x")

                fig = px.histogram(x=valeurs, nbins=30,
                                   title="Distribution des multiplicateurs")
                st.plotly_chart(fig, use_container_width=True)

                st.subheader("🎯 Recherche d'un multiplicateur")
                m_cible_serie = st.number_input("Multiplicateur", 1.01, 100.0, 2.04, 0.01, key="m_serie")
                occurrences = [i+1 for i, v in enumerate(valeurs) if abs(v - m_cible_serie) < 0.05]

                if occurrences:
                    st.info(f"**{m_cible_serie}x** apparaît aux positions : **{', '.join(map(str, occurrences))}** ({len(occurrences)} fois sur {len(valeurs)})")
                    if len(occurrences) > 1:
                        ecarts = [occurrences[i+1] - occurrences[i] for i in range(len(occurrences)-1)]
                        st.write(f"**Écarts observés** : {ecarts}")
                        st.write(f"**Écart moyen** : {np.mean(ecarts):.1f} tours")
                        st.warning("⚠️ Ces écarts varient énormément. Ils ne prédisent rien.")
                else:
                    st.warning(f"{m_cible_serie}x n'apparaît pas dans la série.")

                st.subheader("🔬 Test d'indépendance")
                seuil = 2.0
                suites = [valeurs[i+1] >= seuil for i in range(len(valeurs)-1) if valeurs[i] >= seuil]
                if suites:
                    proba_obs = sum(suites) / len(suites)
                    proba_theo = 0.97 / seuil
                    st.write(f"Probabilité observée après un tour ≥ {seuil}x : **{proba_obs*100:.2f} %**")
                    st.write(f"Probabilité théorique : **{proba_theo*100:.2f} %**")
                    if abs(proba_obs - proba_theo) < 0.15:
                        st.success("✅ Aucune corrélation. Les tours sont indépendants.")
                    else:
                        st.info("Écart = bruit statistique (échantillon trop petit).")

                st.error("🚫 Aucun pattern ne permet de prédire le prochain tour.")

        except Exception as e:
            st.error(f"Erreur : {e}")

# ========== ONGLET 7 : PROVABLY FAIR ==========
with onglets[6]:
    st.header("🔐 Vérification Provably Fair")

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
            st.success("✅ Vérifié.")

st.markdown("---")
st.caption("⚠️ Outil éducatif. Aucune prédiction possible.")

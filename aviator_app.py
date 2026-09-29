import streamlit as st

# ============ PROTECTION PAR MOT DE PASSE ============
def check_password():
    def password_entered():
        if st.session_state.get("password", "") == "yarinino 5730":
            st.session_state["password_correct"] = True
            if "password" in st.session_state:
                del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Application privée")
        st.text_input("Mot de passe", type="password",
                      on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 Application privée")
        st.text_input("Mot de passe", type="password",
                      on_change=password_entered, key="password")
        st.error("❌ Mot de passe incorrect")
        return False
    return True

if not check_password():
    st.stop()
# ============ FIN PROTECTION ============import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import hashlib
import secrets
import re
from datetime import datetime, timedelta

st.set_page_config(page_title="Aviator Analyzer", page_icon="🛩️", layout="wide")
st.title("🛩️ Aviator Analyzer — Éducatif")
st.error(
    "⚠️ **Aucun algorithme ne peut prédire Aviator.** "
    "Les heures affichées sont des estimations statistiques basées sur le passé. "
    "Elles ne garantissent RIEN sur le futur."
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
    "⏳ Attente",
    "🕐 Heure de retour",
    "📈 Analyse de série",
    "🔐 Provably Fair",
])

# ========== ONGLETS 1 à 5 (inchangés) ==========
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
        strategie = st.selectbox("Stratégie",
            ["Cashout fixe", "Martingale", "Fibonacci", "D'Alembert", "Mise proportionnelle"])
        rtp = st.slider("RTP", 0.90, 1.00, 0.97, 0.01)

    if st.button("▶️ Lancer la simulation", type="primary"):
        b, c, m, g = simuler(bankroll, mise, manches, strategie, cible, rtp)
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Bankroll finale", f"{b[-1]:.2f} €", f"{b[-1] - bankroll:+.2f} €")
        k2.metric("Manches jouées", len(c))
        k3.metric("Ruine ?", "Oui" if b[-1] < mise else "Non")
        k4.metric("Espérance par mise", f"{(rtp-1)*100:.2f} %")
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=b, mode="lines+markers", name="Bankroll"))
        fig.update_layout(title="Évolution", xaxis_title="Manche", yaxis_title="€")
        st.plotly_chart(fig, use_container_width=True)

with onglets[1]:
    st.header("🎲 Monte Carlo")
    c1, c2, c3 = st.columns(3)
    with c1:
        mc_bankroll = st.number_input("Bankroll (€)", 1.0, 100000.0, 100.0, key="mc_b")
        mc_mise = st.number_input("Mise (€)", 0.1, 1000.0, 1.0, key="mc_m")
    with c2:
        mc_manches = st.slider("Manches/partie", 10, 1000, 100, key="mc_n")
        mc_cible = st.number_input("Cible (x)", 1.01, 100.0, 1.5, key="mc_c")
    with c3:
        mc_strat = st.selectbox("Stratégie",
            ["Cashout fixe", "Martingale", "Fibonacci", "D'Alembert", "Mise proportionnelle"], key="mc_s")
        mc_sims = st.slider("Simulations", 100, 5000, 1000, 100)
    if st.button("🎲 Lancer", type="primary"):
        with st.spinner("Calcul..."):
            r = monte_carlo(mc_sims, mc_bankroll, mc_mise, mc_manches, mc_strat, mc_cible, 0.97)
        k1, k2, k3 = st.columns(3)
        k1.metric("Bankroll moyenne", f"{r['moyenne']:.2f} €")
        k2.metric("Bankroll médiane", f"{r['mediane']:.2f} €")
        k3.metric("Probabilité de ruine", f"{r['ruine']*100:.2f} %")
        fig = px.histogram(x=r["finales"], nbins=60, title="Distribution")
        st.plotly_chart(fig, use_container_width=True)

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
        cmp_strats = st.multiselect("Stratégies",
            ["Cashout fixe", "Martingale", "Fibonacci", "D'Alembert", "Mise proportionnelle"],
            default=["Cashout fixe", "Martingale"])
    if st.button("📊 Comparer", type="primary") and cmp_strats:
        fig = go.Figure()
        for s in cmp_strats:
            b, c, m, g = simuler(cmp_bankroll, cmp_mise, cmp_manches, s, cmp_cible, 0.97)
            fig.add_trace(go.Scatter(y=b, mode="lines", name=s))
        st.plotly_chart(fig, use_container_width=True)

with onglets[3]:
    st.header("📐 Calculateur")
    col1, col2 = st.columns([1, 2])
    with col1:
        multiplicateur = st.number_input("Multiplicateur (x)", 1.01, 10000.0, 2.04, 0.01)
        rtp_calc = st.slider("RTP", 0.90, 1.00, 0.97, 0.01, key="rtp_c")
    with col2:
        proba = rtp_calc / multiplicateur
        st.metric("Probabilité d'atteindre", f"{proba*100:.4f} %")
        st.metric("Soit", f"1 sur {1/proba:.0f}")
        st.metric("Espérance par mise", f"{(rtp_calc - 1) * 100:.2f} %")

with onglets[4]:
    st.header("⏳ Simulateur d'attente")
    col1, col2 = st.columns([1, 2])
    with col1:
        m_cible = st.number_input("Multiplicateur (x)", 1.01, 100.0, 2.04, 0.01, key="att_m")
        nb_sims_att = st.slider("Parties simulées", 100, 5000, 1000, 100, key="att_s")
    proba_theo = 0.97 / m_cible
    with col2:
        st.metric("Probabilité par tour", f"{proba_theo*100:.2f} %")
        st.metric("Attente moyenne", f"{1/proba_theo:.1f} tours")
    if st.button("⏳ Simuler", type="primary"):
        temps_attente = []
        for _ in range(nb_sims_att):
            for tour in range(1, 201):
                if crash_point(0.97) >= m_cible:
                    temps_attente.append(tour)
                    break
        if temps_attente:
            ta = np.array(temps_attente)
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Attente moyenne", f"{ta.mean():.1f} tours")
            k2.metric("Médiane", f"{np.median(ta):.0f} tours")
            k3.metric("Minimum", f"{ta.min()} tour")
            k4.metric("Maximum", f"{ta.max()} tours")
            fig = px.histogram(x=ta, nbins=40, title="Distribution des attentes")
            st.plotly_chart(fig, use_container_width=True)

# ========== ONGLET 6 : HEURE DE RETOUR ==========
with onglets[5]:
    st.header("🕐 Heure probable de retour d'un tour")
    st.markdown("""
    **Comment ça marche** : tu entres les tours passés avec leur heure.
    L'application calcule les intervalles entre les occurrences d'un multiplicateur,
    puis estime **l'heure probable** de la prochaine apparition.

    ⚠️ **Attention** : cette "heure probable" est basée sur la moyenne des intervalles passés.
    La réalité peut être très différente à cause de l'énorme variance. Ce n'est **pas une prédiction**.
    """)

    st.subheader("📝 Étape 1 : Enregistre les tours passés")
    st.markdown("Format : **`HH:MM multiplicateur`** — une ligne par tour.")

    exemple = """17:50 2.04
17:52 1.50
17:54 2.04
17:56 1.20
17:58 3.50
18:00 2.04
18:02 1.10
18:05 1.85
18:07 2.04
18:10 1.30"""

    tours_texte = st.text_area("Tours passés (HH:MM → multiplicateur)", value=exemple, height=200)

    col_a, col_b = st.columns(2)
    with col_a:
        m_recherche = st.number_input("Multiplicateur à suivre", 1.01, 100.0, 2.04, 0.01, key="m_ret")
    with col_b:
        duree_tour_sec = st.number_input("Durée moyenne d'un tour (secondes)", 5, 300, 30, 1)

    if st.button("🕐 Calculer l'heure probable", type="primary"):
        # Parsing
        lignes = [l.strip() for l in tours_texte.strip().split("\n") if l.strip()]
        tours = []
        erreurs = []
        for ligne in lignes:
            parties = ligne.replace("→", " ").replace("->", " ").split()
            if len(parties) < 2:
                erreurs.append(ligne)
                continue
            try:
                heure_str = parties[0]
                mult = float(parties[1].replace("x", "").replace(",", "."))
                h, m = map(int, heure_str.split(":"))
                tours.append({"heure": heure_str, "heure_min": h*60+m, "mult": mult})
            except Exception:
                erreurs.append(ligne)

        if erreurs:
            st.warning(f"Lignes ignorées (format invalide) : {erreurs}")

        if len(tours) < 3:
            st.error("Il faut au moins 3 tours valides.")
        else:
            df_tours = pd.DataFrame(tours)
            st.success(f"✅ {len(tours)} tours chargés.")

            # Filtrer les occurrences
            tolerance = 0.05
            occurrences = df_tours[abs(df_tours["mult"] - m_recherche) <= tolerance].copy()

            if len(occurrences) < 2:
                st.error(f"Le multiplicateur **{m_recherche}x** n'apparaît pas assez de fois (min 2). Trouvé : {len(occurrences)}.")
            else:
                # Calcul des intervalles
                occ_sorted = occurrences.sort_values("heure_min")
                heures = occ_sorted["heure_min"].tolist()
                heures_str = occ_sorted["heure"].tolist()
                intervalles = [heures[i+1] - heures[i] for i in range(len(heures)-1)]

                st.subheader(f"📊 Analyse de {m_recherche}x")

                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Nombre d'apparitions", len(occurrences))
                k2.metric("Intervalle moyen", f"{np.mean(intervalles):.1f} min")
                k3.metric("Intervalle minimum", f"{min(intervalles)} min")
                k4.metric("Intervalle maximum", f"{max(intervalles)} min")

                # Heure de la dernière occurrence
                derniere_heure = occ_sorted.iloc[-1]["heure"]
                derniere_min = occ_sorted.iloc[-1]["heure_min"]

                st.markdown("---")
                st.subheader("🕐 Heure probable du prochain retour")

                # Estimation basée sur la moyenne
                intervalle_moyen = np.mean(intervalles)
                heure_estimee_min = derniere_min + intervalle_moyen

                # Convertir en HH:MM
                h_est = int(heure_estimee_min // 60) % 24
                m_est = int(heure_estimee_min % 60)
                heure_estimee_str = f"{h_est:02d}:{m_est:02d}"

                # Marge d'erreur (basée sur l'écart-type)
                ecart_type = np.std(intervalles) if len(intervalles) > 1 else 0
                heure_min_min = derniere_min + max(0, intervalle_moyen - ecart_type)
                heure_max_min = derniere_min + intervalle_moyen + ecart_type

                h_min = int(heure_min_min // 60) % 24
                m_min = int(heure_min_min % 60)
                h_max = int(heure_max_min // 60) % 24
                m_max = int(heure_max_min % 60)

                col_res1, col_res2, col_res3 = st.columns(3)
                with col_res1:
                    st.metric("🕐 Dernière apparition", derniere_heure)
                with col_res2:
                    st.metric("🎯 Heure probable", heure_estimee_str,
                              help="Basée sur la moyenne des intervalles passés")
                with col_res3:
                    st.metric("📊 Marge d'erreur",
                              f"{h_min:02d}:{m_min} → {h_max:02d}:{m_max}")

                st.markdown("---")
                st.subheader("📋 Intervalles observés")
                for i, inter in enumerate(intervalles):
                    st.write(f"- Entre **{heures_str[i]}** et **{heures_str[i+1]}** : **{inter} min**")

                # Graphique des intervalles
                fig = go.Figure()
                fig.add_trace(go.Bar(x=heures_str[:-1], y=intervalles,
                                     name="Intervalles", marker_color="royalblue"))
                fig.add_hline(y=intervalle_moyen, line_dash="dash", line_color="red",
                              annotation_text=f"Moyenne : {intervalle_moyen:.1f} min")
                fig.update_layout(title="Intervalle entre chaque apparition",
                                  xaxis_title="Heure de départ", yaxis_title="Minutes")
                st.plotly_chart(fig, use_container_width=True)

                # ⚠️ AVERTISSEMENT CRUCIAL
                st.markdown("---")
                st.error(f"""
                ### 🚨 À LIRE ABSOLUMENT

                **L'heure probable ({heure_estimee_str}) est une moyenne, PAS une prédiction.**

                Regarde bien les intervalles ci-dessus : ils varient de **{min(intervalles)} min** à **{max(intervalles)} min**.
                Cela veut dire que le prochain {m_recherche}x peut très bien arriver :
                - ✅ **Dans {min(intervalles)} minutes** (si ça suit le minimum observé)
                - ❌ **Dans {max(intervalles)} minutes** (si ça suit le maximum observé)
                - 🤷 **Dans 1 minute** ou **dans 2 heures** (cas déjà vus dans d'autres séries)

                **Aucune application ne peut garantir une heure précise.**
                Celles qui te vendent des "heures exactes" utilisent exactement ce calcul,
                mais te cachent la marge d'erreur énorme. C'est de la manipulation.
                """)

                # Simulation de la réalité
                st.markdown("---")
                st.subheader("🔬 Preuve par simulation")
                st.markdown(f"""
                Voici ce qui se passerait **réellement** si tu attendais l'heure prédite pendant 1000 parties.
                Chaque partie simule le temps d'attente réel jusqu'à retomber sur {m_recherche}x.
                """)

                # Simuler 1000 fois l'attente RÉELLE
                proba_theo = 0.97 / m_recherche
                attentes_simulees = []
                for _ in range(1000):
                    for tour in range(1, 500):
                        if crash_point(0.97) >= m_recherche:
                            attentes_simulees.append(tour * duree_tour_sec / 60)
                            break

                attentes_simulees = np.array(attentes_simulees)

                # Heures simulées
                heures_simulees = []
                for att in attentes_simulees:
                    h_sim = (derniere_min + att) % (24*60)
                    heures_simulees.append(h_sim)

                fig2 = px.histogram(x=heures_simulees, nbins=48,
                                    title=f"Répartition RÉELLE des heures d'apparition de {m_recherche}x",
                                    labels={"x": "Heure (minutes depuis minuit)", "y": "Fréquence"})
                fig2.add_vline(x=heure_estimee_min % (24*60), line_dash="dash",
                               line_color="red", annotation_text="Heure 'prédite'")
                st.plotly_chart(fig2, use_container_width=True)

                # Combien de fois l'heure prédite est correcte ?
                marge_min = 2  # tolérance de 2 minutes
                nb_correct = sum(1 for h in heures_simulees
                                 if abs(h - (heure_estimee_min % (24*60))) <= marge_min)
                pct_correct = nb_correct / len(heures_simulees) * 100

                st.warning(f"""
                ### 📉 Résultat de la simulation

                Sur **1000 parties simulées**, l'heure prédite (**{heure_estimee_str}**) 
                avec une tolérance de ±2 minutes n'est tombée juste que **{nb_correct} fois**,
                soit **{pct_correct:.1f} %**.

                Les apparitions sont **dispersées sur toute la plage horaire**.
                Cela prouve que l'heure "probable" ne vaut rien dans la pratique.
                """)

# ========== ONGLET 7 : ANALYSE DE SÉRIE ==========
with onglets[6]:
    st.header("📈 Analyse de série")
    serie_texte = st.text_area("Tours (séparés par virgule)",
        value="1.20, 1.50, 2.04, 1.10, 3.50, 1.05, 1.85, 2.04, 1.30, 5.20, 1.15, 1.95, 2.04, 1.40", height=100)
    if st.button("🔍 Analyser", type="primary"):
        try:
            vals = [float(x) for x in re.sub(r"[,\s\n]+", " ", serie_texte.strip()).split() if x]
            vals = [v for v in vals if v >= 1.0]
            if len(vals) >= 5:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Moyenne", f"{np.mean(vals):.2f}x")
                c2.metric("Médiane", f"{np.median(vals):.2f}x")
                c3.metric("Min", f"{np.min(vals):.2f}x")
                c4.metric("Max", f"{np.max(vals):.2f}x")
                fig = px.histogram(x=vals, nbins=30, title="Distribution")
                st.plotly_chart(fig, use_container_width=True)
                st.error("🚫 Aucun pattern ne permet de prédire le prochain tour.")
            else:
                st.warning("Il faut au moins 5 valeurs.")
        except Exception as e:
            st.error(f"Erreur : {e}")

# ========== ONGLET 8 : PROVABLY FAIR ==========
with onglets[7]:
    st.header("🔐 Provably Fair")
    pf1, pf2 = st.columns(2)
    with pf1:
        client_seed = st.text_input("Client seed", "mon_seed")
    with pf2:
        nonce = st.number_input("Nonce", 0, 1_000_000, 0)
    if st.button("🔐 Générer", type="primary"):
        server_seed = secrets.token_hex(16)
        commit = hashlib.sha256(server_seed.encode()).hexdigest()
        crash = crash_provably_fair(server_seed, client_seed, nonce)
        st.code(f"Commit : {commit}")
        st.metric("Crash", f"{crash}x")
        st.code(f"Server seed : {server_seed}")
        st.success("✅ Vérifié.")

st.markdown("---")
st.caption("⚠️ Outil éducatif. Aucune prédiction fiable possible.")

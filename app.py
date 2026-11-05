from pathlib import Path
 
import pandas as pd
import streamlit as st
 
DOSSIER = Path(__file__).parent / "donnees"
 
st.set_page_config(page_title="L'électricité dans 12 quartiers", page_icon="⚡", layout="wide")
 
 
@st.cache_data
def charger_donnees():
    return pd.read_csv(DOSSIER / "consommation_propre.csv")
 
 
donnees = charger_donnees()
 
st.title("L'électricité dans 12 quartiers")
st.caption("Relevés mensuels de janvier 2024 à décembre 2025. Données fictives.")
 
st.markdown(
    "Une compagnie d'électricité veut savoir si la consommation de ses quartiers "
    "suit la chaleur, ou les heures de courant. "
    f"Ce tableau de bord présente **{len(donnees)} relevés mensuels**, nettoyés, "
    "pour 12 quartiers de Port-au-Prince, Delmas, Pétion-Ville et Cap-Haïtien."
)
 
st.sidebar.header("Filtres")
 
communes = sorted(donnees["commune"].unique())
choix_communes = st.sidebar.multiselect("Communes", communes, default=communes)
 
annees = sorted(donnees["annee"].unique())
annee = st.sidebar.selectbox("Année", annees, index=annees.index(2025))
 
if not choix_communes:
    st.warning("Choisissez au moins une commune dans la barre latérale.")
    st.stop()
 
par_communes = donnees[donnees["commune"].isin(choix_communes)]
filtre = par_communes[par_communes["annee"] == annee]
 
total_millions = filtre["kwh"].sum() / 1_000_000
par_abonne = filtre["kwh_par_abonne"].mean()
heures = filtre["heures_courant"].mean()
 
col1, col2, col3 = st.columns(3)
col1.metric("Consommation totale", f"{total_millions:.2f} millions de kWh")
col2.metric("Consommation par abonné", f"{par_abonne:.1f} kWh / mois")
col3.metric("Heures de courant", f"{heures:.1f} h / jour")
 
onglet1, onglet2, onglet3, onglet4, onglet5 = st.tabs(
    ["Par abonné", "Évolution", "Chaleur ou courant ?", "Coupures", "Relevés hors norme"]
)
 
with onglet1:
    st.subheader("Quels quartiers consomment le plus par abonné ?")
    par_type = par_communes.groupby("type")["kwh_par_abonne"].mean().round(1)
    classement = (
        par_communes.groupby("quartier")["kwh_par_abonne"]
        .mean()
        .round(1)
        .sort_values(ascending=False)
    )
    st.bar_chart(classement, x_label="Quartier", y_label="kWh par abonné et par mois")
    st.markdown(
        f"Un abonné commercial consomme en moyenne **{par_type['Commercial']} kWh** par mois, "
        f"contre **{par_type['Résidentiel']} kWh** pour un abonné résidentiel. "
        f"En tête du classement : **{classement.index[0]}** ({classement.iloc[0]} kWh par abonné)."
    )
 
with onglet2:
    st.subheader("Comment la consommation évolue-t-elle, commune par commune ?")
    totaux = par_communes.pivot_table(index="commune", columns="annee", values="kwh", aggfunc="sum")
    hausse = ((totaux[2025] / totaux[2024] - 1) * 100).sort_values(ascending=False)
    courbes = par_communes.pivot_table(
        index="mois", columns="commune", values="kwh_par_abonne", aggfunc="mean"
    )
    st.line_chart(courbes, x_label="Mois", y_label="kWh par abonné")
    st.markdown(
        f"Entre 2024 et 2025, la plus forte hausse est à **{hausse.index[0]}** "
        f"({hausse.iloc[0]:+.1f} %), la plus faible à **{hausse.index[-1]}** ({hausse.iloc[-1]:+.1f} %)."
    )
 
with onglet3:
    st.subheader("La consommation suit-elle la chaleur, ou les heures de courant ?")
    residentiel = par_communes[par_communes["type"] == "Résidentiel"]
    st.scatter_chart(
        residentiel,
        x="heures_courant",
        y="kwh_par_abonne",
        x_label="Heures de courant par jour",
        y_label="kWh par abonné",
    )
    avec_courant = residentiel["kwh_par_abonne"].corr(residentiel["heures_courant"])
    avec_chaleur = residentiel["kwh_par_abonne"].corr(residentiel["temperature_c"])
    st.markdown(
        f"Dans les quartiers résidentiels, la corrélation entre la consommation par abonné "
        f"et les heures de courant est de **{avec_courant:.2f}**, "
        f"contre **{avec_chaleur:.2f}** avec la température."
    )
 
with onglet4:
    st.subheader("Où les coupures sont-elles les plus longues ?")
    quartiles = (
        par_communes.groupby("commune")["heures_courant"].quantile([0.25, 0.5, 0.75]).unstack()
    )
    quartiles.columns = ["Q1", "Médiane", "Q3"]
    st.bar_chart(quartiles["Médiane"], x_label="Commune", y_label="Heures de courant par jour (médiane)")
    st.dataframe(quartiles.round(1))
    peu_de_courant = filtre[filtre["heures_courant"] < 8]
    phrase = (
        f"La médiane la plus basse est à **{quartiles['Médiane'].idxmin()}** "
        f"({quartiles['Médiane'].min():.1f} heures de courant par jour). "
        f"En {annee}, **{len(peu_de_courant)} relevés** ont moins de 8 heures de courant par jour"
    )
    if len(peu_de_courant) > 0:
        phrase += " : " + ", ".join(sorted(peu_de_courant["quartier"].unique())) + "."
    else:
        phrase += "."
    st.markdown(phrase)
 
with onglet5:
    st.subheader("Quels relevés sortent du lot ?")
    plus_gros = par_communes.nlargest(10, "kwh").copy()
    plus_gros["releve"] = plus_gros["quartier"] + " " + plus_gros["mois"]
    st.bar_chart(plus_gros, x="releve", y="kwh", x_label="Relevé", y_label="kWh")
    st.dataframe(plus_gros[["mois", "quartier", "type", "kwh"]].head(3), hide_index=True)
    premier = plus_gros.iloc[0]
    st.markdown(
        f"La plus grosse consommation est à **{premier['quartier']}** en {premier['mois']} "
        f"({int(premier['kwh'])} kWh), un quartier {premier['type'].lower()}."
    )
 
st.header("Conclusion")
st.markdown(
    "La consommation suit les heures de courant et pas la chaleur. "
    "Dans les quartiers résidentiels la corrélation est de 0.76 avec les heures de courant "
    "et de -0.15 avec la température. "
    "Une corrélation ne prouve pas une cause car d'autres facteurs peuvent jouer."
)
 
with st.expander("Voir les données filtrées"):
    st.dataframe(filtre, hide_index=True)
 
import streamlit as st
import os
import glob
from pathlib import Path
from src.labeling.label_export import export_labels
import src.labeling.export_config as export_config


# Titre
st.title("Label Export Interface")

if "selected_yaml" not in st.session_state:
    st.session_state["selected_yaml"] = None # In case we will be using the latest yaml in the directory scenarios


# Détection du fichier YAML le plus récent
yaml_dir = "scenarios"
yaml_files = glob.glob(os.path.join(yaml_dir, "*.yaml"))
latest_yaml = max(yaml_files, key=os.path.getctime) if yaml_files else ""
latest_yaml = os.path.basename (latest_yaml)  # On ne travaille pas avec des path car pour les cas de browse on n'a pas moyen de les connaitre

# Interface en colonnes
col1, col2 = st.columns(2)

with col2:
    selected_file = st.file_uploader("Browse YAML", type=["yaml"], accept_multiple_files=False)
    if selected_file:
        latest_yaml = selected_file.name
        file_name = selected_file.name
        target_path = os.path.join(yaml_dir, file_name)

        # Vérifie si le fichier est déjà dans le répertoire "scenarios" 
        if not os.path.exists(target_path):
            # Copie le fichier dans le répertoire "scenarios" car on n'a aucun moyen de connaitre son path complet
            with open(target_path, "wb") as out_file:
                out_file.write(selected_file.getbuffer())
              
with col1:
    st.text_input("Selected YAML", value=latest_yaml, key="yaml_display")



if latest_yaml:
    st.session_state["selected_yaml"] = latest_yaml


# Choix de la base de données
dataset_type_set = st.multiselect("Select the simulator for which you want to generate the labels", 
                          ["Flight Simulator", "X-Plane", "ArcGIS", "Bing Maps", "Google Earth"])

# Mapping vers les types
type_mapping = {
    "Google Earth": [export_config.DatasetTypes.EARTH_STUDIO,"GES"],
    # "Real": [export_config.DatasetTypes.REAL, "REAL"],
    "Flight Simulator": [export_config.DatasetTypes.FLSIM, "FLSIM"],
    "X-Plane": [export_config.DatasetTypes.XPLANE, "XPLANE"],
    "ArcGIS": [export_config.DatasetTypes.ARCGIS, "ARCGIS"],
    "Bing Maps": [export_config.DatasetTypes.BING_MAPS, "BING_MAPS"]
}

# Bouton de traitement
#     A partir d'un fichier     scenarios/<nom>.yaml
#     On va créer un répertoire data/<nom>     Ce répertoire peut déja exister et contenir un repertoire footage 
#     On va créer un fichier de label:  data/<nom>/<nom>.csv
#     Si le répertoire data/<nom>/footage existait alors 
#       on créé le répertoire data/<nom>/sanity_check
#       on prend les images du répertoire footage, on leur rajoute les labels et on les stocke dans ce répertoire sanity_check

if st.button("Process labels"):
    if st.session_state["selected_yaml"]:
        output_dir = "data"
        yaml_path = Path(os.path.join(yaml_dir, st.session_state["selected_yaml"]))
        filename_without_ext = yaml_path.stem
        
        export_dir = Path(os.path.join(output_dir, filename_without_ext))
        export_dir.mkdir(parents=True, exist_ok=True)

        
        # try:
        for dataset_type in dataset_type_set:

            label_path = export_dir / f"{filename_without_ext}_{type_mapping[dataset_type][1]}.csv"
            _, messages, atleast_one_good_airport = export_labels(type_mapping[dataset_type][0], yaml_path, out_labels_file=label_path, export_dir=export_dir)


        # #les données ont été produites dans exportedlabels.csv. On renomme ce fichier avec la même base que le fichier yaml et l'extension csv
        # output_filename = yaml_path.with_suffix(".csv")      
        # if os.path.exists(output_filename):
        #     os.remove(output_filename)
        # os.rename(Path(os.path.join(yaml_dir, "exported_labels.csv")), output_filename)
            if atleast_one_good_airport and len(messages) == 0:
                st.success(f"Labels generated in {label_path}.")
            elif atleast_one_good_airport :
                st.warning(f"Labels generated in {label_path}.")
                airportKeyErrors = ", ".join(set(messages))
                st.warning (f"The following airports were not found in the {dataset_type} database: {airportKeyErrors}")
            else:
                st.error(f"No label generated because no valid airports were found in the {dataset_type} database.")
        # except Exception as e:
        #     st.error(f"An error occured : {str(e)}")
    else:
        st.error("No YAML file selected.")


# Navigation
if st.sidebar.button("Home page", key = "LB Home page"):
    st.switch_page("Home_page.py")


if st.sidebar.button("Step 1: Airport filtering", key = "LB Airport filtering"):
    st.switch_page("pages/step1_Airport_filtering.py")


if st.sidebar.button("Step 2: Scenario generation", key = "LB Scenario generation"):
        st.switch_page("pages/step2_Scenario_Generation.py")

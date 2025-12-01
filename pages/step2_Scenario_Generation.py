import streamlit as st 
import json
import os
from pathlib import Path
from src.scenario.write_scenario import write_scenario
from src.scenario.scenario_config import ScenarioConfig


if "current_scenario" not in st.session_state:
    st.session_state.current_scenario = None

if "simulator" not in st.session_state:
    st.session_state.simulator = []
    
# Title of the page
st.title("Scenario generation")
    
# Retrieve the filtered data from the session state
st.title("Scenario generation")

# Retrieve the filtered data from the session state
filtered_data = st.session_state.get("filtered_data", "No data yet")
if len(filtered_data) == 0:
    st.warning("No data available for scenario generation.")
    st.stop()



# File path for the runways database
data_file = 'data/filtered_runways_database_Final.json'

# Load the runways database from the file
with open(data_file, 'r') as f:
    runways_database = json.load(f)

# Create the scenario output directory if needed
output_directory = Path("scenarios/")
os.makedirs(output_directory, exist_ok=True)

def normalize(s):
    return str(int(s)) if s.isdigit() else s  # Normalize numbers, keep alphanumeric as-is

# Function to extract runway data for selected airports
def get_airports_runways(filtered_data):
    airports_runways = {}
    selected_airports = filtered_data['ident'].tolist()

    for airport in selected_airports:
        if airport in runways_database:
            # Get all runways for this airport
            # TODO this is not the right list.
            selected_runways = filtered_data[filtered_data["ident"] == airport]["runway_ident"].tolist()
            all_runways = list(runways_database[airport].keys())
    

            norm_map = {normalize(x): x for x in all_runways}  
            common = {norm_map[x] for x in map(normalize, selected_runways) if x in norm_map}
            
            
            
            airports_runways[airport] = common
    return airports_runways

# Get selected airports and their associated runways
airports_runways = get_airports_runways(filtered_data)

# Initialize scenario configuration
conf = ScenarioConfig(airports_runways, 
                      scenario_dir=output_directory, 
                      runways_database_file=data_file)

# Form for generating the scenario
with st.form("Scenario Generation"):
    
    # Section for configuring the number of images and dimensions
    
    conf.sample_number = st.number_input("Number of images", value=2)  # Number of images to generate for each runway
    col1, col2 = st.columns(2)
    with col1:
        conf.height = st.number_input("Height", value=1080)
    with col2:
        conf.width = st.number_input("Width", value=1920)
    
    conf.watermark_height = st.number_input("Watermark height", value=0)

    with col1:
        conf.fov_x = st.number_input("Field of view (x)", value=60.0)
    with col2:
        conf.fov_y = st.number_input("Field of view (y)", value=60.0)
        
    # Section for setting date and time parameters
    with st.expander("Date and time parameters"):
        col1, col2 = st.columns(2)
        with col1:
            conf.month_max = st.number_input("Max month", value=8, min_value=1, max_value=12)
            conf.day_max = st.number_input("Max day", value=1)
            conf.hour_max = st.number_input("Max hour", value=16)
            conf.minute_max = st.number_input("Max minute", value=0)

        with col2:
            conf.month_min = st.number_input("Min month", value=4)
            conf.day_min = st.number_input("Min day", value=1)
            conf.hour_min = st.number_input("Min hour", value=10)
            conf.minute_min = st.number_input("Min minute", value=0)

    # Section for configuring distance to runway parameters
    with st.expander("Distance to runway parameters"):
        conf.max_distance_m = st.number_input("Max distance (meters)", value=800)  # Default value corresponding to 3 Nautical Miles
        conf.min_distance_m = st.number_input("Min distance (meters)", value=450)  # Min distance to runway

    # Section for setting distribution used for distances from the runway
    #with st.expander("Distribution used for the distances from the runway"):
    #    st.write("Details in generate_dist in src/ges/ges_dataset")  # You can add a reference here
    #    conf.distrib_param = st.number_input("Distribution parameter", value=1.7)
    #    conf.distribution = st.radio("Distribution", ["exp", "normal", "uniform"], index=0, horizontal=True)
    conf.distribution = "uniform"

    # Section for configuring horizontal deviation parameters
    conf.alpha_h_distrib = 'uniform'
    with st.expander("Horizontal deviation parameters"):
        conf.alpha_h_min = st.number_input("Minimum horizontal deviathon (alpha)", value=-3.0)
        conf.alpha_h_max = st.number_input("Maximum horizontal deviathon (alpha)", value=3.0)

    # Section for configuring vertical deviation parameters
    conf.alpha_v_distrib = 'uniform'
    with st.expander("Vertical deviation parameters"):
        conf.alpha_v_min = st.number_input("Minimum vertical deviathon (alpha)", value=-5.2)
        conf.alpha_v_max = st.number_input("Maximum horizontal deviathon (alpha)", value=-1.8)

    # Section for configuring yaw parameters
    conf.yaw_distrib = 'uniform'
    with st.expander("Yaw parameters"):
        conf.yaw_min = st.number_input("Minimum Yaw degree", value=-24.0)
        conf.yaw_max = st.number_input("Maximum Yaw degree", value=24.0)

    # Section for configuring pitch parameters
    conf.pitch_distrib = 'uniform'
    with st.expander("Pitch parameters"):
        conf.pitch_min = st.number_input("Minimum Pitch degree", value=-15.0)
        conf.pitch_max = st.number_input("Maximum Pitch degree", value=5.0)

    # Section for configuring roll parameters
    conf.roll_distrib = 'uniform'
    with st.expander("Roll parameters"):
        conf.roll_min = st.number_input("Minimum Roll degree", value=-30.0)
        conf.roll_max = st.number_input("Maximum Roll degree", value=30.0)
    

    # Button to generate the scenario
    generate_button = st.form_submit_button("Generate scenario")


# If the button is clicked, generate the scenario
if generate_button:
    write_scenario(conf)
    st.success("The scenario was successfully generated")
    # Display the output files
    st.write(f"Scenario exported as .esp   ", conf.outputs.earth_studio_scenario)
    st.write(f"Scenario exported as .yaml  ", conf.outputs.scenario_metadata)
    st.session_state.current_scenario = conf.outputs.scenario_metadata # We only need to yml file for labeling later
    st.session_state.start_labeling = True


# Navigation buttons for the page
page_cols = st.columns(3) 
with page_cols[0]:
    if st.sidebar.button("Home page"):
        st.switch_page("Home_page.py")
with page_cols[1]:
    if st.sidebar.button('Step 1: Airport filtering'):
        st.switch_page("pages/step1_Airport_filtering.py")
with page_cols[2]:
    if st.sidebar.button("Step 3: Labeling"):
        st.switch_page("pages/step3_Labeling.py")
        
        
        

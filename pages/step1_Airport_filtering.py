import streamlit as st
import pandas as pd
import json

# Data exporting function
def get_data():
    # Load airport and runway data from CSV files
    airports = pd.read_csv('data/fused_airports_ourAirports_REDUCED_Again.csv',
                           delimiter=',', na_values=[], keep_default_na=False)
    runways = pd.read_csv('data/fused_runways_FLSim_REDUCED_Again.csv',
                          delimiter=',', na_values=[], keep_default_na=False)
    return airports, runways

# Function that embeds the Bing map
def embed_bing_maps(latitude, longitude, zoom=18):
    # Embed a Bing map with the specified latitude, longitude, and zoom level
    iframe_html = f"""
    <iframe
        width="400"
        height="400"
        style="border:0"
        loading="lazy"
        allowfullscreen
        referrerpolicy="no-referrer-when-downgrade"
        src="https://www.google.com/maps?q={latitude},{longitude}&z={zoom}&t=k&output=embed">
    </iframe>
    """
    st.components.v1.html(iframe_html, height=300)

# Load the data
airports, runways = get_data()

# Merge airport and runway data
filtered_data = pd.merge(airports, runways, left_on="ident", right_on="@ident")
filtered_data['runway_ident'] = filtered_data['@number'].astype(str) + filtered_data['@designator'].astype(str)



with open("data/countries.json") as f:
    country_codes = json.load(f)
    
############# TMP SOLUTION: TO BE REMOVED ONCE FUSED AIRPORTS AND RUNWAYS CSV ALIGN WITH JSON FILES OF GENERATORS ###############################
#with open("data/runways_db_v2_flsim.json") as f:
#     data = json.load(f)
#
#
#json_pairs = {
#    (airport, runway)
#    for airport, runways in data.items()
#    for runway in runways.keys()
#}
#
## Filter your DataFrame to only keep valid pairs
#filtered_data = filtered_data[
#    filtered_data.apply(
#        lambda row: (row["ident"], row["runway_ident"]) in json_pairs,
#        axis=1
#    )
#]

###################################################################################################################################


# Title of the page
st.title("Airport data filtering")

# Filtering options
options = ['continent', 'icao code', 'type', 'runway length', 'runway width', 'number of runways']

# Ensure session state exists
if "filtering_choice" not in st.session_state:
    st.session_state.filtering_choice = []

# Multi-select widget
selected_filters = st.multiselect(
    "Choose filtering criteria",
    options=options,
    default=st.session_state.filtering_choice,  # Use actual session state
    key="filtering_multiselect",
)

# Filtering by Continent and country
if "continent" in selected_filters:
    # Initialize session state variables if not already set
    if "selected_continent" not in st.session_state:
        st.session_state.selected_continent = None
    if "iso" not in st.session_state:
        st.session_state.iso = "All countries"

    continent_options = airports['continent'].drop_duplicates().tolist()
    selected_continent = st.multiselect(
        'Choose a continent',
        options=continent_options,
        key="continent_selectbox",
        default=st.session_state.selected_continent
    )

    # If continent is selected, update the list of available countries
    if selected_continent:
        iso_to_name = {v: k for k, v in country_codes.items()}
        
        # Get list of ISO codes for selected continent
        countries = airports[airports['continent'].isin(selected_continent)]['iso_country'].drop_duplicates().tolist()
        countries.insert(0, "All countries")
        
        # Map ISO codes to full names for display
        countries_display = ["All countries"] + [iso_to_name[iso] for iso in countries if iso in iso_to_name]
        
        # Country selectbox showing full names
        selected_country_display = st.multiselect(
            'Choose the country',
            options=countries_display,
            key="country_selectbox",
            default=[iso_to_name.get(key, "All countries") for key in st.session_state.iso] if "iso" in st.session_state  else "All countries"
        )
        
        # Convert back to ISO for filtering
        if "All countries" in selected_country_display:
            filtered_data = filtered_data[filtered_data['continent'].isin(selected_continent)]
        else:
            selected_country = [country_codes[name] for name in selected_country_display]
            filtered_data = filtered_data[filtered_data['iso_country'].isin(selected_country)]


# Filtering by airport type (Large/ Medium)
if "type" in selected_filters:
    if "type" not in st.session_state:
        st.session_state.type = airports['type'].drop_duplicates().tolist()[0]  # Default value

    # Get unique airport types
    type_options = airports['type'].drop_duplicates().tolist()

    # Selectbox for airport type
    selected_type = st.selectbox(
        "Choose the type of airport",
        options=type_options,
        index=type_options.index(st.session_state.type) if st.session_state.type in type_options else 0,
        key="type_selectbox",
    )

    # Filtering logic
    filtered_data = filtered_data[filtered_data['type'] == selected_type]


if "icao code" in selected_filters:
    if "icao_code" not in st.session_state:
        st.session_state.icao_code = airports['icao_code'].drop_duplicates().tolist()[0]  # Default value

    # Get unique ICAO codes
    icao_code_options = filtered_data['icao_code'].drop_duplicates().tolist()

    # Selectbox for ICAO code
    selected_icao_code = st.multiselect(
        "Choose the ICAO code",
        options=icao_code_options,
        default=[
            code for code in (st.session_state.icao_code or [])
            if code in icao_code_options
        ],
        key="icao_code_selectbox",
    )

    # Filtering logic
    filtered_data = filtered_data[filtered_data['icao_code'].isin(selected_icao_code)]

if "runway length" in selected_filters:
    if "length_min" not in st.session_state:
        st.session_state.length_min = 0
    if "length_max" not in st.session_state:
        st.session_state.length_max = 10000000

    length_cols = st.columns(2)
    with length_cols[0]:
        # Input for minimum runway length
        length_min_input = st.number_input('Enter the minimum length of the runway', min_value=0, max_value=10000000,
                                          value=st.session_state.length_min, key="length_min_input")
    with length_cols[1]:
        # Input for maximum runway length
        length_max_input = st.number_input('Enter the maximum length of the runway', min_value=0, max_value=10000000,
                                          value=st.session_state.length_max, key="length_max_input")

    # Filtering logic
    filtered_data = filtered_data[(filtered_data['@length'] >= st.session_state.length_min) &
                                  (filtered_data['@length'] <= st.session_state.length_max)]


# Filtering by Runway Width
if "runway width" in selected_filters:
    if "width_min" not in st.session_state:
        st.session_state.width_min = 0
    if "width_max" not in st.session_state:
        st.session_state.width_max = 10000000

    width_cols = st.columns(2)
    with width_cols[0]:
        # Input for minimum runway width
        width_min_input = st.number_input('Enter the minimum width of the runway', min_value=0, max_value=10000000,
                                         value=st.session_state.width_min, key="width_min_input")
    with width_cols[1]:
    # Input for maximum runway width
        width_max_input = st.number_input('Enter the maximum width of the runway', min_value=0, max_value=10000000,
                                         value=st.session_state.width_max, key="width_max_input")

    # Filtering logic
    filtered_data = filtered_data[(filtered_data['@width'] >= width_min_input) &
                                  (filtered_data['@width'] <= width_max_input)]


# Filtering by Number of Runways
if "number of runways" in selected_filters:
    if "runway_count" not in st.session_state:
        st.session_state.runway_count = 1
    runway_counts = runways['@ident'].value_counts().reset_index()
    runway_counts.columns = ['ident', 'runway_count']
    filtered_data = filtered_data.merge(runway_counts, on='ident', how='left')

    # Input for runway count
    runway_count_input = st.number_input('Enter the number of runways', min_value=0, max_value=10,
                                        value=st.session_state.runway_count, key="runway_count_input")

    # Filtering logic
    filtered_data = filtered_data[filtered_data['runway_count'] == runway_count_input]


# Store the filtered data back to session state for the scenario generation
st.session_state.filtered_data = filtered_data


#Error message if the filtered_data is empty.
totalFiltered = filtered_data.shape[0]
if totalFiltered == 0:
    st.error("No airport corresponds to the chosen filters")
    st.stop()  # Stop further execution of the page

# Display the filtered data if the button has been clicked
st.text("Here is the list of airports corresponding to your filters") 
st.dataframe(filtered_data[["ident", "type", "name", "continent", "iso_country","runway_ident"]], hide_index=True)


st.write("The total number of corresponding runways is ", totalFiltered)

if "random_selection_count" not in st.session_state:
    st.session_state.random_selection_count = None

default_val = st.session_state.random_selection_count if st.session_state.random_selection_count else (totalFiltered // 2)

# Input widget for random selection count with callback
random_selection_input = st.number_input(
    f"Select the number of randomly chosen runways for the scenario generation stage (max {totalFiltered})",
    min_value=1,
    max_value=totalFiltered,
    value=min(default_val, totalFiltered),
    key="random_selection_input",
)

# Randomly sample the specified number of airports
st.session_state.filtered_data = filtered_data.sample(random_selection_input, random_state=42)
if st.button("Shuffle"):
    st.session_state.filtered_data = filtered_data.sample(random_selection_input, random_state=None)

st.text("Here are the final picked runways: ")
st.dataframe(st.session_state.filtered_data[["ident", "type", "name", "continent", "iso_country","runway_ident"]], hide_index=True)
st.success("The data was filtered, you can now generate scenarios")

if st.sidebar.button("Home page"):
    st.switch_page("Home_page.py")

if st.sidebar.button('Step 2: Scenario generation'):
    #TODO fix session state ici

    st.session_state.filtering_choice = selected_filters

    if "runway width" in selected_filters:
        st.session_state.width_min = width_min_input
        st.session_state.width_max = width_max_input
    
    if "runway length" in selected_filters:
        st.session_state.length_min = length_min_input
        st.session_state.length_max = length_max_input

    if "number of runways" in selected_filters:
        st.session_state.runway_count = runway_count_input
    if "type" in selected_filters:
        st.session_state.type = selected_type
    if "icao code" in selected_filters:
        st.session_state.icao_code = selected_icao_code
    if "continent" in selected_filters:
        st.session_state.iso = selected_country
        st.session_state.selected_continent = selected_continent

    if "random_selection_count" in st.session_state:
        st.session_state.random_selection_count = random_selection_input
        
    st.switch_page("pages/step2_Scenario_Generation.py")
    
if st.sidebar.button("Step 3: Labeling"):
    st.switch_page("pages/step3_Labeling.py")



#Question: for the display part, do we display the airport or each picked runway (A + B + C + D)/4
# Columns for map display
cols = st.columns(3)  # Create 3 columns per row
#if st.session_state['filter_data']:
if st.toggle("Display filtered data", value=False):
    myidents = list(set(st.session_state.filtered_data['ident'].tolist())) #Get unique airport ident for the map
    ## Loop through the identifiers and embed maps in columns
    for i in range(0, len(myidents), 3):  # Step by 3 for three maps per row
        with cols[0]:
            if i < len(myidents):
                ident_data = st.session_state.filtered_data[st.session_state.filtered_data['ident'] == myidents[i]].head(1)
                st.markdown(f"<div style='height: 50px; overflow: hidden;'><strong>{ident_data['name'].squeeze()}</strong></div>", unsafe_allow_html=True)
                embed_bing_maps(ident_data['latitude_deg'].squeeze(), ident_data['longitude_deg'].squeeze())

        with cols[1]:
            if i + 1 < len(myidents):
                ident_data = st.session_state.filtered_data[st.session_state.filtered_data['ident'] == myidents[i + 1]].head(1)
                st.markdown(f"<div style='height: 50px; overflow: hidden;'><strong>{ident_data['name'].squeeze()}</strong></div>", unsafe_allow_html=True)
                embed_bing_maps(ident_data['latitude_deg'].squeeze(), ident_data['longitude_deg'].squeeze())

        with cols[2]:
            if i + 2 < len(myidents):
                ident_data = st.session_state.filtered_data[st.session_state.filtered_data['ident'] == myidents[i + 2]].head(1)
                st.markdown(f"<div style='height: 50px; overflow: hidden;'><strong>{ident_data['name'].squeeze()}</strong></div>", unsafe_allow_html=True)
                embed_bing_maps(ident_data['latitude_deg'].squeeze(), ident_data['longitude_deg'].squeeze())

       

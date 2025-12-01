import streamlit as st 
from PIL import Image


# Function to resize images to a fixed size 
def resize_image(image_path, size=(600, 250)):
    img = Image.open(image_path)
    return img.resize(size)  

# List of image paths
images = ["docs/assets/logo-ONERA.png", "docs/assets/logo-ANITI.jpg", "docs/assets/logo-IRT-StEx_wBackground.png", "docs/assets/logo-DEEL.png", "docs/assets/logo-AIRBUS_.png", "docs/assets/logo-DGA_.png"]

# Create 6 columns
cols = st.columns(6)

# Display resized images
for col, img_path in zip(cols, images):
    resized_img = resize_image(img_path)
    col.image(resized_img)

# Title of the page
st.markdown("<h1 style='text-align: center;'>LARD: Landing Approach Runway Detection</h1>", unsafe_allow_html=True)

# Centered main image
st.image("docs/assets/Lard_grey_transp.png")
st.text(
    "Landing Approach Runway Detection (LARD) is a dataset of aerial front view images of runways designed for aircraft landing phase. "
    "It contains over 17K synthetic images of various runways, enriched with more than 1800 annotated pictures from real landing footages for comparison. "
    "We also provide a synthetic image generator based on Google Earth Studio if you want to enrich your dataset, or fatten your LARD. "
    "Starting from a database of runway positions, our generator produces high quality synthetic pictures of airport runways with their metadata. "
    "Through geometric transformations, these pictures can then be automatically annotated with the position of the runway or any targeted element in the aerial picture."
)

col1, col2 = st.columns(2)
with col1:
    st.image("docs/assets/mosaic_smallest.png", caption="Synthetic and real runways")
with col2:
    st.image("docs/assets/landing_sequence.gif", caption="Synthetic landing sequence")
# Create columns to position the logos at the top-right corner

# Shared initialization 
if "filtered_data" not in st.session_state:
    st.session_state.shared_data = "Default Value"

st.markdown("[Click here to visit our GitHub](https://github.com/deel-ai/LARD/tree/main?tab=readme-ov-file)")

if st.sidebar.button("Step 1: Airport filtering"):
    st.switch_page("pages/step1_Airport_filtering.py")
if st.sidebar.button("Step 2: Scenario generation"):
    st.switch_page("pages/step2_Scenario_Generation.py")
if st.sidebar.button("Step 3: Labeling"):
    st.switch_page("pages/step3_Labeling.py")
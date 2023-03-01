<div align="center">
    <img src="docs/assets/Lard_grey_transp.png" width="50%" alt="LARD dataset" align="center" />
</div>
<br>

Landing Approach Runway Detection (**LARD**) is a [dataset](#lard-dataset) of aerial front view images of runways designed for aircraft landing phase. It contains around 15K synthetic images of various runways, enriched with annotated pictures from real landing footages for comparison.

We also provide a [synthetic image generator](#synthetic-generator) based on Google Earth Studio if you want to enrich your dataset, or *fatten your LARD*. Starting from a database of runway positions, our generator produces high quality synthetic pictures of airport runways with their metadata. Through geometric transformations, these pictures can then be automatically annotated with the position of the runway or any targeted element in the aerial picture.

| | |
:---:|:---:
| ![dataset-mosaic](docs/assets/mosaic_smallest.png "Dataset Mosaic") | ![synthetic-generator](docs/assets/landing_sequence.gif "Synthetic Generator") |
*Synthetic and real runways* | *Synthetic landing sequence*


## 🚀 Quickstart
- 💾 [Download LARD dataset](https://share.deel.ai/s/H4iLKRmLkdBWqSt?path=%2Flard%2F1.0.0)
- 🔥 [Generate scenarios (notebook)](01_scenario_generation.ipynb)
- 🛠️ [Export tool (notebook)](export_tool.ipynb)
- 📜 Read paper (to be published)

# 📚 Table of contents

- [✈️ LARD dataset](#%EF%B8%8F-lard-dataset)
- [⚙️ Synthetic generator](#%EF%B8%8F-synthetic-generator)
  1. [Enrich the runway database](#1-enrich-the-runway-database)
  2. [Generate scenarios](#2-generate-a-scenario)
  3. [Label automatically](#3-automatic-labeling)
- [🛠️ Dataset exploitation](#%EF%B8%8F-dataset-exploitation)
- [🙏 Acknowledgment](#%EF%B8%8F-acknowledgment)
- [🗞️ Citation](#%EF%B8%8F-citation)
- [📝 License](#%EF%B8%8F-license)

# ✈️ LARD Dataset

- 💾 [LARD - **Download**](https://share.deel.ai/s/H4iLKRmLkdBWqSt?path=%2Flard%2F1.0.0)
- Approche (d'avion) generique pour la selection des images
- Renvoi vers le Dataset
- Structure des dossiers (ascii) + description du contenu (split)
- Metadata (Renvoi vers l'exploitation + infos.md)
- Quelques stats? + aeroports du dataset
  - Distrib ratios taille des boites
    - Echelle de distance 3eme dim (couleur)
  - Positions des centres
  - 
  - (video cone)
- Lister les channels contributeurs
  - Videos youtube incrustée sur la minute d'atterrissage
  - Les channels sont disponibles (pour usage recherche & non-commercial uniquement)
  
[![IMAGE ALT TEXT](http://img.youtube.com/vi/17MUtbOfdNQ/0.jpg)](http://www.youtube.com/watch?v=17MUtbOfdNQ?t=500s "Landing at PALERMO, by GreatFlyer")

# ⚙️ Synthetic Generator
The simplified internal working of the generator is as follows:
<div align="center">
    <img src="docs/assets/generator_pipeline.png" width="70%" alt="Generator Pipeline" align="center" />
</div>
<br>

### *In short:*
- 🔥 [Update runways database (notebook)](00_database_generation.ipynb): We use a runway database as input, which you can enrich with new airports and runways.
- 🔥 [Generate scenarios (notebook)](01_scenario_generation.ipynb): We offer the capability to generate highly configurable landing scenarios
- 🔥 [Label automatically (notebook)](02_labeling.ipynb): We provide the tool to automatically annotate the resulting images

## Setup
- You can install python dependancies through `Conda`: 
```
conda env create -f env.yml -p ./env
conda activate ./env
```
- Alternately, you can use the `requirements.txt` to install packages through `pip`
- If neither of these intallation are available for your system, you can find the list of simplified dependencies in `env_simplified.yml`

## 1. Enrich the runway database
- 🔥 [Notebook - **Database generation**](00_database_generation.ipynb)
  - This notebook provides a comprehensive example for adding or update runways and airports in the database.
- The database used for LARD is provided in `data/runways_database.json`
- The database is a simple json file which contains the position of each corner in both `lat/lon/alt` coordinates and the corresponding ECEF (Earth-centered Earth-fixed) coordinates (A,B,C and D are the corners names):
  
``` 
    "AIRPORT": {
      "RUNWAY": {
        "A": {
            "position": {
                "x": -2183272.4689240726,
                "y": 4357496.814901311,
                "z": 4103132.159236785
            },
            "coordinate": {
                "latitude": 40.09288445386455,
                "longitude": 116.61262013286958,
                "altitude": 30.0
            }
        ...
```

_Note that only the WGS84 coordinates (`lat/lon/alt`) are needed, as the ECEF coordinates are automatically computed by the script._

## 2. Generate a scenario
- 🔥 [Notebook - **Scenario generation**](01_scenario_generation.ipynb)
  - This notebook provides a comprehensive example for generating a scenario for a specific runway.
- 🖳 **CLI** - Alternately, you can generate news scenarios in command line :
  1. Configure your scenario as a `.yml` file. An example is provided in `params/example_generation.yml`
  2. Run the script with the `.yml` as an input :
```
python src/scenario/write_scenario.py params/example_generation.yml
```
We used as a reference the following parameters that describe a generic landing trajectory:
|Usual name|parameter name|value ranges|
|-|-|-|
| Distance           | `min_distance_m`, `max_distance_m` (in meters) | [0.08, 3] NM  |
| Vertical deviation / Glide slope angle | `alpha_v_deg`| [2.2°, 3.8]°  | 
| Lateral deviation  | `alpha_h_deg`| [- 4, 4] °    |
| Yaw                | `yaw_deg` | [-10,10] °    |
| Pitch              | `pitch_deg` | [-8,0] °      |
| Roll               | `roll_deg` | [-10,10] °    |

However all these parameters except the distance are not defined as ranges, but rather with gaussian noise around a fixed center and a standard deviation (`std_alpha_v_deg`, `std_alpha_h_deg`, `std_yaw_deg`, `std_pitch_deg`, `std_roll_deg`).
## 3. Automatic labeling
- 🔥 [Notebook - **Labeling**](02_labeling.ipynb)
  - This notebook provides a comprehensive example to automatically label one or multiple Earth Studio generation results and export the corresponding dataset.
- 🖳 **CLI** - Alternately, you can generate news scenarios in command line :
  1. Configure your scenario as a `.yml` file. An example is provided in `params/export_train_dataset.yml`
  2. Run the script with the `.yml` as an input :
```
python src/labeling/generate_dataset.py params/export_train_dataset.yml
```


# 🛠️ Dataset Exploitation
- 🔥 [Notebook - **Export tool**](export_tool.ipynb)
  - This provides a comprehensive example to export the dataset in a specific format such as COCO.
- This tool allows to generate `bounding boxes` around the corners of the runway, in several possible format, to choose between `multiple` label files or a `single` label file, and to `crop` the watermark.
- The dataset before export should respect a specific structure which is detailed in the notebook, and looks like this:
```
    DATASET_PATH/
    | metadata.csv
    | images/
    | | nameimage1.jpeg
    | | nameimage2.jpeg
    | | ...
```

- 🖳 **CLI** - Alternately, you can generate news scenarios in command line :
```
python src/dataset/lard_export.py --train data/multiple_train --test data/test_dataset -o data/converted_coco -b "xywh" -n -lf "multiple" -c -s " "
```
/!\ Not tested yet
## 👀 See Also

More from the DEEL project:
- [Xplique](https://github.com/deel-ai/xplique) a Python library exclusively dedicated to explaining neural networks.
- [deel-lip](https://github.com/deel-ai/deel-lip) a Python library for training k-Lipschitz neural networks on TF.
- [Influenciae](https://github.com/deel-ai/influenciae) Python toolkit dedicated to computing influence values for the discovery of potentially problematic samples in a dataset.
- [deel-torchlip](https://github.com/deel-ai/deel-torchlip) a Python library for training k-Lipschitz neural networks on PyTorch.
- [DEEL White paper](https://arxiv.org/abs/2103.10529) a summary of the DEEL team on the challenges of certifiable AI and the role of data quality, representativity and explainability for this purpose.


## 🙏 Acknowledgment

This project received funding from the French ”Investing for the Future – PIA3” program within the Artificial and Natural Intelligence Toulouse Institute (ANITI).


## 🗞️ Citation

## 📝 License
The package is released under [MIT license](https://choosealicense.com/licenses/mit).
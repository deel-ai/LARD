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
- Démarche generique du générateur 
- Image allégée du pipeline
### *TL; DR*
- 🔥 [Update runways database (notebook)](00_database_generation.ipynb)
- 🔥 [Generate scenarios (notebook)](01_scenario_generation.ipynb)
- 🔥 [Label automatically (notebook)](02_labeling.ipynb)

## Setup
- You can install python dependancies through `Conda`: 

        conda env create -f env.yml -p ./env
- Alternately, you can use the `requirements.txt` to install packages through `pip`
- If neither of these intallation are available for your system, you can find the list of simplified dependencies in `env_simplified.yml`

## 1. Enrich the runway database
- 🔥 [Notebook - **Database generation**](00_database_generation.ipynb)


- The database used for LARD is provided in `data/runways_database.json`
- An example of how to manage the runway database, add or update runways can be found in the notebook [00_database_generation.ipynb](00_database_generation.ipynb)
- Databases are simple json files which contain the position of each corner in both `lat/lon/alt` coordinates and the corresponding ___ coordinates (A,B,C and D the are corners names):
  
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

## 2. Generate a scenario
- 🔥 [Notebook - **Scenario generation**](01_scenario_generation.ipynb)
  - This notebook provides a comprehensive example for generating a scenario for a specific runway.
- 🖳 **CLI** - Alternately, you can generate news scenarios in command line :
  1. Configure your scenario as a `.yml` file. An example is provided in `params/example_generation.yml`
  2. Run the script with the `.yml` as an input :
```
python src\scenario\write_scenario.py params/example_generation.yml
```
- TODO: (GES) infos succintes sur les parametres de generation.

## 3. Automatic labeling
- 🔥 [Notebook - **Labeling**](02_labeling.ipynb)
  - This notebook provides a comprehensive example to automatically label one or multiple Earth Studio generation results and export the corresponding dataset.
- 🖳 **CLI** - Alternately, you can generate news scenarios in command line :
  1. Configure your scenario as a `.yml` file. An example is provided in `params/export_train_dataset.yml`
  2. Run the script with the `.yml` as an input :
```
python src\labeling\generate_dataset.py params/export_train_dataset.yml
```

# 🛠️ Dataset Exploitation
- 🔥 [Notebook - **Export tool**](01_scenario_generation.ipynb)

Each part of the LARD dataset is structured as followed :
```
train_dataset/
| metadata.csv: file with image path, labels (corners positions) and all the metadata of each image in images/
| infos.md: description of the dataset and the content of each column of metadata.csv
| images/: image directory
| | name_of_image_1.png  # each uncropped image of the dataset
| | ....
```

The structure is identic for the test set.

To facilitate its export and usage for detection tasks, we provide an export python script (also available in notebook), 
able to convert LARD to most of the commons format for detection format.
- Please refer to ./notebooks/lard_export.ipynb  for the notebook version and associated documentation.

### How to export LARD to Coco format :

MAXIME : PAS ENCORE TESTE SUR LA V1.3, EN COURS

    python src/dataset/lard_export.py --train data/multiple_train --test data/test_dataset -o data/converted_coco -b "xywh" -n -lf "multiple" -c -s " "

#### How should your dataset be structured for it to work ?

The expected format is one created with the Lard labeling script or notebook :

- Case 1 : single dataset :  with DATASET_PATH either of the path provided to LardDataset(train_path=, test_path=)

    DATASET_PATH :
        ---> DATASET_PATH/metadata.csv
        ---> DATASET_PATH/images/
        ---> DATASET_PATH/images/nameimage1.jpeg
        ---> DATASET_PATH/images/nameimage2.jpeg
    ...

And same structure for TEST_PATH. Please note it is the default structure the labelling script exports the labels.

- Case 2 : multiple datasets :  DATASET_PATH can be either of the path provided to LardDataset(train_path=, test_path=)

    DATASET_PATH :
        ---> DATASET_PATH/dataset_1/metadata.csv
        ---> DATASET_PATH/dataset_1/images/
        ---> DATASET_PATH/dataset_1/images/name_dataset1image1.jpeg
        ---> DATASET_PATH/dataset_1/images/name_dataset1image2.jpeg
        
        ---> DATASET_PATH/dataset_2/others_metadata.csv
        ---> DATASET_PATH/dataset_2/images/
        ---> DATASET_PATH/dataset_2/images/name_dataset2_image1.jpeg
        ---> DATASET_PATH/dataset_2/images/name_dataset2_image2.jpeg
        ...

- Other informations : 
    - train_path and test_path can of the same type, or mixted : train_path can be of type 1 and test_path of type 2, or the opposite. 
    - There can be more than two dataset in DATASET_PATH in case 2. 
    - CSV and images names do not matter, only the architecture : that there is a single csv file in each directory specified above. Each csv is expected to be generated with the LARD labeling script or notebook.

#### What are the supported options for export ?

A more comprehensive description of the available parameters and exports options :

- '--train' : optional, train directory. At least one of train or test should be provided.
- '--test' : optional, test directory
- '-o', '--output_dir' : directory where the converted dataset will be saved. Expects a pathlib Path or a string.
-   '-b', '--bbox' : string format for label bbox. Options are :
    - "tlbr" (x,y of top left then x,y of bottom rights corners of the bbox)
    - "tlwh" (x, y of top left, bbox width and height)
    - "xywh" (x, y of the center of the bbox, bbox width and height)
    - "corners" (x,y of each corner)
- '-n', '--normalize': boolean, option to normalize the bbox position by the image size. 
    - If true, bbox labels are expressed in fraction of the image width and height
    - If False, positions are left in pixels. Default choice.
- '-lf', '--label_format' : string, options are :
    - "single" : all the labels are in a single csv, with a column with image path
    - "multiple" : one label file per image, saved in output_dir/labels.
- '-s', '--sep' : label file(s) separator, default is ";".
- '--header' : boolean. If True, an header column with column names is added to each label file.
- '-c', '--crop' : boolean 
    - If True, crop during export all images with watermarks and updates bboxes position to the cropped image. 
    - If False, the image will be copied without modifications.
- '-e', '--ext' : Extension format for labels files (without the "."). Default is "txt".


## 🙏 Acknowledgment

## 🗞️ Citation

## 📝 License
The package is released under [MIT license](https://choosealicense.com/licenses/mit).
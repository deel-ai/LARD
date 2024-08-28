import os
import argparse
import pathlib
import yaml
import json
import shutil
import glob
import numpy as np
import datetime
from pathlib import Path
from src.labeling.labels import Labels
from src.ges.ges_dataset import GESDataset
from src.ges.ges_camera import GESCamera
from src.labeling.labels_utils import is_runway_image_valid
from src.labeling.export_config import CORNERS_NAMES


def convert_label(yaml_scenario, image_path, image_shape, pose, frame, runway, runways_database):
    airport = pose['airport']
    image_time = datetime.datetime(**pose['time'])
    
    # Access the 'image' information from the top level of the YAML structure
    image_info = yaml_scenario['image']
    print("image_info: ", image_info)
    watermark = image_info.get("watermark_height", 300)  # Default to 300 if not found
    print("watermark: ", watermark)
    label = {
        'image': image_path,
        'airport': airport,
        'runway': runway,
        'height': image_shape[0],
        'width': image_shape[1],
        'watermark_height': watermark,
        'time': image_time,
        'roll': pose['pose'][5],
        'pitch': pose['pose'][4],
        'yaw': pose['pose'][3]
    }
    camera = GESCamera(image_shape, frame)
    # Add a complete debug here to be sure which runway we consider, 
    print(f"Computing camera for airport {airport}, runway {runway}")
    # Add a debug for for which current roll, pitch, yaw, etc
    print(f"Pose: {pose}")
        
    camera.compute(runways_database=runways_database, runway=runway, airport=airport)
    camera.compute_intrinsics_matrix()
    camera.compute_extrinsics_matrix()
    corners = np.array(camera.compute_runway_corners_projection(runways_database, airport, runway))

    # Add computed values to the label
    label['slant_distance'] = float(np.round(camera.slant_distance / 1852, 2))
    label['along_track_distance'] = float(np.round(camera.along_track_distance / 1852, 2))
    label['height_above_runway'] = float(np.round(camera.height_above_runway * 3.28084, 2))
    label['lateral_path_angle'] = float(np.round(camera.lateral_path_angle, 2))
    label['vertical_path_angle'] = float(np.round(camera.vertical_path_angle, 2))

    for i, corner in enumerate(corners):
        label[f"x_{CORNERS_NAMES[i]}"] = corner[0]
        label[f"y_{CORNERS_NAMES[i]}"] = corner[1]

    return label


# OBSOLETE: Previous version, single target runway labelling
# def convert_label(image_shape, image_path, c, frame, runways_database, img_nb):
#     airport = c['poses'][img_nb]['airport']
#     runway = c['poses'][img_nb]['runway']
#     image_time = datetime.datetime(**c['poses'][img_nb]['time'])
#     try:
#         watermark = c["watermark"]["height"]
#     except KeyError:
#         watermark = c["image"]["watermark_height"]
#     label = {'image': image_path,
#              'airport': airport,
#              'runway': runway,
#              'height': image_shape[0],
#              'width': image_shape[1],
#              'watermark_height': watermark,
#              'time': image_time,
#              'roll': c['poses'][img_nb]['pose'][5],
#              'pitch': c['poses'][img_nb]['pose'][4],
#              'yaw': c['poses'][img_nb]['pose'][3]
#              }
#     camera = GESCamera(image_shape, frame)
#     camera.compute(runways_database=runways_database, runway=runway, airport=airport)
#     # compute intrinsics and extrinsics matrix
#     camera.compute_intrinsics_matrix()
#     camera.compute_extrinsics_matrix()
#     corners = np.array(camera.compute_runway_corners_projection(
#         runways_database,
#         airport,
#         runway
#     ))
#     label['slant_distance'] = float(np.round(camera.slant_distance / 1852, 2))
#     label['along_track_distance'] = float(np.round(camera.along_track_distance / 1852, 2))
#     label['height_above_runway'] = float(np.round(camera.height_above_runway*3.28084, 2))
#     label['lateral_path_angle'] = float(np.round(camera.lateral_path_angle, 2))
#     label['vertical_path_angle'] = float(np.round(camera.vertical_path_angle, 2))

#     for i, corner in enumerate(corners):
#         label[f"x_{CORNERS_NAMES[i]}"] = corner[0]
#         label[f"y_{CORNERS_NAMES[i]}"] = corner[1]
#     return label



def export_labels(yaml_scenario_path, google_export_dir=None, out_labels_file=None, out_images_dir=None):
    # Parse configuration file
    # All the dependencies
    print(f"Label export of {yaml_scenario_path} started")
    if google_export_dir is None:
        google_export_dir = yaml_scenario_path.parent
    json_path = google_export_dir / (google_export_dir.name + ".json")
    if out_labels_file is None:
        out_labels_file = google_export_dir / 'exported_labels.csv'
    if out_images_dir is None:
        out_images_dir = google_export_dir / "exported_images"

    with open(yaml_scenario_path, 'r') as f:
        yaml_scenario: dict = yaml.safe_load(f)
        if 'poses' not in yaml_scenario.keys():
            raise RuntimeError('The yaml scenario file is not complete, missing poses.')
        elif 'image' not in yaml_scenario.keys():
            raise RuntimeError('The yaml scenario file is not complete, missing images.')
        elif 'trajectory' not in yaml_scenario.keys():
            raise RuntimeError('The yaml scenario file is not complete, missing trajectory.')
        else:
            print(f" Yaml scenario {yaml_scenario_path} correctly loaded")

    # Load the appropriate runways database
    database_path = Path(yaml_scenario.get("runways_database", "data/runways_database.json"))  
    with open(database_path, 'r') as f:
        runways_database = json.load(f)

    ges_dataset = GESDataset(loc_path=json_path)
    ges_dataset.load_data()

    # Compute runway corners
    image_shape = ges_dataset.data['height'], ges_dataset.data['width']
    img_digits = len(str(len(yaml_scenario['poses']) - 1))
    labels = Labels()
    os.makedirs(out_images_dir, exist_ok=True)
    j = 0
    # TODO: clear this code once the .json dependency is removed
    if len(ges_dataset.data['cameraFrames']) != len(glob.glob(str(google_export_dir /  "footage/*.jpeg"))):
        raise FileNotFoundError("Number of images in footage do not match poses in .json")
    
    # enumerate over each frame and generate the associated list of labels
    for i, frame in enumerate(ges_dataset.data['cameraFrames']):
        image_path = None
        valid_runways = False # Flag to check if the runway is labeled at least once
        while image_path is None or not os.path.exists(image_path):
            image_path: Path = google_export_dir / "footage" / f"{google_export_dir.stem}_{str(j).zfill(img_digits)}.jpeg"
            j += 1
        if not os.path.exists(image_path):
            print(f"Problem during export: missing image : {image_path}")
            
        pose = yaml_scenario['poses'][i]
        airport = pose['airport']
        print(f"\nExporting image {image_path} for airport {airport}, \n  - frame: {frame}")            
        for runway in yaml_scenario['airports_runways'][airport]:
            output_image_path = out_images_dir / image_path.name
            label = convert_label(yaml_scenario, output_image_path, image_shape, pose, frame, runway, runways_database)
            print(f"  - runway{runway}_label: {label}")
            
            if is_runway_image_valid(image_shape, label):
                valid_runways = True
                labels.add_label(label)
        
        
        # output_image_path = out_images_dir / image_path.name
        if valid_runways:
            shutil.copy(image_path, output_image_path)

    # Generate label file
    labels.export(out_labels_file)
    return labels

# OBSOLETE - Previous version, single target runway labelling
# def export_labels(yaml_config, google_export_dir=None, out_labels_file=None, out_images_dir=None):
#     # Parse configuration file
#     # All the dependencies
#     print(f"Label export of {yaml_config} started")
#     if google_export_dir is None:
#         google_export_dir = yaml_config.parent
#     json_path = google_export_dir / (google_export_dir.name + ".json")
#     if out_labels_file is None:
#         out_labels_file = google_export_dir / 'exported_labels.csv'
#     if out_images_dir is None:
#         out_images_dir = google_export_dir / "exported_images"

#     with open(yaml_config, 'r') as f:
#         c: dict = yaml.safe_load(f)
#         if 'poses' not in c.keys():
#             raise RuntimeError('The configuration file is not complete, missing poses.')

#     # Initialize
#     database_path = Path(c.get("runways_database", "data/runways_database.json"))  # default value to support older yaml
#     with open(database_path, 'r') as f:
#         runways_database = json.load(f)

#     d = GESDataset(
#         loc_path=json_path
#     )
#     d.load_data()

#     # Compute runway corners
#     image_shape = d.data['height'], d.data['width']
#     digits = len(str(len(c['poses']) - 1))
#     labels = Labels()
#     os.makedirs(out_images_dir, exist_ok=True)
#     j = 0
#     if len(d.data['cameraFrames']) != len(glob.glob(str(google_export_dir /  "footage/*.jpeg"))):
#         raise FileNotFoundError("Number of images in footage do not match poses in .json")
    
#     for i, frame_position in enumerate(d.data['cameraFrames']):
#         image_path = None
#         while image_path is None or not os.path.exists(image_path):
#             image_path: Path = google_export_dir / "footage" / f"{google_export_dir.stem}_{str(j).zfill(digits)}.jpeg"
#             j += 1
#         # if not os.path.exists(image_path):
#         #     print(f"Skipping missing image : {image_path}")
#         #     continue
#         output_image_path = out_images_dir / image_path.name
#         label = convert_label(image_shape, output_image_path, c, frame_position, runways_database, i)
#         if not is_runway_image_valid(image_shape, label):
#             print(f"Skipping invalid image : {image_path}")
#             continue
#         labels.add_label(label)
#         shutil.copy(image_path, output_image_path)

#     # Generate label file
#     labels.export(out_labels_file)
#     return labels


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(
        prog=pathlib.Path(os.path.basename(__file__)).stem,
        description="""Generate labeling"""
    )
    parser.add_argument(
        'config_filepath',
        type=pathlib.Path,
        help='YAML configuration filepath'
    )
    parser.add_argument(
        '-v', '--verbose',
        help='Verbose mode',
        action='store_true'
    )
    args = parser.parse_args()

    export_labels(args.config_filepath)

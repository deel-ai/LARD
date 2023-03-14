import os
import shutil
import json
from glob import glob
from argparse import ArgumentParser
from pathlib import Path


def sanitize_dataset(dataset_path: Path):
    export_dict = {}
    for json_file in glob(f"{dataset_path}/*.json"):
        json_path = Path(json_file)
        with open(json_file, 'r') as f:
            json_label = json.load(f)
        image_path = Path(json_label['imagePath'])
        airport = json_label.get("airport", "")
        runway = json_label.get("runway", "")
        if len(airport) == 0 or len(runway) == 0:  # we do not rename the ones without runway and airport
            continue
        key = f"{airport}_{runway}"
        if not key in export_dict.keys():
            export_dict[key] = {"old_json": [], "old_images": [], "order": []}
        export_dict[key]["old_json"].append(json_path)
        export_dict[key]["old_images"].append(image_path)
        export_dict[key]["order"].append(json_label["timeToLanding"])
    for key, val in export_dict.items():
        nb_images = len(val["old_images"])
        for idx, vals in enumerate(sorted(zip(val["order"], val["old_images"], val["old_json"]), reverse=True)):
            _, old_image, old_json = vals
            new_basename = f"{key}_{nb_images}_{idx}"
            new_image = new_basename + old_image.suffix
            new_json = new_basename + old_json.suffix
            shutil.move(dataset_path/old_image, dataset_path/new_image)
            with open(old_json, 'r') as f:
                json_label = json.load(f)
            json_label["imagePath"] = new_image
            with open(old_json, 'w') as f:
                json.dump(json_label, f)
            shutil.move(old_json, dataset_path/new_json)
    #shutil.copy(image_path, label['image'])


if __name__ == "__main__":
    # Parse arguments
    parser = ArgumentParser(
        prog=Path(os.path.basename(__file__)).stem,
        description="""Sanitize the names of every image file of the real dataset"""
    )
    parser.add_argument(
        'dataset_path',
        type=Path,
        help='Path to a dataset export configuration. Example : params/export_test_dataset.yaml'
    )
    args = parser.parse_args()

    sanitize_dataset(args.dataset_path)

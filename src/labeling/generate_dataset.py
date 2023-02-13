import argparse
import os
import glob
import shutil
from pathlib import Path
from typing import Union
from src.labeling.earth_studio_export import export_labels
from src.labeling.json_export import from_json
from src.labeling.labels import Labels
from src.labeling.export_config import ExportConfig, DatasetTypes


IMG_TYPES = ".png", ".jpg", ".jpeg"


def export_real_directory(folder_path: Union[str, Path], test_images_dir: Union[str, Path]) -> dict:
    """
    Parse and return the metadata for a real dataset and associated files.
    """
    labels = Labels()
    img_list = []
    for ext in IMG_TYPES:
        img_list += glob.glob(f"{folder_path}/*{ext}")
    for image in img_list:
        image_path = Path(image)
        json_path = image_path.with_suffix(".json")
        label = from_json(json_path)
        label['image'] = test_images_dir / image_path.name
        labels.add_label(label)
        shutil.copy(image_path, label['image'])
    return labels


def export_synthesized_directory(folder_path: Union[str, Path], test_images_dir: Union[str, Path]) -> dict:
    """
    Parse and return the metadata for a synthetized google earth dataset.
    """
    labels = Labels()
    folder_path = Path(folder_path)
    for scenario in os.listdir(folder_path):
        acquisition_path = folder_path / scenario
        if os.path.isdir(acquisition_path):
            try:
                folder_labels = export_labels(acquisition_path / f"{scenario}.yaml", out_images_dir=test_images_dir)
            except KeyError as e:
                print(f"Missing data for scenario {scenario} ({e} was not found): scenario skipped ")
                continue
            except FileNotFoundError as e:
                print(f"File {e.filename} could not be found for scenario {scenario} : scenario skipped ")
                continue
            folder_labels.add_metadata("scenario", scenario)
            labels += folder_labels
    return labels


def export_datasets(export_config: ExportConfig) -> None:
    """
    Main dataset labelisation and export method. Take as input an ExportConfig with all parameters, inputs and outputs
    targets for export, and generate a single, merged dataset with all the Lard metadatas.

    :param export_config: export configuration
    :type export_config: ExportConfig
    :return: None
    """
    out_test_dir = Path(export_config.output_directory) / export_config.dataset_name
    test_images_dir = out_test_dir / "images"
    os.makedirs(out_test_dir, exist_ok=True)
    os.makedirs(test_images_dir, exist_ok=True)

    input_datasets = export_config.included_datasets
    labels = Labels()
    for dataset_name, dataset_infos in input_datasets.items():
        dataset_type = dataset_infos["type"]
        dataset_path = dataset_infos["path"]
        if dataset_type == DatasetTypes.EARTH_STUDIO:
            dataset_labels = export_synthesized_directory(dataset_path, test_images_dir)
        elif dataset_type == DatasetTypes.REAL:
            dataset_labels = export_real_directory(dataset_path, test_images_dir)
        else:
            raise NotImplementedError(f"Dataset type {dataset_type} is not supported yet")
        dataset_labels.add_metadata("type", dataset_type.value)
        dataset_labels.add_metadata("original_dataset", dataset_name)
        labels += dataset_labels
    labels.as_relative_paths(out_test_dir)
    labels.reorder_corners() # ensures corners names matches their order in the image
    labels.export(out_test_dir / (export_config.dataset_name+".csv"))
    info_file = Path("data/infos.md")
    shutil.copy(info_file, out_test_dir/info_file.name)


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(
        prog=Path(os.path.basename(__file__)).stem,
        description="""Generate labeling"""
    )
    parser.add_argument(
        'config_file',
        type=Path,
        help='Path to a dataset export configuration. Example : params/export_test_dataset.yaml'
    )
    parser.add_argument(
        '-v', '--verbose',
        help='Verbose mode',
        action='store_true'
    )
    args = parser.parse_args()
    config = ExportConfig(args.config_file)
    export_datasets(config)

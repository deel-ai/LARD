import argparse
import os
import glob
import shutil
from pathlib import Path
from typing import Union
from src.labeling.label_export import export_labels
from src.labeling.labels import Labels
from src.labeling.export_config import ExportConfig


IMG_TYPES = ".png", ".jpg", ".jpeg"


def export_directory(dataset_type, folder_path: Union[str, Path], test_images_dir: Union[str, Path]) -> dict:
    """
    Parse and returns the metadata for a flight simulator dataset. 
    """
    labels = Labels()
    folder_path = Path(folder_path)
    for scenario in os.listdir(folder_path):
        acquisition_path = folder_path / scenario
        yaml_file_path = acquisition_path / f"{scenario}.yaml"
        
        if os.path.isdir(acquisition_path):
            if not yaml_file_path.exists():
                parent_yaml_file_path = folder_path / f"{scenario}.yaml"
                if parent_yaml_file_path.exists():
                    print(f"YAML file for scenario {scenario} found in the parent folder. Copying it to the correct location.")
                    shutil.copy(parent_yaml_file_path, yaml_file_path)
                else:
                    parent_parent_yaml_file_path = folder_path / f"../{scenario}.yaml"
                    if parent_parent_yaml_file_path.exists():
                        print(f"YAML file for scenario {scenario} found in the parent-parent folder. Copying it to the correct location.")
                        shutil.copy(parent_parent_yaml_file_path, yaml_file_path)
                    else :
                        print(f"YAML file for scenario {scenario} not found in the parent or parent-parent folder. Scenario skipped.")
                        continue
            try:
                folder_labels = export_labels(dataset_type, acquisition_path / f"{scenario}.yaml", out_images_dir=test_images_dir)
            except KeyError as e:
                print(f"Missing data for scenario {scenario} ({e} was not found): scenario skipped ")
                continue
            except FileNotFoundError as e:
                print(e)
                print(f"File {e.filename} could not be found for scenario {scenario} : scenario skipped ")
                continue
            if (folder_labels is None):
                print(f"[EXPORT FAILURE] Scenario {scenario} label export has failed; skipping scenario.")
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

        dataset_labels = export_directory(dataset_type, dataset_path, test_images_dir)

        dataset_labels.add_metadata("type", dataset_type.value)
        dataset_labels.add_metadata("original_dataset", dataset_name)
        labels += dataset_labels


    labels.as_relative_paths(out_test_dir)
    # labels.reorder_corners() # ensures corners names matches their order in the image
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

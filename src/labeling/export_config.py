from enum import Enum
from pathlib import Path
from typing import Optional

from yaml import safe_load


# Ensure user do not misspell the types, or add not supported yet types
class DatasetTypes(Enum):
    EARTH_STUDIO = "earth_studio"
    REAL = "real"


# Corner names in export
CORNERS_NAMES = ["A", "B", "C", "D"]


class ExportConfig:
    """
    Class to load and store configuration for Lard dataset creation, merge and export.
    """
    def __init__(self, yaml_file: str = None, strict: bool = True):
        """
        :param yaml_file: path to yml file. If None, an empty config is generated.
        :type yaml_file: str
        :param strict: whether to force all runway corners to be part of the image.
        :type strict: bool
        """
        if yaml_file is None:
            self.output_directory = None
            self.dataset_name = None
            self.strict = strict
            self.included_datasets = dict()
        else:
            with open(yaml_file, 'r') as f:
                self.__dict__.update(safe_load(f))
            for value in self.included_datasets.values():
                value["type"] = DatasetTypes(value["type"])

    def add_dataset_for_export(self, dataset_name: str, dataset_folder: str, dataset_type: str, records_dirpath: Optional[Path] = None) -> None:
        """
        Add an acquisition dataset to the ones being exported and merged.
        """
        dataset_type = DatasetTypes(dataset_type)
        params = {"path": dataset_folder, "type": dataset_type}
        if records_dirpath is not None:
            params["records_dirpath"] = Path(records_dirpath)
        self.included_datasets[dataset_name] = params

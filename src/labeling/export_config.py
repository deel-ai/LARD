from yaml import safe_load
from enum import Enum

runways_db_gearth = "data/runways_db_V2_GEarth.json"
runways_db_arcgis = "data/runways_db_V2_ArcGIS.json"
runways_db_bing = "data/runways_db_V2_Bing.json"
runways_db_real = "data/runways_db_V2_real.json"
runways_db_flsim = "data/runways_db_V2_FLSim.json"
runways_db_xplane = "data/runways_db_V2_XPlane.json"

# Ensure user do not misspell the types, or add not supported yet types
class DatasetTypes(Enum):
    EARTH_STUDIO = "earth_studio"
    REAL = "real"
    FLSIM = "flight_simulator"
    XPLANE = "xplane"
    ARCGIS = "arcgis"
    BING_MAPS = "bingmaps"
# class DatasetTypes(Enum):
#     EARTH_STUDIO=0
#     REAL=1
#     FLSIM=2
#     XPLANE=3

def database_name(dataset_type):
    if dataset_type == DatasetTypes.EARTH_STUDIO:
        return runways_db_gearth
    elif dataset_type == DatasetTypes.REAL:
        return runways_db_real
    elif dataset_type == DatasetTypes.FLSIM:
        return runways_db_flsim
    elif dataset_type == DatasetTypes.XPLANE:
        return runways_db_xplane
    elif dataset_type == DatasetTypes.ARCGIS:
        return runways_db_arcgis
    elif dataset_type == DatasetTypes.BING_MAPS:
        return runways_db_bing
    else:
        raise RuntimeError('Unknown dataset_type')


# Corner names in export
# CORNERS_NAMES = ["A", "B", "C", "D"]
# TODO: Change names to TL, BL, TR, BR
CORNERS_NAMES = ["TL", "TR", "BR", "BL"]
NEW_CORNERS_NAMES = ["TR", "TL", "BL", "BR"]     # A B C D
# 


class ExportConfig:
    """
    Class to load and store configuration for Lard dataset creation, merge and export.
    """
    def __init__(self, yaml_file: str = None):
        """
        :param yaml_file: path to yml file. If None, an empty config is generated.
        :type yaml_file: str
        """
        if yaml_file is None:
            self.output_directory = None
            self.dataset_name = None
            self.included_datasets = dict()
        else:
            with open(yaml_file, 'r') as f:
                self.__dict__.update(safe_load(f))
            for value in self.included_datasets.values():
                value["type"] = DatasetTypes(value["type"])

    def add_dataset_for_export(self, dataset_name: str, dataset_folder: str, dataset_type: str) -> None:
        """
        Add an acquisition dataset to the ones being exported and merged.
        """
        dataset_type = DatasetTypes(dataset_type)
        self.included_datasets[dataset_name] = {"path": dataset_folder, "type": dataset_type}

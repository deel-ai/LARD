import json
from typing import Union
from pathlib import Path
from src.labeling.export_config import CORNERS_NAMES


def from_json(path: Union[str, Path]) -> dict:
    """
    Return label dictionary from a json file. Only the information required is returned, and not the entirety of the
    content of the json file.

    :param path: path to the json file
    :type path: str
    :return: labels loaded in a python dict
    :rtype: dict
    """
    label = {}
    with open(path, 'r') as f:
        json_label = json.load(f)

    label["image"] = json_label['imagePath']
    label["height"] = json_label['imageHeight']
    label["width"] = json_label["imageWidth"]
    try:
        label["airport"] = json_label["airport"]
    except KeyError:
        pass
    try:
        label["runway"] = json_label["runway"]
    except KeyError:
        pass
    try:
        label["time_to_landing"] = json_label["timeToLanding"]
    except KeyError:
        print(f"No time to landing in json {path}")
    try:
        label["weather"] = json_label["weather"]
    except KeyError:
        pass  # no weather field is expected to happen for a lot of images
    try:
        label["night"] = json_label["night"]
    except KeyError:
        pass  # no night field is expected to happen for a lot of images

    for i, corner in enumerate(json_label["shapes"][0]["points"]):
        label[f"x_{CORNERS_NAMES[i]}"] = int(corner[0])
        label[f"y_{CORNERS_NAMES[i]}"] = int(corner[1])
    return label

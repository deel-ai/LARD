import numpy as np
import pandas as pd
from shapely.geometry import Polygon
from src.labeling.export_config import CORNERS_NAMES


def compute_bbox(corners: np.array) -> np.array:
    """
    create the smallest box countaining all the corners of a corner set
    return [x_min, y_min, x_max, y_max]

    """
    x_min, x_max = np.min(corners[:, 0]), np.max(corners[:, 0])
    y_min, y_max = np.min(corners[:, 1]), np.max(corners[:, 1])
    return np.array([x_min, y_min, x_max, y_max])


def crop_bbox(bbox: np.array, width: int, height: int) -> np.array:
    """ 
    crop a box by the dimensions of the image (width, height)
    
    """
    x_min, y_min, x_max, y_max = bbox
    x_min = max(x_min, 0)
    y_min = max(y_min, 0)
    x_max = min(x_max, width)
    y_max = min(y_max, height)
    return np.array([x_min, y_min, x_max, y_max])


def is_runway_image_valid(image_shape: tuple[int], label: pd.DataFrame, debug: bool = False) -> bool:
    """
    Check if a dataset image is valid :
    - it contains exactly one runway visible in it
    - the runway in its entirety is visible in the image
    """
    corners = [(label[f"x_{name}"], label[f"y_{name}"]) for name in CORNERS_NAMES]
    runway_poly = Polygon(corners)
    image_poly = Polygon([(0, 0), (0, image_shape[0]), image_shape[:2], (image_shape[1], 0)])

    if not runway_poly.intersects(image_poly):
        if debug:
            print("Invalid image : runway fully out of the image")
        # runway and image do not intersects and are not contained in one another, we continue to next runway
        return False
    if runway_poly.contains(image_poly):
        if debug:
            print("Invalid image : runway fully contains the image")
        return False
    if not image_poly.contains(runway_poly):
        if debug:
            print("Invalid image : at least one runway corner is outside the image ")
        return False
    return True

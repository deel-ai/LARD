import pandas as pd
import numpy as np
from pathlib import PurePath, Path
from src.labeling.export_config import CORNERS_NAMES
from typing import Union, List


class Labels:
    """
    The Label class :

    - defines the different fields of the labels and metadata of the LARD dataset
    - provided utility method to add, export or manipulate them.

    The exact metadata is stored in an internal pandas Dataframe, which can be directly accessed for custom usage :

    .. code-block:: python

        lbl = Labels(csv_metadata_path)
        metadata_in_pandas_dataframe = lbl.df

    :ivar sep: separator symbol in the export file.
    :ivar default_cols: default metadata columns. Specify all the possible metadata field and
        their order in the exported field.

    :param path: Path to a Lard metadata csv.
    :type path: str or Path
    """
    sep = ";"
    default_cols = ["image",
                    "height",
                    "width",
                    "type",
                    "original_dataset",
                    "scenario",
                    "airport",
                    "runway",
                    "time_to_landing",
                    "weather",
                    "night",
                    "time",
                    "slant_distance",
                    "along_track_distance",
                    "height_above_runway",
                    "lateral_path_angle",
                    "vertical_path_angle",
                    "yaw",  # -180 to +180, 0=south
                    "pitch",  # (degree, clockwise, 90 is horizontal)
                    "roll",  # (counterclockwise, degree. 0 is horizontal).
                    "watermark_height"
                    ] + [f"{c}_{name}" for name in CORNERS_NAMES for c in ["x", "y"]]  # names of labels columns (
    # corners positions in the image)

    def __init__(self, path: Union[str, Path] = None) -> None:
        """
        Constructor
        """
        if path is None:
            self.path = None
            self.df = pd.DataFrame(columns=self.default_cols)
        else:
            self.path = PurePath(path)
            self.df = pd.read_csv(path, sep=self.sep)

    def export(self, out_file: str) -> None:
        """
        Export metadata in a csv file.

        :param out_file: path of the output csv file
        :type out_file: str
        :return: None
        """
        self.df.to_csv(out_file, sep=self.sep, header=True, index=False)

    def add_label(self, label_infos: dict):
        """
        Add additional labels and metadata, provided as a python dictionary, to the ones stored.

        :param label_infos: dict with metadata and labels information. Keys should be columns names as described in
            ``Labels.default_cols``
        :type label_infos: dict
        :return: None
        """
        try:
            self.df = pd.concat([self.df, pd.DataFrame.from_records([label_infos])])
        except TypeError:
            print("Not a valid label :", label_infos)

    def get_label(self, img_idx: Union[str, int]):
        """
        Return all information stored for a specific image from its image path or dataframe index

        :param img_idx: image path or index
        :type img_idx: str or int
        :return: dict with all the image metadata
        """
        try:
            img_idx = int(img_idx)
            return self.df.iloc[img_idx].to_dict()
        except ValueError:  # try if an image path was provided
            return self.df[self.df["image"] == img_idx].iloc[0].to_dict()

    def __iadd__(self, other: "Labels") -> "Labels":
        """
        Add the content of another Lard Labels object to the current ones.

        :param other: other Labels
        :type other: Labels
        :return: None
        """
        self.df = pd.concat([self.df, other.df], ignore_index=True)
        return self

    def get_corners_list(self, img: Union[str, int]) -> list:
        """
        Return the list of corner positions in a given image.

        :param img: img path or index
        :type img: str or int
        :return: list of tuples (x,y), with x, y position of each corner in the image.
        :rtype: list
        """
        img_label = self.get_label(img)

        return [(img_label[x], img_label[y]) for x, y in zip(self.x_corners_names, self.y_corners_names)]

    @property
    def x_corners_names(self) -> List[str]:
        """
        Get the list of columns names for the x coordinates of the corners

        :return: list of columns names
        :rtype: list of string
        """
        return [f"x_{name}" for name in CORNERS_NAMES]

    @property
    def y_corners_names(self) -> List[str]:
        """
        Get the list of columns names for the y coordinates of the corners

        :return: list of columns names
        :rtype: list of string
        """
        return [f"y_{name}" for name in CORNERS_NAMES]

    @property
    def watermark_size(self) -> str:
        """
        Return the name of the field of self.df with the watermark sizes of each image

        :return: Name of the columns which contains the watermark sizes of each image.
        :rtype: str
        """
        return "watermark_height"

    def add_metadata(self, metadata_name, metadata_value) -> None:
        """
        Add a metadata column and values for each image.

        :param metadata_name: new metadata field
        :type metadata_name: str
        :param metadata_value: list of the field value for each image
        :type metadata_value: list
        :return: None
        """
        self.df[metadata_name] = metadata_value

    def as_relative_paths(self, path: Union[Path, str]) -> None:
        """
        Convert the image path in the metadata as path relative to the provided reference path

        :param path: reference path
        :type path: str or Path
        :return: None
        """
        self.df.image = self.df.image.apply(lambda x: PurePath(x).relative_to(path).as_posix())

    def as_working_dir_paths(self) -> None:
        """
        Convert image paths as paths relative to the working directory (at the moment of the Labels instance creation)

        :return: None
        """
        self.df.image = self.df.image.apply(lambda x: Path(self.path.parent / x))

    def reorder_corners(self) -> None:
        """
        Ensures the names of the corners in the dataset matches their order in the image.
        The order is the order of corner obtained by reading the image row by row.
        I.e. the order obtained by sorting the corners on their value (y_corner * image_width + x_corner).

        :return: None
        """
        pos_in_img = np.zeros(4)
        coord = ["x", "y"]
        ordered_dict = {f"{c}_{name}": [] for name in CORNERS_NAMES for c in coord}
        for _, row in self.df.iterrows():
            for i in range(4):
                col_x = f"x_{CORNERS_NAMES[i]}"
                col_y = f"y_{CORNERS_NAMES[i]}"
                pos_in_img[i] = row[col_x] + row[col_y] * row["width"]
            point_order = pos_in_img.argsort()
            for i, name in enumerate(CORNERS_NAMES):
                for c in coord:
                    col = f"{c}_{CORNERS_NAMES[point_order[i]]}"
                    ordered_dict[f"{c}_{name}"].append(row[col])
        for key, val in ordered_dict.items():
            self.df[key] = val

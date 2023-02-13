import os
import shutil

import cv2
import pandas as pd
import numpy as np
from pathlib import Path, PureWindowsPath
from typing import Union
from src.labeling.labels import Labels
from glob import glob


class LardDataset:
    """
    Class to load, merge (in the case of a splitted dataset), remove watermark and easily export a LardDataset to other
     detection formats  (coco, tlbr,..).
    Usage :
    dataset = LardDataset(train_path=PATH_TO_TRAIN_DATASET, test_path=PATH_TO_TEST_DATASET)
    # Coco format
    dataset.export(output_directory,
                   bbx_format="xywh",   # other formats are tlbr (top left bottom right), tlwh (top left width height,
                                        # corners (keep corner instead of bbox)
                   normalized=True,  # are bbox positions normalized with respect to image size or kept as pixel
                   label_file="multiple", # one file per image, "single" for a single label file
                   crop=True) # crop each synthetized image to remove watermarks
    """
    def __init__(self, train_path: Union[Path, str] = None, test_path: Union[Path, str] = None) -> None:
        self.datasets: dict = {}
        self.datasets_dirs = {}
        if train_path is not None:
            dataset_name = "train"
            self.datasets_dirs[dataset_name] = Path(train_path)
            self.datasets[dataset_name] = self._load_labels_file(self.datasets_dirs[dataset_name])
        if test_path is not None:
            dataset_name = "test"
            self.datasets_dirs[dataset_name] = Path(test_path)
            self.datasets[dataset_name] = self._load_labels_file(self.datasets_dirs[dataset_name], dataset_name)
        if len(self.datasets) > 0:
            dataset = list(self.datasets.values())[0]
            self.x_cols = dataset.x_corners_names
            self.y_cols = dataset.y_corners_names

    @staticmethod
    def _load_labels_file(path: Path, dataset: str = "train") -> Labels:
        """
        Load lard label metadata.csv in the provided path.
        If the dataset was splitted in multiple subdir, all the metadata csv will be merged and included in the
        resulting Label object

        :param path: Path to a Lard dataset.
        :type path: Path
        :param dataset: dataset name, train or test
        :type dataset: str
        :return: Labels instance of the dataset, merged if multiple csv were found.
        :rtype: Labels
        """
        try:
            labels = Labels(path / f"{path.name}.csv")
            labels.as_working_dir_paths()
        except FileNotFoundError:
            # Try check if we can find one in the current repo
            csv_candidates = list(glob(f"{path}*.csv"))
            if len(csv_candidates) > 0:
                labels = Labels(csv_candidates[0])
                labels.as_working_dir_paths()
            else:
                # Try check if the dataset was splitted in different parts
                csv_candidates = list(glob(f"{path}{os.sep}*{os.sep}*.csv"))
                if len(csv_candidates) > 0:
                    labels = None
                    for csv_candidate in csv_candidates:
                        lbl = Labels(csv_candidate)
                        lbl.as_working_dir_paths()
                        if labels is None:
                            labels = lbl
                        else:
                            labels += lbl
                else:
                    raise FileNotFoundError(f"No metadata csv for {dataset} was not found in {path}")
        return labels

    def to_tlbr(self, labels: Labels) -> None:
        """
        Convert labels with corners position to bboxes in tlbr (top left and bottom right points ) format.

        :param labels: Lard dataset labels with corner positions
        :type labels: Labels
        :return: None
        """
        df = labels.df
        df["y_tl"] = df[labels.y_corners_names].min(axis=1)
        df["y_br"] = df[labels.y_corners_names].max(axis=1)
        df["x_tl"] = df[labels.x_corners_names].min(axis=1)
        df["x_br"] = df[labels.x_corners_names].max(axis=1)
        self.x_cols = ["x_tl", "x_br"]
        self.y_cols = ["y_tl", "y_br"]

    def to_tlwh(self, labels: Labels) -> None:
        """
        Convert corners position to tlwh bbox labels.

        :param labels: Lard dataset labels with corner positions
        :type labels: Labels
        :return: None
        """
        df = labels.df
        df["y"] = df[labels.y_corners_names].min(axis=1)
        df["h"] = df[labels.y_corners_names].max(axis=1) - df["y"]
        df["x"] = df[labels.x_corners_names].min(axis=1)
        df["w"] = df[labels.x_corners_names].max(axis=1) - df["x"]
        self.x_cols = ["x", "w"]
        self.y_cols = ["y", "h"]

    @staticmethod
    def tlwh_to_xywh(labels: Labels) -> None:
        """
        Convert tlwh bboxes to xywh.

        :param labels: Lard dataset Labels in tlwh format.
        :type labels: Labels
        :return: None
        """
        df = labels.df
        df.x = df.x + df.w / 2
        df.y = df.y + df.h / 2

    def normalize_labels(self, labels: Labels) -> None:
        """
        Normalize label with the image size. Input labels should be in pixels, and will be divided by image width/height

        :param labels: Lard dataset Labels, with target positions in pixels.
        :type labels: Labels
        :return: None
        """
        df = labels.df
        for x_col in self.x_cols:
            df[x_col] = df[x_col] / df["width"]
        for y_col in self.y_cols:
            df[y_col] = df[y_col] / df["height"]

    def get_ordered_cols(self):
        """
        Return the names of the columns containing target position in order.
        Order is x coordinate, then y coordinate, for each of the position columns in self.x_cols order.

        :return: ordered list of columns names for target position.
        :rtype: list
        """
        return [cols[i] for i in range(len(self.x_cols)) for cols in [self.x_cols, self.y_cols]]

    @staticmethod
    def crop_labels(labels: Labels) -> None:
        """
        Update labels to positions in cropped images.

        :param labels: dataset Label
        :type labels: Labels
        :return: None
        """
        df = labels.df
        df.loc[~df[labels.watermark_size].isna(), "height"] = df["height"] - 2 * df[labels.watermark_size]
        for col in labels.y_corners_names:
            df.loc[~df[labels.watermark_size].isna(), col] = df[col] - df[labels.watermark_size]

    def export(self,
               output_dir: Union[Path, str],
               bbx_format: str = None,
               normalized: bool = False,
               label_file: str = "single",
               sep: str = ";",
               header: bool = None,
               crop: bool = True,
               ext: str = "txt") -> None:
        """
        Export the Lard dataset to another format

        :param output_dir: directory where the converted dataset will be saved
        :type output_dir: Path or string
        :param bbx_format: Format for label bbox. Options are :
        - "tlbr" (x,y of top left then x,y of bottom rights corners of the bbox)
        - "tlwh" (x, y of top left, bbox width and height)
        - "xywh" (x, y of the center of the bbox, bbox width and height)
        - "corners" (x,y of each corner)
        :type bbx_format: str
        :param normalized: option to normalize the bbox position by the image size. If true, bbox labels are expressed
        in fraction of the image width and height, if False, left in pixels. Default = False.
        :type normalized: bool
        :param label_file: "single" (all the labels are in a single csv, with a column with image path) or
        "multiple" (one label file per image, saved in output_dir/labels).
        :type label_file: str
        :param sep: label file(s) separator, default is ";".
        :type sep: " "
        :param header: If True, an header with column names is added to each label file.
        :type header: bool
        :param crop: If True, crop during export all images with watermarks and updates bboxes position for the cropped
        image. If False, the image will be copied without modifications.
        :type crop: bool
        :param ext: Extension format for labels files. Default is "txt".
        :type ext: str
        :return: None
        """
        output_dir = Path(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        for name, dataset in self.datasets.items():
            print(f"------ Exporting {name} dataset -------")
            dataset_dir = output_dir / name
            os.makedirs(dataset_dir, exist_ok=True)
            image_dir = dataset_dir / "images"
            os.makedirs(image_dir, exist_ok=True)
            if crop:
                print(f"Cropping labels bbox")
                self.crop_labels(dataset)
            if bbx_format == "tlbr":
                print("Converting bboxes to tlbr format")
                self.to_tlbr(dataset)
            elif bbx_format in ["tlwh", "xywh"]:
                print("Converting bboxes to tlwh format")
                self.to_tlwh(dataset)
                if bbx_format == "xywh":
                    print("Converting bboxes from tlwh to xywh")
                    self.tlwh_to_xywh(dataset)
            if normalized:
                print("Normalizing bboxes")
                self.normalize_labels(dataset)
            if label_file == "multiple":
                out_label_dir = dataset_dir / "labels"
                os.makedirs(out_label_dir, exist_ok=True)
            else:
                out_label_file = dataset_dir / ("labels."+ext)
            bbox_id = 0
            out = {"id": [bbox_id]}
            last_image = None
            coco_df = pd.DataFrame(columns=["id"] + self.get_ordered_cols())
            print("Starting images export")
            for index, row in dataset.df.iterrows():
                if 0 == index % 100:
                    print(f"Progress : {index} images on {dataset.df.shape[0]}")
                img_path = Path(row.image)
                if last_image != img_path:
                    if crop and not np.isnan(row["watermark_height"]):
                        img = cv2.imread(str(img_path))
                        if img is None:  # older versions of the dataset might contain windows not posix paths
                            row.image = PureWindowsPath(row.image).as_posix()
                            img_path = self.datasets_dirs[name].parent / row.image
                            img = cv2.imread(str(img_path))
                        img = img[int(row["watermark_height"]):-int(row["watermark_height"]), :]
                        cv2.imwrite((image_dir / img_path.name).as_posix(), img)
                    else:
                        shutil.copyfile(img_path, image_dir / img_path.name)
                    if label_file == "multiple":
                        last_image = img_path
                        out_label_file = out_label_dir / (img_path.stem + "." + ext)
                        coco_df = pd.DataFrame(columns=["id"]+self.get_ordered_cols())

                for col in self.x_cols + self.y_cols:
                    out[col] = row[col]
                if label_file == "single":
                    out["image"] = [str(img_path.resolve())]
                coco_df = pd.concat([coco_df, pd.DataFrame(out)])
                if label_file == "multiple":
                    coco_df.to_csv(out_label_file, sep=sep, header=header, index=False)

            if label_file == "single":
                coco_df.to_csv(out_label_file, sep=sep, header=header, index=False)


if __name__ == "__main__":
    lard_dataset = LardDataset("data/multiple_train", "data/test_dataset")
    lard_dataset.export(output_dir="data/converted_dataset_no_crop",
                        bbx_format=None,
                        normalized=False,
                        label_file="single",
                        crop=False,
                        sep=',',
                        header=True)

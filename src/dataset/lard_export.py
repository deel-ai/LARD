"""
Command-line script to export a lard dataset to most of the popular formats.

To get the list of available options :

.. code-block:: console

    python lard_export.py -h

Usage example for coco format:

.. code-block:: console

    python src/dataset/lard_export.py --train data/multiple_train --test data/test_dataset -o data/converted_coco -b "xywh"
    -n -lf "multiple" -c -s " "

Parameters values and expected format are the same as the python methods, described in ``export_tool.ipynb``
"""
import os
import argparse
from pathlib import Path
from src.dataset.lard_dataset import LardDataset


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(
        prog=Path(os.path.basename(__file__)).stem,
        description="""Tool to prepare and export Lard dataset to other detections formats"""
    )
    parser.add_argument(
        '--train',
        type=Path,
        help='Path to train dataset',
        default=None,
        required=False
    )
    parser.add_argument(
        '--test',
        type=Path,
        help='Path to test dataset. At least one of train or test dataset must be filled',
        default=None,
        required=False
    )
    parser.add_argument(
        '-o', '--output_dir',
        type=Path,
        help='Path where the converted dataset will be saved',
        default=None,
        required=False
    )
    parser.add_argument(
        '-b', '--bbox',
        help='Bbox format. Available formats are "tlbr", "tlwh", "xywh" and "corners".',
        default="corners",
    )
    parser.add_argument(
        '-n', '--normalize',
        help='Bboxes positions are normalized by image size',
        default="False",
        action='store_true'
    )
    parser.add_argument(
        '-lf', '--label_format',
        help='Label format : "single" (one file) or "multiple" (one label file per image)',
        default="single"
    )
    parser.add_argument(
        '-c', '--crop',
        help='Crop images with watermarks to remove it',
        default="False",
        action='store_true'
    )
    parser.add_argument(
        '-s', '--sep',
        help='Custom separator for label files',
        default=" ",
    )
    parser.add_argument(
        '--header',
        help='Add column header to each label file',
        default=False,
        action='store_true'
    )
    parser.add_argument(
        '-v', '--verbose',
        help='Verbose mode',
        action='store_true'
    )
    parser.add_argument(
        '-e', '--ext',
        help='label file extension ("txt", "csv",...)',
        default="txt"
    )
    args = parser.parse_args()

    lard_dataset = LardDataset(args.train, args.test)
    lard_dataset.export(output_dir=args.output_dir,
                        bbx_format=args.bbox,
                        normalized=args.normalize,
                        label_file=args.label_format,
                        crop=args.crop,
                        sep=args.sep,
                        header=args.header,
                        ext=args.ext)

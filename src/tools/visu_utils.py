import os
from pathlib import Path
import matplotlib.pyplot as plt
import cv2
import numpy as np
from src.labeling.labels import Labels
from src.labeling.labels_utils import compute_bbox


def display_img_with_labels(dataset_labels, img_idx, figsize=None, save_dir=None, dataset_dir=None):
    """
    Display image, bbox and corner for the image and for every runway in it.
    """
    if figsize is None:
        figsize = [12, 12]
    plt.rcParams['figure.figsize'] = figsize

    # Load metadata
    labels = list(dataset_labels.get_labels(img_idx).values())
    img_filepath = labels[0]["image"]

    # Load image
    if dataset_dir is not None:
        img_total_path = str(dataset_dir/img_filepath)
    else:
        img_total_path = img_filepath
    img = cv2.imread(img_total_path)
    if img is None:
        print(f"Image {img_total_path} not found ")
        return

    # Display the full image and bouding box
    print("Displaying ", img_filepath)
    runway_img = img.copy()

    for label in labels:
        corners = np.array([(label[x], label[y]) for x, y in zip(dataset_labels.x_corners_names, dataset_labels.y_corners_names)])
        bbox = compute_bbox(corners)
        tl = bbox[:2]  # top left corner of bbox
        br = bbox[2:]  # bottom right corner of bbox
        cv2.rectangle(runway_img, tl, br, (255, 0, 0), 2)
        
        # Add Text Background
        # Finds space required by the text so that we can put a background with that amount of width.
        label = "%s_%s" % (label['airport'], label['runway'])
        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 1.1, 2)
        text_h_offset = 5
        runway_img = cv2.rectangle(runway_img, tl, (tl[0] + w, tl[1] - h - text_h_offset), (255, 0, 0), -1)

        # Add Text
        runway_img = cv2.putText(runway_img, label, (tl[0], tl[1] - text_h_offset), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                (255, 255, 255), 2)

        # Add Corners
        for c in corners:
            cv2.circle(runway_img, c, 5, [0, 0, 255], thickness=-1)

        # Add Corners
        for c in corners:
            cv2.circle(runway_img, c, 5, [0, 0, 255], thickness=-1)

    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)
        save_filepath = save_dir / Path(img_filepath).name
        cv2.imwrite(str(save_filepath), runway_img)

    runway_img = cv2.cvtColor(runway_img, cv2.COLOR_RGB2BGR)
    plt.imshow(runway_img)
    plt.show()

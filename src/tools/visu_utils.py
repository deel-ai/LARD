import os
from pathlib import Path
import matplotlib.pyplot as plt
import cv2
import math
import numpy as np
import pandas as pd
from src.labeling.labels_utils import compute_bbox


def display_img_with_labels(dataset_labels, img_idx, figsize=None, save_dir=None, dataset_dir=None, do_plot=True):
    """
    Display image, bbox and corner for the image and for every runway in it.
    """
    if figsize is None:
        figsize = [12, 12]
    plt.rcParams['figure.figsize'] = figsize

    # Load metadata
    labels = dataset_labels.get_label(img_idx)
    img_filepath = labels["image"]

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

    # Add bbox
    try:
        corners = np.array(dataset_labels.get_corners_list(img_idx))
        bbox = compute_bbox(corners)
    except IndexError:
        plt.title(f"No corners found for image {img_filepath}")
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        plt.imshow(img)
        plt.show()
        return
    tl = bbox[:2]  # top left corner of bbox
    br = bbox[2:]  # bottom right corner of bbox
    cv2.rectangle(runway_img, tl, br, (255, 0, 0), 2)

    # Helper function to check if a value is NaN
    def is_nan(value):
        return value is None or (isinstance(value, float) and math.isnan(value))
    
    airport = labels.get('airport', None)
    runway = labels.get('runway', None)
    # Construct the label text
    if not is_nan(airport) and not is_nan(runway):
        label = f"{airport}_{runway}"
    elif not is_nan(airport):
        label = f"{airport}"
    elif not is_nan(runway):
        label = f"{runway}"
    else:
        label = None  # No valid label parts

    if label:  # Only proceed if there's a valid label to display
        # Add Text Background
        # Finds space required by the text so that we can put a background with that amount of width.
        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 1.1, 2)
        text_h_offset = 5
        runway_img = cv2.rectangle(runway_img, tl, (tl[0] + w, tl[1] - h - text_h_offset), (255, 0, 0), -1)

        # Add Text
        runway_img = cv2.putText(runway_img, label, (tl[0], tl[1] - text_h_offset), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    # Add Corners
    for c in corners:
        cv2.circle(runway_img, c, 5, [0, 0, 255], thickness=-1)
    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)
        save_filepath = save_dir / Path(img_filepath).name
        cv2.imwrite(str(save_filepath), runway_img)

    if do_plot:
        runway_img = cv2.cvtColor(runway_img, cv2.COLOR_RGB2BGR)
        plt.imshow(runway_img)
        plt.show()


def display_image_with_all_bboxes(
    dataset_labels,
    image_idx: int,
    figsize=(12, 12),
    hide_not_visible_labels=True,
    save_dir=None,
    dataset_dir=None,
    do_plot=True
):
    """
    For a single DataFrame row `image_idx`, this function:
      - Finds which image file that row refers to
      - Retrieves *all rows* that share that same image (i.e., all bounding boxes)
      - Draws each bounding box on a single displayed image
    """
    plt.rcParams['figure.figsize'] = figsize

    visible_polyg_color = (0, 0, 255)
    visible_box_color = (255, 0, 0)

    extended_polyg_color = (180, 0, 80)
    extended_box_color = (80, 0, 180)

    not_visible_polyg_color = (0, 154, 124)
    not_visible_box_color = (124, 154, 0)

    any_polyg_color = (0, 80, 200)
    any_box_color = (200, 80, 0)
    
    row = dataset_labels.df.iloc[image_idx]
    image_path = row["image"]

    # Find *all rows* in the CSV that have this same image
    rows_for_image = dataset_labels.get_rows_for_image(image_path)

    if dataset_dir is not None:
        img_full_path = str(Path(dataset_dir) / image_path)
    else:
        img_full_path = image_path

    img = cv2.imread(img_full_path)
    if img is None:
        print(f"Image not found: {img_full_path}")
        return

    # Convert to color space for plotting (only needed at display time)
    out_img = img.copy()
    def is_nan(value):
        return value is None or (isinstance(value, float) and math.isnan(value))

    for _, r in rows_for_image.iterrows():
        
        box_color = any_box_color
        polyg_color = any_polyg_color
        if r['runway_in_cone'] == 'IN_ODD':
            polyg_color = visible_polyg_color
            box_color = visible_box_color
        elif r['runway_in_cone'] == 'OUT_OF_ODD':
            box_color = not_visible_box_color
            polyg_color = not_visible_polyg_color
        elif r['runway_in_cone'] == 'IN_EXTENDED_ODD':
            box_color = extended_box_color
            polyg_color = extended_polyg_color
        x_TL, y_TL = int(r["x_TL"]), int(r["y_TL"])
        x_BL, y_BL = int(r["x_BL"]), int(r["y_BL"])
        x_TR, y_TR = int(r["x_TR"]), int(r["y_TR"])
        x_BR, y_BR = int(r["x_BR"]), int(r["y_BR"])

        min_x = min(x_TL, x_BL, x_TR, x_BR)
        max_x = max(x_TL, x_BL, x_TR, x_BR)
        min_y = min(y_TL, y_BL, y_TR, y_BR)
        max_y = max(y_TL, y_BL, y_TR, y_BR)

        lineweight = 2 if r['runway_in_cone'] == 'OUT_OF_ODD' else 1
        cv2.rectangle(out_img, (min_x, min_y), (max_x, max_y), box_color, lineweight)

        cv2.circle(out_img, (x_TL, y_TL), 2, polyg_color, -1)
        cv2.circle(out_img, (x_BL, y_BL), 2, polyg_color, -1)
        cv2.circle(out_img, (x_TR, y_TR), 2, polyg_color, -1)
        cv2.circle(out_img, (x_BR, y_BR), 2, polyg_color, -1)

        airport = r.get("airport", None)
        runway = r.get("runway", None)
        if not is_nan(airport) and not is_nan(runway):
            label = f"{airport}_{runway}"
        elif not is_nan(airport):
            label = f"{airport}"
        elif not is_nan(runway):
            label = f"{runway}"
        else:
            label = None
        if hide_not_visible_labels:
            if r['runway_in_cone'] == 'OUT_OF_ODD':
                label = None

        if label:
            # filled rectangle behind the text 
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
            text_offset = 5
            top_left = (min_x, min_y - text_offset - text_h)
            bottom_right = (min_x + text_w, min_y - text_offset)

            overlay = out_img.copy()

            # Filled rectangle on the overlay copy:
            cv2.rectangle(
                overlay,
                top_left, 
                bottom_right,
                polyg_color, 
                -1
            )

            # Blend the overlay with the original image:
            alpha = 0.4  # 0.0 = fully transparent, 1.0 = fully opaque
            cv2.addWeighted(overlay, alpha, out_img, 1 - alpha, 0, out_img)

            # Then draw text, etc. onto out_img as usual.
            cv2.putText(
                out_img,
                label,
                (min_x, min_y - text_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (255, 255, 255),
                2
            )
            
            # cv2.rectangle(out_img, top_left, bottom_right, polyg_color, -1)

            # cv2.putText(
            #     out_img,
            #     label,
            #     (min_x, min_y - text_offset),
            #     cv2.FONT_HERSHEY_SIMPLEX,
            #     1.0,
            #     (255, 255, 255),
            #     2
            # )

    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)
        save_path = Path(save_dir) / Path(image_path).name
        cv2.imwrite(str(save_path), out_img)
        print(f"Saved labeled image to {save_path}")

    if do_plot:
        # Convert BGR -> RGB just for displaying with matplotlib
        out_img_rgb = cv2.cvtColor(out_img, cv2.COLOR_BGR2RGB)
        plt.imshow(out_img_rgb)
        plt.title(f"All bounding boxes for {image_path}")
        plt.axis("off")
        plt.show()

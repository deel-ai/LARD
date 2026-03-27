import os
import pathlib
import yaml
import json
import math
import numpy as np
import pyproj
import shutil
import datetime
import re
import fnmatch

from typing import Union
from pathlib import Path
from src.labeling.labels import Labels
from src.labeling.export_config import NEW_CORNERS_NAMES, database_name

class BehindCameraError(Exception):
    "Exception raised when a part of the runway is behind the camera. In this case runway is not labeled"
    def __init__(self, message):
        super().__init__(message)

def extract_runway_info(runway_name):
    """Extracts the numerical part and suffix from a runway identifier"""
    match = re.match(r"(\d+)([LCR]?)", runway_name)
    if match:
        number = int(match.group(1))
        suffix = match.group(2)
        return number, suffix
    return None, None

def angle_diff_in_degrees(a, b):
    """
    Returns the absolute difference between two headings a and b (in degrees),
    wrapped into the range [0, 180]
    """
    diff = abs(a - b) % 360
    if diff > 180:
        diff = 360 - diff
    return diff

def runway_is_facing_us(plane_heading_deg, runway_identifier):
    """ Returns True if the runway's orientation is strictly less than 90° away from heading"""
    runway_num, suffix = extract_runway_info(runway_identifier)
    runway_heading_deg = runway_num * 10
    diff = angle_diff_in_degrees(plane_heading_deg, runway_heading_deg)
    return (diff < 90)  # strictly less than 90

def export_labels(dataset_type, yaml_scenario_path, export_dir=None, out_labels_file=None, out_images_dir=None):
    # Parse configuration file
    # All the dependencies
    debug=False
    print(f"Label export of {yaml_scenario_path} started")
    if export_dir is None:
        export_dir = yaml_scenario_path.parent
    if out_labels_file is None:
        out_labels_file = export_dir / 'exported_labels.csv'
    if out_images_dir is None:
        out_images_dir = export_dir / 'exported_images'

    with open(yaml_scenario_path, 'r') as f:
        yaml_scenario: dict = yaml.safe_load(f)
        if 'poses' not in yaml_scenario.keys():
            raise RuntimeError('The yaml scenario file is not complete, missing poses.')
        elif 'image' not in yaml_scenario.keys():
            raise RuntimeError('The yaml scenario file is not complete, missing image info.')
        elif 'trajectory' not in yaml_scenario.keys():
            raise RuntimeError('The yaml scenario file is not complete, missing trajectory.')
        else:
            print(f" Yaml scenario {yaml_scenario_path} correctly loaded")

    # Load the default ODD sets from file, e.g. 'ODD_Far', 'ODD_Medium', 'ODD_Close'
    with open('data/Lard_v2_Default_ODD.yaml', 'r') as file:
        default_odd = yaml.safe_load(file)

    # Load the appropriate runways database
    # database no longer depends on yaml. It depends on the image generator.
    database_path = database_name (dataset_type)

    print("For labeling, using runways database at ", database_path)
    with open(database_path, 'r') as f:
        runways_database = json.load(f)
 
    if os.path.exists(export_dir / "footage") and os.path.isdir(export_dir / "footage"):
        with_images = True
        os.makedirs(out_images_dir, exist_ok=True)
        all_files = os.listdir(export_dir / "footage")
        img_digits = len(str(len(yaml_scenario['poses']) - 1))
        # Filter footage folder only for files matching .jpg, .jpeg, and .png
        valid_files = [f for f in all_files if fnmatch.fnmatch(f, '*.jpg') or fnmatch.fnmatch(f, '*.jpeg') or fnmatch.fnmatch(f, '*.png')]
        if len(yaml_scenario['poses']) != len(valid_files):
            print("nb poses", len(yaml_scenario['poses']))
            print("nb images", len(valid_files))
            raise FileNotFoundError("Number of images in footage DOES NOT match poses in .yaml")
    else:
        with_images = False
        output_image_path = ""

    labels = Labels()
    airportsKeysNotFound=[]
    atleast_one_good_airport = False
    # # enumerate over each pose and generate the associated list of labels, 1 label per runway
    # # but we skip the opposite runway of a runway already treated
    for i, pose in enumerate (yaml_scenario['poses']):      # i is the pose indice in yaml file
        if debug:
            print (f" Labelling Pose {i} for airport {pose['airport']} and runway {pose['runway']}")
        if with_images == True:
            image_path = None
            # Iterate through the possible image file extensions for the current index
            for ext in ['jpeg', 'png', 'jpg']:
                image_path_candidate: Path = export_dir / "footage" / f"{export_dir.stem}_{str(i).zfill(img_digits)}.{ext}"            
                if os.path.exists(image_path_candidate):
                    image_path = image_path_candidate
                    break
                        
            if image_path is None:
                print (f"No image found for {export_dir.stem}_{str(i).zfill(img_digits)}")
                continue
            else:
                output_image_path = out_images_dir / image_path.name

        airport = pose['airport']
        treated_runways = []
        # for runway in yaml_scenario['airports_runways'][airport]:
        #     print (f"runway {runway}")
        #     # skip opposite runways
        #     if any(opposite(runway, treated_runway) for treated_runway in treated_runways):
        #         continue
        try: 
            for runway in runways_database[airport]:
                try: 
                    # Skip if it is not facing us (difference with the opposite of our heading is >= 90 deg)
                    # if not runway_is_facing_us((pose['pose'][3] + 180) % 360, runway): # DB Is Inversed right now....
                    if not runway_is_facing_us((pose['pose'][3]) % 360, runway):
                        if debug:
                            print (f"[FAILURE ORIENTATION] Runway {runway} is not facing current aircraft pose ({(pose['pose'][3] + 360) % 360}), skipping")
                        continue
                    if debug:
                        print (f"[SUCCESS ORIENTATION] Runway {runway} is facing current aircraft pose ({(pose['pose'][3] + 360) % 360})")

                    label = convert_label(yaml_scenario, output_image_path, pose, runway, runways_database, default_odd)

                    # Removed current validity check to allow multiple partial runways per image
                    # if is_runway_image_valid(image_shape, label):
                    #     valid_runways = True
                    labels.add_label(label)
                    atleast_one_good_airport = True
                except BehindCameraError as e:
                    if debug:
                        print (f"{airport} {runway} not labelled: {e}")
                treated_runways.append(runway)
        except KeyError as e:
            airportsKeysNotFound.append(f"{airport}")
            continue
        
        if with_images == True:
            shutil.copy(image_path, output_image_path)
    # Generate label file
    labels.export(out_labels_file)
    return labels, airportsKeysNotFound, atleast_one_good_airport


def convert_label(yaml_scenario, output_image_path, pose, runway, runways_database, default_odd):
    airport = pose['airport']
    image_time = datetime.datetime(**pose['time'])
    image_info = yaml_scenario['image']
    scen_gen_params = yaml_scenario['trajectory']
    width, height = image_info['width'], image_info['height']   # Param
    fov_x, fov_y = image_info['fov_x'], image_info['fov_y']     # Param
    try:
        use_default_ODD = yaml_scenario['trajectory']['use_ODD']
    except:
        use_default_ODD = False

    watermark = image_info.get("watermark_height", 300)
    
    label = {
        'uuid': pose['uuid'],
        'image': output_image_path,
        'airport': airport,
        'runway': runway,
        'height': height,
        'width': width,
        'watermark_height': watermark,
        'time': image_time,
        'lat_cam' : pose['pose'][1],        # Param
        'lon_cam' : pose['pose'][0],        # Param
        'alt_cam' : pose['pose'][2],        # Param
        'yaw': pose['pose'][3],             # Param
        'pitch': pose['pose'][4],           # Param
        'roll': pose['pose'][5]             # Param
    }
 
    runway_points = runways_database[airport][runway]
    runway_pts = [
        list(runway_points['A']['coordinate'].values()),  # TR
        list(runway_points['B']['coordinate'].values()),  # TL
        list(runway_points['C']['coordinate'].values()),  # BL
        list(runway_points['D']['coordinate'].values())   # BR
    ]
 
    A = np.array(runway_pts[0]) # TR
    B = np.array(runway_pts[1]) # TL
    C = np.array(runway_pts[2]) # BL
    D = np.array(runway_pts[3]) # BR
 
    """ Runway orientation """
    runway_true_heading = get_forward_azimuth(A, D)
    if runway_true_heading < 0: 
        runway_true_heading += 360
 
    computeLabels(label,runway_pts,fov_x,fov_y)     # compute label[<x|y>_<T|B><R|L>]   eg x_TL, y_BL ...
                                                    # compute slant distance, along track distance, height above rnwy, lateral path angle, vertical path angle

    # # Computing horizontal and vertical deviations for pose validity analysis
    # # We consider +/- 1 ° for the angles and +/- 100m for the distance
    label['runway_in_cone'] = check_pose_validity_against_cone(
        scen_gen_params,
        default_odd, 
        label['along_track_distance']*1852, 
        label['lateral_path_angle'], 
        -label['vertical_path_angle'], # Negative following vertical path angle inversion
        yaw = (label['yaw'] - runway_true_heading + 180) % 360, # normalizing and inversing the yaw for comparison (acft is facing runway)
        pitch=label['pitch'] - 90, 
        roll=label['roll'],
        use_default_ODD=use_default_ODD
    )
    if label['runway_in_cone'] == "OUT_OF_ODD": # Pose was outside the cone. Check with extended ODD
        label['runway_in_cone'] = check_pose_validity_against_cone(
            scen_gen_params,
            default_odd,
            label['along_track_distance']*1852,
            label['lateral_path_angle'], 
            -label['vertical_path_angle'], # Negative following vertical path angle inversion
            yaw = (label['yaw'] - runway_true_heading + 180) % 360, # normalizing and inversing the yaw for comparison (acft is facing runway)
            pitch=label['pitch'] - 90, 
            roll=label['roll'],
            use_default_ODD=use_default_ODD,
            extended=True
        )
        if label['runway_in_cone'] == "IN_ODD":
            label['runway_in_cone'] = "IN_EXTENDED_ODD"
    return label

def geodetic_to_cartesian(lat, lon, alt, ref_lat, ref_lon, ref_alt, runw_az):
    """Convert lat lon coordinates to local cartesian coordinates"""
    """angles in degrees """
    """Local repere origin is (ref_lat, ref_lon). X is horizontal in the direction of the runway (runw_az), """
    """ Y is horizontal to the left of the runway so that Z = X^Y is vertical upwards """
    geod = pyproj.Geod(ellps="WGS84")
    azimuth, _, distance = geod.inv(ref_lon, ref_lat, lon, lat)
    
    x = distance * np.cos(np.radians(azimuth - runw_az))   # along track of the runway
    y = -distance * np.sin(np.radians(azimuth - runw_az))  # y to the left of the runway
    z = alt - ref_alt
    
    return np.array([x, y, z])

def get_forward_azimuth(P1, P2):
    """Calcule l'azimut de l'axe de la piste en degrés par rapport au nord"""
    geod = pyproj.Geod(ellps="WGS84")
    azimuth, _, _ = geod.inv(P1[1], P1[0], P2[1], P2[0])  # lon, lat order
    return azimuth


def angle_between_vectors(v1, v2):
    dot_product = np.dot(v1, v2)
    
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    
    val = dot_product / (norm_v1 * norm_v2)
    if val > 1:
        val = 1
    elif val < -1:
        val = -1    
    
    angle_rad = np.arccos(val)
    
    return angle_rad


def rotation_matrix (axis, angle):
    """
    Return a rotation matrix of angle in radians around the axis.

    :param axis: Vector (x, y, z) 
    :param angle: Angle in radians
    :return: Rotation matrix 3x3
    """
    axis = np.array(axis)
    axis = axis / np.linalg.norm(axis)  # Normalisation du vecteur

    x, y, z = axis
    cos_theta = np.cos(angle)
    sin_theta = np.sin(angle)
    
    Q = np.array([
        [0, -z, y],
        [z, 0, -x],
        [-y, x, 0]
    ])
    
    I = np.eye(3)  # Matrice identité
    
    P = np.array([
        [x*x, x*y, x*z],
        [y*x, y*y, y*z],
        [z*x, z*y, z*z]
    ])
        
    R = P + cos_theta*(I - P) + sin_theta*Q;
    
    return R


def apply_rotations_int (yaw, pitch, roll):
    """Apply rotations Yaw → Pitch → Roll to X,Y,Z axis 
       Angles are in radians
       Rotations are intrinsic, meaning next rotations use modified axis 
       Return NewX, NewY, NewZ 
       Note that applying Roll -> Pitch -> Yaw extrinsicly is similar"""
    
#    print ("INTRINSIC ROTATIONS !!!!")
    
    X_init = np.array([1, 0, 0])
    Y_init = np.array([0, 1, 0])
    Z_init = np.array([0, 0, 1])

    # Application de Ryaw autour de Z_init
    Ryaw = rotation_matrix(Z_init, yaw)
    Xprim = Ryaw @ X_init
    Yprim = Ryaw @ Y_init
    Zprim = Z_init

    # Application de Rpitch autour de Yprim
    Rpitch = rotation_matrix(Yprim, pitch)
    Xter = Rpitch @ Xprim
    Yter = Yprim
    Zter = Rpitch @ Zprim

    # Application de Rroll autour de Xter
    Rroll = rotation_matrix(Xter, roll)
    Xquart = Xter
    Yquart = Rroll @ Yter
    Zquart = Rroll @ Zter

    return Xquart, Yquart, Zquart


def point_in_new_repere (point, XNew, YNew, ZNew) :
    """ Input: point and XNew, YNew, ZNew are in X Y Z repere """
    """ Output: point in XNew, YNew, ZNew repere """
    
    x = np.dot(point,XNew)
    y = np.dot(point,YNew)
    z = np.dot(point,ZNew)
    
    return np.array([x,y,z])
 

def pointcam_to_pix(P: np.array, fov_h, fov_v, img_h, img_v):
    """ input point in camera repere and camera parameters. Angles in degrees"""
    """ output pixel x and pixel y of the point projection on the image """
    
    # If point is behind camera then not visible
    if P[0] <= 0:
        raise BehindCameraError ("One point is behind the camera")  # The runway will not be labelled at all.
    
    fov_h_rad = np.radians(fov_h)
    fov_v_rad = np.radians(fov_v)

    # visible word size for the point depth
    world_width = 2 * P[0] * np.tan(fov_h_rad * 0.5)  
    world_height = 2 * P[0] * np.tan(fov_v_rad * 0.5)  

    # normalised x and y according to this size
    x_norm = (1 - ((P[1] / world_width) + 0.5))   # Normalisation between 0 and 1
    y_norm = (1 - ((P[2] / world_height) + 0.5))  # both negative because y is toward left and z is toward up

    # # if the point is out of visibility
    # if x_norm < 0 or x_norm > 1 or y_norm < 0 or y_norm > 1:
    #     return None, None

    # Else return corresponding pixel
    x_pixel = int(x_norm * img_h)
    y_pixel = int(y_norm * img_v)
   
    return x_pixel, y_pixel


def computeLabels(label,points,fov_x,fov_y):
    latCam = label['lat_cam']
    lonCam = label['lon_cam']
    altCam = label['alt_cam']
    yawCam = label['yaw']
    pitchCam = label['pitch']
    rollCam = label['roll']
    img_width = label['width']
    img_height = label['height']
   
    A = np.array(points[0]) # TR
    B = np.array(points[1]) # TL
    C = np.array(points[2]) # BL
    D = np.array(points[3]) # BR
 
    """ Runway orientation """
    opp_runway_azimuth = get_forward_azimuth((D+C)/2, (A+B)/2)
    if opp_runway_azimuth < 0: 
        opp_runway_azimuth += 360
    #print (f"runway azimuth {opp_runway_azimuth}")

    """ word origin = middle of C and D """
    O = ( C + D) / 2            #ltp
    """ middle of A & B """ 
    P = ( A + B) / 2            #fpap

    """ correction of orientation according to runway_azimuth """
    cam_pos = np.array([latCam, lonCam,  altCam])
    cam_orientation = np.radians (np.array([opp_runway_azimuth - yawCam , 90 - pitchCam, rollCam]))

    """ Translation to cartesian repere """
    """ X normalised horizontal proj of O->P """
    """ Y normalised horizontal proj of O->C """
    """ Z normalised vertical  """
    cam_pos_cart = geodetic_to_cartesian(*cam_pos, *O, opp_runway_azimuth)

    """ Compute the camera repere """
    """ x_cam , y_cam, z_cam  = R (X,Y,Z)  """
    x_cam, y_cam, z_cam = apply_rotations_int (*cam_orientation) 

    for i, pt in enumerate(points):
        point = np.array(pt)
        point_cart = geodetic_to_cartesian(*pt, *O, opp_runway_azimuth)
        #print (f"point_cart {point_cart} {fov_x} {fov_y} {img_height} {img_width}")
        point_trans = point_cart - cam_pos_cart             # point translated according to cam pos
        #print (f"point_trans {point_trans} {fov_x} {fov_y} {img_height} {img_width}")

        point_cam = point_in_new_repere (point_trans, x_cam, y_cam, z_cam)  # point in camera repere
        pix_x , pix_y = pointcam_to_pix (point_cam, fov_x, fov_y, img_height, img_width)
        #print (f"pix_x = {pix_x}  pix_y = {pix_y}")

        label[f"x_{NEW_CORNERS_NAMES[i]}"] = pix_x
        label[f"y_{NEW_CORNERS_NAMES[i]}"] = pix_y


    """ additionnal metrics """
    """ runway repere = X along ltp->fpap  Y along ltp -> C  """
    C_cart = geodetic_to_cartesian(*C, *O, opp_runway_azimuth)
    ltp_cart = geodetic_to_cartesian(*O, *O, opp_runway_azimuth)    # [0 0 0] ltp
    fpap_cart = geodetic_to_cartesian(*P, *O, opp_runway_azimuth)   #         fpap

    # runway plane is defined by 3 points (C, D, fpap)  <==> (C, ltp, fpap)
    #   fpap is (A + B) / 2
    #   ltp  is (C + D) / 2.
    # We prefer NOT to look for an approximated plan that best includes points A,B,C,and D
    # as we consider that points C and D have a greater impact on the approach since they are the closest
    x_runway = (fpap_cart - ltp_cart)/np.linalg.norm(fpap_cart - ltp_cart)     
    y_runway = (C_cart - ltp_cart)/np.linalg.norm(C_cart - ltp_cart) 
    z_runway = np.cross (x_runway, y_runway)
         
    # """ runway slope """
    # runway_slope = math.asin((fpap_cart[2] - ltp_cart[2])/(np.linalg.norm(fpap_cart - ltp_cart)))
    # print(f"runway_slope (deg): {np.degrees(runway_slope)}")
    
    # slant distance is the real distance between aircraft and ltp
    slant_distance = np.linalg.norm (ltp_cart - cam_pos_cart)                                       # meters
    slant_distance_miles = slant_distance / 1852                                                    # miles
    label['slant_distance'] = slant_distance_miles
    #print(f"Slant distance miles: {slant_distance_miles}")
    
    # along track distance is norm of the projection of (aircraft -> ltp) on x_runway
    cam_pos_along_track = point_in_new_repere (cam_pos_cart, x_runway, y_runway, z_runway)
    along_track_distance = np.abs(cam_pos_along_track[0]) # proj on x_runway                        # meters
    along_track_distance_miles = along_track_distance / 1852                                        # miles
    label['along_track_distance'] = along_track_distance_miles
    #print(f"Along track distance (miles): {along_track_distance_miles}")
    
    # height above runway is the difference of altitude between the aircraft and ltp
    height_above_runway = cam_pos_cart[2]                                                           # meters
    height_above_runway_feets = height_above_runway * 3.28084                                       # feets
    label['height_above_runway'] = height_above_runway_feets
    #print(f"Height above runway (feet): {height_above_runway_feets}")
    
    # lateral path angle is the angle between (-x_runway) and projection of (lateralRefPoint -> aircraft) on runway plane
    latPathAngleRefPoint = ltp_cart  # + 3050 * x_runway     The lateral reference point is now ltp !!!
    v1 = (cam_pos_cart - latPathAngleRefPoint)
    v2 = point_in_new_repere (v1, x_runway, y_runway, z_runway)
    v2[2] = 0                                       # projection of (lateralRefPoint -> aircraft) on runway plane
    v3 = np.array([-1,0,0])                         # -x_runway in runway repere
    lateralPathAngle = angle_between_vectors (v2,v3)                                                # radians
    if v2[1] > 0:      # aircraft left of the extended centerline
        lateralPathAngle = -lateralPathAngle
    lateralPathAngle_deg = np.degrees(lateralPathAngle)                                             # degrees
    label['lateral_path_angle'] = lateralPathAngle_deg
    #print(f"lateralPathAngle (deg): {lateralPathAngle_deg}")
    
    # vertical path angle is the angle between runway plane and (verticalRefPoint -> aircraft)
    vertPathAngleRefPoint = ltp_cart + 305 * x_runway
    v1 = (cam_pos_cart - vertPathAngleRefPoint)
    v2 = point_in_new_repere (v1, x_runway, y_runway, z_runway)                 # (lateralRefPoint -> aircraft) in runway repere
    v3 = point_in_new_repere (v1, x_runway, y_runway, z_runway)                 
    v3[2] = 0;         # projection on runway plane                             # projection of (lateralRefPoint -> aircraft) on runway plane

    verticalPathAngle = angle_between_vectors (v2,v3)                                               # radians
    if v2[2] < 0:      # aircraft under runway plane
        verticalPathAngle = -verticalPathAngle
    verticalPathAngle_deg = np.degrees(verticalPathAngle)                                           # degrees
    label['vertical_path_angle'] = verticalPathAngle_deg
    #print(f"verticalPathAngle (deg): {verticalPathAngle_deg}")

def in_angular_range(angle, angle_min, angle_max, margin=0.1, margin_max=None):
    """
    Return True if `angle` is within [angle_min, angle_max] on the circle,
    accounting for potential wrap around 360.
    """
    if not margin_max:
        margin_max = margin
    # Normalize angles into [0,360)
    angle     = angle % 360
    angle_min = angle_min % 360
    angle_max = angle_max % 360
    angle_min -= margin
    angle_max += margin_max
    angle_min_mod = angle_min % 360
    angle_max_mod = angle_max % 360

    if angle_min_mod <= angle_max_mod:
        return angle_min_mod <= angle <= angle_max_mod
    else:
        # wrap-around range
        return angle >= angle_min_mod or angle <= angle_max_mod
    

def is_pose_in_param_set(params, along_track_dist, lateral_path_angle, vertical_path_angle, yaw, pitch, roll, debug=False, extended=False):
    """
    Checks if a given pose is inside the position-rotation 'cone' defined by 'params' 
    with the +/- 100m and +/- 1° margins mentioned.
    """
    # Distance check (with +/- 100 m margin):
    if debug:
        print(f"Checking along_track_dist {along_track_dist} vs [{params['min_distance_m'] - 100}, {params['max_distance_m'] + 100}]")
    if not extended:
        if (along_track_dist < params["min_distance_m"] - 100) or (along_track_dist > params["max_distance_m"] + 100):
            return False
    else:
        if (along_track_dist < params["min_distance_m"] - 300) or (along_track_dist > params["max_distance_m"] + 2000):
            return False
    
    margin = 1 if not extended else 6 # +/- 5° horizontal for extended ODD
    if not in_angular_range(lateral_path_angle, params["alpha_h_min"], params["alpha_h_max"], margin=margin):
            return False
    
    margin_max = None if not extended else 10 # + 10° positive vertical only for extended ODD
    if not in_angular_range(vertical_path_angle, params["alpha_v_min"], params["alpha_v_max"], margin=0.8, margin_max=margin_max):
            return False
    
    # Angle checks (with +/- 10° margin):
    angle_checks = [
        (yaw,               "yaw_min",      "yaw_max"),
        (pitch,             "pitch_min",    "pitch_max"),
        (roll,              "roll_min",     "roll_max"),
    ]
    
    margin = 1 if not extended else 15 # +/- 5° yaw/pitch/roll for extended ODD
    for value, min_key, max_key in angle_checks:
        if debug:
            print(f"Checking angle {value} vs [{params[min_key]}, {params[max_key]}], ±{margin}°")
        if not in_angular_range(value, params[min_key], params[max_key], margin=margin):
            return False
    # All checks passed
    return True

def check_pose_validity_against_cone(scen_gen_params, default_odd, along_track_dist, lateral_path_angle, vertical_path_angle, yaw, pitch, roll, use_default_ODD=False, extended=False):
    """Sets the parameter as 'IN_ODD', 'OUT_OF_ODD', or 'UNKNOWN', depending on the trajectory parameters"""
    debug = False
    #print(f"Parameters: along_track_dist={along_track_dist}, lateral_path_angle={lateral_path_angle}, vertical_path_angle={vertical_path_angle}, yaw={yaw}, pitch={pitch}, roll={roll}")
    #print(f"Scenario generation parameters: {scen_gen_params}")

    distributions = [ "alpha_h_distrib", "alpha_v_distrib", "pitch_distrib", "yaw_distrib", "roll_distrib"]
    if (not use_default_ODD) and any(scen_gen_params[d] != "uniform" for d in distributions):
        # At least one parameter is generated using standard deviation instead of ranges, therefore we cannot ensure 
        # that the pose is valid against the generation cone.
        return "UNKNOWN"    
    if debug:
        print(f"Checking along_track_dist {along_track_dist} against {scen_gen_params['min_distance_m']} and {scen_gen_params['max_distance_m']} (+/- 1m)")

    if not use_default_ODD:
        # Just use the scenario params directly (single set of ranges)
        if is_pose_in_param_set(scen_gen_params, along_track_dist,
                                lateral_path_angle, vertical_path_angle,
                                yaw, pitch, roll, debug=debug, extended=extended):
            return "IN_ODD"
        else:
            return "OUT_OF_ODD"
    else:
        # Here we assume each of these ODD_* keys is a param dict with 
        # "min_distance_m", "max_distance_m", "alpha_h_min", etc.
        odd_param_sets = [
            default_odd["ODD_Far"],
            default_odd["ODD_Medium"],
            default_odd["ODD_Close"]
        ]

        # If the pose is inside *any* of these 3 sets → "IN_ODD"
        for param_set in odd_param_sets:
            if is_pose_in_param_set(param_set, along_track_dist,
                                    lateral_path_angle, vertical_path_angle,
                                    yaw, pitch, roll, debug=debug, extended=extended):
                return "IN_ODD"
        
        # If we exhaust all sets and none matches, it's "OUT_OF_ODD"
        return "OUT_OF_ODD"

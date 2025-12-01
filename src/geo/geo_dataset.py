import pathlib
import json
import os
import pyproj
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Union

import pytz
from timezonefinder import TimezoneFinder

from src.geo.geo_utils import find_center, ecef2llh, llh2ecef, find_azimuth_between_2_coordinates, forward_pos
from src.scenario.default_scenario_values import DefaultTrajectory


def add_or_update_runways(database_file: str, airport_ocai: str, runways: str, coordinates):
    """
    
    Update the database with new runways or update the coordinates of existing ones.
    
    :param database_file: file containing coordinates of the runways
    :type database_file: str
    :param airport_ocai: code of the airport
    :type airport_ocai: str
    :param runways: Runway code and optionally the id of the opposite runway
    :type runways: array of str, max length of 2
    :param coordinates: table of 4 points, each defined by latitude, longitude and altitude
    :type coordinates: numpy array of floats, with shape (4, 3)
    """
    
    if not os.path.exists(database_file):
        # If the file doesn't exist, create a new one with an empty structure
        with open(database_file, 'w') as f:
            json.dump({}, f)  # Empty dictionary to initialize the file
        print(f"Runways database file '{database_file}' created.")
    with open(database_file, 'r') as f:
        runways_db = json.load(f)

    if airport_ocai not in runways_db.keys():
        runways_db[airport_ocai] = {}

    latitude = coordinates[:, 0].tolist()
    longitude = coordinates[:, 1].tolist()
    altitude = coordinates[:, 2].tolist()

    rway = runways[0]  # Treat the first runway id
    runways_db[airport_ocai][rway] = {
        'A': {'position': {'x': 0, 'y': 0, 'z': 0},
              'coordinate': {'latitude': latitude[2], 'longitude': longitude[2], 'altitude': altitude[2]}},
        'B': {'position': {'x': 0, 'y': 0, 'z': 0},
              'coordinate': {'latitude': latitude[3], 'longitude': longitude[3], 'altitude': altitude[3]}},
        'C': {'position': {'x': 0, 'y': 0, 'z': 0},
              'coordinate': {'latitude': latitude[0], 'longitude': longitude[0], 'altitude': altitude[0]}},
        'D': {'position': {'x': 0, 'y': 0, 'z': 0},
              'coordinate': {'latitude': latitude[1], 'longitude': longitude[1], 'altitude': altitude[1]}},
    }

    for point in runways_db[airport_ocai][rway]:
        runways_db[airport_ocai][rway][point]['position']['x'], \
        runways_db[airport_ocai][rway][point]['position']['y'], \
        runways_db[airport_ocai][rway][point]['position']['z'] = llh2ecef(
            runways_db[airport_ocai][rway][point]['coordinate']['latitude'],
            runways_db[airport_ocai][rway][point]['coordinate']['longitude'],
            runways_db[airport_ocai][rway][point]['coordinate']['altitude'])

    if len(runways) > 1:
        # Treat the opposite runway if needed
        rway = runways[1]
        runways_db[airport_ocai][rway] = {
            'A': {'position': {'x': 0, 'y': 0, 'z': 0},
                  'coordinate': {'latitude': latitude[0], 'longitude': longitude[0], 'altitude': altitude[0]}},
            'B': {'position': {'x': 0, 'y': 0, 'z': 0},
                  'coordinate': {'latitude': latitude[1], 'longitude': longitude[1], 'altitude': altitude[1]}},
            'C': {'position': {'x': 0, 'y': 0, 'z': 0},
                  'coordinate': {'latitude': latitude[2], 'longitude': longitude[2], 'altitude': altitude[2]}},
            'D': {'position': {'x': 0, 'y': 0, 'z': 0},
                  'coordinate': {'latitude': latitude[3], 'longitude': longitude[3], 'altitude': altitude[3]}},
        }
        for point in runways_db[airport_ocai][rway]:
            runways_db[airport_ocai][rway][point]['position']['x'], \
            runways_db[airport_ocai][rway][point]['position']['y'], \
            runways_db[airport_ocai][rway][point]['position']['z'] = llh2ecef(
                runways_db[airport_ocai][rway][point]['coordinate']['latitude'],
                runways_db[airport_ocai][rway][point]['coordinate']['longitude'],
                runways_db[airport_ocai][rway][point]['coordinate']['altitude'])

    with open(database_file, 'w') as f:
        json.dump(runways_db, f, indent=4)

def update_runways_altitudes(airport_ocai, runway_str, altitudes, database_file):
    """
    Update the altitudes of specified runways in pairs, re-computing position (ECEF) for points A/B/C/D.
    
    For each pair (rwy1, rwy2) in runway_str:
      - rwy1: C & D => alt1, A & B => alt2
      - rwy2 (opposite of rwy1): C & D => alt2, A & B => alt1

    Example:
        airport = "EDDK"
        runways_to_update = "6,24,14L,32R"
        new_altitudes = [67,80,72,89]
      Means:
        (6,24) => alt1=67, alt2=80
          - runway 6:   C&D=67, A&B=80
          - runway 24:  C&D=80, A&B=67
        (14L,32R) => alt1=72, alt2=89
          - runway 14L: C&D=72, A&B=89
          - runway 32R: C&D=89, A&B=72

    :param airport_ocai: Airport code to update (e.g. 'EDDK')
    :param runway_str: A comma-separated string of runway IDs (e.g. '6,24,14L,32R')
    :param altitudes: A list of altitudes (floats/ints) in the same length & pairing as runway_str
    :param database_file: Path to the JSON database file
    """
    if not os.path.exists(database_file):
        raise FileNotFoundError(f"Database file '{database_file}' not found.")

    with open(database_file, 'r') as f:
        runways_db = json.load(f)

    if airport_ocai not in runways_db:
        print(f"Airport '{airport_ocai}' not found in the database.")
        return

    runway_list = [r.strip() for r in runway_str.split(',')]
    
    # We expect runway_list and altitudes to come in pairs.
    # ex: runway_list = [rwy1, rwy2, rwy3, rwy4], altitudes = [alt1, alt2, alt3, alt4]
    # Where rwy1 and rwy2 are paired, and rwy3 and rwy4 are paired.
    if len(runway_list) % 2 != 0:
        print("Error: The number of runway IDs must be even.")
        return
    if len(altitudes) % 2 != 0:
        print("Error: The number of altitudes must be even.")
        return
    if len(runway_list) != len(altitudes):
        print("Error: The number of runways does not match the number of altitudes provided.")
        return

    # Process runways in pairs
    for i in range(0, len(runway_list), 2):
        rwy1 = runway_list[i]
        rwy2 = runway_list[i + 1]
        alt1 = altitudes[i]
        alt2 = altitudes[i + 1]

        # Runway 1 => C&D = alt1, A&B = alt2
        if rwy1 in runways_db[airport_ocai]:
            for point_id in ['C', 'D']:
                prev_alt = runways_db[airport_ocai][rwy1][point_id]['coordinate']['altitude']
                runways_db[airport_ocai][rwy1][point_id]['coordinate']['altitude'] = alt1
                if point_id == 'C':
                    print(f"Correction for runway {rwy1} point {point_id}: {prev_alt} -> {alt1}\t\t\t\t({alt1 - prev_alt} m )")
                lat = runways_db[airport_ocai][rwy1][point_id]['coordinate']['latitude']
                lon = runways_db[airport_ocai][rwy1][point_id]['coordinate']['longitude']
                x, y, z = llh2ecef(lat, lon, alt1)
                runways_db[airport_ocai][rwy1][point_id]['position']['x'] = x
                runways_db[airport_ocai][rwy1][point_id]['position']['y'] = y
                runways_db[airport_ocai][rwy1][point_id]['position']['z'] = z
            for point_id in ['A', 'B']:
                runways_db[airport_ocai][rwy1][point_id]['coordinate']['altitude'] = alt2
                lat = runways_db[airport_ocai][rwy1][point_id]['coordinate']['latitude']
                lon = runways_db[airport_ocai][rwy1][point_id]['coordinate']['longitude']
                x, y, z = llh2ecef(lat, lon, alt2)
                runways_db[airport_ocai][rwy1][point_id]['position']['x'] = x
                runways_db[airport_ocai][rwy1][point_id]['position']['y'] = y
                runways_db[airport_ocai][rwy1][point_id]['position']['z'] = z
        else:
            print(f"Warning: Runway '{rwy1}' not found in {airport_ocai}. Skipping updates for it.")
        
        # Runway 2 (opposite) => C&D = alt2, A&B = alt1
        if rwy2 in runways_db[airport_ocai]:
            for point_id in ['C', 'D']:
                prev_alt = runways_db[airport_ocai][rwy2][point_id]['coordinate']['altitude']
                runways_db[airport_ocai][rwy2][point_id]['coordinate']['altitude'] = alt2
                if point_id == 'C':
                    print(f"Correction for runway {rwy2} point {point_id}: {prev_alt} -> {alt2}\t\t\t\t({alt2 - prev_alt} m )")
                lat = runways_db[airport_ocai][rwy2][point_id]['coordinate']['latitude']
                lon = runways_db[airport_ocai][rwy2][point_id]['coordinate']['longitude']
                x, y, z = llh2ecef(lat, lon, alt2)
                runways_db[airport_ocai][rwy2][point_id]['position']['x'] = x
                runways_db[airport_ocai][rwy2][point_id]['position']['y'] = y
                runways_db[airport_ocai][rwy2][point_id]['position']['z'] = z
            for point_id in ['A', 'B']:
                runways_db[airport_ocai][rwy2][point_id]['coordinate']['altitude'] = alt1
                lat = runways_db[airport_ocai][rwy2][point_id]['coordinate']['latitude']
                lon = runways_db[airport_ocai][rwy2][point_id]['coordinate']['longitude']
                x, y, z = llh2ecef(lat, lon, alt1)
                runways_db[airport_ocai][rwy2][point_id]['position']['x'] = x
                runways_db[airport_ocai][rwy2][point_id]['position']['y'] = y
                runways_db[airport_ocai][rwy2][point_id]['position']['z'] = z
        else:
            print(f"Warning: Runway '{rwy2}' not found in {airport_ocai}. Skipping updates for it.")
    
    # Write the updated data back to the file
    with open(database_file, 'w') as f:
        json.dump(runways_db, f, indent=4)
        
def update_xyz(database_file: str, output_database_file=""):
    """Update the xyz field in the database"""
    if output_database_file == "":
        output_database_file = database_file

    print(f"Treating xyz of database file '{database_file}'.")
    with open(database_file, 'r') as f:
        runways_db = json.load(f)

    for airport_ocai in runways_db.keys():
        print(f"Treating airport {airport_ocai} with {len(runways_db[airport_ocai])} runways.")
        for runway_id in runways_db[airport_ocai].keys():
            for point in runways_db[airport_ocai][runway_id]:
                runways_db[airport_ocai][runway_id][point]['position']['x'], \
                runways_db[airport_ocai][runway_id][point]['position']['y'], \
                runways_db[airport_ocai][runway_id][point]['position']['z'] = llh2ecef(
                    runways_db[airport_ocai][runway_id][point]['coordinate']['latitude'],
                    runways_db[airport_ocai][runway_id][point]['coordinate']['longitude'],
                    runways_db[airport_ocai][runway_id][point]['coordinate']['altitude'])

    with open(database_file, 'w') as f:
        json.dump(runways_db, f, indent=4)


def get_runways_list(airport_oaci, database_file):
    """
    Return a comma-separated string of all runway IDs for the given airport in the DB.
    
    :param airport_ocai: Airport code (e.g. 'KATL')
    :param database_file: Path to the JSON database file
    :return: String of runway IDs separated by commas (e.g. '8R,26L')
    """
    if not os.path.exists(database_file):
        raise FileNotFoundError(f"Database file '{database_file}' not found.")
    
    with open(database_file, 'r') as f:
        runways_db = json.load(f)
    
    if airport_oaci not in runways_db:
        return f"None (Airport {airport_oaci} not found in DB)"
    
    runway_list = list(runways_db[airport_oaci].keys())
    return ",".join(runway_list)

def get_runway_points(database_file: str, airport_oaci: str, runway_id: str):
    """
    
    Return the points around the runway (4 corners, ltp and fpap)
    
    :param database_file: file containing coordinates of the runways
    :type database_file: str
    :param airport_oaci: code of the airport
    :type airport_oaci: str
    :param runway_id: code of the runway
    """
    with open(database_file, 'r') as f:
        runways_database = json.load(f)
    runway_points = runways_database[airport_oaci][runway_id]
    _, ltp = find_center(
        [list(runway_points['C']['position'].values()), list(runway_points['D']['position'].values())])
    _, fpap = find_center(
        [list(runway_points['A']['position'].values()), list(runway_points['B']['position'].values())])
    return runway_points, ltp, fpap


def compute_aiming_point(database_file: str, airport_ocai: str, runway_id: str, dist_m: float):
    """
        
    get the aiming point on the runway at a distance 'dist' from the LTP
    
    :param database_file: file containing coordinates of the runways
    :type database_file: str
    :param airport_ocai: code of the airport
    :type airport_ocai: str
    :param runway_id: code of the runway
    :type runway_id: str
    :param dist_m: distance of the aiming point from the LTP
    :type dist_m: float        
    """
    _, ltp, fpap = get_runway_points(database_file, airport_ocai, runway_id)

    # centerline_vector = (np.array(ltp) - np.array(fpap)) / np.linalg.norm(np.array(ltp) - np.array(fpap))
    ltp_lat, ltp_long, _ = ecef2llh(ltp[0], ltp[1], ltp[2])
    fpap_lat, fpap_long, _ = ecef2llh(fpap[0], fpap[1], fpap[2])
    rwy_psi = find_azimuth_between_2_coordinates(ltp_long, ltp_lat, fpap_long, fpap_lat) # (forward azimuth, back azimuth, distance between points)
    # compute aiming point
    ap_long, ap_lat, _ = forward_pos(ltp_long, ltp_lat, rwy_psi[0], dist_m)  # (longitude, latitude, azimuth)

    return ap_long, ap_lat, rwy_psi, ltp, fpap


def generate_dist(min, max, sample_number, distribution: str, par_distrib1=0):
    """
    generate the distances from the runway
    
    - uniform: uniform between min and max distances
    - exp: uniform(0,1)**par_distrib1 then reshape to [min, max] par_distrib <1 -> more images far from the runway
                                                               par_distrib >1 -> more images near the runway
    - normal: normal distribution troncated to have the maximum of the distribution at 1
    - linear: evenly spaced points between [min_val, max_val] 
    """

    assert distribution in ['uniform', 'exp', 'normal', 'linear'], \
        f"distribution must be one of ['uniform', 'exp', 'normal', 'linear']"
    if distribution == 'uniform':
        dh_m = np.random.uniform(0., 1., (sample_number,)) * (max - min) + min
    elif distribution == 'exp':  # here the user will fill the par_distrib1 parameter
        dh_m = np.random.uniform(0., 1., (sample_number,)) ** par_distrib1 * (max - min) + min
    elif distribution == 'normal':
        dh_m = np.random.normal(0, 1, sample_number)
        # get only the negative values
        for i in range(sample_number):
            if dh_m[i] > 0:
                dh_m[i] = -dh_m[i]
        # reshape (-inf, 0) to (min, max) (in reality we just take the values below -10 and put it at 10)
        # then we reshape (-10,0) to (min, max)
        for i in range(sample_number):
            if dh_m[i] < -10:
                dh_m[i] = -10
        dh_m = dh_m / 10
        dh_m = dh_m * (max - min) + min
    elif distribution == 'linear':
        dh_m = np.linspace(min, max, num=sample_number)
    return dh_m


def generate_distri_based_samples(
        distribution_type: str,
        sample_size: int,
        mean: float,
        std_dev: float,
        lower: float,
        upper: float
) -> np.ndarray:
    """
    Generate an array of `sample_size` angles based on the specified distribution
    """
    if distribution_type == 'normal':
        # Normal distribution around mean ± std_dev
        return np.random.normal(mean, std_dev, sample_size)

    elif distribution_type == 'uniform':
        # if not lower or not upper:
        #     raise ValueError(f"uniform distribution requested, but lower or upper bound is missing. Provide bounds like alpha_h_min or max, yaw_min or max, roll_min or max, etc.")
        # Uniform distribution in [lower, upper]
        return np.random.uniform(lower, upper, sample_size)

    else:
        raise ValueError(f"Unknown distribution_type: {distribution_type}")

def define_offset(
        aiming_point,
        rwy_psi,
        ltp,
        fpap,
        traj
):
    """

    distribution,

    alpha_v_deg: float = -3,
    std_alpha_v_deg: float = 0.2,
    alpha_h_deg: float = 0.,
    std_alpha_h_deg: float = 2.,
    min_distance_m: float = 150.,
    max_distance_m: float = 10000.,
    roll_deg: float = 0.,
    std_roll_deg: float = 5.,
    pitch_deg: float = -4.,
    std_pitch_deg: float = 2.,
    std_yaw_deg: float = 5.,
    sample_number: int = 1000,
    par_distrib1=0,
    return all the camera positions and angle with the deviations
    we get more footage when close to the aiming point with the exp(sqrt(2))
    
    """
    ap_long = aiming_point[0]
    ap_lat = aiming_point[1]
    ltp_lat, ltp_lon, ltp_alt = ecef2llh(ltp[0], ltp[1], ltp[2])
    
    dh_m = generate_dist(traj.min_distance_m, traj.max_distance_m, traj.sample_number, traj.distribution, traj.distrib_param)
    dh_m = np.sort(dh_m)[::-1]
    # dh_m += traj.dist_ap_m # add Move the distances origins from Aiming Point to LTP
    # angles are generated from the dh_m

    dav_deg = generate_distri_based_samples(
        distribution_type=traj.alpha_v_distrib,
        sample_size=traj.sample_number,
        mean=traj.alpha_v_deg,
        std_dev=traj.std_alpha_v_deg,
        lower=traj.alpha_v_min,
        upper=traj.alpha_v_max
    )
    
    dz_m = -np.tan(np.deg2rad(dav_deg)) * (dh_m + 305) # vertical angle origin starting from aiming point instead of LTP
    
    dah_deg = generate_distri_based_samples(
        distribution_type=traj.alpha_h_distrib,
        sample_size=traj.sample_number,
        mean=traj.alpha_h_deg,
        std_dev=traj.std_alpha_h_deg,
        lower=traj.alpha_h_min,
        upper=traj.alpha_h_max
    )
    
    phi_deg = generate_distri_based_samples( # PLANE ROLL
        distribution_type=traj.roll_distrib,
        sample_size=traj.sample_number,
        mean=traj.roll_deg,
        std_dev=traj.std_roll_deg,
        lower=traj.roll_min,
        upper=traj.roll_max
    )
    
    theta_deg = generate_distri_based_samples( # PLANE PITCH
        distribution_type=traj.pitch_distrib,
        sample_size=traj.sample_number,
        mean=traj.pitch_deg,
        std_dev=traj.std_pitch_deg,
        lower=traj.pitch_min,
        upper=traj.pitch_max
    )
    
    psi_deg = generate_distri_based_samples( # PLANE YAW
        distribution_type=traj.yaw_distrib,
        sample_size=traj.sample_number,
        mean=traj.yaw_deg,
        std_dev=traj.std_yaw_deg,
        lower=traj.yaw_min,
        upper=traj.yaw_max
    )
    g = pyproj.Geod(ellps='WGS84')
    lon_deg, lat_deg, _ = g.fwd(
        ltp_lon * np.ones(traj.sample_number),
        ltp_lat * np.ones(traj.sample_number),
        rwy_psi[1] + dah_deg,
        dh_m,
        radians=False
    )
    alt_m = ltp_alt + dz_m

    return dh_m, dav_deg, dz_m, dah_deg, phi_deg, theta_deg, psi_deg, lon_deg, lat_deg, alt_m


class GEODataset(object):

    def __init__(self, loc_path: Union[str, pathlib.Path] = None, name: str = None):
        self.loc_path = pathlib.Path(loc_path)
        self.name = name if name else self.loc_path.name
        self.data = None
        self.size = None
        self.width = None
        self.height = None
        self.images_list = []

        self.labels = {}

    def load_data(self):
        """
        Extract the frame parameters which are in a json file generated by GoogleEarth Studio.

        Frame information:
            "cameraFrames":[
                { "position": {"x": ... , "y": ... , "z": ...}
                  "rotation": {"x": ... , "y": ... , "z": ...}
                  "coordinate": {"latitude": ... , "longitude": ... , "altitude": ... }
                  "fovVertical":
                },
                { "position": ....
                },
                ...
            ]
        :return: None

        """

        if self.loc_path is not None:
            with open(self.loc_path) as f:
                self.data = json.load(f)

            self.width = self.data['width']  # Camera sensor size (pixel number)
            self.height = self.data['height']  # Camera sensor size (pixel number)
            self.size = self.data["numFrames"] + 1

    # content of each attribute of this GEODataset
    def show(self):
        print(f"Name: {self.name}")
        print(f"Location: {self.loc_path}")
        print(f"Width: {self.width}")
        print(f"Height: {self.height}")
        print(f"Size: {self.size}")
        ##Complete with the image list
        for i in range(self.size):
            print(f"Frame {i} : {self.data['cameraFrames'][i]}")
        
    
    @staticmethod
    def generate_landing_poses(
            runway_db,
            airport: str,
            runway: str,
            trajectory: DefaultTrajectory):
        """

        distribution: str = 'exp',
        distrib_param: float = math.sqrt(2),
        alpha_v_deg: float = -3,
        std_alpha_v_deg: float = 0.2,
        alpha_h_deg: float = 0.,
        std_alpha_h_deg: float = 2.,
        min_distance_m: float = 150.,
        max_distance_m: float = 10000.,
        roll_deg: float = 0.,
        std_roll_deg: float = 5.,
        pitch_deg: float = -4.,
        std_pitch_deg: float = 2.,
        std_yaw_deg: float = 5.,
        sample_number: int = 1000,
        dist_ap_m: float = 300.):

        Take a trajectory config and return a flight plan (ie. all the camera positions and 
        rotations according to the config file)

        :param airport: code of the airport
        :type airport: str
        
        :param runway: code of the runway
        :type runway: str
        
        :param alpha_v_deg: vertical angle. Defaults to -3.
        :type alpha_v_deg: float, optional
        
        :param std_alpha_v_deg: standard deviation of alpha_v. Defaults to 0.2.
        :type std_alpha_v_deg: float, optional  
        
        :param alpha_h_deg: horizontal angle. Defaults to 0..
        :type alpha_h_deg: float, optional
        
        :param std_alpha_h_deg: standard deviation of alpha_h. Defaults to 2..
        :type std_alpha_h_deg: float, optional
        
        :param min_distance_m: minimal distance from the runway in meters. Defaults to 150..
        :type min_distance_m: float, optional
        
        :param max_distance_m:  maximal distance from the runway in meters. Defaults to 10000..
        :type max_distance_m: float, optional
        
        :param roll_deg: roll angle. Defaults to 0..
        :type roll_deg: float, optional
        
        :param std_roll_deg: standard deviation of roll angle. Defaults to 5..
        :type std_roll_deg: float, optional
        
        :param pitch_deg:  pitch angle. Defaults to -4..
        :type pitch_deg: float, optional
        
        :param std_pitch_deg: standard deviation of the pitch angle. Defaults to 2.
        :type std_pitch_deg: float, optional
        
        :param std_yaw_deg:  standard deviation of the yaw angle. Defaults to 5.
        :type std_yaw_deg: float, optional
        
        :param sample_number:  number of footages. Defaults to 1000.
        :type sample_number: int, optional
        
        :param plot_scatter: Defaults to True.
        :type plot_scatter: bool, optional
        
        :return: The flight plan(ie positions and camera angles)
        """
        # get runway points
        ap_long, ap_lat, rwy_psi, ltp, fpap = compute_aiming_point(runway_db, airport, runway, trajectory.dist_ap_m)

        # Here, we define all the positions of the camera
        _, _, _, _, phi_deg, theta_deg, psi_deg, lon_deg, lat_deg, alt_m = define_offset(
            [ap_long, ap_lat],
            rwy_psi,
            ltp,
            fpap,
            trajectory
        )

        # We put all the camera positions into the flight_data list
        flight_data = list(
            zip(
                lon_deg.tolist(),  #
                lat_deg.tolist(),  # camera coordinates
                alt_m.tolist(),  #
                (rwy_psi[0] + psi_deg).tolist(),  # back azimuth angle + yaw angle
                (90 + theta_deg).tolist(),  # pitch deg
                phi_deg.tolist()  # roll deg
            )
        )   
        return flight_data

    def create_scenario(self, flight_data, fov_vertical=30,
                        fov_horizontal=None,
                        width=3840, height=2160, nb_frames=100, fps=25,
                        times=None, export_metadata=False):
        """
        
        Take the flight_plan generated by generate_landing_poses() to convert it into a esp format file

        """

        with open(os.path.join('data', 'template.json'), 'r') as f:
            scenario = json.load(f)

        scenario['settings']['frameRate'] = fps
        scenario['settings']['dimensions']['width'] = width
        scenario['settings']['dimensions']['height'] = height

        scenario['settings']['metadata_index'] = {'keyframes': []}

        scenario['scenes'][0]['attributes'][0]['attributes'][0]['attributes'][0]['attributes'][0][
            'keyframes'] = []  # longitude
        scenario['scenes'][0]['attributes'][0]['attributes'][0]['attributes'][0]['attributes'][1][
            'keyframes'] = []  # latitude
        scenario['scenes'][0]['attributes'][0]['attributes'][0]['attributes'][0]['attributes'][2][
            'keyframes'] = []  # altitude

        scenario['scenes'][0]['attributes'][0]['attributes'][1]['attributes'][0]['keyframes'] = []  # yaw
        scenario['scenes'][0]['attributes'][0]['attributes'][1]['attributes'][1]['keyframes'] = []  # pitch
        scenario['scenes'][0]['attributes'][0]['attributes'][1]['attributes'][2]['keyframes'] = []  # roll

        scenario['scenes'][0]['attributes'][0]['attributes'][2]['attributes'][0]['keyframes'] = []  # lens

        scenario['scenes'][0]['attributes'][1]['attributes'][1]['keyframes'] = []  # time
        scenario['scenes'][0]['attributes'][1]['attributes'][2]['keyframes'] = []  # cloud
        scenario['scenes'][0]['attributes'][1]['attributes'][4]['keyframes'] = []  # buildings

        scenario['scenes'][0]['duration'] = nb_frames - 1
        scenario['settings']['duration'] = nb_frames - 1
        scenario['playbackManager']['range']['end'] = scenario['settings']['duration']

        # if fov_horizontal:
        #     fov_vertical = fov_horizontal * height / width
        # else:
        # if not fov_horizontal:
        #     fov_horizontal = fov_vertical * width / height

        if export_metadata:
            metadata = pd.DataFrame()
        else:
            metadata = None

        index = 0
        tf = TimezoneFinder()
        for i in range(len(flight_data)):

            row = flight_data[i]
            time = times[i]

            year = time['year']
            month = time['month']
            day = time['day']
            minute = time['minute']
            second = time['second']
            myhour = time['hour']

            tz = tf.timezone_at(lng=row[0], lat=row[1])
            timezone = pytz.timezone(tz)

            dt = datetime(year, month, day, myhour, minute, second)
            dt = timezone.localize(dt)
            date_time = int(dt.timestamp()) * 1000

            # date_time = int(datetime(year, month, day, myhour, minute, second).timestamp()) * 1000
            date_time_max = scenario['scenes'][0]['attributes'][1]['attributes'][1]['value']['maxValueRange'] = int(
                datetime(year, 12, 31, 23, 59, 59).timestamp()) * 1000
            date_time_min = scenario['scenes'][0]['attributes'][1]['attributes'][1]['value']['minValueRange'] = int(
                datetime(year, 1, 1, 0, 0, 0).timestamp()) * 1000
            date_time = (date_time - date_time_min) / (date_time_max - date_time_min)

            longitude = (row[0] -
                         scenario['scenes'][0]['attributes'][0]['attributes'][0]['attributes'][0]['attributes'][0][
                             'value']['minValueRange']) / \
                        (scenario['scenes'][0]['attributes'][0]['attributes'][0]['attributes'][0]['attributes'][0][
                             'value']['maxValueRange'] -
                         scenario['scenes'][0]['attributes'][0]['attributes'][0]['attributes'][0]['attributes'][0][
                             'value']['minValueRange'])
            latitude = (row[1] -
                        scenario['scenes'][0]['attributes'][0]['attributes'][0]['attributes'][0]['attributes'][1][
                            'value']['minValueRange']) / \
                       (scenario['scenes'][0]['attributes'][0]['attributes'][0]['attributes'][0]['attributes'][1][
                            'value']['maxValueRange'] -
                        scenario['scenes'][0]['attributes'][0]['attributes'][0]['attributes'][0]['attributes'][1][
                            'value']['minValueRange'])
            altitude = (row[2] -
                        scenario['scenes'][0]['attributes'][0]['attributes'][0]['attributes'][0]['attributes'][2][
                            'value']['minValueRange']) \
                       / (scenario['scenes'][0]['attributes'][0]['attributes'][0]['attributes'][0]['attributes'][2][
                              'value']['maxValueRange'] -
                          scenario['scenes'][0]['attributes'][0]['attributes'][0]['attributes'][0]['attributes'][2][
                              'value']['minValueRange'])

            yaw = (row[3] -
                   scenario['scenes'][0]['attributes'][0]['attributes'][1]['attributes'][0]['value']['minValueRange']) / (scenario['scenes'][0]['attributes'][0]['attributes'][1]['attributes'][0]['value'][
                       'maxValueRange'] - scenario['scenes'][0]['attributes'][0]['attributes'][1]['attributes'][0]['value'][
                       'minValueRange'])
            if yaw<0:
                yaw += 1 # TODO: A verifier
            if yaw>1:
                yaw -= 1
            pitch = (row[4] -
                     scenario['scenes'][0]['attributes'][0]['attributes'][1]['attributes'][1]['value'][
                         'minValueRange']) / \
                    (scenario['scenes'][0]['attributes'][0]['attributes'][1]['attributes'][1]['value'][
                         'maxValueRange'] -
                     scenario['scenes'][0]['attributes'][0]['attributes'][1]['attributes'][1]['value'][
                         'minValueRange'])
            roll = (row[5] -
                    scenario['scenes'][0]['attributes'][0]['attributes'][1]['attributes'][2]['value'][
                        'minValueRange']) / \
                   (scenario['scenes'][0]['attributes'][0]['attributes'][1]['attributes'][2]['value'][
                        'maxValueRange'] -
                    scenario['scenes'][0]['attributes'][0]['attributes'][1]['attributes'][2]['value'][
                        'minValueRange'])

            fov = (fov_vertical - scenario['scenes'][0]['attributes'][0]['attributes'][2]['attributes'][0]['value'][
                'minValueRange']) / (
                          scenario['scenes'][0]['attributes'][0]['attributes'][2]['attributes'][0]['value'][
                              'maxValueRange'] -
                          scenario['scenes'][0]['attributes'][0]['attributes'][2]['attributes'][0]['value'][
                              'minValueRange'])

            scenario['scenes'][0]['attributes'][0]['attributes'][0]['attributes'][0]['attributes'][0][
                'keyframes'].append({'time': index / (len(flight_data) - 1), 'value': longitude})  # longitude
            scenario['scenes'][0]['attributes'][0]['attributes'][0]['attributes'][0]['attributes'][1][
                'keyframes'].append({'time': index / (len(flight_data) - 1), 'value': latitude})  # latitude
            scenario['scenes'][0]['attributes'][0]['attributes'][0]['attributes'][0]['attributes'][2][
                'keyframes'].append({'time': index / (len(flight_data) - 1), 'value': altitude})  # altitude

            scenario['scenes'][0]['attributes'][0]['attributes'][1]['attributes'][0]['keyframes'].append(
                {'time': index / (len(flight_data) - 1), 'value': yaw})  # yaw
            scenario['scenes'][0]['attributes'][0]['attributes'][1]['attributes'][1]['keyframes'].append(
                {'time': index / (len(flight_data) - 1), 'value': pitch})  # pitch
            scenario['scenes'][0]['attributes'][0]['attributes'][1]['attributes'][2]['keyframes'].append(
                {'time': index / (len(flight_data) - 1), 'value': roll})  # roll

            scenario['scenes'][0]['attributes'][0]['attributes'][2]['attributes'][0]['keyframes'].append(
                {'time': index / (len(flight_data) - 1), 'value': fov})  # fov

            scenario['scenes'][0]['attributes'][1]['attributes'][1]['keyframes'].append(
                {'time': index / (len(flight_data) - 1), 'value': date_time})  # time
            scenario['scenes'][0]['attributes'][1]['attributes'][2]['keyframes'].append(
                {'time': index / (len(flight_data) - 1), 'value': 1, 'transitionIn': {'type': 'step'},
                 'transitionOut': {'type': 'step'},
                 'transitionLinked': False})  # cloud

            scenario['scenes'][0]['attributes'][1]['attributes'][4]['keyframes'].append(
                {'time': index / (len(flight_data) - 1), 'value': 1})  # buildings

            scenario['settings']['metadata_index']['keyframes'].append(
                {'time': index / (len(flight_data) - 1), 'value': i})  # actual GMTs and flight data file index
            index += 1

            if export_metadata:
                metadata = metadata.append(row)

        return scenario, metadata

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

from src.ges.geo_utils import find_center, ecef2llh, llh2ecef, find_azimuth_between_2_coordinates, forward_pos
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
    rwy_psi = find_azimuth_between_2_coordinates(ltp_long, ltp_lat, fpap_long,
                                                 fpap_lat)  # (forward azimuth, back azimuth, distance between points)
    # compute aiming point
    ap_long, ap_lat, _ = forward_pos(ltp_long, ltp_lat, rwy_psi[0], dist_m)  # (longitude, latitude, azimuth)

    return ap_long, ap_lat, rwy_psi, ltp, fpap


def generate_dist(min, max, sample_number, distribution: str, par_distrib1=0):
    """
    generate the distances from the runway
    
    uniform: uniform between min and max distances
    exp: uniform(0,1)**par_distrib1 then reshape to [min, max] par_distrib <1 -> more images far from the runway
                                                               par_distrib >1 -> more images near the runway
    normal: normal distribution troncated to have the maximum of the distribution at 1
    """

    assert distribution in ['uniform', 'exp', 'normal']
    if distribution == 'uniform':
        dh_m = np.random.uniform(0., 1., (sample_number,)) * (max - min) + min

    if distribution == 'exp':  # here the user will fill the par_distrib1 parameter
        dh_m = np.random.uniform(0., 1., (sample_number,)) ** par_distrib1 * (max - min) + min

    if distribution == 'normal':
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

    return dh_m


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
    _, _, ltp_alt = ecef2llh(ltp[0], ltp[1], ltp[2])
    # fpap_lat, fpap_long, fpap_alt = ecef2llh(fpap[0], fpap[1], fpap[2])
    dh_m = generate_dist(traj.min_distance_m, traj.max_distance_m, traj.sample_number, traj.distribution, traj.distrib_param)
    dh_m = np.sort(dh_m)[::-1]
    # print(std_roll_deg)
    dav_deg = np.random.normal(traj.alpha_v_deg, traj.std_alpha_v_deg, (traj.sample_number,))
    dz_m = -np.tan(np.deg2rad(dav_deg)) * dh_m
    dah_deg = np.random.normal(traj.alpha_h_deg, traj.std_alpha_h_deg, (traj.sample_number,))
    phi_deg = np.random.normal(traj.roll_deg, traj.std_roll_deg, (traj.sample_number,))
    theta_deg = np.random.normal(traj.pitch_deg, traj.std_pitch_deg, (traj.sample_number,))
    psi_deg = np.random.normal(0., traj.std_yaw_deg, (traj.sample_number,))
    g = pyproj.Geod(ellps='WGS84')
    lon_deg, lat_deg, _ = g.fwd(
        ap_long * np.ones(traj.sample_number),
        ap_lat * np.ones(traj.sample_number),
        rwy_psi[1] + dah_deg,
        dh_m,
        radians=False
    )
    alt_m = ltp_alt + dz_m

    return dh_m, dav_deg, dz_m, dah_deg, phi_deg, theta_deg, psi_deg, lon_deg, lat_deg, alt_m


class GESDataset(object):

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

    @staticmethod
    def generate_landing_poses(
            runaway_db,
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
        ap_long, ap_lat, rwy_psi, ltp, fpap = compute_aiming_point(runaway_db, airport, runway, trajectory.dist_ap_m)
        # define offsets

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
                        fov_horizontal=30,
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
                   scenario['scenes'][0]['attributes'][0]['attributes'][1]['attributes'][0]['value'][
                       'minValueRange']) / \
                  (scenario['scenes'][0]['attributes'][0]['attributes'][1]['attributes'][0]['value'][
                       'maxValueRange'] -
                   scenario['scenes'][0]['attributes'][0]['attributes'][1]['attributes'][0]['value'][
                       'minValueRange'])
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

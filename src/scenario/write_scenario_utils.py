import pathlib
import json
import random
import uuid
from src.geo.geo_dataset import GEODataset
from src.scenario.default_scenario_values import ScenarioContent, DefaultTrajectory
import yaml

def load_trajectory_from_yaml(yaml_data):
    trajectory = DefaultTrajectory()
    for key, value in yaml_data.items():
        setattr(trajectory, key, value)
    return trajectory

def initialize_dataset(dataset_path: pathlib.Path) -> GEODataset:
    """ 
    Returns an instance of GEODataset with the config.yaml parameters in it
    
    """
    return GEODataset(dataset_path)


def load_runways_database(runways_database_path):
    """ 
    load the runways database
    
    """
    with open(runways_database_path, 'r') as f:
        runways = json.load(f)
    return runways


def generate_poses(runway_db, scenario: ScenarioContent, d: GEODataset, use_ODD=False):
    """
    Generate all the camera poses with the config c and the GEODataset d
    """
    time = scenario.time
    for airport, runways in scenario.airports_runways.items():
        for runway in runways:
            if not use_ODD:
                poses = d.generate_landing_poses(runway_db,
                                                airport,
                                                runway,
                                                scenario.trajectory)
                for p in poses:
                    scenario.poses.append({
                        'uuid': str(uuid.uuid4()),
                        'airport': airport,
                        'runway': runway,
                        'pose': list(p),  # list of flight data
                        'time': {
                            'second': random.randint(time.second_min, time.second_max),
                            'minute': random.randint(time.minute_min, time.minute_max),
                            'hour': random.randint(time.hour_min, time.hour_max),
                            'day': random.randint(time.day_min, time.day_max),
                            'month': random.randint(time.month_min, time.month_max),
                            'year': random.randint(time.year_min, time.year_max),
                        }
                    })
            else:
                ## Boucler sur les 3 odds du fichier yaml et append les poses
                
                with open('data/Lard_v2_Default_ODD.yaml', 'r') as file:
                    trajectories_yaml = yaml.safe_load(file)

                trajectories = {
                    'ODD_Far': load_trajectory_from_yaml(trajectories_yaml['ODD_Far']),
                    'ODD_Medium': load_trajectory_from_yaml(trajectories_yaml['ODD_Medium']),
                    'ODD_Close': load_trajectory_from_yaml(trajectories_yaml['ODD_Close']),
                }

                for name, trajectory in trajectories.items():
                    poses = d.generate_landing_poses(runway_db, airport, runway, trajectory)
                    for p in poses:
                        scenario.poses.append({
                            'uuid': str(uuid.uuid4()),
                            'airport': airport,
                            'runway': runway,
                            'pose': list(p),  # list of flight data
                            'time': {
                                'second': random.randint(time.second_min, time.second_max),
                                'minute': random.randint(time.minute_min, time.minute_max),
                                'hour': random.randint(time.hour_min, time.hour_max),
                                'day': random.randint(time.day_min, time.day_max),
                                'month': random.randint(time.month_min, time.month_max),
                                'year': random.randint(time.year_min, time.year_max),
                            }
                        })



# OBSOLETE : Previous single runway-airport version
# def generate_poses(runway_db, scenario: ScenarioContent, d: GEODataset):
#     """
#     generate all the camera poses with the config c and the GEODataset d

#     """
#     time = scenario.time
#     for runway in scenario.runways:
#         poses = d.generate_landing_poses(runway_db,
#                                          scenario.airport,
#                                          runway,
#                                          scenario.trajectory)
#         for p in poses:
#             scenario.poses.append({
#                 # 'airport': scenario.airport,
#                 # 'runway': runway,
#                 'pose': list(p),  # list of flight data
#                 'time': {
#                     'year': random.randint(time.year_min, time.year_max),
#                     'month': random.randint(time.month_min, time.month_max),
#                     'day': random.randint(time.day_min, time.day_max),
#                     'hour': random.randint(time.hour_min, time.hour_max),
#                     'minute': random.randint(time.minute_min, time.minute_max),
#                     'second': random.randint(time.second_min, time.second_max),
#                 }
#             })


def generate_scenario(image_width, poses, times, fov_x, fov_y, height, d: GEODataset):
    """ 
    generate the scenario (format for GES)
    
    """
    scenario, _ = d.create_scenario(
        flight_data=poses,
        nb_frames=len(poses),
        fov_vertical=fov_x,
        fov_horizontal=fov_y,
        width=image_width,
        height=height,
        times=times
    )
    return scenario

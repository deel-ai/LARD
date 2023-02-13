import pathlib
import json
import random
from src.ges.ges_dataset import GESDataset
from src.scenario.default_scenario_values import ScenarioContent


def initialize_dataset(dataset_path: pathlib.Path) -> GESDataset:
    """ 
    Returns an instance of GESDataset with the config.yaml parameters in it
    
    """
    return GESDataset(dataset_path)


def load_runways_database(runways_database_path):
    """ 
    load the runways database
    
    """
    with open(runways_database_path, 'r') as f:
        runways = json.load(f)
    return runways


def generate_poses(runaway_db, scenario: ScenarioContent, d: GESDataset):
    """
    generate all the camera poses with the config c and the GESDataset d

    """
    time = scenario.time
    for runway in scenario.runways:
        poses = d.generate_landing_poses(runaway_db,
                                         scenario.airport,
                                         runway,
                                         scenario.trajectory)
        for p in poses:
            scenario.poses.append({
                'airport': scenario.airport,
                'runway': runway,
                'pose': list(p),  # list of flight data
                'time': {
                    'year': random.randint(time.year_min, time.year_max),
                    'month': random.randint(time.month_min, time.month_max),
                    'day': random.randint(time.day_min, time.day_max),
                    'hour': random.randint(time.hour_min, time.hour_max),
                    'minute': random.randint(time.minute_min, time.minute_max),
                    'second': random.randint(time.second_min, time.second_max),
                }
            })


def generate_scenario(image_width, poses, times, fov, height, d: GESDataset):
    """ 
    generate the scenario (format for GES)
    
    """
    scenario, _ = d.create_scenario(
        flight_data=poses,
        nb_frames=len(poses),
        fov_vertical=fov,
        width=image_width,
        height=height,
        times=times
    )
    return scenario

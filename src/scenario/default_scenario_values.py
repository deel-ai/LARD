from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class DefaultOutputs:
    dataset_directory: str = "scenarios"
    earth_studio_scenario: str = None
    scenario_metadata: str = None
    plot_generated_points: str = None


@dataclass
class DefaultTime:
    second_max: int = 1
    second_min: int = 1
    minute_max: int = 1
    minute_min: int = 1
    hour_max: int = 12
    hour_min: int = 12
    day_max: int = 1
    day_min: int = 1
    month_max: int = 1
    month_min: int = 1
    year_max: int = 2020
    year_min: int = 2020


@dataclass
class DefaultTrajectory:
    sample_number: int = 10
    dist_ap_m: float = 300.0

    max_distance_m: float = 5556
    min_distance_m: float = 280
    distribution: str = "exp"
    distrib_param: float = 1.41

    alpha_h_distrib: str = 'normal' # or uniform for ranges, with alpha_h_min and alpha_h_max
    alpha_h_min: float = None
    alpha_h_max: float = None
    alpha_h_deg: float = 0
    std_alpha_h_deg: float = 2

    alpha_v_distrib: str = 'normal' # or uniform for ranges, with alpha_v_min and alpha_v_max
    alpha_v_min: float = None
    alpha_v_max: float = None
    alpha_v_deg: float = -3
    std_alpha_v_deg: float = 0.4
    
    yaw_distrib: str = 'normal' # or uniform for ranges, with yaw_min and yaw_max
    yaw_min: float = None
    yaw_max: float = None
    yaw_deg: float = 0
    std_yaw_deg: float = 5.0

    pitch_distrib: str = 'normal' # or uniform for ranges, with yaw_min and yaw_max
    pitch_min: float = None
    pitch_max: float = None
    pitch_deg: float = -4
    std_pitch_deg: float = 2

    roll_distrib: str = 'normal' # or uniform for ranges, with yaw_min and yaw_max
    roll_min: float = None
    roll_max: float = None
    roll_deg: float = 0
    std_roll_deg: float = 5
    
    use_ODD: bool = False

@dataclass
class DefaultImage:
    height: int = 2048
    width: int = 2448
    fov_x: float = 30.0
    fov_y: float = None
    watermark_height: int = 0


@dataclass
class ScenarioContent:
    airports_runways: Dict[str, List[str]] = field(default_factory=dict)
    image: DefaultImage = DefaultImage()
    poses: list = field(default_factory=list)
    runways_database: str = "data/filtered_runways_database_Final.json"
    trajectory: DefaultTrajectory = DefaultTrajectory()
    time: DefaultTime = DefaultTime()

    def from_dict(self, in_dict): # TODO rework the json files for scenarios loading 
        self.airports_runways = in_dict["airports_runways"]
        self.image.__dict__.update(in_dict["image"])
        self.time.__dict__.update(in_dict["time"])
        self.trajectory.__dict__.update(in_dict["trajectory"])

    def update_if_exists(self, key, val):
        if hasattr(self, key):
            setattr(self, key, val)
        else:
            if hasattr(self.image, key):
                setattr(self.image, key, val)
            if hasattr(self.time, key):
                setattr(self.time, key, val)
            if hasattr(self.trajectory, key):
                setattr(self.trajectory, key, val)

# @dataclass
# class ScenarioContent: #TODO rework this class to handle multiple airports & runways
#     airport: str = None
#     runways_database: str = "data/runways_database.json"
#     runways: list = field(default_factory=list)
#     image: DefaultImage = DefaultImage()
#     time: DefaultTime = DefaultTime()
#     trajectory: DefaultTrajectory = DefaultTrajectory()
#     poses: list = field(default_factory=list)

#     def from_dict(self, in_dict):
#         self.airport = in_dict["airport"]
#         self.runways = in_dict["runways"]
#         self.image.__dict__.update(in_dict["image"])
#         self.time.__dict__.update(in_dict["time"])
#         self.trajectory.__dict__.update(in_dict["trajectory"])

#     def update_if_exists(self, key, val):
#         if hasattr(self, key):
#             self.__setattr__(key, val)
#         else:
#             if hasattr(self.image, key):
#                 self.image.__setattr__(key, val)
#             if hasattr(self.time, key):
#                 self.time.__setattr__(key, val)
#             if hasattr(self.trajectory, key):
#                 self.trajectory.__setattr__(key, val)

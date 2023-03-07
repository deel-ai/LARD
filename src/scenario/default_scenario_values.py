from dataclasses import dataclass, field


@dataclass
class DefaultOutputs:
    dataset_directory: str = "scenarios"
    earth_studio_scenario: str = None
    scenario_metadata: str = None
    plot_generated_points: str = None


@dataclass
class DefaultTime:
    day_max: int = 1
    day_min: int = 1
    hour_max: int = 12
    hour_min: int = 12
    minute_max: int = 1
    minute_min: int = 1
    month_max: int = 1
    month_min: int = 1
    second_max: int = 1
    second_min: int = 1
    year_max: int = 2020
    year_min: int = 2020


@dataclass
class DefaultTrajectory:
    sample_number: int = 10
    alpha_h_deg: float = 0
    alpha_v_deg: float = -3
    dist_ap_m: float = 300.0
    distrib_param: float = 1.41
    distribution: str = "exp"
    max_distance_m: float = 5556
    min_distance_m: float = 150
    pitch_deg: float = -4
    roll_deg: float = 0
    std_alpha_h_deg: float = 2
    std_alpha_v_deg: float = 0.4
    std_pitch_deg: float = 2
    std_roll_deg: float = 5
    std_yaw_deg: float = 5.0


@dataclass
class DefaultImage:
    height: int = 2048
    width: int = 2448
    fov: float = 33.50717983885091
    watermark_height: int = 300


@dataclass
class ScenarioContent:
    airport: str = None
    runways_database: str = "data/runways_database.json"
    runways: list = field(default_factory=list)
    image: DefaultImage = DefaultImage()
    time: DefaultTime = DefaultTime()
    trajectory: DefaultTrajectory = DefaultTrajectory()
    poses: list = field(default_factory=list)

    def from_dict(self, in_dict):
        self.airport = in_dict["airport"]
        self.runways = in_dict["runways"]
        self.image.__dict__.update(in_dict["image"])
        self.time.__dict__.update(in_dict["time"])
        self.trajectory.__dict__.update(in_dict["trajectory"])

    def update_if_exists(self, key, val):
        if hasattr(self, key):
            self.__setattr__(key, val)
        else:
            if hasattr(self.image, key):
                self.image.__setattr__(key, val)
            if hasattr(self.time, key):
                self.time.__setattr__(key, val)
            if hasattr(self.trajectory, key):
                self.trajectory.__setattr__(key, val)

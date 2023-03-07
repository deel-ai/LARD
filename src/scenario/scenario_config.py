import yaml
from pathlib import Path
from src.scenario.default_scenario_values import DefaultOutputs, ScenarioContent
from dataclasses import asdict


class ScenarioConfig:
    def __init__(self, airport=None, runway=None, scenario_dir=None, yaml_file=None):
        """
        If a yaml_file is provided, the parameters airport, runway, scenario dir are not used,
        and the ones from the yaml will be used instead.
        """
        self.content = ScenarioContent(airport=airport, runways=runway)
        self.outputs = DefaultOutputs()
        if scenario_dir is not None:
            self.scenario_dir = Path(scenario_dir)
        if yaml_file is not None:
            with open(yaml_file, 'r') as f:
                params = yaml.safe_load(f)
                self.outputs.__dict__.update(params["outputs"])
                self.content.from_dict(params["content"])

    @property
    def scenario_name(self):
        return f"{self.content.airport}_{self.content.runways[0]}_{self.content.trajectory.sample_number}"

    def autofill_empty_outputs(self):
        if self.outputs.earth_studio_scenario is None:
            self.outputs.earth_studio_scenario = self.scenario_dir / (self.scenario_name + ".esp")
        if self.outputs.scenario_metadata is None:
            self.outputs.scenario_metadata = self.scenario_dir / (self.scenario_name + ".yaml")

    def update_fields(self):
        for key, val in self.__dict__.items():
            if hasattr(self.outputs, key):
                self.outputs.__setattr__(key, val)
            self.content.update_if_exists(key, val)
        self.autofill_empty_outputs()

    def to_dict(self):
        """
        generate the config.yaml file according to the class attributes
        """
        new_yaml = {"content": asdict(self.content),
                    "outputs": asdict(self.outputs)}
        return new_yaml

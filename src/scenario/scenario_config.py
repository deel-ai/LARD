import json
import yaml
from datetime import datetime
import random
from pathlib import Path
from src.scenario.default_scenario_values import DefaultOutputs, ScenarioContent
from dataclasses import asdict


class ScenarioConfig:
    def __init__(self, airports_runways=None, airport=None, runway=None, scenario_dir=None, yaml_file=None, runways_database_file="data/runways_database.json"):
        """
        If a yaml_file is provided, the parameters airport, runway, scenario dir are not used,
        and the ones from the yaml will be used instead.
        """
        self.outputs = DefaultOutputs()
        if scenario_dir is not None:
            self.scenario_dir = Path(scenario_dir)
        if yaml_file is not None:
            with open(yaml_file, 'r') as f:
                params = yaml.safe_load(f)
                self.outputs.__dict__.update(params["outputs"])
                self.content.from_dict(params["content"])
                #TODO check if this ,needs a rework once scenarioContent is reworked
        elif airports_runways is not None:
            # For each airport of the dictionary with empty runways, 
            # add all existing runways from the airport_database
            with open(runways_database_file, 'r') as f:
                runways_database = json.load(f)
            print(airports_runways, "before adding missing runways")
            for airport, runways in airports_runways.items():
                if not runways:
                    airports_runways[airport] = list(runways_database[airport].keys())
            print(airports_runways, "after adding missing runways")           
            self.content = ScenarioContent(airports_runways=airports_runways)
        elif airport is not None and runway is not None:
            airport_runways = {airport: [runway]}
            self.content = ScenarioContent(airports_runways=airport_runways)
        else:
            raise ValueError("Provide either:\n- airports_runways,\n- an airport and its runways,\n- a yaml configuration file")
            
    @property
    def scenario_name(self):
        scenario_name_parts = []
        max_airports_name = 2
        for airport, runways in self.content.airports_runways.items():
            rwy_str = "-".join(runways)
            scenario_name_parts.append(f"{airport}-{rwy_str}")
            max_airports_name -= 1
            if max_airports_name == 0:
                break
        scenario_name_parts.append(f"_{self.content.trajectory.sample_number}-smpl")
        current_time = datetime.now().strftime("%Hh%M")
        scenario_name_parts.append(f"_{current_time}")
        return "_".join(scenario_name_parts)
    
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

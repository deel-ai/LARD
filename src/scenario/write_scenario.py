import os
import argparse
import pathlib
import yaml
import json
import numpy as np
from pathlib import Path
from src.scenario.write_scenario_utils import initialize_dataset, generate_scenario, generate_poses
from src.scenario.scenario_config import ScenarioConfig
from typing import Union
from dataclasses import asdict


def write_scenario(scenario_config: Union[pathlib.Path, ScenarioConfig]) -> None:
    """
    Export a scenario from a yaml config file to eps format
    """
    scenario_config.update_fields()
    scenario_content = scenario_config.content
    dataset_dir = scenario_config.outputs.dataset_directory
    os.makedirs(pathlib.Path(dataset_dir), exist_ok=True)

    ges_dataset = initialize_dataset(dataset_dir)

    # Watermark management
    if scenario_content.image.watermark_height is not None:
        f = scenario_content.image.height / 2. / np.tan(np.deg2rad(scenario_content.image.fov / 2.))
        height = scenario_content.image.height + 2 * scenario_content.image.watermark_height
        fov = 2 * np.rad2deg(np.arctan2(height / 2., f))
    else:
        fov = scenario_content.image.fov
        height = scenario_content.image.height

    # Generate poses
    scenario_content.poses = []
    runaways_db = scenario_content.runways_database
    generate_poses(runaways_db, scenario_content, ges_dataset)

    # Generate scenario
    poses = [p['pose'] for p in scenario_content.poses]
    times = [p['time'] for p in scenario_content.poses]
    scenario = generate_scenario(scenario_content.image.width, poses, times, fov, height, ges_dataset)

    # Write scenario in esp format (google engine format)
    out_google_file = scenario_config.outputs.earth_studio_scenario
    os.makedirs(Path(out_google_file).parent, exist_ok=True)
    with open(out_google_file, 'w') as f:
        json.dump(scenario, f, indent=2)
    print(f"Scenario exported as esp : {out_google_file}")

    # Save scenario configuration as yaml
    output_scenario_file = scenario_config.outputs.scenario_metadata
    with open(output_scenario_file, 'w') as f:
        yaml.dump(asdict(scenario_content), f)
    print(f"Scenario exported as yaml : {output_scenario_file}")


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(
        prog=pathlib.Path(os.path.basename(__file__)).stem,
        description="""Generate a Google Earth Scenario file based on the \
configuration file provided."""
    )
    parser.add_argument(
        'config_filepath',
        type=pathlib.Path,
        help='YAML configuration filepath',
        default=pathlib.Path('params/example_generation.yaml')
    )
    parser.add_argument(
        '-v', '--verbose',
        help='Verbose mode',
        action='store_true'
    )
    args = parser.parse_args()
    """
    airport = "BGBW"
    runway = "06"
    output_directory = Path("scenarios/debug_test")
    sample_number = 61
    config = ScenarioConfig(airport,
                          [runway],
                          scenario_dir=output_directory / f"{airport}_{runway}_{sample_number}")
    config.sample_number = 61
    """
    config = ScenarioConfig(yaml_file=args.config_filepath)
    write_scenario(config)

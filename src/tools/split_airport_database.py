import os
import json
from argparse import ArgumentParser
from pathlib import Path

# DEPRECATED -- NOT UP TO DATE WITH CURRENT DATABASE
TRAIN_AIPORTS = ['BGBW', 'BGPT', 'BIRK', 'DAAG', 'LFMP', 'LFPO', 'LFQQ', 'LFRN', 'LFRS', 'LFST', 'LPPT', 'VABB', 'YBBN']

# DEPRECATED -- NOT UP TO DATE WITH CURRENT DATABASE
TEST_AIPORTS = ['LTAI', 'LICJ', 'LIRN', 'EDDV', 'LAX', 'LSZH', 'LEMD', 'LWSK', 'VHHH', 'CYUL', 'VRMM', 'LFSB', 'LCPH',
                 'LFML', 'GCRR', 'EHAM', 'SAEZ', 'CYVR', 'CYYZ', 'KIAH', 'KJFK', 'KMIA', 'KSFO', 'LFMN', 'MDSD', 'OMDB',
                 'RJAA', 'RJTT', 'WSSS', 'FMEP', 'VQPR']


def split_database(database_path):
    with open(database_path, 'r') as f:
        runways_database = json.load(f)

    train_dict = {airport: runways_database[airport] for airport in TRAIN_AIPORTS}
    test_dict = {airport: runways_database[airport] for airport in TEST_AIPORTS}
    not_found = {airport: data for airport, data in runways_database.items() if not (airport in train_dict
                                                                                      or airport in test_dict)}
    print(f"Airports not found : {list(not_found.keys())}")
    with open(database_path.parent / (database_path.stem+"_train.json"), 'w') as f:
        json.dump(train_dict, f)
    with open(database_path.parent / (database_path.stem+"_test.json"), 'w') as f:
        json.dump(test_dict, f)


if __name__ == "__main__":
    parser = ArgumentParser(
        prog=Path(os.path.basename(__file__)).stem,
        description="""Sanitize the names of every image file of the real dataset"""
    )
    parser.add_argument(
        '-i',
        '--input_database',
        type=Path,
        help='Path to a dataset export configuration. Example : params/export_test_dataset.yaml',
        default='data/runways_database.json'
    )
    args = parser.parse_args()

    split_database(args.input_database)

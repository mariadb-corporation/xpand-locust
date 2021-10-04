import os
import sys

import numpy as np
import pandas as pd
import yaml


class YamlConfigException(Exception):
    pass


def load_yaml_config(yaml_config_file):
    if os.path.exists(yaml_config_file):
        try:
            with open(yaml_config_file, "rt") as f:
                yaml_config_dict = yaml.load(f, Loader=yaml.Loader)
                return yaml_config_dict
        except (yaml.YAMLError, yaml.MarkedYAMLError) as exc:
            raise YamlConfigException(
                f"Error occurred during parsing config file {yaml_config_file}"
            )

    else:
        raise YamlConfigException(f"Config file {yaml_config_file} does not exist")


def load_seed_file(seed_file, num_rows_required=10000):
    df = pd.read_csv(seed_file, header=None)
    values = df[0].values.tolist()
    arr = np.random.choice(values, num_rows_required)
    return iter(arr)


def is_worker():
    return "--worker" in sys.argv


def is_master():
    return "--master" in sys.argv

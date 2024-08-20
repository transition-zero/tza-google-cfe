import os
import yaml


def setup_dir(path_to_dir):
    if not os.path.exists(path_to_dir):
        os.makedirs(path_to_dir)


def load_configs(path):
    with open(path, 'r') as file:
        configs = yaml.safe_load(file)
    return configs
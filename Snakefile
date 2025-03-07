from os.path import exists
from shutil import copyfile, move


if not exists("config.yaml"):
    copyfile("config.default.yaml", "config.yaml")

configfile: "config.yaml"


RDIR = config['results_dir'] + config['run']

rule download_brownfield:
    output: RDIR + "/brownfield/original_brownfield.nc"
    script: "scripts/download_brownfield.py"
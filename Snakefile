from os.path import exists
from shutil import copyfile, move


if not exists("config.yaml"):
    copyfile("config.default.yaml", "config.yaml")

configfile: "config.yaml"


RDIR = config['results_dir'] + config['run']

rule download_brownfield:
    output: 
        original_brownfield = RDIR + "/brownfield/original_brownfield.nc"
    script: "scripts/download_brownfield.py"

rule add_cfe_to_brownfield:
    input: 
        original_brownfield = RDIR + "/brownfield/original_brownfield.nc"
    output: 
        cfe_brownfield = RDIR + "/brownfield/cfe_brownfield.nc"
    script: "scripts/add_cfe_to_brownfield.py"
from os.path import exists
from shutil import copyfile, move


if not exists("config.yaml"):
    copyfile("config.default.yaml", "config.yaml")


configfile: "config.yaml"


RDIR = config["results_dir"] + config["run"]


rule download_brownfield:
    output:
        original_brownfield=RDIR + "/brownfield/original_brownfield.nc",
    script:
        "scripts/download_brownfield.py"


rule add_cfe_to_brownfield:
    input:
        original_brownfield=RDIR + "/brownfield/original_brownfield.nc",
    output:
        cfe_brownfield=RDIR + "/brownfield/cfe_brownfield.nc",
    script:
        "scripts/add_cfe_to_brownfield.py"


rule solve_brownfield:
    input:
        cfe_brownfield=RDIR + "/brownfield/cfe_brownfield.nc",
    output:
        solved_cfe_brownfield=RDIR + "/brownfield/solved_cfe_brownfield.nc",
    script:
        "scripts/solve_brownfield.py"


rule prepare_brownfield_for_cfe:
    input:
        solved_cfe_brownfield=RDIR + "/brownfield/solved_cfe_brownfield.nc",
    output:
        prepared_cfe_brownfield=RDIR + "/brownfield/prepared_cfe_brownfield.nc",
    script:
        "scripts/prepare_brownfield_for_cfe.py"


rule run_annual_matching:
    input:
        prepared_cfe_brownfield=RDIR + "/brownfield/prepared_cfe_brownfield.nc",
    output:
        annual_matching=RDIR + "/cfe_100/annual_matching.nc",
    script:
        "scripts/run_annual_matching.py"

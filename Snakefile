from os.path import exists
from shutil import copyfile, move


if not exists("config.yaml"):
    copyfile("config.default.yaml", "config.yaml")


configfile: "config.yaml"


RDIR = config["results_dir"] + config["run"]


palettes = config["scenario"]["palette"]
years = config["scenario"]["year"]


rule download_brownfield:
    output:
        original_brownfield= RDIR + "/brownfield/{year}/original_brownfield.nc",
    script:
        "scripts/download_brownfield.py"


rule add_cfe_to_brownfield:
    input:
        original_brownfield= RDIR + "/brownfield/{year}/original_brownfield.nc",
    output:
        cfe_brownfield= RDIR + "/brownfield/{year}/{palette}/cfe_brownfield.nc",
    script:
        "scripts/add_cfe_to_brownfield.py"


rule solve_brownfield:
    input:
        cfe_brownfield=RDIR + "/brownfield/{year}/{palette}/cfe_brownfield.nc",
    output:
        solved_cfe_brownfield=RDIR + "/brownfield/{year}/{palette}/solved_cfe_brownfield.nc",
    script:
        "scripts/solve_brownfield.py"


rule prepare_brownfield_for_cfe:
    input:
        solved_cfe_brownfield=RDIR + "/brownfield/{year}/{palette}/solved_cfe_brownfield.nc",
    output:
        prepared_cfe_brownfield=RDIR + "/brownfield/{year}/{palette}//prepared_cfe_brownfield.nc",
    script:
        "scripts/prepare_brownfield_for_cfe.py"


rule run_annual_matching:
    input:
        prepared_cfe_brownfield=RDIR + "/brownfield/{year}/{palette}/prepared_cfe_brownfield.nc",
    output:
        annual_matching=RDIR + "/annual_matching/{year}/{palette}/annual_matching.nc",
    script:
        "scripts/run_annual_matching.py"

rule run_hourly_matching:
    input:
        prepared_cfe_brownfield=RDIR + "/brownfield/{year}/{palette}/prepared_cfe_brownfield.nc",
    output:
        hourly_matching = RDIR + "/hourly_matching/{year}/{palette}/{regime}.nc",
    script:
        "scripts/run_hourly_matching.py"
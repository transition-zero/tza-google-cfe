import os
import yaml
import pypsa

import tz_pypsa as tza
from tz_pypsa.model import Model
from _helpers import *


# get configs
def load_configs():
    with open('01_configs.yaml', 'r') as file:
        configs = yaml.safe_load(file)
    return configs

# run brownfield
def run_brownfield_scenario(
        configs : dict = None
    ) -> pypsa.Network:
    '''Run a brownfield scenario without CFE considerations.
    '''
    
    # setup brownfield network
    for run in configs['model_runs']:

        print('Loading model: ', run['core_model'])
        network = (
            Model.load_model(
                run['core_model'], 
                frequency = configs['global_vars']['frequency'],
                select_nodes=run['select_nodes'], 
                years=[ configs['global_vars']['year'] ],
                backstop=run['backstop'],
                set_global_constraints=configs['global_vars']['set_global_constraints'],
            )
        )

    # add renewable targets
    # TODO!

    # solve
    print('Beginning optimization...')
    try:
        network.optimize.solve_model(
            solver_name=configs['global_vars']['solver'],
        )
    except:
        network.optimize(
            solver_name=configs['global_vars']['solver'],
            #solver_options={ 'solver': 'pdlp' },
            #multi_year_investment=True,
        )
    
    # save results
    setup_dir(
        path_to_dir=configs['paths']['output_model_runs'] + run['name'] + '/solved_networks/'
    )

    network.export_to_netcdf(
        os.path.join(
            configs['paths']['output_model_runs'], run['name'], 'solved_networks', 'brownfield_' + str(configs['global_vars']['year']) + '.nc'
        )
    )
    
    return network

def run_annual_matching_scenario():
    pass

def run_hourly_matching_scenario():
    pass

if __name__ == '__main__':

    # get config file
    configs = load_configs()

    # run scenarios
    run_brownfield_scenario(configs)
    run_annual_matching_scenario()
    run_hourly_matching_scenario()

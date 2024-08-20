import os
import yaml
import pypsa

import tz_pypsa as tza
from tz_pypsa.model import Model

from .helpers import *

def run_brownfield_scenario(
        run : dict = None,
        configs : dict = None
) -> pypsa.Network:

    '''Run a brownfield scenario without CFE considerations.
    '''
    
    # setup network
    print('loading model: ', run['core_model'])

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

    # set 2030 renewable targets
    # TODO!

    # ensure p_nom is extendable
    network.generators['p_nom_extendable']      = True
    network.links['p_nom_extendable']           = True
    network.storage_units['p_nom_extendable']   = True

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
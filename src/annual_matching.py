import os
import yaml
import pypsa

import tz_pypsa as tza
from tz_pypsa.model import Model

from .helpers import *
from .constraints import *

def run_annual_matching_scenario(
        run : dict = None,
        configs : dict = None,
        brownfield_network : pypsa.Network = None,
        cfe_score : float = 1.0,
    ) -> pypsa.Network:
    
    '''Run a network with annually matched renewable generation.
    '''
    
    # make a copy of the brownfield network
    network = brownfield_network.copy()

    # fix p_nom to p_nom_opt in brownfield network
    network.generators['p_nom']      = network.generators['p_nom_opt']
    network.links['p_nom']           = network.links['p_nom_opt']
    network.storage_units['p_nom']   = network.storage_units['p_nom_opt']

    # make everything unextendable
    network.generators['p_nom_extendable']      = False
    network.links['p_nom_extendable']           = False
    network.storage_units['p_nom_extendable']   = False

    # make C&I assets extendable
    clean_carriers = network.carriers.query(" co2_emissions <= 0 ").index.to_list() 
    #network.generators.loc[ network.generators.carrier.isin( clean_carriers ), 'p_nom_extendable' ]                             = True
    network.generators.loc[network.generators.bus.str.contains(configs['global_vars']['ci_label']), 'p_nom_extendable' ]        = True
    network.links.loc[network.links.bus0.str.contains(configs['global_vars']['ci_label']), 'p_nom_extendable' ]                 = True
    network.storage_units.loc[network.storage_units.bus.str.contains(configs['global_vars']['ci_label']), 'p_nom_extendable' ]  = True
    
    # --------------------------------------------------------
    # ADD CONSTRAINTS
    # --------------------------------------------------------

    # init linopy model
    lp_model = network.optimize.create_model()

    # Renewable targets
    # --------------------

    # TODO! ADD A PLACEHOLDER 30% CLEAN GENERATION TARGET FOR NOW
    lp_model, network = constraint_clean_generation_target(lp_model, network, ci_nodes=run['nodes_with_ci_load'], configs=configs)

    # Charging storages with fossil fuels
    # --------------------

    # add fossil storage charging constraint
    if not configs['global_vars']['enable_fossil_charging']:
        lp_model, network = constraint_fossil_storage_charging(lp_model, network)

    # Annual matching
    # --------------------

    lp_model, network = annual_matching(lp_model, network, cfe_score=cfe_score, ci_nodes=run['nodes_with_ci_load'], configs=configs)

    # --------------------------------------------------------
    # SOLVE
    # --------------------------------------------------------

    # solve
    print('Beginning optimisation')

    network.optimize.solve_model(
        solver_name=configs['global_vars']['solver'],
        multi_investment=True,
    )

    # save results
    setup_dir(
        path_to_dir=configs['paths']['output_model_runs'] + run['name'] + '/solved_networks/'
    )

    network.export_to_netcdf(
        os.path.join(
            configs['paths']['output_model_runs'], run['name'], 'solved_networks', 'annual_matching_' + str(configs['global_vars']['year']) + '_cfe' + str(int(cfe_score*100)) + '.nc'
        )
    )

    return network
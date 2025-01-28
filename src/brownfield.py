
import pypsa

from tz_pypsa.model import Model
from tz_pypsa.constraints import constr_bus_self_sufficiency

def SetupBrownfieldNetwork(run, configs) -> pypsa.Network:
    """
    
    Sets up the brownfield network based on the provided run configuration and global variables.

    Parameters:
    -----------
    run (dict): A dictionary containing run-specific configurations such as 'stock_model', 'select_nodes', 'backstop', and 'allow_grid_expansion'.
    configs (dict): A dictionary containing global configuration variables including 'frequency', 'timesteps', 'year', and 'set_global_constraints'.

    Returns:
    -----------
    pypsa.Network: A PyPSA Network object with the brownfield system set up according to the provided configurations.

    """
    
    # load csv stock model from tza-pypsa 
    network = (
        Model.load_csv_from_dir(
            configs['paths']['path_to_model'], 
            #run['stock_model'], 
            frequency = configs['global_vars']['frequency'],
            timesteps = configs['global_vars']['timesteps'],
            #select_nodes=configs['global_vars']['select_nodes'], 
            years=[ configs['global_vars']['year'] ],
            #backstop=run['backstop'],
            set_global_constraints=configs['global_vars']['set_global_constraints'],
        )
    )

    lp_model = network.optimize.create_model()

    # constr_policy_targets(network,
    #                       lp_model,
    #                       configs['paths']['path_to_model'])

    constr_bus_self_sufficiency(network,
                                lp_model,
                                min_self_sufficiency = network.buses.bus_self_sufficiency)
    
    # constr_max_annual_utilisation()

    network.buses['bus_self_sufficiency']       = network.buses['bus_self_sufficiency']
    network.carriers['max_annual_utilisation']  = network.carriers['max_annual_utilisation']

    # ensure p_nom is extendable in the brownfield network
    network.generators['p_nom_extendable']      = True
    network.storage_units['p_nom_extendable']   = True
    network.links['p_nom_extendable']           = run['allow_grid_expansion']

    # set p_nom_min to prevent early decommissioning of assets
    network.generators['p_nom_min']      = network.generators['p_nom']
    network.storage_units['p_nom_min']   = network.storage_units['p_nom']
    network.links['p_nom_min']           = network.links['p_nom']

    return network
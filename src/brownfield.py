
import pypsa

from tz_pypsa.model import Model

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
    
    
    if configs["model_runs"][0]["stock_model"] == "ASEAN":
    # load the stock model from tza-pypsa 
        network = (
            Model.load_model(
                run['stock_model'], 
                frequency = configs['global_vars']['frequency'],
                timesteps = configs['global_vars']['timesteps'],
                select_nodes=run['select_nodes'], 
                years=[ configs['global_vars']['year'] ],
                backstop=run['backstop'],
                set_global_constraints=configs['global_vars']['set_global_constraints'],
            )
        )
    else: 
        network = (
        Model.load_csv_from_dir(
            configs['paths']['path_to_model'], 
            #run['stock_model'], 
            frequency = configs['global_vars']['frequency'],
            timesteps = configs['global_vars']['timesteps'],
            #select_nodes=configs['global_vars']['select_nodes'], 
            year=[ configs['global_vars']['year'] ],
            #backstop=run['backstop'],
            set_global_constraints=configs['global_vars']['set_global_constraints'],
        )
    )

    # if expansion is set to True, set p_nom_extendable to True for generators and storage units
    # otherwise if False, leaves propreties as they are (in case some are already set to True and others to False)
    if run["allow_generation_expansion"]:
        network.generators['p_nom_extendable'] = run["allow_generation_expansion"]
    if run["allow_storage_expansion"]:
        network.storage_units['p_nom_extendable']   = run["allow_storage_expansion"]
    if run["allow_grid_expansion"]:
        network.links['p_nom_extendable']   = run["allow_grid_expansion"]
    # network.storage_units.p_nom_extendable.loc[network.storage_units.index.str.contains('lithium')] = True
    # network.storage_units.p_nom_extendable.loc[network.storage_units.index.str.contains('pumped')] = False

    # set p_nom_min to prevent early decommissioning of assets
    network.generators['p_nom_min']      = network.generators['p_nom']
    network.storage_units['p_nom_min']   = network.storage_units['p_nom']
    network.links['p_nom_min']           = network.links['p_nom']

    return network
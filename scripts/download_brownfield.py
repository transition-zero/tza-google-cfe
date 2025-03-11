import pypsa
from tz_pypsa.model import Model


def download_brownfield(configs: dict, run: dict) -> pypsa.Network:
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
    run = configs["model_runs"][0]
    if configs["model_runs"][0]["stock_model"] == "ASEAN":
        # load the stock model from tza-pypsa
        network = Model.load_model(
            configs["global_vars"]["stock_model"],
            frequency=configs["global_vars"]["frequency"],
            timesteps=configs["global_vars"]["timesteps"],
            select_nodes=run["select_nodes"],
            years=[configs["global_vars"]["year"]],
            backstop=run["backstop"],
            set_global_constraints=configs["global_vars"]["set_global_constraints"],
        )
    else:
        network = Model.load_csv_from_dir(
            configs["paths"]["path_to_model"],
            # run['stock_model'],
            frequency=configs["global_vars"]["frequency"],
            timesteps=configs["global_vars"]["timesteps"],
            # select_nodes=configs['global_vars']['select_nodes'],
            years=[configs["global_vars"]["year"]],
            # backstop=run['backstop'],
            set_global_constraints=configs["global_vars"]["set_global_constraints"],
        )

    return network


def prepare_brownfield(run: dict, network: pypsa.Network) -> pypsa.Network:
    """
    Prepares a brownfield network by ensuring that the nominal power (p_nom)
    of generators, storage units, and links is extendable and setting minimum
    nominal power to prevent early decommissioning of assets.
    Parameters:
    run (dict): A dictionary containing configuration options, including
                whether grid expansion is allowed.
    network (pypsa.Network): The PyPSA network object to be modified.
    Returns:
    pypsa.Network: The modified PyPSA network object with updated properties.
    """

    network.generators["p_nom_extendable"] = True
    network.storage_units["p_nom_extendable"] = True
    network.links["p_nom_extendable"] = run["allow_grid_expansion"]
    network.generators["committable"] = False
    network.generators["p_nom_min"] = network.generators["p_nom"]
    network.storage_units["p_nom_min"] = network.storage_units["p_nom"]
    network.links["p_nom_min"] = network.links["p_nom"]

    return network


if __name__ == "__main__":
    if "snakemake" not in globals():
        from helper import mock_snakemake

        snakemake = mock_snakemake(
            "download_brownfield",
        )
    run = snakemake.config["model_runs"][0]
    network = download_brownfield(configs=snakemake.config, run=run)
    network = prepare_brownfield(
        network=network,
        run=run,
    )
    network.export_to_netcdf(snakemake.output[0])

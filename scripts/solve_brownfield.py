import pypsa


def solve_brownfield(network: pypsa.Network, config: dict) -> pypsa.Network:
    """
    Optimize the given PyPSA network using the specified solver from the configuration.
    Args:
        network (pypsa.Network): The PyPSA network to be optimized.
        config (dict): Configuration dictionary containing solver settings.
    Returns:
        pypsa.Network: The optimized PyPSA network.
    """

    network.optimize(solver_name=config["solver"])
    return network


if __name__ == "__main__":
    if "snakemake" not in globals():
        from helper import mock_snakemake

        snakemake = mock_snakemake(
            "solve_brownfield",
        )
    config = snakemake.config["global_vars"]

    cfe_brownfield = pypsa.Network(snakemake.input.cfe_brownfield)
    solved_brownfield_cfe = solve_brownfield(config=config, network=cfe_brownfield)
    cfe_brownfield.export_to_netcdf(snakemake.output.solved_cfe_brownfield)

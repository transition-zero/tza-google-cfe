import pypsa


def prepare_brownfield_for_cfe(n: pypsa.Network, ci_identifier: str):
    """
    This function post-processes the brownfield network to make it ready for the CFE and RES100 simulations.
    The logic is that we fix all optimised capacities in 2030 (brownfield) and only allow the C&I assets to be extendable,
    representing the "additionality" of their PPA.
    """
    components = ["generators", "links", "storage_units"]
    for c in components:
        # Fix p_nom to p_nom_opt for each component in brownfield network
        getattr(n, c)["p_nom"] = getattr(n, c)["p_nom_opt"]
        # make everything non-extendable
        getattr(n, c)["p_nom_extendable"] = False
        # ...besides the C&I assets
        getattr(n, c).loc[
            getattr(n, c).index.str.contains(ci_identifier), "p_nom_extendable"
        ] = True
    return n


if __name__ == "__main__":
    if "snakemake" not in globals():
        from helper import mock_snakemake

        snakemake = mock_snakemake(
            "solve_brownfield",
        )
    ci_identifier = snakemake.config["global_vars"]["ci_label"]
    solved_brownfield = pypsa.Network(snakemake.input.solved_cfe_brownfield)
    prepared_brownfield = prepare_brownfield_for_cfe(
        n=solved_brownfield, ci_identifier=ci_identifier
    )
    prepared_brownfield.export_to_netcdf(snakemake.output.prepared_cfe_brownfield)

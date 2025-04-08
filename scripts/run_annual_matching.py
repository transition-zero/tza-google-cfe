import pypsa


def RunRES100(
    network: pypsa.Network,
    run: dict,
    ci_identifier: str,
    configs: dict,
    # bus : str,
):
    """Sets up the 100% RES (annual matching) simulation"""
    RES_TARGET = 100
    # init linopy model
    network.optimize.create_model()

    for bus in run["nodes_with_ci_load"]:

        # get total C&I load (float)
        CI_Demand = (
            network.loads_t.p_set.filter(regex=bus)
            .filter(regex=ci_identifier)
            .sum()
            .sum()
        )

        # get grid exports
        CI_GridExport = (
            network.model.variables["Link-p"]
            .sel(
                Link=[
                    i
                    for i in network.links.index
                    if ci_identifier in i and "Export" in i and bus in i
                ]
            )
            .sum(dims="Link")
        )

        # get total PPA procurement (linopy.Var)
        ci_ppa_generators = network.generators.loc[
            (network.generators.bus.str.contains(bus))
            & (network.generators.bus.str.contains(ci_identifier))
        ].index.tolist()  # get c&i ppa generators

        CI_PPA = (
            network.model.variables["Generator-p"]
            .sel(Generator=ci_ppa_generators)
            .sum()
        )

        # get clean carriers in the regional grid
        clean_carriers = [
            i
            for i in network.carriers.query(" co2_emissions <= 0").index.tolist()
            if i in network.generators.carrier.tolist()
        ]

        # clean generators
        clean_region_generators = [
            i
            for i in network.generators.loc[
                network.generators.carrier.isin(clean_carriers)
            ].index
            if ci_identifier not in i and bus[0:3] in i
        ]

        # Constraint 1: Annual matching
        # ---------------------------------------------------------------
        network.model.add_constraints(
            CI_PPA >= (RES_TARGET / 100) * CI_Demand,
            name=f"{RES_TARGET}_RES_constraint_{bus}",
        )

        # Constraint 2: Excess (export from C&I system to grid)
        # ---------------------------------------------------------------
        network.model.add_constraints(
            CI_GridExport.sum()
            <= CI_Demand * configs["global_vars"]["maximum_excess_export"],
        )
    network.optimize.solve_model(solver_name=configs["global_vars"]["solver"])

    return network


if __name__ == "__main__":
    if "snakemake" not in globals():
        from helper import mock_snakemake

        snakemake = mock_snakemake(
            "run_annual_matching",
        )
    ci_identifier = snakemake.config["global_vars"]["ci_label"]
    network = pypsa.Network(snakemake.input.prepared_cfe_brownfield)
    cfe_100 = RunRES100(
        network, snakemake.config["model_runs"][0], ci_identifier, snakemake.config
    )
    cfe_100.export_to_netcdf(snakemake.output.annual_matching)

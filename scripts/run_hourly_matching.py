import pandas as pd
import pypsa


def apply_cfe_constraint(
    n: pypsa.Network,
    GridCFE: list,
    ci_buses: list,
    ci_identifier: str,
    CFE_Score: float,
    max_excess_export: float,
) -> pypsa.Network:
    """Set CFE constraint"""
    for bus in ci_buses:
        # ---
        # fetch necessary variables to implement CFE

        CI_Demand = (
            n.loads_t.p_set.filter(regex=bus)
            .filter(regex=ci_identifier)
            .values.flatten()
        )

        CI_StorageCharge = (
            n.model.variables["Link-p"]
            .sel(
                Link=[
                    i
                    for i in n.links.index
                    if ci_identifier in i and "Charge" in i and bus in i
                ]
            )
            .sum(dims="Link")
        )

        CI_StorageDischarge = (
            n.model.variables["Link-p"]
            .sel(
                Link=[
                    i
                    for i in n.links.index
                    if ci_identifier in i and "Discharge" in i and bus in i
                ]
            )
            .sum(dims="Link")
        )

        CI_GridExport = (
            n.model.variables["Link-p"]
            .sel(
                Link=[
                    i
                    for i in n.links.index
                    if ci_identifier in i and "Export" in i and bus in i
                ]
            )
            .sum(dims="Link")
        )

        CI_GridImport = (
            n.model.variables["Link-p"]
            .sel(
                Link=[
                    i
                    for i in n.links.index
                    if ci_identifier in i and "Import" in i and bus in i
                ]
            )
            .sum(dims="Link")
        )

        CI_PPA = (
            n.model.variables["Generator-p"]
            .sel(
                Generator=[
                    i
                    for i in n.generators.index
                    if ci_identifier in i and "PPA" in i and bus in i
                ]
            )
            .sum(dims="Generator")
        )

        # Constraint 1: Hourly matching
        # ---------------------------------------------------------------

        n.model.add_constraints(
            CI_Demand
            == CI_PPA
            - CI_GridExport
            + CI_GridImport
            + CI_StorageDischarge
            - CI_StorageCharge
        )

        # Constraint 2: CFE target
        # ---------------------------------------------------------------
        n.model.add_constraints(
            (CI_PPA - CI_GridExport + (CI_GridImport * list(GridCFE))).sum()
            >= ((CI_StorageCharge - CI_StorageDischarge) + CI_Demand).sum() * CFE_Score,
        )

        # Constraint 3: Excess
        # ---------------------------------------------------------------
        n.model.add_constraints(
            CI_GridExport.sum() <= sum(CI_Demand) * max_excess_export,
        )

        # Constraint 4: Battery can only be charged by clean PPA (not grid)
        # ---------------------------------------------------------------
        n.model.add_constraints(
            CI_PPA >= CI_StorageCharge,
        )

    return n


def RunCFE(
    network: pypsa.Network, CFE_Score, ci_identifier: str, run: dict, configs: dict
):
    """Run 24/7 CFE scenario"""

    # init linopy model
    network.optimize.create_model()

    # ---------------------------------------------------------------
    #
    #   ITERATIVELY SOLVE FOR GRID CFE
    #
    #   Following Xu and Jenkins (2021), here we iteratively solve
    #   for the grid supply CFE score. We have to do this to avoid a
    #   a non-convex problem, where two dynamic decision variables
    #   (grid supply and grid CFE) are being multiplied by one another.
    #   This approach allows us to compute the grid CFE "a priori" and
    #   then feed it as a parameter into the model.
    #
    #   The process is as follows:
    #       1. Set the grid CFE to 0 and run the model
    #       2. Calculate the real grid CFE from (1)
    #       3. Now, fix the grid CFE to (2) and re-run the model
    #       4. Calculate the grid CFE from (3) and compare against (2)
    #       5. If the difference is less than 0.01, stop. Otherwise, repeat from (3)
    #
    # ---------------------------------------------------------------

    # start a counter and initialise a dataframe to store the results
    count = 1
    GridSupplyCFE = pd.DataFrame({})

    # [Step 1] Run the model with grid supply CFE set to 0
    GridCFE = [0 for i in range(network.snapshots.size)]
    GridSupplyCFE[f"iteration_{count}"] = GridCFE

    # apply the CFE constraint
    N_CFE = apply_cfe_constraint(
        network,
        GridCFE,
        run["nodes_with_ci_load"],
        ci_identifier,
        CFE_Score,
        configs["global_vars"]["maximum_excess_export"],
    )

    # optimise
    N_CFE.optimize.solve_model(solver_name=configs["global_vars"]["solver"])

    # get GridCFE
    GridCFE = GetGridCFE(N_CFE, ci_identifier)
    count += 1
    GridSupplyCFE[f"iteration_{count}"] = GridCFE

    # calculate difference between iterations with a maximum of 100 loops
    max_iterations = 100
    while (
        GridSupplyCFE[f"iteration_{count}"].sum()
        - GridSupplyCFE[f"iteration_{count-1}"].sum()
    ) > 0.01 and count < max_iterations:
        N_CFE = apply_cfe_constraint(
            N_CFE,
            GridCFE,
            run["nodes_with_ci_load"],
            ci_identifier,
            CFE_Score,
            configs["global_vars"]["maximum_excess_export"],
        )

        N_CFE.optimize.solve_model(solver_name=configs["global_vars"]["solver"])
        GridCFE = GetGridCFE(N_CFE, ci_identifier)
        count += 1
        GridSupplyCFE[f"iteration_{count}"] = GridCFE


def GetGridCFE(n: pypsa.Network, ci_identifier):
    """Returns CFE of regional grid as a list of floats"""
    # get clean carriers
    clean_carriers = [
        i
        for i in n.carriers.query(" co2_emissions <= 0").index.tolist()
        if i in n.generators.carrier.tolist()
    ]
    # get clean generators
    clean_generators_grid = n.generators.loc[
        (n.generators.carrier.isin(clean_carriers))
        & (~n.generators.index.str.contains(ci_identifier))
    ].index
    # get all generators
    all_generators_grid = n.generators.loc[
        (~n.generators.index.str.contains(ci_identifier))
    ].index
    # return CFE
    return (
        (
            n.generators_t.p[clean_generators_grid].sum(axis=1)
            / n.generators_t.p[all_generators_grid].sum(axis=1)
        )
        .round(2)
        .tolist()
    )


if __name__ == "__main__":
    if "snakemake" not in globals():
        from helper import mock_snakemake

        snakemake = mock_snakemake(
            "run_hourly_matching",
        )
    CFE_Score = snakemake.wildcards.regime 
    run = snakemake.config["model_runs"][0]
    config = snakemake.config
    RunCFE(
        network=pypsa.Network(snakemake.input.solved_brownfield),
        ci_identifier=snakemake.config["global_vars"]["ci_label"],
        CFE_Score=CFE_Score,
        run=run,
        configs=config,
    )
    
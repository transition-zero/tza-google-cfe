import os
import sys
sys.path.append('../')
import pypsa
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from matplotlib.ticker import MaxNLocator

import src.helpers as helpers
import src.postprocess as postprocess
import src.plotting as plotting
import src.postprocess_plotting as postprocess_plotting

from src.prepare_brownfield_network import SetupBrownfieldNetwork
from src.prepare_network_for_cfe import PrepareNetworkForCFE

def cfe_constraint(
        n : pypsa.Network, 
        GridCFE : list, 
        ci_buses : list, 
        ci_identifier : str, 
        CFE_Score : float,
    ) -> pypsa.Network:
    '''Set CFE constraint
    '''
    for bus in ci_buses:
        # ---
        # fetch necessary variables to implement CFE

        CI_Demand = (
            n.loads_t.p_set.filter(regex=bus).filter(regex=ci_identifier).values.flatten()
        )

        CI_StorageCharge = (
            n.model.variables['Link-p'].sel(
                Link=[i for i in n.links.index if ci_identifier in i and 'Charge' in i and bus in i]
            )
            .sum(dims='Link')
        )

        CI_StorageDischarge = (
            n.model.variables['Link-p'].sel(
                Link=[i for i in n.links.index if ci_identifier in i and 'Discharge' in i and bus in i]
            )
            .sum(dims='Link')
        )

        CI_GridExport = (
            n.model.variables['Link-p'].sel(
                Link=[i for i in n.links.index if ci_identifier in i and 'Export' in i and bus in i]
            )
            .sum(dims='Link')
        )

        CI_GridImport = (
            n.model.variables['Link-p'].sel(
                Link=[i for i in n.links.index if ci_identifier in i and 'Import' in i and bus in i]
            )
            .sum(dims='Link')
        )

        CI_PPA = (
            n.model.variables['Generator-p'].sel(
                Generator=[i for i in n.generators.index if ci_identifier in i and 'PPA' in i and bus in i]
            )
            .sum(dims='Generator')
        )

        # Constraint 1: Hourly matching
        # ---------------------------------------------------------------

        n.model.add_constraints(
            CI_Demand == CI_PPA - CI_GridExport + CI_GridImport + CI_StorageDischarge - CI_StorageCharge
        )

        # Constraint 2: CFE target
        # ---------------------------------------------------------------
        n.model.add_constraints(
            ( CI_PPA - CI_GridExport + (CI_GridImport * list(GridCFE) ) ).sum() >= ( (CI_StorageCharge - CI_StorageDischarge) + CI_Demand ).sum() * CFE_Score, 
        )

        # Constraint 3: Excess
        # ---------------------------------------------------------------
        n.model.add_constraints(
            CI_GridExport.sum() <= sum(CI_Demand) * configs['global_vars']['maximum_excess_export'],
        )

        # Constraint 4: Battery can only be charged by clean PPA (not grid)
        # ---------------------------------------------------------------
        n.model.add_constraints(
            CI_PPA >= CI_StorageCharge,
        )

    return n


def GetGridCFE(n:pypsa.Network, ci_identifier, system_boundary='Local'):
    '''Returns CFE of regional grid as a list of floats
    '''
    # TODO: can we add an option to toggle expansion of system boundary (e.g., local, anytown, anycountry, anothercountry etc.)
    # get clean carriers
    clean_carriers = [
        i for i in n.carriers.query(" co2_emissions <= 0").index.tolist() 
        if i in n.generators.carrier.tolist()
    ]
    # get clean generators
    clean_generators_grid = (
        n.generators.loc[ 
            (n.generators.carrier.isin(clean_carriers)) &
            (~n.generators.index.str.contains(ci_identifier))
        ]
        .index
    )
    # get all generators
    all_generators_grid = (
        n.generators.loc[ 
            (~n.generators.index.str.contains(ci_identifier))
        ]
        .index
    )
    # return CFE
    return (n.generators_t.p[clean_generators_grid].sum(axis=1) / n.generators_t.p[all_generators_grid].sum(axis=1)).round(2).tolist()


def PostProcessBrownfield(n : pypsa.Network):
    components = ['generators', 'links', 'storage_units']
    for c in components:
        # Fix p_nom to p_nom_opt for each component in brownfield network
        getattr(n, c)['p_nom'] = getattr(n, c)['p_nom_opt']
        # make everything non-extendable
        getattr(n, c)['p_nom_extendable'] = False
        # ...besides the C&I assets
        getattr(n, c).loc[ getattr(n, c).index.str.contains(ci_identifier), 'p_nom_extendable' ] = True
    return n


def RunBrownfieldSimulation(run, configs):
    '''Setup and run the brownfield simulation
    '''
    N_BROWNFIELD = SetupBrownfieldNetwork(run, configs)

    N_BROWNFIELD = (
        PrepareNetworkForCFE(
            N_BROWNFIELD, 
            buses_with_ci_load=run['nodes_with_ci_load'],
            ci_load_fraction=run['ci_load_fraction'],
            technology_palette=configs['technology_palette'][ run['palette'] ],
            p_nom_extendable=False,
        )
    )
    
    print('prepared network for CFE')
    print('Begin solving...')

    N_BROWNFIELD.optimize(solver_name='gurobi')

    N_BROWNFIELD.export_to_netcdf(
        os.path.join(
            configs['paths']['output_model_runs'], 
            run['name'], 
            'solved_networks', 
            'brownfield_' + str(configs['global_vars']['year']) + '.nc'
        )
    )

    return N_BROWNFIELD


def RunRES100(N_BROWNFIELD : pypsa.Network):
    '''
    TODO: 
    Right now, this assumes that we apply 100% RES at each bus, but in reality this type 
    of procurement can happen at any bus. We need to think about how to implement this.
    '''
    
    # make a copy of the brownfield
    N_RES_100 = N_BROWNFIELD.copy()

    # post-process to set what is expandable and non-expandable
    N_RES_100 = PostProcessBrownfield(N_RES_100)

    # init linopy model
    N_RES_100.optimize.create_model()

    for bus in run['nodes_with_ci_load']:

        # get total C&I load (float)
        CI_Demand = (
            N_RES_100.loads_t.p_set
            .filter(regex=bus)
            .filter(regex=ci_identifier)
            .sum()
            .sum()
        )

        # get grid exports
        CI_GridExport = (
            N_RES_100.model.variables['Link-p'].sel(
                Link=[i for i in N_RES_100.links.index if ci_identifier in i and 'Export' in i and bus in i]
            )
            .sum(dims='Link')
        )

        # get total PPA procurement (linopy.Var)
        ci_ppa_generators = (
            N_RES_100.generators.loc[
                (N_RES_100.generators.bus.str.contains(bus)) &
                (N_RES_100.generators.bus.str.contains(ci_identifier))
            ]
            .index
            .tolist()
        ) # get c&i ppa generators

        CI_PPA = (
            N_RES_100
            .model
            .variables['Generator-p']
            .sel(
                Generator=ci_ppa_generators
            )
            .sum()
        )

        # get clean carriers in the regional grid
        clean_carriers = [
            i for i in N_RES_100.carriers.query(" co2_emissions <= 0").index.tolist() 
            if i in N_RES_100.generators.carrier.tolist()
        ]

        # clean generators
        clean_region_generators = [
            i for i in N_RES_100.generators.loc[ N_RES_100.generators.carrier.isin(clean_carriers) ].index
            if ci_identifier not in i and bus[0:3] in i
        ]

        GRID_CLEAN_GEN = (
            N_RES_100
            .model
            .variables['Generator-p']
            .sel(
                Generator=clean_region_generators
            )
            .sum()
        )

        # Constraint 1: Annual matching
        # ---------------------------------------------------------------
        N_RES_100.model.add_constraints(
            CI_PPA >= (RES_TARGET/100) * CI_Demand, #+ GRID_CLEAN_GEN
            name = f'{RES_TARGET}_RES_constraint_{bus}',
        )

        # Constraint 2: Excess (export from C&I system to grid)
        # ---------------------------------------------------------------
        N_RES_100.model.add_constraints(
            CI_GridExport.sum() <= CI_Demand * configs['global_vars']['maximum_excess_export'],
        )

    N_RES_100.optimize.solve_model(solver_name = 'gurobi')

    N_RES_100.export_to_netcdf(
        os.path.join(
            configs['paths']['output_model_runs'], 
            run['name'], 
            'solved_networks', 
            'annual_matching_' + 'RES' + str(RES_TARGET) + '_' + str(configs['global_vars']['year']) + '.nc'
        )
    )

    return N_RES_100


def RunCFE(N_BROWNFIELD : pypsa.Network, CFE_Score):
    '''Run 24/7 CFE scenario
    '''

    N_CFE = N_BROWNFIELD.copy()
    N_CFE = PostProcessBrownfield(N_CFE)

    # init linopy model
    N_CFE.optimize.create_model()

    # Run a set of iterations to calculate GridSupply CFE
    count = 1
    GridSupplyCFE = pd.DataFrame({})
    GridCFE = [0 for i in range(N_CFE.snapshots.size)]
    GridSupplyCFE[f'iteration_{count}'] = GridCFE

    # set CFE constraint
    N_CFE = cfe_constraint(
        N_CFE, 
        GridCFE, 
        run['nodes_with_ci_load'], 
        ci_identifier, 
        CFE_Score
    )

    # optimise
    N_CFE.optimize.solve_model(solver_name = 'gurobi')

    # get GridCFE
    GridCFE = GetGridCFE(N_CFE, ci_identifier)
    count += 1
    GridSupplyCFE[f'iteration_{count}'] = GridCFE

    # calculate difference between iterations with a maximum of 10 loops
    max_iterations = 10
    while (GridSupplyCFE[f'iteration_{count}'].sum() - GridSupplyCFE[f'iteration_{count-1}'].sum()) > 0.01 and count < max_iterations:
        N_CFE = cfe_constraint(
            N_CFE, 
            GridCFE, 
            run['nodes_with_ci_load'], 
            ci_identifier, 
            CFE_Score
        )
        N_CFE.optimize.solve_model(solver_name='gurobi')
        GridCFE = GetGridCFE(N_CFE, ci_identifier)
        count += 1
        GridSupplyCFE[f'iteration_{count}'] = GridCFE

    # save iteration results
    helpers.setup_dir(
        path_to_dir=os.path.join(configs['paths']['output_model_runs'], run['name'], 'grid_supply_cfe_iterations')
    )

    GridSupplyCFE.to_csv(
        os.path.join(
            configs['paths']['output_model_runs'], run['name'], 'grid_supply_cfe_iterations',
            'cfe' + str(int(CFE_Score*100)) + '.csv'
        )
    )

    N_CFE.export_to_netcdf(
        os.path.join(
            configs['paths']['output_model_runs'], 
            run['name'], 
            'solved_networks', 
            'hourly_matching_' + 'CFE' + str(int(CFE_Score*100)) + '_' + str(configs['global_vars']['year']) + '.nc'
        )
    )


if __name__ == '__main__':

    print('*'*100)
    print('BEGIN MODEL RUNS')
    print('')

    # setup params
    RES_TARGET = 100
    ci_identifier = 'C&I'

    # get config file
    configs = helpers.load_configs('configs.yaml')

    # ----------------------------------------------------------------------
    # RUN SCENARIOS
    # ----------------------------------------------------------------------
    # scenarios = {}
    # for run in configs['model_runs']:

    #     # setup a directory for outputs
    #     helpers.setup_dir(
    #         path_to_dir=configs['paths']['output_model_runs'] + run['name'] + '/solved_networks/'
    #     )

    #     print('Running: ' + run['name'])

    #     # Run brownfield
    #     print('Compute brownfield scenario...')
    #     N_BROWNFIELD = RunBrownfieldSimulation(run, configs)

    #     # 100% RES SIMULATION
    #     print(f'Computing annual matching scenario (RES Target: {int(RES_TARGET)}%)...')
    #     RunRES100(N_BROWNFIELD)

    #     # Compute hourly matching scenarios
    #     for CFE_Score in run['cfe_score']:
    #         print(f'Computing hourly matching scenario (CFE: {int(CFE_Score*100)}...')
    #         RunCFE(N_BROWNFIELD, CFE_Score=CFE_Score)

    # ----------------------------------------------------------------------
    # MAKE PLOTS FOR EACH SCENARIO
    # ----------------------------------------------------------------------

    # def summarise_results():
    #     pass
    
    for run in configs['model_runs']:

        path_to_run_dir = (
            os.path.join(
                configs['paths']['output_model_runs'], run['name'],
            )
        )

        postprocess.plot_results(path_to_run_dir)

    print('*'*100)
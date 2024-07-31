import os
import yaml
import pypsa

import tz_pypsa as tza
from tz_pypsa.model import Model
from _helpers import *


# get configs
def load_configs():
    with open('01_configs.yaml', 'r') as file:
        configs = yaml.safe_load(file)
    return configs


# run brownfield
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


def run_annual_matching_scenario(
        run : dict = None,
        configs : dict = None,
        brownfield_network : pypsa.Network = None,
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

    # ----
    # ADJUST NETWORK TO DO ANNUAL MATCHING

    for bus in run['nodes_with_cfe_load']:

        # -----------------------------------
        # Step 1: 
        # Separate cfe and non-cfe load
        # -----------------------------------

        # subtract out cfe load from bus
        network.loads_t.p_set[bus] *= (1 - run['cfe_load_fraction'])

        # add cfe load to bus as a separate load
        network.add(
            "Load",
            bus + '-cfe-load',
            bus=bus,
            p_set=network.loads_t.p_set[bus] * run['cfe_load_fraction'],
        )

        # -----------------------------------
        # Step 2: 
        # Add new generators solely for cfe matching
        # -----------------------------------

        for technology in configs['cfe_technology_palette'][run['palette']]:
            
            # add generator if technolgy is a generator
            if technology in network.generators.type.unique():

                # get params
                params = (
                    network
                    .generators
                    .loc[ 
                        network.generators.type == technology
                    ]
                    .groupby(by='type')
                    .first()
                    .melt()
                    .set_index('attribute')
                    ['value']
                    .to_dict()
                )

                # get cf if renewable
                cf = network.generators_t.p_max_pu.filter(regex = bus + '-' + technology)

                if cf.empty:
                    cf = params['p_max_pu']
                else:
                    cf = cf.iloc[:,0].values

                # add generator
                network.add(
                    'Generator', # PyPSA component
                    bus + '-' + technology + '-ext-' + str(params['build_year']) + '-annual-matching', # generator name
                    type = technology, # technology type (e.g., solar, gas-ccgt etc.)
                    bus = bus, # region/bus/balancing zone
                    # ---
                    # unique technology parameters by bus
                    p_nom = 0, # starting capacity (MW)
                    p_nom_min = 0, # minimum capacity (MW)
                    p_max_pu = cf, # capacity factor
                    p_min_pu = params['p_min_pu'], # minimum capacity factor
                    efficiency = params['efficiency'], # efficiency
                    ramp_limit_up = params['ramp_limit_up'], # per unit
                    ramp_limit_down = params['ramp_limit_down'], # per unit
                    # ---
                    # universal technology parameters
                    p_nom_extendable = True, # can the model build more?
                    capital_cost = params['capital_cost'], # currency/MW
                    marginal_cost = params['marginal_cost'], # currency/MWh
                    carrier = params['carrier'], # commodity/carrier
                    build_year = params['build_year'], # year available from
                    lifetime = params['lifetime'], # years
                    start_up_cost = params['start_up_cost'], # currency/MW
                    shut_down_cost = params['shut_down_cost'], # currency/MW
                    committable = params['committable'], # UNIT COMMITMENT
                    ramp_limit_start_up = params['ramp_limit_start_up'], # 
                    ramp_limit_shut_down = params['ramp_limit_shut_down'], # 
                    min_up_time = params['min_up_time'], # 
                    min_down_time = params['min_down_time'], # 
                )
            
            # add storage if technolgy is a storage unit
            if technology in network.storage_units.carrier.unique():

                # get params
                params = (
                    network
                    .storage_units
                    .loc[ 
                        network.storage_units.carrier == technology
                    ]
                    .groupby(by='type')
                    .first()
                    .melt()
                    .set_index('attribute')
                    ['value']
                    .to_dict()
                )

                # add storage unit
                network.add(
                    'StorageUnit',
                    bus + '-' + technology + '-ext-' + str(params['build_year']) + '-annual-matching',
                    bus=bus, 
                    carrier=params['carrier'],
                    p_nom=0, # starting capacity (MW)
                    p_nom_min=0, # minimum capacity (MW)
                    p_nom_extendable=True,
                    capital_cost=params['capital_cost'],
                    marginal_cost=params['marginal_cost'],
                    build_year=params['build_year'],
                    lifetime=params['lifetime'],
                    state_of_charge_initial=params['state_of_charge_initial'],
                    max_hours=params['max_hours'],
                    efficiency_store=params['efficiency_store'],
                    efficiency_dispatch=params['efficiency_dispatch'],
                    standing_loss=params['standing_loss'],
                    cyclic_state_of_charge=params['cyclic_state_of_charge'],
                )

        # ----
        # ADD ANNUAL MATCHING CONSTRAINT
        lhs_generators = [i for i in network.generators.index if 'annual-matching' in i]
        rhs_load = network.loads_t.p_set[bus + '-cfe-load'].sum().sum()
        
        tza.constraints.constr_annual_matching(
            network = network,
            lhs_generators = lhs_generators,
            rhs_min_generation = rhs_load,
            sign = '>=',
            name = 'annual_matching_constraint_{bus}',
        )

    # solve
    print('Beginning optimisation')

    network.optimize.solve_model(
        solver_name=configs['global_vars']['solver'],
    )

    # save results
    setup_dir(
        path_to_dir=configs['paths']['output_model_runs'] + run['name'] + '/solved_networks/'
    )

    network.export_to_netcdf(
        os.path.join(
            configs['paths']['output_model_runs'], run['name'], 'solved_networks', 'annual_matching_' + str(configs['global_vars']['year']) + '.nc'
        )
    )

    return network


def run_hourly_matching_scenario(
        run : dict = None,
        configs : dict = None,
        brownfield_network : pypsa.Network = None,
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

    # ----
    # ADJUST NETWORK TO DO ANNUAL MATCHING

    for bus in run['nodes_with_cfe_load']:

        # -----------------------------------
        # Step 1: 
        # Separate cfe and non-cfe load
        # -----------------------------------

        # subtract out cfe load from bus
        network.loads_t.p_set[bus] *= (1 - run['cfe_load_fraction'])

        # add cfe load to bus as a separate load
        network.add(
            "Load",
            bus + '-cfe-load',
            bus=bus,
            p_set=network.loads_t.p_set[bus] * run['cfe_load_fraction'],
        )

        # -----------------------------------
        # Step 2: 
        # Add new generators solely for cfe matching
        # -----------------------------------

        for technology in configs['cfe_technology_palette'][run['palette']]:
            
            # add generator if technolgy is a generator
            if technology in network.generators.type.unique():

                # get params
                params = (
                    network
                    .generators
                    .loc[ 
                        network.generators.type == technology
                    ]
                    .groupby(by='type')
                    .first()
                    .melt()
                    .set_index('attribute')
                    ['value']
                    .to_dict()
                )

                # get cf if renewable
                cf = network.generators_t.p_max_pu.filter(regex = bus + '-' + technology)

                if cf.empty:
                    cf = params['p_max_pu']
                else:
                    cf = cf.iloc[:,0].values

                # add generator
                network.add(
                    'Generator', # PyPSA component
                    bus + '-' + technology + '-ext-' + str(params['build_year']) + '-annual-matching', # generator name
                    type = technology, # technology type (e.g., solar, gas-ccgt etc.)
                    bus = bus, # region/bus/balancing zone
                    # ---
                    # unique technology parameters by bus
                    p_nom = 0, # starting capacity (MW)
                    p_nom_min = 0, # minimum capacity (MW)
                    p_max_pu = cf, # capacity factor
                    p_min_pu = params['p_min_pu'], # minimum capacity factor
                    efficiency = params['efficiency'], # efficiency
                    ramp_limit_up = params['ramp_limit_up'], # per unit
                    ramp_limit_down = params['ramp_limit_down'], # per unit
                    # ---
                    # universal technology parameters
                    p_nom_extendable = True, # can the model build more?
                    capital_cost = params['capital_cost'], # currency/MW
                    marginal_cost = params['marginal_cost'], # currency/MWh
                    carrier = params['carrier'], # commodity/carrier
                    build_year = params['build_year'], # year available from
                    lifetime = params['lifetime'], # years
                    start_up_cost = params['start_up_cost'], # currency/MW
                    shut_down_cost = params['shut_down_cost'], # currency/MW
                    committable = params['committable'], # UNIT COMMITMENT
                    ramp_limit_start_up = params['ramp_limit_start_up'], # 
                    ramp_limit_shut_down = params['ramp_limit_shut_down'], # 
                    min_up_time = params['min_up_time'], # 
                    min_down_time = params['min_down_time'], # 
                )
            
            # add storage if technolgy is a storage unit
            if technology in network.storage_units.carrier.unique():

                # get params
                params = (
                    network
                    .storage_units
                    .loc[ 
                        network.storage_units.carrier == technology
                    ]
                    .groupby(by='type')
                    .first()
                    .melt()
                    .set_index('attribute')
                    ['value']
                    .to_dict()
                )

                # add storage unit
                network.add(
                    'StorageUnit',
                    bus + '-' + technology + '-ext-' + str(params['build_year']) + '-annual-matching',
                    bus=bus, 
                    carrier=params['carrier'],
                    p_nom=0, # starting capacity (MW)
                    p_nom_min=0, # minimum capacity (MW)
                    p_nom_extendable=True,
                    capital_cost=params['capital_cost'],
                    marginal_cost=params['marginal_cost'],
                    build_year=params['build_year'],
                    lifetime=params['lifetime'],
                    state_of_charge_initial=params['state_of_charge_initial'],
                    max_hours=params['max_hours'],
                    efficiency_store=params['efficiency_store'],
                    efficiency_dispatch=params['efficiency_dispatch'],
                    standing_loss=params['standing_loss'],
                    cyclic_state_of_charge=params['cyclic_state_of_charge'],
                )

        # ----
        # ADD ANNUAL MATCHING CONSTRAINT
        lhs_generators = [i for i in network.generators.index if 'annual-matching' in i]
        rhs_load = network.loads_t.p_set[bus + '-cfe-load']
        
        tza.constraints.constr_hourly_matching(
            network = network,
            lhs_generators = lhs_generators,
            rhs_load = rhs_load,
            sign = '>=',
            name = 'hourly_matching_constraint_{bus}',
        )

    # solve
    print('Beginning optimisation')

    network.optimize.solve_model(
        solver_name=configs['global_vars']['solver'],
    )

    # save results
    setup_dir(
        path_to_dir=configs['paths']['output_model_runs'] + run['name'] + '/solved_networks/'
    )

    network.export_to_netcdf(
        os.path.join(
            configs['paths']['output_model_runs'], run['name'], 'solved_networks', 'hourly_matching_' + str(configs['global_vars']['year']) + '.nc'
        )
    )

    return network


if __name__ == '__main__':

    # get config file
    configs = load_configs()

    # run scenarios
    for run in configs['model_runs']:

        print('Running: ' + run['core_model'])

        print('computing brownfield scenario...')

        brownfield_network = (
            run_brownfield_scenario(
                run,
                configs,
            )
        )

        # print('computing annual matching scenario...')

        # run_annual_matching_scenario(
        #     run,
        #     configs,
        #     brownfield_network,
        # )

        print('computing hourly matching scenario...')

        run_hourly_matching_scenario(
            run,
            configs,
            brownfield_network,
        )

def get_local_grid_cfe(network, local_grid_bus):
    '''Returns a CFE score for a given bus.
    '''

    clean_carriers = [i for i in network.carriers.query(" co2_emissions <= 0 ").index.to_list()  if i in network.generators.carrier.unique()]
    dirty_carriers = [i for i in network.carriers.query(" co2_emissions > 0 ").index.to_list()  if i in network.generators.carrier.unique()]

    # calculate local grid clean resources
    local_clean_generation = (
        network
        .generators_t
        .p
        .filter(regex=local_grid_bus)
        .T
        .groupby(by=network.generators.carrier)
        .sum()
        .loc[clean_carriers]
        .sum(axis=1)
        .sum()
    )

    # calculate local grid dirty resources
    local_dirty_generation = (
        network
        .generators_t
        .p
        .filter(regex=local_grid_bus)
        .T
        .groupby(by=network.generators.carrier)
        .sum()
        .loc[dirty_carriers]
        .sum(axis=1)
        .sum()
    )

    local_grid_cfe_score = local_clean_generation / (local_clean_generation + local_dirty_generation)

    return local_grid_cfe_score


def hourly_matching(lp_model, network, ci_nodes, cfe_score, configs, palette='palette_1'):
    '''Sets hourly matching constraints at C&I nodes
    '''

    # # compute grid supply cfe
    # clean_country_generators = network.generators.index[
    #     network.generators.bus.isin(country_buses) & network.generators.carrier.isin(clean_techs)
    # ]
    # clean_country_links = network.links.index[
    #     network.links.bus1.isin(country_buses) & n.links.carrier.isin(clean_techs)
    # ]
    # clean_country_storage_units = network.storage_units.index[
    #     network.storage_units.bus.isin(country_buses)
    #     & network.storage_units.carrier.isin(clean_techs)
    # ]
    # clean_grid_generators = network.generators.index[
    #     network.generators.bus.isin(grid_buses) & network.generators.carrier.isin(clean_techs)
    # ]
    # dirty_grid_links = network.links.index[
    #     network.links.bus1.isin(grid_buses) & network.links.carrier.isin(emitters)
    # ]

    # clean_country_gens = network.generators_t.p[clean_country_generators].sum(axis=1)
    # clean_country_ls = -network.links_t.p1[clean_country_links].sum(axis=1)
    # clean_country_sus = network.storage_units_t.p[clean_country_storage_units].sum(axis=1)
    # clean_country_resources = clean_country_gens + clean_country_ls + clean_country_sus

    # clean_grid_gens = network.generators_t.p[clean_grid_generators].sum(axis=1)
    # #clean_grid_sus = network.storage_units_t.p[clean_grid_storage_units].sum(axis=1)
    # #clean_grid_ls = -network.links_t.p1[clean_grid_links].sum(axis=1)
    # clean_grid_resources = clean_grid_gens #+ clean_grid_sus #+ clean_grid_ls 

    # dirty_grid_resources = -network.links_t.p1[dirty_grid_links].sum(axis=1)

    # import_cfe = clean_grid_resources / (clean_grid_resources + dirty_grid_resources)
    # grid_supply_cfe = (clean_country_resources + country_import * import_cfe) / (clean_country_resources + dirty_country_resources + country_import)

    for bus in ci_nodes:

        # get clean generators
        clean_generators = [
            i for i in network.generators.index 
            if network.generators.loc[i].type in configs['technology_palette'][palette]
            and bus in i
        ]

        clean_cfe_generators = [i for i in clean_generators if configs['global_vars']['ci_label'] in i]

        print('> clean_generators', clean_generators)
        print('> clean_cfe_generators', clean_cfe_generators)

        # get total generation by clean generators
        cfe_gen = (
            lp_model
            .variables['Generator-p']
            .sel(Generator=clean_cfe_generators)
        )

        # get import to C&I bus
        import_links = [
            i for i in network.links.index
            if configs['global_vars']['ci_label'] in network.links.loc[i].bus1
        ]

        ci_import = (
            (
                lp_model
                .variables['Link-p']
                .sel(Link=import_links)
            )
            #* grid_supply_cfe
        ).sum()

        # get exports by C&I bus
        export_links = [
            i for i in network.links.index
            if configs['global_vars']['ci_label'] in network.links.loc[i].bus0
        ]

        ci_export = (
            (
                lp_model
                .variables['Link-p']
                .sel(Link=export_links)
            )
        ).sum()

        # get total C&I load
        total_ci_load = (
            network
            .loads_t
            .p_set[
                bus + '-' + configs['global_vars']['ci_label']
            ]
            .sum()
        )

        print('> total_ci_load', total_ci_load)

        # get storage discharge
        cfe_storages = [
            i for i in network.storage_units.index 
            if network.storage_units.loc[i].carrier in configs['technology_palette'][palette]
            and bus in i and configs['global_vars']['ci_label'] in i
        ]

        print('> cfe_storages', cfe_storages)

        discharge = (
            lp_model
            .variables['StorageUnit-p_dispatch']
            .sel(StorageUnit=cfe_storages)
        )

        # get storage charge
        charge = (cfe_gen - discharge)

        # define LHS
        LHS = cfe_gen.sum() + discharge.sum() + charge.sum()  #+ (ci_export - ci_import) #+ discharge + charge

        # define constraint
        lp_model.add_constraints(
            LHS >= cfe_score * total_ci_load,
            name = f'cfe_constraint_{bus}',
        )

        # # additionality
        # if configs['global_vars']['enable_additionality']:
        #     # get baseline clean generation
        #     brownfield_clean_generation = network.generators_t.p[clean_generators].sum().sum()
        #     # add constraint
        #     lp_model.add_constraints(
        #         cfe_gen.sum() >= brownfield_clean_generation + total_ci_load,
        #         name = f'hourly_matching_additionality_{bus}',
        #     )

    return lp_model, network


def hourly_matching3(lp_model, network, ci_nodes, cfe_score, configs, palette='palette_1'):
    weights = network.snapshot_weightings["generators"]

    for bus in ci_nodes:

        clean_carriers = network.carriers.query(" co2_emissions <= 0 ").index.to_list() 

        clean_gens = [
            i for i in network.generators.index 
            if network.generators.loc[i].carrier in clean_carriers
            and bus in i
            and configs['global_vars']['ci_label'] in i
        ]

        gen_sum = (lp_model["Generator-p"].loc[:, clean_gens] * weights).sum()
        
        ci_stores = [
            i for i in network.storage_units.index 
            if bus in i and configs['global_vars']['ci_label'] in i
        ]

        storage_dischargers = network.links.loc[ network.links.bus0 == ci_stores[0] ].index.to_list()
        discharge_sum = (
            lp_model["Link-p"]
            #.loc[:, storage_dischargers]
            .sel(Link=storage_dischargers)
            * network.links.loc[storage_dischargers, "efficiency"]
            #* weights
            * 1
        ).sum()

        storage_chargers = network.links.loc[ network.links.bus1 == ci_stores[0] ].index.to_list()
        charge_sum = ( -1 * (
            lp_model["Link-p"]
            #.loc[:, storage_chargers] * 1
            .sel(Link=storage_chargers)
            )
            .sum() #* weights
        )

        ci_export_links = [
            i for i in network.links.index
            if bus in i
            and 'virtual-link' in i
            and configs['global_vars']['ci_label'] in network.links.loc[i].bus0
        ]

        ci_export = (
            lp_model
            .variables['Link-p']
            .sel(Link=ci_export_links)
            #.sum()
        )

        ci_import_links = [
            i for i in network.links.index
            if bus in i
            and 'virtual-link' in i
            and configs['global_vars']['ci_label'] in network.links.loc[i].bus1
        ]

        ci_import = (
            lp_model
            .variables['Link-p']
            .sel(Link=ci_import_links)
            #.sum()
        )

        grid_supply_cfe = get_local_grid_cfe(network, bus)
        grid_sum = (
            (-1 * ci_export * weights)
            + (
                ci_import
                * network.links.efficiency.max()
                * grid_supply_cfe
                * weights
            )
        ).sum()  # linear expr

        lhs = gen_sum + grid_sum + discharge_sum + charge_sum

        total_ci_load = (
            network
            .loads_t
            .p_set[
                bus + '-' + configs['global_vars']['ci_label']
            ]
            .sum()
        )

        lp_model.add_constraints(lhs >= cfe_score * total_ci_load, name="CFE_constraint" + bus)

    return lp_model, network


def hourly_matching2(lp_model, network, ci_nodes, cfe_score, configs, palette='palette_1'):
    '''Sets hourly matching constraints at C&I nodes
    '''

    # ------------------
    # CFE CONSTRAINT

    for bus in ci_nodes:

        # ---
        # Get load at C&I bus
        total_ci_load = (
            network
            .loads_t
            .p_set[
                bus + '-' + configs['global_vars']['ci_label']
            ]
            #.sum()
        )

        print('> ci-bus', bus + '-' + configs['global_vars']['ci_label'])
        print('> total_ci_load', total_ci_load)

        # ---
        # Get bespoke PPA procurement

        # get clean generators
        clean_carriers = network.carriers.query(" co2_emissions <= 0 ").index.to_list() 

        clean_generators_ppa_procured = [
            i for i in network.generators.index 
            if network.generators.loc[i].carrier in clean_carriers
            and bus in i
            and configs['global_vars']['ci_label'] in i
        ]

        print('> clean_generators', clean_generators_ppa_procured)

        # get total generation by clean generators
        ci_generation = (
            lp_model
            .variables['Generator-p']
            .sel(Generator=clean_generators_ppa_procured)
            #.sum()
        )

        # ---
        # Get bespoke PPA storage charge/discharge 

        # get total storage charge
        ci_stores = [
            i for i in network.storage_units.index 
            if bus in i and configs['global_vars']['ci_label'] in i
        ]

        charge_link = network.links.loc[ network.links.bus1 == ci_stores[0] ].index.to_list()

        print('> clean_stores', ci_stores)
        print('> charge_link', charge_link)

        ci_charge = (
            lp_model
            .variables['Link-p']
            .sel(Link=charge_link)
            #.sum()
        )

        # get total storage discharge
        discharge_link = network.links.loc[ network.links.bus0 == ci_stores[0] ].index.to_list()

        ci_discharge = (
            lp_model
            .variables['Link-p']
            .sel(Link=discharge_link)
            #.sum()
        )

        print('> discharge_link', discharge_link)

        # ---
        # Get exports from C&I bus

        ci_export_links = [
            i for i in network.links.index
            if bus in i
            and 'virtual-link' in i
            and configs['global_vars']['ci_label'] in network.links.loc[i].bus0
        ]

        ci_export = (
            lp_model
            .variables['Link-p']
            .sel(Link=ci_export_links)
            #.sum()
        )

        print('> export_links', ci_export_links)

        # ---
        # Get imports into C&I bus

        ci_import_links = [
            i for i in network.links.index
            if bus in i
            and 'virtual-link' in i
            and configs['global_vars']['ci_label'] in network.links.loc[i].bus1
        ]

        ci_import = (
            lp_model
            .variables['Link-p']
            .sel(Link=ci_import_links)
            #.sum()
        )

        grid_supply_cfe = get_local_grid_cfe(network, bus)

        print('> import_links', ci_import_links)

        # # define LHS
        # lhs = ci_generation + (ci_charge - ci_discharge) + (ci_import*grid_supply_cfe - ci_export) #+ clean_storage_p_ppa_procured

        # # define constraint
        # lp_model.add_constraints(
        #     lhs >= cfe_score * total_ci_load, #+ cfe_storage_dispatch
        #     name = f'cfe_constraint_{bus}',
        # )

        # sum ci_procurement
        ci_procurement = ci_generation + ci_discharge - ci_charge #+ (ci_import*grid_supply_cfe - ci_export) #+ clean_storage_p_ppa_procured

        # define constraint
        lp_model.add_constraints(
            ci_procurement.sum() >= cfe_score * total_ci_load.sum(), #+ cfe_storage_dispatch
            name = f'cfe_constraint_{bus}',
        )

        # ------------------
        # STORAGE-LINK RELATIONSHIP

        ci_discharge = (
            lp_model
            .variables['Link-p']
            .sel(Link=discharge_link)
        )

        ci_storages = [
            i for i in network.storage_units.index 
            if bus in i and configs['global_vars']['ci_label'] in i
        ]

        ci_storage_unit_p = (
            lp_model
            .variables['StorageUnit-p_dispatch']
            .sel(StorageUnit=ci_storages)
        )

        lp_model.add_constraints(
            ci_storage_unit_p - ci_discharge >= 0, #+ cfe_storage_dispatch
            name = f'storage_link_relationship_{bus}',
        )
    
        # ------------------
        # EXCESS CONSTRAINT

        # define constraint
        lp_model.add_constraints(
            ci_export <= configs['global_vars']['maximum_excess_export'] * total_ci_load,
            name = f'excess_constraint_{bus}',
        )

    return lp_model, network


def annual_matching(lp_model, network, ci_nodes, cfe_score, configs):
    '''Sets annual matching constraints at C&I nodes
    '''
    unique_iso_codes = list({code[:3] for code in ci_nodes})

    for iso_code in unique_iso_codes:

        # get clean generators
        clean_carriers = network.carriers.query(" co2_emissions <= 0 ").index.to_list() 

        clean_generators = [
            i for i in network.generators.index 
            if network.generators.loc[i].carrier in clean_carriers
            and iso_code in i
            and configs['global_vars']['ci_label'] in i
        ]

        # get total C&I load
        total_ci_load = (
            network
            .loads_t
            .p_set
            .filter(regex = iso_code)
            .filter(regex = configs['global_vars']['ci_label'])
            .sum()
            .sum()
        )

        # get hourly dispatch from clean generators
        generation_clean_sum = (
            lp_model
            .variables['Generator-p']
            .sel(Generator=clean_generators)
            .sum()
        )

        # TODO: THIS CONSTRAINT NEEDS TO BE APPLIED IN EACH GEOGRAPHY
        # add constraint
        lp_model.add_constraints(
            generation_clean_sum >= cfe_score * total_ci_load,
            name = f'100_RES_constraint_{iso_code}',
        )

        # # ------------------
        # # EXCESS CONSTRAINT
        # ci_export_links = [
        #     i for i in network.links.index
        #     if iso_code in i
        #     and configs['global_vars']['ci_label'] in network.links.loc[i].bus0
        # ]

        # ci_export = (
        #     lp_model
        #     .variables['Link-p']
        #     .sel(Link=ci_export_links)
        #     .sum()
        # )

        # # define constraint
        # lp_model.add_constraints(
        #     ci_export <= configs['global_vars']['maximum_excess_export'] * total_ci_load,
        #     name = f'excess_constraint_{iso_code}',
        # )

    return lp_model, network


def constraint_clean_generation_target(lp_model, network, ci_nodes, configs):
    '''Sets targets for clean generation
    '''

    unique_iso_codes = list({code[:3] for code in ci_nodes})
    for iso_code in unique_iso_codes:

        clean_carriers = network.carriers.query(" co2_emissions <= 0 ").index.to_list() 

        clean_generators = [
            i for i in network.generators.index
            if network.generators.loc[i].carrier in clean_carriers
            and iso_code in i
            and configs['global_vars']['ci_label'] not in i
        ]

        # get total generation
        all_generators = [
            i for i in network.generators.index
            if iso_code in i
            and configs['global_vars']['ci_label'] not in i
        ]

        # get dispatch from clean generators
        generation_clean_sum = (
            lp_model
            .variables['Generator-p']
            .sel(Generator=clean_generators)
            .sum()
        )

        # get total dispatch 
        generation_total = (
            lp_model
            .variables['Generator-p']
            .sel(Generator=all_generators)
            .sum()
        )

        # define constraint
        lp_model.add_constraints(
            generation_clean_sum >= 0.4 * generation_total,
            name = f'brownfield_clean_gen_constraint',
        )

        return lp_model, network


def constraint_fossil_storage_charging(lp_model, network):
    '''Only allows charging of clean storage units by clean generators (i.e., non-emitting)
    '''
    for bus in network.buses.index:

        clean_carriers  = network.carriers.query(" co2_emissions <= 0").index
        dirty_carriers  = network.carriers.query(" co2_emissions > 0").index

        gens = (
            network
            .generators
            .query("bus == @bus ")
            .query("carrier.isin(@clean_carriers)")
            .index
        )

        stos = (
            network
            .storage_units
            .query("bus == @bus ")
            .query("carrier.isin(@clean_carriers)")
            .index
        )

        clean_gen_p = lp_model['Generator-p'].sel(Generator=gens).sum()
        clean_sto_p = lp_model['StorageUnit-p_dispatch'].sel(StorageUnit=stos).sum()

        lp_model.add_constraints(
            clean_gen_p - clean_sto_p >= 0,
            #name = f'cfe_constraint_{bus}',
        )
    
    return lp_model, network
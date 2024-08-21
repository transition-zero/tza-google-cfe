

def fossil_storage_charging_constraint(lp_model, network, configs):
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
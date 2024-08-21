import pandas as pd

def aggregate_capacity(
        scenarios,
        components = ['generators', 'storage_units', 'links'],
        groupby=['carrier'], 
        attrs=['p_nom', 'p_nom_opt']
    ):
    '''Aggregates the capacity of components across a set of scenarios.
    '''
    def get_capacity(
            data, 
            scenario_name
        ):

        capacity_frames = []
        for component in components:
            if hasattr(data, component):
                capacity_frame = (
                    getattr(data, component)
                    .groupby(by=groupby)
                    .sum(numeric_only=True)[attrs]
                    .fillna(0)
                    .assign(scenario=scenario_name)
                )
                capacity_frames.append(capacity_frame)
        
        return pd.concat(capacity_frames)

    return (
        pd
        .concat(
            [
                get_capacity(scenario_data, scenario_name) for scenario_name, scenario_data in scenarios.items()
            ]
        )
    )
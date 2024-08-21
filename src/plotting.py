import pandas as pd
import plotly.express as px

def plot_capacity_bar(
        capacity : pd.DataFrame,
        carriers : pd.DataFrame,
        x : str = 'scenario',
        y : str = 'p_nom_opt',
        hue : str = 'carrier',
        height : int = 500,
        width : int = 800,
        xlabel : str = 'Scenario',
        ylabel : str = 'Optimal Capacity (p_nom_opt)',
        title : str = '',
    ):

    return px.bar(
        capacity,
        x=x,
        y=y,
        color=hue,
        color_discrete_map={carrier: carriers.loc[carrier].color for carrier in capacity.carrier.unique()},
        title=title,
        labels={y: ylabel, x: xlabel},
        height=height,
        width=width,
    )
import pandas as pd
import plotly.express as px

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

def bar_plot_2row(
        df1 : pd.DataFrame,
        df2 : pd.DataFrame,
        ylabel = 'C&I Series',
        xlabel = 'C&I CFE Score\n[%]',
        color = None,
        legend_anchor = (1.12, 0.6),
        width_ratios=[1, 1],
        figsize=(6, 5),
):

    # Create a figure
    fig = plt.figure(figsize=figsize)

    # Create a GridSpec with 1 row and 2 columns, setting the width ratios
    gs = gridspec.GridSpec(1, 2, width_ratios=width_ratios)

    # create subplots
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1], sharey=ax0)

    # colormap = [solved_networks['n_bf'].carriers.color.to_dict().get(i, 'red') for i in df1.columns]

    # plot reference
    df1.plot(
        kind='bar', 
        stacked=True, 
        ax=ax0,
        color=color,
        legend=False,
        edgecolor='gray',
        width=0.4,
    )

    # plot reference
    df2.plot(
        kind='bar', 
        stacked=True, 
        ax=ax1,
        color=color,
        legend=False,
        edgecolor='gray',
        width=0.4,
    )

    # Titles
    ax0.set_title('a.', loc='left', fontweight='bold')
    ax1.set_title('b.', loc='left', fontweight='bold')

    # y-axes labels
    ax0.set_ylabel(ylabel)
    ax1.set_ylabel('')

    # x-axes labels
    ax0.set_xlabel('')
    ax1.set_xlabel('')

    # x-ticks
    # ax0.set_xticklabels(xticklabels[0])
    # ax1.set_xticklabels(xticklabels[1])

    # x-tick rotation
    ax0.tick_params(axis='x', rotation=0)
    ax1.tick_params(axis='x', rotation=0)

    # grids
    ax0.set_axisbelow(True)
    ax1.set_axisbelow(True)

    ax0.grid(which='major', axis='y', color='lightgray', linestyle=':', linewidth=1)
    ax1.grid(which='major', axis='y', color='lightgray', linestyle=':', linewidth=1)

    # padding
    gs.tight_layout(fig, rect=[0, 0, 0.8, 0.97])

    # legend
    # Customize the legend
    ax1.legend(
        loc='upper center',
        bbox_to_anchor=legend_anchor,
        ncol=1,
        frameon=False,
        title=None
    )

    return fig, ax0, ax1


def bar_plot_3row(
        df1 : pd.DataFrame,
        df2 : pd.DataFrame,
        df3 : pd.DataFrame,
        ylabel = 'C&I Series',
        xlabel = 'C&I CFE Score\n[%]',
        color = None,
        legend_anchor = (1.12, 0.6),
        width_ratios=[1, 1, 5],
        figsize=(10, 5),
):

    # Create a figure
    fig = plt.figure(figsize=figsize)

    # Create a GridSpec with 1 row and 2 columns, setting the width ratios
    gs = gridspec.GridSpec(1, 3, width_ratios=width_ratios)

    # create subplots
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1], sharey=ax0)
    ax2 = fig.add_subplot(gs[2], sharey=ax0)

    # colormap = [solved_networks['n_bf'].carriers.color.to_dict().get(i, 'red') for i in df1.columns]

    # plot reference
    df1.plot(
        kind='bar', 
        stacked=True, 
        ax=ax0,
        color=color,
        legend=False,
        edgecolor='gray',
        width=0.4,
    )

    # plot reference
    df2.plot(
        kind='bar', 
        stacked=True, 
        ax=ax1,
        color=color,
        legend=False,
        edgecolor='gray',
        width=0.4,
    )

    # plot ppa
    df3.plot(
        kind='bar', 
        stacked=True, 
        ax=ax2,
        color=color,
        edgecolor='gray',
        width=0.8,
        label='test',
    )

    # Titles
    ax0.set_title('a.', loc='left', fontweight='bold')
    ax1.set_title('b.', loc='left', fontweight='bold')
    ax2.set_title('c.', loc='left', fontweight='bold')

    # y-axes labels
    ax0.set_ylabel(ylabel)
    ax1.set_ylabel('')

    # x-axes labels
    ax0.set_xlabel('')
    ax1.set_xlabel('')
    ax2.set_xlabel(xlabel)

    # x-ticks
    # ax0.set_xticklabels(xticklabel1)
    # ax1.set_xticklabels(xticklabel2)

    # x-tick rotation
    ax0.tick_params(axis='x', rotation=0)
    ax1.tick_params(axis='x', rotation=0)
    ax2.tick_params(axis='x', rotation=0)

    # grids
    ax0.set_axisbelow(True)
    ax1.set_axisbelow(True)
    ax2.set_axisbelow(True)

    ax0.grid(which='major', axis='y', color='lightgray', linestyle=':', linewidth=1)
    ax1.grid(which='major', axis='y', color='lightgray', linestyle=':', linewidth=1)
    ax2.grid(which='major', axis='y', color='lightgray', linestyle=':', linewidth=1)

    # padding
    gs.tight_layout(fig, rect=[0, 0, 0.8, 0.97])

    # legend
    # Customize the legend
    ax2.legend(
        loc='upper center',
        bbox_to_anchor=legend_anchor,
        ncol=1,
        frameon=False,
        title=None
    )

    return fig, ax0, ax1, ax2


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
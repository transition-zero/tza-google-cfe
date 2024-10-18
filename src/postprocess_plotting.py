import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

def set_tz_theme():
    '''Set the plotting theme for to match TransitionZero colour palette
    '''

    plt.rcParams.update({
        'figure.facecolor': '#1F283D',  # Background color of the entire figure (outer area)
        'axes.facecolor': '#1F283D',    # Background color of the plot (inside axes)
        'axes.edgecolor': 'white',      # Color of the axes/box edges
        'axes.labelcolor': 'white',     # Color of the axis labels
        'xtick.color': 'white',         # Color of the x-tick labels
        'ytick.color': 'white',         # Color of the y-tick labels
        'axes.spines.top': False,       # Remove the top spine (optional)
        'axes.spines.right': False,     # Remove the right spine (optional)
        'font.family': 'Arial',         # Font family set to Arial
        'axes.prop_cycle': plt.cycler(color=['#00C0B0', '#FE8348', '#008DCE', '#FFB405']),  # Custom color cycle
        'grid.color': 'white',          # Gridline color (if enabled)
        'grid.linestyle': ':',          # Gridline style (if enabled)
        'grid.linewidth': 0.5,          # Gridline width (if enabled)
        'grid.alpha': 0.5,              # Gridline transparency (if enabled)
        'text.color': 'white',          # Default text color
    })

    sns.set_context(rc = {'patch.linewidth': 0.0})


def tech_color_palette():
    return {
        "Generation": "#2e374e",
        "FossilThermal": "#202020",
        "Coal": "#322f34",
        "Subcritical": "#3a3538",
        "Supercritical": "#4f4444",
        "Ultrasupercritical": "#5d4e4c",
        "IGCC": "#6b5853",
        "Gas": "#bababa",
        "CCGT": "#999999",
        "OCGT": "#777777",
        "Oil": "#5d407c",
        "Nuclear": "#ee9dda",
        "Renewables": "#00c0b0",
        "Firmrenewables": "#b7492d",
        "Biomass": "#e25329",
        "Geothermal": "#f75726",
        "Tidal": "#25367b",
        "Marine": "#2e4ad9",
        "Hydro": "#8292e8",
        "Variablerenewables": "#ffb405",
        "Solar": "#ffce5d",
        "Utility": "#ffe19b",
        "Rooftop": "#fff0cd",
        "Wind": "#06a299",
        "Offshore Wind": "#66dad0",
        "Onshore Wind": "#99e6df",
        "Innovativethermal": "#fe8348",
        "CoalCCS": "#b18873",
        "GasCCS": "#d9d9d9",
        "BECCS": "#fa9474",
        "Ammonia": "#d9a88b",
        "Hydrogen": "#f3f3f3",
        "Storage": "#69b2f5",
        "Pumpedhydro": "#a5d1f9",
        "Battery": "#c3e0fb",
        "Batteries": "#c3e0fb",
        "Interconnectors": "#ba63da",
        "DSR": "#feba9a",
    }


def bar_plot_3row(
        width_ratios=[1, 1, 8],
        figsize=(10, 5),
):
    '''Create a 3-row bar plot with 3 subplots
    '''
    
    set_tz_theme()

    # Create a figure
    fig = plt.figure(figsize=figsize)

    # Create a GridSpec with 1 row and 2 columns, setting the width ratios
    gs = gridspec.GridSpec(1, 3, width_ratios=width_ratios)

    # create subplots
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1], sharey=ax0)
    ax2 = fig.add_subplot(gs[2], sharey=ax0)

    return fig, ax0, ax1, ax2
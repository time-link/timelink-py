from bokeh.models import Range1d
from bokeh.models import Circle
from bokeh.models import MultiLine
from bokeh.plotting import figure
from bokeh.plotting import from_networkx
from bokeh.io import show, save
import networkx as nx


def draw_network(
    G,
    title="Timelink network",
    hover_tooltips=None,
    iterations=50,
    node_colors=None,
    width=500,
    height=500,
):
    """draws a network using Bokeh and networkx layout"""

    if hover_tooltips is None:
        hover_tooltips = [("desc", "@desc"), ("type", "@type")]
    if node_colors is None:
        node_colors = (
            "type",  # TODO this should be generic maybe bokeh has builtin
            {
                "person": "green",
                "wicky-viagem": "red",
                "jesuita-entrada": "blue",
                "*default*": "gray",
            },
        )
    # Establish which categories will appear when hovering over each node
    HOVER_TOOLTIPS = hover_tooltips

    # Color nodes
    (cattribute, node_colors) = node_colors
    for m in list(G.nodes):
        nt = G.nodes[m].get(cattribute, "*default*")
        nc = node_colors.get(nt, "gray")
        G.nodes[m]["color"] = nc

    # Create a plot — set dimensions, toolbar, and title
    plot = figure(
        tooltips=HOVER_TOOLTIPS,
        tools="pan,wheel_zoom,save,reset",
        active_scroll="wheel_zoom",
        x_range=Range1d(-20.1, 20.1),
        y_range=Range1d(-15.1, 15.1),
        plot_width=width,
        plot_height=height,
        title=title,
    )

    # Create a network graph object with spring layout
    # https://networkx.github.io/documentation/networkx-1.9/reference/generated/networkx.drawing.layout.spring_layout.html
    network_graph = from_networkx(
        G, nx.spring_layout, iterations=iterations, scale=20, center=(0, 0)
    )

    # Set node size and color
    network_graph.node_renderer.glyph = Circle(size=15, fill_color="color")

    # Set edge opacity and width
    network_graph.edge_renderer.glyph = MultiLine(line_alpha=0.5, line_width=1)

    # Add network graph to the plot
    plot.renderers.append(network_graph)
    show(plot)
    fn = save(plot, title=title, filename=f"{title}.html")
    print("timelink draw_network plot saved to file: " + fn)

import networkx as nx
from bokeh.io import output_notebook, save, show
from bokeh.models import Circle, MultiLine, Range1d
from bokeh.palettes import Category10
from bokeh.plotting import figure, from_networkx


def draw_network(
    Graph: nx.Graph,
    title="Timelink network",
    node_tooltips=None,
    edge_tooltips=None,
    iterations=50,
    scale=1,
    node_color_attr="type",
    node_colors: dict | None = None,
    color_palette: dict | None = None,
    circle_size=10,
    line_color="#CCCCCC",
    line_alpha=0.8,
    line_width=2,
    filename=None,  # if provided, saves the plot to this file
    width=500,
    height=500,
):
    """Draws a network using Bokeh and networkx layout

    Arguments:
        Graph: a networkx graph object
        title: the title of the plot
        node_tooltips: a list of tuples with the information to show when hovering over nodes
                        defaults to [("desc", "@desc"), ("type", "@type")]
        edge_tooltips: a list of tuples with the information to show when hovering over edges
                        defaults to None, which means no tooltips for edges
        iterations: number of iterations for the spring layout
        node_color_attr: the attribute to color nodes by (default is "type")
        node_colors: a dictionary mapping node types to colors. If None, a default color palette is used.
        color_palette:  a dictionary mapping node types to colors. If none a
                        default color palette is used.
        filename: if provided, saves the plot to this file
        width: width of the plot
        height: height of the plot
    Returns:
        None, but saves the plot to a file if filename is provided

    Note on coloring of nodes:
        Coloring is done by the attribute specified in `node_color_attr`.
        Each node is inspected to get its attribute `node_color_attr`.
        If `node_colors` is provided, it uses that dictionary to set the color.
        `node_colors` should be a dictionary mapping attributes to colors.
        Colors are set to "gray" if the attribute is not found in `node_colors`.
        If `node_colors` is None, this functions will inspect the nodes
        to get the number of different values for `node_color_attr` and
        build a color palette using `bokeh.palettes.Category10` or a
        custom `color_palette` if provided in the arguments.

    """
    output_notebook()  # Use this if you want to display the plot in a Jupyter notebook

    # convert the label to integer
    G = nx.convert_node_labels_to_integers(Graph, label_attribute="original_id")

    # Establish which categories will appear when hovering over each node
    if node_tooltips is None:
        node_tooltips = [("desc", "@desc"), ("type", "@type")]

    HOVER_TOOLTIPS = node_tooltips

    # Color nodes
    if node_colors is None:
        # we first inspect the nodes to get the types
        node_types = {G.nodes[n][node_color_attr] for n in G.nodes}
        if color_palette is None:
            color_palette = Category10
            palette_len = max(len(node_types), 3)  # palette length should be at least 3
            colors = {
                n: color_palette[palette_len][i] for i, n in enumerate(node_types)
            }
            for node in G.nodes:
                G.nodes[node]["color"] = colors.get(
                    G.nodes[node][node_color_attr], "gray"
                )
    else:
        # use the provided node_colors dictionary
        cattribute = node_color_attr
        for node in G.nodes:
            G.nodes[node]["color"] = node_colors.get(G.nodes[node][cattribute], "gray")

    # Create a plot — set dimensions, toolbar, and title
    plot = figure(
        tooltips=HOVER_TOOLTIPS,
        tools="pan,wheel_zoom,save,reset",
        active_scroll="wheel_zoom",
        x_range=Range1d(-1.1, 1.1),
        y_range=Range1d(-1.1, 1.1),
        width=width,
        height=height,
        title=title,
    )

    # Create a network graph object with spring layout
    # https://networkx.github.io/documentation/networkx-1.9/reference/generated/networkx.drawing.layout.spring_layout.html
    network_graph = from_networkx(
        G,
        nx.spring_layout,  # type: ignore
        iterations=iterations,
        scale=scale,
        center=(0, 0),
    )

    # Set node size and color
    network_graph.node_renderer.glyph = Circle(size=circle_size, fill_color="color")  # type: ignore

    # Set edge opacity and width
    network_graph.edge_renderer.glyph = MultiLine(
        line_color=line_color, line_alpha=line_alpha, line_width=line_width
    )

    # Add network graph to the plot
    plot.renderers.append(network_graph)
    show(plot)
    if filename is not None:
        if not filename.endswith(".html"):
            filename += ".html"
        # Save the plot to a file
        if title is None:
            title = "timelink_network"
        fn = save(plot, title=title, filename=f"{title}.html")
        print("timelink draw_network plot saved to file: " + fn)

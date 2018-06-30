# -*- coding: utf-8 -*-
"""
Created on Sun Jul  1 00:59:19 2018

@author: Tsvika
"""
import random

import networkx as nx

from stars import random_star_names


# set-up systems
def setup_board(seed=None):
    NUMBER_OF_STARS = 50
    ROUTES_ARGS = 2, 0.9

    random.seed(seed)

    def get_distance():
        return random.uniform(3, 5)

    def get_production(centrality, min_centrality):
        return int(
            round((centrality / min_centrality) ** 2.5 * random.lognormvariate(0, 0.2))
        )

    systems_graph = nx.relabel.convert_node_labels_to_integers(
        nx.generators.random_graphs.powerlaw_cluster_graph(
            NUMBER_OF_STARS, *ROUTES_ARGS, seed=seed
        ),
        1,
    )
    assert nx.is_connected(systems_graph)
    for system, name in zip(systems_graph.nodes, random_star_names(len(systems_graph))):
        systems_graph.nodes[system]['name'] = name

    for src in systems_graph:
        for dst in systems_graph[src]:
            systems_graph[src][dst]['distance'] = get_distance()
    centrality = nx.algorithms.centrality.closeness_centrality(
        systems_graph, distance='distance'
    )
    min_centrality = min(centrality.values())
    for system in systems_graph.nodes:
        systems_graph.nodes[system]['centrality'] = centrality[system]
        systems_graph.nodes[system]['production'] = get_production(
            centrality[system], min_centrality
        )
    return systems_graph


def draw_map(systems_graph, ax=None):
    nx.draw(
        systems_graph,
        node_color=[
            systems_graph.nodes[system]['centrality'] for system in systems_graph.nodes
        ],
        edge_color=[
            1 / systems_graph.edges[edge]['distance'] for edge in systems_graph.edges
        ],
        edge_cmap=plt.get_cmap('Greys'),
        edge_vmin=0,
        edge_vmax=1,
        labels={
            system: '\n{}\n{}'.format(
                systems_graph.nodes[system]['production'],
                systems_graph.nodes[system]['name'],
            )
            for system in systems_graph.nodes
        },
        ax=ax,
    )

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    systems_graph = setup_board()
    _f, ax = plt.subplots()
    draw_map(systems_graph, ax=ax)

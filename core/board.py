# -*- coding: utf-8 -*-
"""
Created on Sun Jul  1 00:59:19 2018

@author: Tsvika
"""
import random

import networkx as nx

from core.stars import random_star_names


# set-up systems
def setup_board(seed=None):
    # game-play constants:
    # TODO: a test case to check that
    # setup_board(1) == setup_board(1) != setup_board(2)
    number_of_stars = 50

    def get_graph(number_of_stars, seed=None):
        return nx.generators.random_graphs.powerlaw_cluster_graph(
            n=number_of_stars, m=2, p=0.9, seed=seed
        )

    def get_distance():
        return random.uniform(3, 5)

    def get_production(centrality, min_centrality):
        return int(
            round((centrality / min_centrality) ** 2.5 * random.lognormvariate(0, 0.2))
        )

    # board generation
    random.seed(seed)
    while True:
        systems_graph = nx.relabel.convert_node_labels_to_integers(
            get_graph(number_of_stars, seed=seed), 1
        )
        if nx.is_connected(systems_graph):
            break

    # board metadata
    for system, name in zip(systems_graph.nodes, random_star_names(len(systems_graph))):
        systems_graph.nodes[system]['name'] = name
    for src in systems_graph:
        for dst in systems_graph[src]:
            systems_graph[src][dst]['distance'] = get_distance()
    centrality_dict = nx.algorithms.centrality.closeness_centrality(
        systems_graph, distance='distance'
    )
    for system in systems_graph.nodes:
        systems_graph.nodes[system]['centrality'] = centrality_dict[system]
        systems_graph.nodes[system]['production'] = get_production(
            centrality_dict[system], min(centrality_dict.values())
        )
    return systems_graph


def draw_map(systems_graph, ax=None):
    # TODO: draw map random seed control?
    import matplotlib.pyplot as plt

    if ax is None:
        _f, ax = plt.subplots()
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
    plt.show()
    return ax


if __name__ == "__main__":
    systems_g = setup_board()
    ax = draw_map(systems_g)

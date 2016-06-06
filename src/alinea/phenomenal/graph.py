# -*- python -*-
#
#       Copyright 2015 INRIA - CIRAD - INRA
#
#       Distributed under the Cecill-C License.
#       See accompanying file LICENSE.txt or copy at
#           http://www.cecill.info/licences/Licence_CeCILL-C_V1-en.html
#
#       OpenAlea WebSite : http://openalea.gforge.inria.fr
#
# ==============================================================================
import gc
import math
import time

import networkx
import numpy
import scipy.spatial


# ==============================================================================


def create_graph(voxel_centers, verbose=False):
    if verbose:
        print "Graph building : ...",
        t0 = time.time()

    graph = networkx.Graph()
    graph.add_nodes_from(voxel_centers)

    ijk = [(-1, -1, -1), (-1, -1, 0), (-1, -1, 1),
           (-1, 0, -1), (-1, 0, 0), (-1, 0, 1),
           (-1, 1, -1), (-1, 1, 0), (-1, 1, 1),
           (0, -1, -1), (0, -1, 0), (0, -1, 1),
           (0, 0, -1), (0, 0, 0), (0, 0, 1),
           (0, 1, -1), (0, 1, 0), (0, 1, 1),
           (1, -1, -1), (1, -1, 0), (1, -1, 1),
           (1, 0, -1), (1, 0, 0), (1, 0, 1),
           (1, 1, -1), (1, 1, 0), (1, 1, 1)]

    for pt in voxel_centers:
        for i, j, k in ijk:
            pos = pt[0] + i, pt[1] + j, pt[2] + k
            if graph.has_node(pos):
                graph.add_edge(pt, pos, weight=abs(i) + abs(j) + abs(k))

    if verbose:
        print "done, in ", time.time() - t0, 'seconds'
        print 'Nodes :', graph.number_of_nodes()
        print 'Edges :', graph.number_of_edges()

    gc.collect()

    return graph


def add_nodes(graph, voxel_centers, verbose=False):
    if verbose:
        print "Graph adding : ...",
        t0 = time.time()

    graph.add_nodes_from(voxel_centers)

    ijk = [(-1, -1, -1), (-1, -1, 0), (-1, -1, 1),
           (-1, 0, -1), (-1, 0, 0), (-1, 0, 1),
           (-1, 1, -1), (-1, 1, 0), (-1, 1, 1),
           (0, -1, -1), (0, -1, 0), (0, -1, 1),
           (0, 0, -1), (0, 0, 0), (0, 0, 1),
           (0, 1, -1), (0, 1, 0), (0, 1, 1),
           (1, -1, -1), (1, -1, 0), (1, -1, 1),
           (1, 0, -1), (1, 0, 0), (1, 0, 1),
           (1, 1, -1), (1, 1, 0), (1, 1, 1)]

    for pt in voxel_centers:
        for i, j, k in ijk:
            pos = pt[0] + i, pt[1] + j, pt[2] + k
            if graph.has_node(pos):
                graph.add_edge(pt, pos, weight=abs(i) + abs(j) + abs(k))
        if verbose:
            print "done, in ", time.time() - t0, 'seconds'

    gc.collect()

    return graph
# ==============================================================================


def ball(graph, node_src, radius):
    g = networkx.single_source_shortest_path_length(
        graph, node_src, cutoff=int(radius * 2))

    ball_list = list()
    for node in g:
        d = scipy.spatial.distance.euclidean(node_src, node)
        if d <= radius:
            ball_list.append(node)

    return ball_list


def get_max_size_ball(value):
    m = 0
    my_range = int(1 + value * 2)
    for i in xrange(-my_range, my_range, 1):
        for j in xrange(-my_range, my_range, 1):
            for k in xrange(-my_range, my_range, 1):
                if math.sqrt(i ** 2 + j ** 2 + k ** 2) <= value:
                    m += 1

    return m


len_max_ball = dict()
for radius in numpy.arange(0, 10, 0.1):
    radius = round(radius, 2)
    len_max_ball[radius] = get_max_size_ball(radius)


def get_max_radius_ball_2(graph, node_src):
    max_radius_ball = 0

    for radius_int in xrange(0, 10, 1):

        g = networkx.single_source_shortest_path_length(
            graph, node_src, cutoff=radius_int)

        for radius_decimal in numpy.arange(0, 1, 0.1):
            radius_decimal = round(radius_decimal, 2)
            radius = radius_int + radius_decimal

            len_ball = 0
            for node in g:
                d = scipy.spatial.distance.euclidean(node_src, node)
                if d <= radius:
                    len_ball += 1

            if len_ball == len_max_ball[radius]:
                max_radius_ball = radius
            else:
                return max_radius_ball

    return max_radius_ball


def get_max_radius_ball(graph, node_src):
    max_radius_ball = 0
    for radius in numpy.arange(0, 15, 0.1):
        radius = round(radius, 2)
        len_ball = len(ball(graph, node_src, radius))

        if len_ball >= len_max_ball[radius]:
            max_radius_ball = radius
        else:
            break

    return max_radius_ball


def get_max_radius_floating_ball(graph, node_src):

    max_radius = get_max_radius_ball(graph, node_src)
    node_save = node_src

    labelize = list()
    labelize.append(node_src)

    nodes = list()
    nodes += networkx.all_neighbors(graph, node_src)
    while nodes:
        node = nodes.pop()

        if node not in labelize:
            labelize.append(node)

            radius = get_max_radius_ball(graph, node)
            d = scipy.spatial.distance.euclidean(node_src, node)
            if d <= radius:
                nodes += networkx.all_neighbors(graph, node)

                if radius >= max_radius:
                    max_radius = radius
                    node_save = node

    return max_radius, node_save


def get_max_radius_floating_ball_2(graph, node_src, nodes):

    max_radius = get_max_radius_ball(graph, node_src)
    for node in nodes:
        r = get_max_radius_ball(graph, node)
        d = scipy.spatial.distance.euclidean(node_src, node)

        if d <= r and r >= max_radius:
            max_radius = r

    return max_radius

# -*- python -*-
#
#       data_transformation.py :
#
#       Copyright 2015 INRIA - CIRAD - INRA
#
#       File author(s): Simon Artzet <simon.artzet@gmail.com>
#
#       File contributor(s):
#
#       Distributed under the Cecill-C License.
#       See accompanying file LICENSE.txt or copy at
#           http://www.cecill.info/licences/Licence_CeCILL-C_V1-en.html
#
#       OpenAlea WebSite : http://openalea.gforge.inria.fr
#
#       ========================================================================

#       ========================================================================
#       External Import
import os
import numpy
import cv2


#       ========================================================================
#       Code


def change_orientation(cubes):
    for cube in cubes:
        x = cube.position[0]
        y = - cube.position[2]
        z = - cube.position[1]

        cube.position[0] = x
        cube.position[1] = y
        cube.position[2] = z

    return cubes


def save_matrix_like_stack_image(matrix, data_directory):

    if not os.path.exists(data_directory):
        os.makedirs(data_directory)

    xl, yl, zl = matrix.shape
    print xl, yl, zl
    for i in range(zl):
        mat = matrix[:, :, i] * 255
        cv2.imwrite(data_directory + '%d.png' % i, mat)


def limit_points_3d(points_3d):
    x_min = float("inf")
    y_min = float("inf")
    z_min = float("inf")

    x_max = - float("inf")
    y_max = - float("inf")
    z_max = - float("inf")

    for point_3d in points_3d:
        x, y, z = point_3d[0], point_3d[1], point_3d[2]

        x_min = min(x_min, x)
        y_min = min(y_min, y)
        z_min = min(z_min, z)

        x_max = max(x_max, x)
        y_max = max(y_max, y)
        z_max = max(z_max, z)

    return x_min, y_min, z_min, x_max, y_max, z_max


def matrix_to_points_3d(matrix, radius, point_3d):

    points_3d = list()
    for (x, y, z), value in numpy.ndenumerate(matrix):
        if value == 1:

            pt_3d = (point_3d[0] + x * radius * 2,
                     point_3d[1] + y * radius * 2,
                     point_3d[2] + z * radius * 2)

            points_3d.append(pt_3d)

    return points_3d


def points_3d_to_matrix(points_3d, radius):

    x_min, y_min, z_min, x_max, y_max, z_max = limit_points_3d(points_3d)

    r = radius * 2

    x_r_min = x_min / r
    y_r_min = y_min / r
    z_r_min = z_min / r

    mat = numpy.zeros((round((x_max - x_min) / r) + 1,
                       round((y_max - y_min) / r) + 1,
                       round((z_max - z_min) / r) + 1), dtype=numpy.uint8)

    for point_3d in points_3d:
        x_new = (point_3d[0] / r) - x_r_min
        y_new = (point_3d[1] / r) - y_r_min
        z_new = (point_3d[2] / r) - z_r_min

        mat[x_new, y_new, z_new] = 1

    return mat


#       ========================================================================
#       LOCAL TEST

if __name__ == "__main__":
    pass
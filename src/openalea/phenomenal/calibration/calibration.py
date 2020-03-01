# -*- python -*-
#
#       Copyright INRIA - CIRAD - INRA
#
#       Distributed under the Cecill-C License.
#       See accompanying file LICENSE.txt or copy at
#           http://www.cecill.info/licences/Licence_CeCILL-C_V1-en.html
#
# ==============================================================================
""" This module contains a calibration model for phenoarch experiment
where a target is rotating instead of a plant in the image acuisition system.
"""
# ==============================================================================
from __future__ import division, print_function, absolute_import

import json
import math
import numpy
import scipy.optimize

from .frame import (Frame, x_axis, y_axis, z_axis)
from .transformations import (concatenate_matrices, rotation_matrix)

# ==============================================================================

__all__ = ["cam_origin_axis",
           "CalibrationCamera",
           "CalibrationCameraTop",
           "Calibration",
           "CalibrationCameraSideWith2TargetYXZ"]


# ==============================================================================


def cam_origin_axis(axes):
    """ Defines cam_origin_axis transformation matrix given a
    positioning of camera axes in the world frame

    :Parameters:
     - `axes` ([array,array,array]) - orientation of camera axes given as
                   the coordinates of the local axis in the global frame"""
    f = Frame(axes)
    rot = numpy.identity(4)
    rot[:3, :3] = f.rotation_to_global()
    return rot


def normalise_angle(angle):
    """normalise an angle to the [-pi, pi] range"""
    angle = numpy.array(angle)
    modulo = 2 * numpy.pi
    angle %= modulo
    # force to [0, modulo] range
    angle = (angle + modulo) % modulo
    return angle - numpy.where(angle > modulo / 2., modulo, 0)


class CalibrationCamera(object):
    def __init__(self):
        # Camera Parameters
        self._cam_width_image = None
        self._cam_height_image = None
        self._cam_focal_length_x = None
        self._cam_focal_length_y = None
        self._cam_pos_x = None
        self._cam_pos_y = None
        self._cam_pos_z = None
        self._cam_rot_x = None
        self._cam_rot_y = None
        self._cam_rot_z = None
        self._angle_factor = None
        self._cam_origin_axis = None

    def __str__(self):
        out = ''
        out += 'Camera Parameters : \n'
        out += '\tFocal length X : ' + str(self._cam_focal_length_x) + '\n'
        out += '\tFocal length Y : ' + str(self._cam_focal_length_y) + '\n'
        if self._cam_width_image is not None:
            out += '\tOptical Center X : ' + str(self._cam_width_image / 2.0) + '\n'
            out += '\tOptical Center Y : ' + str(self._cam_height_image / 2.0)
        else:
            out += '\tOptical Center X : ' + str(self._cam_width_image) + '\n'
            out += '\tOptical Center Y : ' + str(self._cam_height_image)
        out += '\n\n'

        out += '\tPosition X : ' + str(self._cam_pos_x) + '\n'
        out += '\tPosition Y : ' + str(self._cam_pos_y) + '\n'
        out += '\tPosition Z : ' + str(self._cam_pos_z) + '\n\n'

        out += '\tRotation X : ' + str(self._cam_rot_x) + '\n'
        out += '\tRotation Y : ' + str(self._cam_rot_y) + '\n'
        out += '\tRotation Z : ' + str(self._cam_rot_z) + '\n'

        out += '\t Angle Factor : ' + str(self._angle_factor) + '\n'

        out += '\tOrigin rotation position : \n'
        out += str(self._cam_origin_axis) + '\n\n'

        return out

    @staticmethod
    def pixel_coordinates(point_3d,
                          width_image, height_image,
                          focal_length_x, focal_length_y):
        """ Compute image coordinates of a 3d point

        Args:
         - point (float, float, float): a point/array of points in space
                    expressed in camera frame coordinates

        return:
         - (int, int): coordinate of point in image in pix
        """
        pt = numpy.array(point_3d)
        x, y, z = pt.T

        u = x / z * focal_length_x + width_image / 2.0
        v = y / z * focal_length_y + height_image / 2.0

        if len(pt.shape) > 1:
            return numpy.column_stack((u, v))
        else:
            return u, v

    @staticmethod
    def pixel_coordinates_2(point_3d, cx, cy, fx, fy):
        """ Compute image coordinates of a 3d point

        Args:
         - point (float, float, float): a point in space
                    expressed in camera frame coordinates

        return:
         - (int, int): coordinate of point in image in pix
        """
        pt = numpy.array(point_3d)
        x, y, z = pt.T

        u = x / z * fx + cx
        v = y / z * fy + cy

        if len(pt.shape) > 1:
            return numpy.column_stack((u, v))
        else:
            return u, v

    @staticmethod
    def target_frame(pos_x, pos_y, pos_z,
                     rot_x, rot_y, rot_z,
                     alpha):

        origin = [
            pos_x * math.cos(alpha) - pos_y * math.sin(alpha),
            pos_x * math.sin(alpha) + pos_y * math.cos(alpha),
            pos_z]

        mat_rot_x = rotation_matrix(rot_x, x_axis)
        mat_rot_y = rotation_matrix(rot_y, y_axis)
        mat_rot_z = rotation_matrix(alpha + rot_z, z_axis)

        rot = concatenate_matrices(mat_rot_z, mat_rot_x, mat_rot_y)

        return Frame(rot[:3, :3].T, origin)

    @staticmethod
    def camera_frame(pos_x, pos_y, pos_z,
                     rot_x, rot_y, rot_z,
                     origin_axis):

        origin = (pos_x, pos_y, pos_z)

        mat_rot_x = rotation_matrix(rot_x, x_axis)
        mat_rot_y = rotation_matrix(rot_y, y_axis)
        mat_rot_z = rotation_matrix(rot_z, z_axis)

        rot = concatenate_matrices(origin_axis,
                                   mat_rot_x, mat_rot_y, mat_rot_z)

        return Frame(rot[:3, :3].T, origin)

    def get_camera_frame(self):
        return self.camera_frame(
            self._cam_pos_x, self._cam_pos_y, self._cam_pos_z,
            self._cam_rot_x, self._cam_rot_y, self._cam_rot_z,
            self._cam_origin_axis)

    def get_projection(self, alpha):

        fr_cam = self.get_camera_frame()

        angle = math.radians(alpha * self._angle_factor)

        def projection(pts):
            pt = numpy.array(pts)
            x, y, z = pt.T
            x = x * math.cos(angle) - y * math.sin(angle)
            y = x * math.sin(angle) + y * math.cos(angle)

            if len(pt.shape) > 1:
                origin = numpy.column_stack((x, y, z))
            else:
                origin = x, y, z

            return self.pixel_coordinates(fr_cam.local_point(origin),
                                              self._cam_width_image,
                                              self._cam_height_image,
                                              self._cam_focal_length_x,
                                              self._cam_focal_length_y)

        return projection

    @staticmethod
    def load(filename):
        with open(filename, 'r') as input_file:
            save_class = json.load(input_file)

            c = CalibrationCamera()

            c._cam_width_image = save_class['cam_width_image']
            c._cam_height_image = save_class['cam_height_image']
            c._cam_focal_length_x = save_class['cam_focal_length_x']
            c._cam_focal_length_y = save_class['cam_focal_length_y']
            c._cam_pos_x = save_class['cam_pos_x']
            c._cam_pos_y = save_class['cam_pos_y']
            c._cam_pos_z = save_class['cam_pos_z']
            c._cam_rot_x = save_class['cam_rot_x']
            c._cam_rot_y = save_class['cam_rot_y']
            c._cam_rot_z = save_class['cam_rot_z']
            c._angle_factor = save_class['angle_factor']
            c._cam_origin_axis = numpy.array(
                save_class['cam_origin_axis']).reshape((4, 4)).astype(
                numpy.float32)

        return c

    def dump(self, filename):
        save_class = dict()

        save_class['cam_width_image'] = self._cam_width_image
        save_class['cam_height_image'] = self._cam_height_image
        save_class['cam_focal_length_x'] = self._cam_focal_length_x
        save_class['cam_focal_length_y'] = self._cam_focal_length_y
        save_class['cam_pos_x'] = self._cam_pos_x
        save_class['cam_pos_y'] = self._cam_pos_y
        save_class['cam_pos_z'] = self._cam_pos_z
        save_class['cam_rot_x'] = self._cam_rot_x
        save_class['cam_rot_y'] = self._cam_rot_y
        save_class['cam_rot_z'] = self._cam_rot_z
        save_class['angle_factor'] = self._angle_factor
        save_class['cam_origin_axis'] = self._cam_origin_axis.reshape(
            (16,)).tolist()

        with open(filename, 'w') as output_file:
            json.dump(save_class, output_file,
                      sort_keys=True,
                      indent=4,
                      separators=(',', ': '))


class CalibrationCameraTop(CalibrationCamera):
    def __init__(self):
        CalibrationCamera.__init__(self)
        self._verbose = False

        self._ref_target_points_local_3d = None
        self._ref_target_points_2d = None
        self._ref_target_points_3d = None

        self._ref_number = None

        # camera frame axis coordinates expressed in world coordinates
        axes = numpy.array([[1., 0., 0.],
                            [0., -1., 0.],
                            [0., 0., -1.]])

        self._cam_origin_axis = cam_origin_axis(axes)

    def fit_function(self, x0):
        err = 0

        cam_focal_length_x, cam_focal_length_y, \
        cam_pos_x, cam_pos_y, cam_pos_z, \
        cam_rot_x, cam_rot_y, cam_rot_z = x0

        fr_cam = self.camera_frame(
            cam_pos_x, cam_pos_y, cam_pos_z,
            cam_rot_x, cam_rot_y, cam_rot_z,
            self._cam_origin_axis)

        for i in range(len(self._ref_target_points_2d)):
            pts = list(map(lambda pt: self.pixel_coordinates(
                fr_cam.local_point(pt),
                self._cam_width_image,
                self._cam_height_image,
                cam_focal_length_x,
                cam_focal_length_y), self._ref_target_points_3d[i]))

            err += numpy.linalg.norm(
                numpy.array(pts) - self._ref_target_points_2d[i], axis=1).sum()

        if self._verbose:
            print(err)

        return err

    def find_parameters(self, number_of_repetition):
        best_parameters = None
        min_err = float('inf')
        for i in range(number_of_repetition + 1):

            cam_focal_length_x = numpy.random.uniform(0.0, 10000.0)
            cam_focal_length_y = numpy.random.uniform(0.0, 10000.0)
            cam_pos_x = numpy.random.uniform(-500.0, 500.0)
            cam_pos_y = numpy.random.uniform(-500.0, 500.0)
            cam_pos_z = numpy.random.uniform(0.0, 10000.0)
            cam_rot_x = 0.0
            cam_rot_y = 0.0
            cam_rot_z = 0.0

            parameters = [cam_focal_length_x, cam_focal_length_y,
                          cam_pos_x, cam_pos_y, cam_pos_z,
                          cam_rot_x, cam_rot_y, cam_rot_z]

            # Optimization
            parameters = scipy.optimize.minimize(
                self.fit_function, parameters, method='BFGS').x

            # Compute error compare with min_err
            err = self.fit_function(parameters)
            if err < min_err:
                min_err = err
                best_parameters = parameters

            if self._verbose:
                print('Result : ', parameters)
                print('Err : ', err / self._ref_number)

        return best_parameters

    def project_points_3d(self, points_3d):

        fr_cam = self.camera_frame(
            self._cam_pos_x, self._cam_pos_y, self._cam_pos_z,
            self._cam_rot_x, self._cam_rot_y, self._cam_rot_z,
            self._cam_origin_axis)

        pts = list(map(lambda pt: self.pixel_coordinates(
            fr_cam.local_point(pt),
            self._cam_width_image,
            self._cam_height_image,
            self._cam_focal_length_x,
            self._cam_focal_length_y), points_3d))

        return pts

    @staticmethod
    def load(filename):
        with open(filename, 'r') as input_file:
            save_class = json.load(input_file)

            c = CalibrationCameraTop()

            c._cam_width_image = save_class['cam_width_image']
            c._cam_height_image = save_class['cam_height_image']
            c._cam_focal_length_x = save_class['cam_focal_length_x']
            c._cam_focal_length_y = save_class['cam_focal_length_y']
            c._cam_pos_x = save_class['cam_pos_x']
            c._cam_pos_y = save_class['cam_pos_y']
            c._cam_pos_z = save_class['cam_pos_z']
            c._cam_rot_x = save_class['cam_rot_x']
            c._cam_rot_y = save_class['cam_rot_y']
            c._cam_rot_z = save_class['cam_rot_z']
            c._angle_factor = save_class['angle_factor']
            c._cam_origin_axis = numpy.array(
                save_class['cam_origin_axis']).reshape((4, 4)).astype(
                numpy.float32)

        return c

    def calibrate(self,
                  ref_target_points_2d,
                  ref_target_points_3d,
                  size_image,
                  angle_factor,
                  number_of_repetition=1,
                  verbose=False):

        self._verbose = verbose
        self._angle_factor = angle_factor

        self._ref_target_points_2d = ref_target_points_2d
        self._ref_number = len(ref_target_points_2d)

        self._ref_target_points_3d = ref_target_points_3d
        self._cam_width_image = size_image[0]
        self._cam_height_image = size_image[1]

        parameters = self.find_parameters(number_of_repetition)

        for i in [5, 6, 7]:
            parameters[i] %= math.pi * 2.0

        self._cam_focal_length_x = parameters[0]
        self._cam_focal_length_y = parameters[1]
        self._cam_pos_x = parameters[2]
        self._cam_pos_y = parameters[3]
        self._cam_pos_z = parameters[4]
        self._cam_rot_x = parameters[5]
        self._cam_rot_y = parameters[6]
        self._cam_rot_z = parameters[7]

        err = self.fit_function(parameters)
        if self._verbose:
            print('Result : ', parameters)
            print('Err : ', err, ' -- ', err / self._ref_number)

        self._verbose = False

        return err / self._ref_number


class CalibrationCameraSideWith2TargetYXZ(CalibrationCamera):
    def __init__(self):
        CalibrationCamera.__init__(self)
        self._verbose = False
        self._ref_target_1_points_local_3d = None
        self._ref_target_2_points_local_3d = None
        self._ref_number = None
        self._ref_target_1_points_2d = None
        self._ref_target_2_points_2d = None

        self._cam_pos_z = 0.0

        self._cam_rot_y = 0.0
        # camera frame axis coordinates expressed in world coordinates
        axes = numpy.array([[1., 0., 0.],
                            [0., 0., -1.],
                            [0., 1., 0.]])

        self._cam_origin_axis = cam_origin_axis(axes)

        self._target_1_pos_x = None
        self._target_1_pos_y = None
        self._target_1_pos_z = None
        self._target_1_rot_x = None
        self._target_1_rot_y = None
        self._target_1_rot_z = None

        self._target_2_pos_x = None
        self._target_2_pos_y = None
        self._target_2_pos_z = None
        self._target_2_rot_x = None
        self._target_2_rot_y = None
        self._target_2_rot_z = None

    def __str__(self):
        out = ''
        out += CalibrationCamera.__str__(self)

        out += 'Target 1: \n'
        out += '\tPosition X : ' + str(self._target_1_pos_x) + '\n'
        out += '\tPosition Y : ' + str(self._target_1_pos_y) + '\n'
        out += '\tPosition Z : ' + str(self._target_1_pos_z) + '\n\n'
        out += '\tRotation X : ' + str(self._target_1_rot_x) + '\n'
        out += '\tRotation Y : ' + str(self._target_1_rot_y) + '\n'
        out += '\tRotation Z : ' + str(self._target_1_rot_z) + '\n\n'

        out += 'Target 2: \n'
        out += '\tPosition X : ' + str(self._target_2_pos_x) + '\n'
        out += '\tPosition Y : ' + str(self._target_2_pos_y) + '\n'
        out += '\tPosition Z : ' + str(self._target_2_pos_z) + '\n\n'
        out += '\tRotation X : ' + str(self._target_2_rot_x) + '\n'
        out += '\tRotation Y : ' + str(self._target_2_rot_y) + '\n'
        out += '\tRotation Z : ' + str(self._target_2_rot_z) + '\n\n'

        return out

    def fit_function(self, x0):
        err = 0

        cam_focal_length_x, cam_focal_length_y, \
        cam_pos_x, cam_pos_y, \
        cam_rot_x, cam_rot_z, \
        angle_factor, \
        target_1_pos_x, target_1_pos_y, target_1_pos_z, \
        target_1_rot_x, target_1_rot_y, target_1_rot_z, \
        target_2_pos_x, target_2_pos_y, target_2_pos_z, \
        target_2_rot_x, target_2_rot_y, target_2_rot_z = x0

        fr_cam = self.camera_frame(
            cam_pos_x, cam_pos_y, self._cam_pos_z,
            cam_rot_x, self._cam_rot_y, cam_rot_z,
            self._cam_origin_axis)

        for alpha, ref_pts in self._ref_target_1_points_2d.items():
            fr_target = self.target_frame(target_1_pos_x,
                                          target_1_pos_y,
                                          target_1_pos_z,
                                          target_1_rot_x,
                                          target_1_rot_y,
                                          target_1_rot_z,
                                          math.radians(alpha * angle_factor))

            target_pts = list(map(lambda pt: fr_target.global_point(pt),
                                  self._ref_target_1_points_local_3d))

            pts = list(map(lambda pt: self.pixel_coordinates(
                fr_cam.local_point(pt),
                self._cam_width_image,
                self._cam_height_image,
                cam_focal_length_x,
                cam_focal_length_y), target_pts))

            err += numpy.linalg.norm(numpy.array(pts) - ref_pts, axis=1).sum()

        for alpha, ref_pts in self._ref_target_2_points_2d.items():
            fr_target = self.target_frame(target_2_pos_x,
                                          target_2_pos_y,
                                          target_2_pos_z,
                                          target_2_rot_x,
                                          target_2_rot_y,
                                          target_2_rot_z,
                                          math.radians(alpha * angle_factor))

            target_pts = list(map(lambda pt: fr_target.global_point(pt),
                                  self._ref_target_2_points_local_3d))

            pts = list(map(lambda pt: self.pixel_coordinates(
                fr_cam.local_point(pt),
                self._cam_width_image,
                self._cam_height_image,
                cam_focal_length_x,
                cam_focal_length_y), target_pts))

            err += numpy.linalg.norm(numpy.array(pts) - ref_pts, axis=1).sum()

        if self._verbose:
            print(err)

        return err

    def find_parameters(self, number_of_repetition):

        best_parameters = None
        min_err = float('inf')
        for i in range(number_of_repetition + 1):

            cam_focal_length_x = numpy.random.uniform(1000.0, 10000.0)
            cam_focal_length_y = numpy.random.uniform(1000.0, 10000.0)
            cam_pos_x = 0.0
            cam_pos_y = - numpy.random.uniform(10000.0, 1000.0)

            cam_rot_x = 0.0
            cam_rot_z = 0.0

            angle_factor = 1.0

            target_1_pos_x = numpy.random.uniform(-1000.0, 1000.0)
            target_1_pos_y = numpy.random.uniform(-1000.0, 1000.0)
            target_1_pos_z = numpy.random.uniform(-1000, 1000.0)
            target_1_rot_x = 0
            target_1_rot_y = 0
            target_1_rot_z = 0

            target_2_pos_x = -target_1_pos_x
            target_2_pos_y = -target_1_pos_y
            target_2_pos_z = numpy.random.uniform(-1000, 1000.0)
            target_2_rot_x = 0
            target_2_rot_y = 0
            target_2_rot_z = 0

            parameters = [cam_focal_length_x, cam_focal_length_y,
                          cam_pos_x, cam_pos_y,
                          cam_rot_x, cam_rot_z,
                          angle_factor,
                          target_1_pos_x, target_1_pos_y, target_1_pos_z,
                          target_1_rot_x, target_1_rot_y, target_1_rot_z,
                          target_2_pos_x, target_2_pos_y, target_2_pos_z,
                          target_2_rot_x, target_2_rot_y, target_2_rot_z]

            parameters = scipy.optimize.minimize(
                self.fit_function, parameters, method='BFGS').x

            err = self.fit_function(parameters)
            if err < min_err:
                min_err = err
                best_parameters = parameters

            if self._verbose:
                err = self.fit_function(parameters)
                print('Result : ', parameters)
                print('Err : ', err / self._ref_number)

        return best_parameters

    def get_target_1_projected(self, alpha, ref_target_1_points_local_3d):

        fr_cam = self.camera_frame(
            self._cam_pos_x, self._cam_pos_y, self._cam_pos_z,
            self._cam_rot_x, self._cam_rot_y, self._cam_rot_z,
            self._cam_origin_axis)

        fr_target = self.target_frame(self._target_1_pos_x,
                                      self._target_1_pos_y,
                                      self._target_1_pos_z,
                                      self._target_1_rot_x,
                                      self._target_1_rot_y,
                                      self._target_1_rot_z,
                                      math.radians(alpha * self._angle_factor))

        target_pts = list(map(lambda pt: fr_target.global_point(pt),
                              ref_target_1_points_local_3d))

        pts = list(map(lambda pt: self.pixel_coordinates(
            fr_cam.local_point(pt),
            self._cam_width_image,
            self._cam_height_image,
            self._cam_focal_length_x,
            self._cam_focal_length_y), target_pts))

        return pts

    def get_target_2_projected(self, alpha, ref_target_2_points_local_3d):

        fr_cam = self.camera_frame(
            self._cam_pos_x, self._cam_pos_y, self._cam_pos_z,
            self._cam_rot_x, self._cam_rot_y, self._cam_rot_z,
            self._cam_origin_axis)

        fr_target = self.target_frame(self._target_2_pos_x,
                                      self._target_2_pos_y,
                                      self._target_2_pos_z,
                                      self._target_2_rot_x,
                                      self._target_2_rot_y,
                                      self._target_2_rot_z,
                                      math.radians(alpha * self._angle_factor))

        target_pts = list(map(lambda pt: fr_target.global_point(pt),
                              ref_target_2_points_local_3d))

        pts = list(map(lambda pt: self.pixel_coordinates(
            fr_cam.local_point(pt),
            self._cam_width_image,
            self._cam_height_image,
            self._cam_focal_length_x,
            self._cam_focal_length_y), target_pts))

        return pts

    def get_target_1_ref_points_global_3d(self,
                                          alpha,
                                          ref_target_1_points_local_3d):

        fr_target = self.target_frame(self._target_1_pos_x,
                                      self._target_1_pos_y,
                                      self._target_1_pos_z,
                                      self._target_1_rot_x,
                                      self._target_1_rot_y,
                                      self._target_1_rot_z,
                                      math.radians(alpha * self._angle_factor))

        return list(map(lambda pt: fr_target.global_point(pt),
                        ref_target_1_points_local_3d))

    def get_target_2_ref_points_global_3d(self,
                                          alpha,
                                          ref_target_2_points_local_3d):

        fr_target = self.target_frame(self._target_2_pos_x,
                                      self._target_2_pos_y,
                                      self._target_2_pos_z,
                                      self._target_2_rot_x,
                                      self._target_2_rot_y,
                                      self._target_2_rot_z,
                                      math.radians(alpha * self._angle_factor))

        return list(map(lambda pt: fr_target.global_point(pt),
                        ref_target_2_points_local_3d))

    def calibrate(self,
                  ref_target_1_points_2d,
                  ref_target_1_points_local_3d,
                  ref_target_2_points_2d,
                  ref_target_2_points_local_3d,
                  size_image,
                  number_of_repetition=3,
                  verbose=False):
        """ Find physical parameters associated with a camera
        (i.e. distances and angles), using pictures of a rotating
        target.

        args:
         - 'target_ref' (target): reference target
         - 'target_corners' dict of (angle, list of pts): for
                        a picture taken with a given angle, list
                        the coordinates of all intersections on
                        the target in the picture
        """
        self._verbose = verbose

        self._ref_target_1_points_local_3d = ref_target_1_points_local_3d
        self._ref_target_2_points_local_3d = ref_target_2_points_local_3d

        self._ref_number_image = (len(ref_target_1_points_2d) + len(
            ref_target_2_points_2d))

        # for angle in ref_target_1_points_2d:
        #     ref_target_1_points_2d

        self._ref_number = (len(ref_target_1_points_2d) +
                            len(ref_target_2_points_2d))

        self._ref_target_1_points_2d = ref_target_1_points_2d.copy()
        self._ref_target_2_points_2d = ref_target_2_points_2d.copy()

        self._cam_width_image = size_image[0]
        self._cam_height_image = size_image[1]

        parameters = self.find_parameters(number_of_repetition)

        for i in [4, 6, 10, 11, 12, 16, 17, 18]:
            parameters[i] %= math.pi * 2.0

        # Camera Parameters
        self._cam_focal_length_x = parameters[0]
        self._cam_focal_length_y = parameters[1]
        self._cam_pos_x = parameters[2]
        self._cam_pos_y = parameters[3]
        self._cam_rot_x = parameters[4]
        self._cam_rot_z = parameters[5]

        self._angle_factor = parameters[6]

        # Target 1 Parameters
        self._target_1_pos_x = parameters[7]
        self._target_1_pos_y = parameters[8]
        self._target_1_pos_z = parameters[9]
        self._target_1_rot_x = parameters[10]
        self._target_1_rot_y = parameters[11]
        self._target_1_rot_z = parameters[12]

        # Target 2 Parameters
        self._target_2_pos_x = parameters[13]
        self._target_2_pos_y = parameters[14]
        self._target_2_pos_z = parameters[15]
        self._target_2_rot_x = parameters[16]
        self._target_2_rot_y = parameters[17]
        self._target_2_rot_z = parameters[18]

        err = self.fit_function(parameters)
        if self._verbose:
            print('Result : ', parameters)
            print('Err : ', err, ' -- ', err / self._ref_number)

        self._verbose = False

        return err / self._ref_number

    def dump(self, filename):
        save_class = dict()

        save_class['cam_width_image'] = self._cam_width_image
        save_class['cam_height_image'] = self._cam_height_image
        save_class['cam_focal_length_x'] = self._cam_focal_length_x
        save_class['cam_focal_length_y'] = self._cam_focal_length_y
        save_class['cam_pos_x'] = self._cam_pos_x
        save_class['cam_pos_y'] = self._cam_pos_y
        save_class['cam_pos_z'] = self._cam_pos_z
        save_class['cam_rot_x'] = self._cam_rot_x
        save_class['cam_rot_y'] = self._cam_rot_y
        save_class['cam_rot_z'] = self._cam_rot_z
        save_class['angle_factor'] = self._angle_factor
        save_class['cam_origin_axis'] = self._cam_origin_axis.reshape(
            (16,)).tolist()

        save_class['target_1_pos_x'] = self._target_1_pos_x
        save_class['target_1_pos_y'] = self._target_1_pos_y
        save_class['target_1_pos_z'] = self._target_1_pos_z
        save_class['target_1_rot_x'] = self._target_1_rot_x
        save_class['target_1_rot_y'] = self._target_1_rot_y
        save_class['target_1_rot_z'] = self._target_1_rot_z

        save_class['target_2_pos_x'] = self._target_2_pos_x
        save_class['target_2_pos_y'] = self._target_2_pos_y
        save_class['target_2_pos_z'] = self._target_2_pos_z
        save_class['target_2_rot_x'] = self._target_2_rot_x
        save_class['target_2_rot_y'] = self._target_2_rot_y
        save_class['target_2_rot_z'] = self._target_2_rot_z

        with open(filename, 'w') as output_file:
            json.dump(save_class, output_file,
                      sort_keys=True,
                      indent=4,
                      separators=(',', ': '))

    @staticmethod
    def load(filename):
        with open(filename, 'r') as input_file:
            save_class = json.load(input_file)

            c = CalibrationCameraSideWith2TargetYXZ()

            c._cam_width_image = save_class['cam_width_image']
            c._cam_height_image = save_class['cam_height_image']
            c._cam_focal_length_x = save_class['cam_focal_length_x']
            c._cam_focal_length_y = save_class['cam_focal_length_y']
            c._cam_pos_x = save_class['cam_pos_x']
            c._cam_pos_y = save_class['cam_pos_y']
            c._cam_pos_z = save_class['cam_pos_z']
            c._cam_rot_x = save_class['cam_rot_x']
            c._cam_rot_y = save_class['cam_rot_y']
            c._cam_rot_z = save_class['cam_rot_z']
            c._angle_factor = save_class['angle_factor']
            c._cam_origin_axis = numpy.array(
                save_class['cam_origin_axis']).reshape((4, 4)).astype(
                numpy.float32)

            c._target_1_pos_x = save_class['target_1_pos_x']
            c._target_1_pos_y = save_class['target_1_pos_y']
            c._target_1_pos_z = save_class['target_1_pos_z']
            c._target_1_rot_x = save_class['target_1_rot_x']
            c._target_1_rot_y = save_class['target_1_rot_y']
            c._target_1_rot_z = save_class['target_1_rot_z']

            c._target_2_pos_x = save_class['target_2_pos_x']
            c._target_2_pos_y = save_class['target_2_pos_y']
            c._target_2_pos_z = save_class['target_2_pos_z']
            c._target_2_rot_x = save_class['target_2_rot_x']
            c._target_2_rot_y = save_class['target_2_rot_y']
            c._target_2_rot_z = save_class['target_2_rot_z']

        return c


class TargetParameters(object):
    def __init__(self):
        self._pos_x = None
        self._pos_y = None
        self._pos_z = None
        self._rot_x = None
        self._rot_y = None
        self._rot_z = None

    def __str__(self):
        out = ''
        out += '\tPosition X : ' + str(self._pos_x) + '\n'
        out += '\tPosition Y : ' + str(self._pos_y) + '\n'
        out += '\tPosition Z : ' + str(self._pos_z) + '\n\n'
        out += '\tRotation X : ' + str(self._rot_x) + '\n'
        out += '\tRotation Y : ' + str(self._rot_y) + '\n'
        out += '\tRotation Z : ' + str(self._rot_z) + '\n\n'
        return out


class Calibration(CalibrationCamera):

    def __init__(self, nb_targets=1, nb_cameras=1, cameras_origin_axis=((1., 0., 0.), (0., 0., -1.), (0., 1., 0.)),
                 targets_origin_axis=((1., 0., 0.), (0., 0., 1.), (0., -1., 0.)), clockwise_rotation=True):
        """
        A class for calibration of n-camera, n-turning targets, imaging systems

        Args:
            nb_targets: (int) number of targets
            nb_cameras: (int) number of cameras
            cameras_origin_axis: [vec, vec, vec] camera origin axis coordinates expressed in world coordinates
                                Camera origin axis define a base position for all camera, that will be used as
                                the origin of camera rotations parameters. Default position is for an horizontal
                                camera pointing as world y+.
            targets_origin_axis: [vec, vec, vec] target origin axis coordinates expressed in world coordinates
                                target origin axis define a base position for all targets (before turning), that will be
                                 used as the origin of targets rotations parameters. Default is for an horizontal
                                 target facing the camera origin.
            clockwise_rotation: (bool) : are targets rotating clockwise ? (default True)

        Details:
            The global world frame is defined by a right handed xyz frame composed of the axis of target rotation
            (z+ upward), x=0 and z=0 planes are defined by xyz position of a reference camera (y+ direction is from
            camera toward z-axis).

            The (local) cameras and image frames are as depicted in
            https://docs.opencv.org/2.4/modules/calib3d/doc/camera_calibration_and_3d_reconstruction.html

            that is :
                - for camera frame: camera origin is image center, z-axis points toward the scene, x is left-> right
                along image width, y is
                    up->down along image height
                - for image frame: origin is top-left, u is left->right along image width, v is up->down along image
                height

            The local target frame origin is target center,right being left-> right along target width and y+ bottom->up
            along target height
        """

        CalibrationCamera.__init__(self)

        self._cameras_origin_axis = cameras_origin_axis
        self._targets_origin_axis = targets_origin_axis
        self.clockwise = clockwise_rotation

        self._verbose = False

        # targets corner points coordinates expressed in targets local frame
        self._targets_points_local_3d = None

        # coordinates of targets corner points on images for the reference camera
        self._ref_targets_points_2d = None
        # total number of target corners points
        self._nb_corners = None

        self._nb_targets = nb_targets
        self._targets_parameters = [TargetParameters() for i in range(nb_targets)]

        # additional cameras (other than reference camera)
        self._nb_others = nb_cameras - 1
        self._others = [CalibrationCamera() for i in range(self._nb_others)]
        self._others_targets_points_2d = None

    def __str__(self):
        out = 'Reference Camera:\n'

        out += CalibrationCamera.__str__(self)

        for i, target in enumerate(self._targets_parameters):
            out += 'Target {}: \n'.format(i)
            out += str(target)

        for i, camera in enumerate(self._others):
            out += 'Additional Camera {}: \n'.format(i)
            out += str(camera)

        return out

    def fit_function(self, x0):
        err = 0

        # reference camera parameters
        cam_pos_x = 0.0
        cam_pos_z = 0.0
        cam_origin_axis_ = cam_origin_axis(self._cameras_origin_axis)
        cam_focal_length_x, cam_focal_length_y, \
        cam_pos_y, \
        cam_rot_x, cam_rot_y, cam_rot_z, \
        angle_factor = x0[0:7]

        fr_cam = CalibrationCamera.camera_frame(
            cam_pos_x, cam_pos_y, cam_pos_z,
            cam_rot_x, cam_rot_y, cam_rot_z,
            cam_origin_axis_)

        for i in range(self._nb_targets):
            for alpha, ref_pts in self._ref_targets_points_2d[i].items():
                pos_x, pos_y, pos_z, rot_x, rot_y, rot_z = x0[7 + i * 6: 13 + i * 6]
                alpha *= angle_factor
                if self.clockwise:
                    alpha *= -1  # alpha labels of ref_pts dict are positive

                fr_target = CalibrationCamera.target_frame(pos_x, pos_y, pos_z,
                                                           rot_x, rot_y, rot_z,
                                                           numpy.radians(alpha))

                target_pts = fr_target.global_point(self._targets_points_local_3d[i])

                pts = CalibrationCamera.pixel_coordinates(fr_cam.local_point(target_pts),
                    self._cam_width_image,
                    self._cam_height_image,
                    cam_focal_length_x,
                    cam_focal_length_y)

                err += numpy.linalg.norm(numpy.array(pts) - ref_pts, axis=1).sum()

        offset = 7 + self._nb_targets * 6
        for i, camera in enumerate(self._others):
            cam_focal_length_x, cam_focal_length_y, \
            cam_pos_x, cam_pos_y, cam_pos_z, \
            cam_rot_x, cam_rot_y, cam_rot_z = x0[offset + i * 8: offset + i * 8 + 8]

            fr_cam = CalibrationCamera.camera_frame(
                cam_pos_x, cam_pos_y, cam_pos_z,
                cam_rot_x, cam_rot_y, cam_rot_z,
                cam_origin_axis_)

            for j in range(self._nb_targets):
                pos_x, pos_y, pos_z, rot_x, rot_y, rot_z = x0[7 + j * 6: 13 + j * 6]
                for alpha, ref_pts in self._others_targets_points_2d[i][j].items():
                    alpha *= angle_factor
                    if self.clockwise:
                        alpha *= -1  # alpha labels of ref_pts dict are positive

                    fr_target = CalibrationCamera.target_frame(pos_x, pos_y, pos_z,
                                                               rot_x, rot_y, rot_z,
                                                               numpy.radians(alpha))

                    target_pts = fr_target.global_point(self._targets_points_local_3d[i])

                    pts = self.pixel_coordinates(fr_cam.local_point(target_pts),
                                                 self._others[i]._cam_width_image,
                                                 self._others[i]._cam_height_image,
                                                 cam_focal_length_x,
                                                 cam_focal_length_y)

                    err += numpy.linalg.norm(
                        numpy.array(pts) - ref_pts, axis=1).sum()

        if self._verbose:
            print(err)

        return err

    def find_parameters(self, number_of_repetition):

        best_parameters = None
        min_err = float('inf')
        for i in range(number_of_repetition + 1):

            cam_focal_length_x = 5500 #numpy.random.uniform(1000.0, 10000.0)
            cam_focal_length_y = 5500 #numpy.random.uniform(1000.0, 10000.0)
            cam_pos_y = - 5500#numpy.random.uniform(10000.0, 1000.0)

            cam_rot_x = 0.0
            cam_rot_y = 0.0
            cam_rot_z = 0.0

            angle_factor = 1.0

            parameters = [cam_focal_length_x, cam_focal_length_y,
                          cam_pos_y,
                          cam_rot_x, cam_rot_y, cam_rot_z,
                          angle_factor]

            for i in range(self._nb_targets):
                parameters += [numpy.random.uniform(-1000.0, 1000.0),  # X Position
                               numpy.random.uniform(-1000.0, 1000.0),  # Y Position
                               numpy.random.uniform(-1000, 1000.0),  # Z Position
                               numpy.pi / 2,  # X Rotation
                               0,  # Y Rotation
                              0]  # Z Rotation

            for i in range(self._nb_others):
                parameters += [numpy.random.uniform(1000.0, 10000.0),  # focal length X
                               numpy.random.uniform(1000.0, 10000.0),  # focal length Y
                               numpy.random.uniform(-200.0, 200.0),  # X Position
                               numpy.random.uniform(-200.0, 500.0),  # Y Position
                               numpy.random.uniform(0, 5000.0),  # Z Position
                               0,  # X Rotation
                               0,  # Y Rotation
                               0]  # Z Rotation

            parameters = scipy.optimize.minimize(
                self.fit_function,
                parameters,
                method='BFGS').x

            err = self.fit_function(parameters)
            if err < min_err:
                min_err = err
                best_parameters = parameters

            if self._verbose:
                err = self.fit_function(parameters)
                print('Result : ', parameters)
                print('Err : ', err / self._nb_corners)

        return best_parameters

    def get_target_1_projected(self, alpha, ref_target_1_points_local_3d):

        fr_cam = self.camera_frame(
            self._cam_pos_x, self._cam_pos_y, self._cam_pos_z,
            self._cam_rot_x, self._cam_rot_y, self._cam_rot_z,
            self._cam_origin_axis)

        fr_target = self.target_frame(self._target_1_pos_x,
                                      self._target_1_pos_y,
                                      self._target_1_pos_z,
                                      self._target_1_rot_x,
                                      self._target_1_rot_y,
                                      self._target_1_rot_z,
                                      math.radians(alpha * self._angle_factor))

        target_pts = list(map(lambda pt: fr_target.global_point(pt),
                              ref_target_1_points_local_3d))

        pts = list(map(lambda pt: self.pixel_coordinates(
            fr_cam.local_point(pt),
            self._cam_width_image,
            self._cam_height_image,
            self._cam_focal_length_x,
            self._cam_focal_length_y), target_pts))

        return pts

    def get_target_2_projected(self, alpha, ref_target_2_points_local_3d):

        fr_cam = self.camera_frame(
            self._cam_pos_x, self._cam_pos_y, self._cam_pos_z,
            self._cam_rot_x, self._cam_rot_y, self._cam_rot_z,
            self._cam_origin_axis)

        fr_target = self.target_frame(self._target_2_pos_x,
                                      self._target_2_pos_y,
                                      self._target_2_pos_z,
                                      self._target_2_rot_x,
                                      self._target_2_rot_y,
                                      self._target_2_rot_z,
                                      math.radians(alpha * self._angle_factor))

        target_pts = list(map(lambda pt: fr_target.global_point(pt),
                              ref_target_2_points_local_3d))

        pts = list(map(lambda pt: self.pixel_coordinates(
            fr_cam.local_point(pt),
            self._cam_width_image,
            self._cam_height_image,
            self._cam_focal_length_x,
            self._cam_focal_length_y), target_pts))

        return pts

    def get_target_1_ref_points_global_3d(self,
                                          alpha,
                                          ref_target_1_points_local_3d):

        fr_target = self.target_frame(self._target_1_pos_x,
                                      self._target_1_pos_y,
                                      self._target_1_pos_z,
                                      self._target_1_rot_x,
                                      self._target_1_rot_y,
                                      self._target_1_rot_z,
                                      math.radians(alpha * self._angle_factor))

        return list(map(lambda pt: fr_target.global_point(pt),
                        ref_target_1_points_local_3d))

    def get_target_2_ref_points_global_3d(self,
                                          alpha,
                                          ref_target_2_points_local_3d):

        fr_target = self.target_frame(self._target_2_pos_x,
                                      self._target_2_pos_y,
                                      self._target_2_pos_z,
                                      self._target_2_rot_x,
                                      self._target_2_rot_y,
                                      self._target_2_rot_z,
                                      math.radians(alpha * self._angle_factor))

        return list(map(lambda pt: fr_target.global_point(pt),
                        ref_target_2_points_local_3d))

    def calibrate(self,
                  targets,
                  size_image,
                  other_cameras=[],
                  number_of_repetition=3,
                  verbose=False):
        """ Find physical parameters associated with a camera
        (i.e. distances and angles), using pictures of a rotating
        target.

        args:
         - 'targets' (target): reference target
         - 'target_corners' dict of (angle, list of pts): for
                        a picture taken with a given angle, list
                        the coordinates of all intersections on
                        the target in the picture
        """
        self._verbose = verbose

        self._targets_points_local_3d = [target[1] for target in targets]

        self._cam_width_image = size_image[0]
        self._cam_height_image = size_image[1]
        self._ref_targets_points_2d = [target[0] for target in targets]

        self._nb_corners = 0
        for target in targets:
            self._nb_corners += len(target[0])

        self._others_targets_points_2d = []
        for i,(image_size, targets_points_2d) in enumerate(other_cameras):
            camera = self._others[i]
            camera._cam_width_image = image_size[0]
            camera._cam_height_image = image_size[1]
            self._others_targets_points_2d.append(targets_points_2d)
            for target in targets_points_2d:
                self._nb_corners += len(target)



        parameters = self.find_parameters(number_of_repetition)

        # Reference Camera Parameters
        self._cam_focal_length_x = parameters[0]
        self._cam_focal_length_y = parameters[1]
        self._cam_pos_y = parameters[2]
        self._cam_rot_x = parameters[3] % math.pi * 2.0
        self._cam_rot_y = parameters[4] % math.pi * 2.0
        self._cam_rot_z = parameters[5] % math.pi * 2.0

        self._angle_factor = parameters[6]

        # Targets Parameters
        for i, target_param in enumerate(self._targets_parameters):
            target_param._pos_x = parameters[7 + i * 6]
            target_param._pos_y = parameters[8 + i * 6]
            target_param._pos_z = parameters[9 + i * 6]
            target_param._rot_x = parameters[10 + i * 6] % math.pi * 2.0
            target_param._rot_y = parameters[11 + i * 6] % math.pi * 2.0
            target_param._rot_z = parameters[12 + i * 6] % math.pi * 2.0

        # other camera parameters
        offset = 7 + self._nb_targets * 6
        for i, camera in enumerate(self._others):
            camera._cam_focal_length_x = parameters[offset + i * 8]
            camera._cam_focal_length_y = parameters[offset + i * 8 + 1]
            camera._cam_pos_x = parameters[offset + i * 8 + 2]
            camera._cam_pos_y = parameters[offset + i * 8 + 3]
            camera._cam_pos_z = parameters[offset + i * 8 + 4]
            camera._cam_rot_x = parameters[offset + i * 8 + 5] % math.pi * 2.0
            camera._cam_rot_y = parameters[offset + i * 8 + 6] % math.pi * 2.0
            camera._cam_rot_z = parameters[offset + i * 8 + 7] % math.pi * 2.0

            camera._angle_factor = parameters[6]

        err = self.fit_function(parameters)
        if self._verbose:
            print('Result : ', parameters)
            print('Err : ', err, ' -- ', err / self._nb_corners)

        self._verbose = False

        return err / self._nb_corners

    def dump(self, filename):
        save_class = dict()

        save_class['cam_width_image'] = self._cam_width_image
        save_class['cam_height_image'] = self._cam_height_image
        save_class['cam_focal_length_x'] = self._cam_focal_length_x
        save_class['cam_focal_length_y'] = self._cam_focal_length_y
        save_class['cam_pos_x'] = self._cam_pos_x
        save_class['cam_pos_y'] = self._cam_pos_y
        save_class['cam_pos_z'] = self._cam_pos_z
        save_class['cam_rot_x'] = self._cam_rot_x
        save_class['cam_rot_y'] = self._cam_rot_y
        save_class['cam_rot_z'] = self._cam_rot_z
        save_class['angle_factor'] = self._angle_factor
        save_class['cam_origin_axis'] = self._cam_origin_axis.reshape(
            (16,)).tolist()

        save_class['targets_parameters'] = [t.__dict__ for t in self._targets_parameters]

        with open(filename, 'w') as output_file:
            json.dump(save_class, output_file,
                      sort_keys=True,
                      indent=4,
                      separators=(',', ': '))

    @staticmethod
    def load(filename):
        with open(filename, 'r') as input_file:
            save_class = json.load(input_file)

            c = Calibration(len(save_class['targets_parameters']))

            c._cam_width_image = save_class['cam_width_image']
            c._cam_height_image = save_class['cam_height_image']
            c._cam_focal_length_x = save_class['cam_focal_length_x']
            c._cam_focal_length_y = save_class['cam_focal_length_y']
            c._cam_pos_x = save_class['cam_pos_x']
            c._cam_pos_y = save_class['cam_pos_y']
            c._cam_pos_z = save_class['cam_pos_z']
            c._cam_rot_x = save_class['cam_rot_x']
            c._cam_rot_y = save_class['cam_rot_y']
            c._cam_rot_z = save_class['cam_rot_z']
            c._angle_factor = save_class['angle_factor']
            c._cam_origin_axis = numpy.array(
                save_class['cam_origin_axis']).reshape((4, 4)).astype(
                numpy.float32)

            c._targets_parameters = list()
            for target_param in save_class['targets_parameters']:
                print(target_param)
                tp = TargetParameters()
                tp._pos_x = target_param["_pos_x"]
                tp._pos_y = target_param["_pos_y"]
                tp._pos_z = target_param["_pos_z"]
                tp._rot_x = target_param["_rot_x"]
                tp._rot_y = target_param["_rot_y"]
                tp._rot_z = target_param["_rot_z"]
                print(tp)
                c._targets_parameters.append(tp)
            print(c._targets_parameters)
            return c


def find_position_3d_points(pt2d, calibrations):
    def fit_function(x0):

        sum_err = 0
        vec_err = list()
        for id_camera in pt2d:
            for angle in pt2d[id_camera]:
                if id_camera in calibrations:
                    calib = calibrations[id_camera]
                    fr_cam = calib.camera_frame(
                        calib._cam_pos_x, calib._cam_pos_y, calib._cam_pos_z,
                        calib._cam_rot_x, calib._cam_rot_y, calib._cam_rot_z,
                        calib._cam_origin_axis)

                    pos_x, pos_y, pos_z = x0
                    alpha = math.radians(angle * calib._angle_factor)

                    origin = [pos_x * math.cos(alpha) - pos_y * math.sin(alpha),
                              pos_x * math.sin(alpha) + pos_y * math.cos(alpha),
                              pos_z]

                    pt = calibrations[id_camera].pixel_coordinates(
                        fr_cam.local_point(origin),
                        calib._cam_width_image,
                        calib._cam_height_image,
                        calib._cam_focal_length_x,
                        calib._cam_focal_length_y)

                    err = numpy.linalg.norm(
                        numpy.array(pt) - pt2d[id_camera][angle]).sum()

                    # vec_err.append(err)
                    sum_err += err

        # return vec_err
        return sum_err

    parameters = [0.0] * 3
    parameters = scipy.optimize.basinhopping(fit_function, parameters).x

    print("Err : ", fit_function(parameters))
    return parameters


def find_position_3d_points_soil(pts, calibrations, verbose=False):
    def soil_frame(pos_x, pos_y, pos_z,
                   rot_x, rot_y, rot_z):

        origin = (pos_x, pos_y, pos_z)

        mat_rot_x = rotation_matrix(rot_x, x_axis)
        mat_rot_y = rotation_matrix(rot_y, y_axis)
        mat_rot_z = rotation_matrix(rot_z, z_axis)

        rot = concatenate_matrices(mat_rot_x, mat_rot_y, mat_rot_z)

        return Frame(rot[:3, :3].T, origin)

    def err_projection(x0, verbose=False):
        err = 0

        sf = soil_frame(0, 0, x0[0],
                        x0[1], x0[2], x0[3])

        for i in range(len(pts)):
            pt2d = pts[i]
            for id_camera in pt2d:
                for angle in pt2d[id_camera]:
                    if id_camera in calibrations:
                        calib = calibrations[id_camera]
                        fr_cam = calib.camera_frame(
                            calib._cam_pos_x, calib._cam_pos_y, calib._cam_pos_z,
                            calib._cam_rot_x, calib._cam_rot_y, calib._cam_rot_z,
                            calib._cam_origin_axis)

                        pos_x, pos_y, pos_z = sf.global_point(
                            (x0[4 + i * 2], x0[5 + i * 2], 0))
                        alpha = math.radians(angle * calib._angle_factor)

                        origin = [pos_x * math.cos(alpha) - pos_y * math.sin(alpha),
                                  pos_x * math.sin(alpha) + pos_y * math.cos(alpha),
                                  pos_z]

                        pt = calib.pixel_coordinates(
                            fr_cam.local_point(origin),
                            calib._cam_width_image,
                            calib._cam_height_image,
                            calib._cam_focal_length_x,
                            calib._cam_focal_length_y)

                        err += numpy.linalg.norm(
                            numpy.array(pt) - pt2d[id_camera][angle]).sum()

                        if verbose:
                            print("ID CAMERA & ANGLE", id_camera, angle)
                            print('PT 3D : ', pos_x, pos_y, pos_z)
                            print("Projection image 2D", pt)
                            print("Ref image 2D", pt2d[id_camera][angle])
                            print("Distance :", numpy.linalg.norm(
                                numpy.array(pt - pt2d[id_camera][angle]).sum()))
                            print("\n\n")

        print(err)
        return err

    def fit_function(x0):
        return err_projection(x0)

    parameters = [0, 0, 0, 0]
    parameters += [0] * 2 * len(pts)

    parameters = scipy.optimize.basinhopping(
        fit_function, parameters, niter=10).x

    for i in [1, 2, 3]:
        parameters[i] %= math.pi * 2.0

    if verbose:
        print("Err : ", err_projection(parameters, verbose=True))

    sf = soil_frame(0, 0, parameters[0],
                    parameters[1], parameters[2], parameters[3])

    return parameters, sf

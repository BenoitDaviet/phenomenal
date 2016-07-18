# -*- python -*-
#
#       Copyright 2015 INRIA - CIRAD - INRA
#
#       Distributed under the Cecill-C License.
#       See accompanying file LICENSE.txt or copy at
#           http://www.cecill.info/licences/Licence_CeCILL-C_V1-en.html
#
# ==============================================================================
""" This module contains a calibration model for phenoarch experiment
where a target is rotating instead of a plant in a picture cabin.
"""
# ==============================================================================
import json
import math

import numpy
import scipy.optimize

from alinea.phenomenal.calibration.frame import (
    Frame, x_axis, y_axis, z_axis)
from alinea.phenomenal.calibration.transformations import (
    concatenate_matrices, rotation_matrix)

# ==============================================================================

__all__ = ["CalibrationCamera",
           "CalibrationCameraTop",
           "CalibrationCameraSideWith1Target",
           "CalibrationCameraSideWith2Target"]

# ==============================================================================


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
        out += '\tOptical Center X : ' + str(self._cam_width_image / 2.0) + '\n'
        out += '\tOptical Center Y : ' + str(self._cam_height_image / 2.0)
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
         - point (float, float, float): a point in space
                    expressed in camera frame coordinates

        return:
         - (int, int): coordinate of point in image in pix
        """
        # if point[2] < 1:
        #     raise UserWarning("point too close to the camera")

        u = point_3d[0] / point_3d[2] * focal_length_x + width_image / 2.0
        v = point_3d[1] / point_3d[2] * focal_length_y + height_image / 2.0

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
        # if point[2] < 1:
        #     raise UserWarning("point too close to the camera")

        u = point_3d[0] / point_3d[2] * fx + cx
        v = point_3d[1] / point_3d[2] * fy + cy

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

    def get_projection(self, alpha):

        fr_cam = self.camera_frame(
            self._cam_pos_x, self._cam_pos_y, self._cam_pos_z,
            self._cam_rot_x, self._cam_rot_y, self._cam_rot_z,
            self._cam_origin_axis)

        angle = math.radians(alpha * self._angle_factor)

        def projection(pt):
            # -pt[0] = x <=> For inverse X axis orientation
            origin = [-pt[0] * math.cos(angle) - pt[1] * math.sin(angle),
                      -pt[0] * math.sin(angle) + pt[1] * math.cos(angle),
                      pt[2]]

            return self.pixel_coordinates(fr_cam.local_point(origin),
                                          self._cam_width_image,
                                          self._cam_height_image,
                                          self._cam_focal_length_x,
                                          self._cam_focal_length_y)

        return projection

    def get_projection2(self, alpha):
        fr_cam = self.camera_frame(
            self._cam_pos_x, self._cam_pos_y, self._cam_pos_z,
            self._cam_rot_x, self._cam_rot_y, self._cam_rot_z,
            self._cam_origin_axis)

        angle = math.radians(alpha * self._angle_factor)

        def projection(pt):
            # -pt[0] = x <=> For inverse X axis orientation
            origin = [pt[0] * math.cos(angle) - pt[1] * math.sin(angle),
                      pt[0] * math.sin(angle) + pt[1] * math.cos(angle),
                      pt[2]]

            return self.pixel_coordinates(fr_cam.local_point(origin),
                                          self._cam_width_image,
                                          self._cam_height_image,
                                          self._cam_focal_length_x,
                                          self._cam_focal_length_y)

        return projection

    @staticmethod
    def load(file_path):
        with open(file_path + '.json', 'r') as input_file:
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

    def dump(self, file_path):
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
            (16, )).tolist()

        with open(file_path + '.json', 'w') as output_file:
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

        self._cam_origin_axis = numpy.array([[0., -1., 0., 0.],
                                             [1., 0., 0., 0.],
                                             [0., 0., 1., 0.],
                                             [0., 0., 0., 1.]])

    def fit_function(self, x0):
        err = 0

        cam_focal_length_x, cam_focal_length_y, \
        cam_pos_x, cam_pos_y, cam_pos_z, \
        cam_rot_x, cam_rot_y, cam_rot_z = x0

        fr_cam = self.camera_frame(
            cam_pos_x, cam_pos_y, cam_pos_z,
            cam_rot_x, cam_rot_y, cam_rot_z,
            self._cam_origin_axis)

        for i in xrange(len(self._ref_target_points_2d)):
            pts = map(lambda pt: self.pixel_coordinates(
                fr_cam.local_point(pt),
                self._cam_width_image,
                self._cam_height_image,
                cam_focal_length_x,
                cam_focal_length_y), self._ref_target_points_3d[i])

            err += numpy.linalg.norm(
                numpy.array(pts) - self._ref_target_points_2d[i], axis=1).sum()

        if self._verbose:
            print err

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
                print 'Result : ', parameters
                print 'Err : ', err / self._ref_number

        return best_parameters

    def project_points_3d(self, points_3d):

        fr_cam = self.camera_frame(
            self._cam_pos_x, self._cam_pos_y, self._cam_pos_z,
            self._cam_rot_x, self._cam_rot_y, self._cam_rot_z,
            self._cam_origin_axis)

        pts = map(lambda pt: self.pixel_coordinates(
            fr_cam.local_point(pt),
            self._cam_width_image,
            self._cam_height_image,
            self._cam_focal_length_x,
            self._cam_focal_length_y), points_3d)

        return pts

    @staticmethod
    def load(file_path):
        with open(file_path + '.json', 'r') as input_file:
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
            print 'Result : ', parameters
            print 'Err : ', err, ' -- ', err / self._ref_number

        self._verbose = False

        return err / self._ref_number


class CalibrationCameraTopBis(CalibrationCamera):
    def __init__(self, camera_top=None):
        CalibrationCamera.__init__(self)
        self._verbose = False

        self._ref_target_points_local_3d = None
        self._ref_target_points_2d = None
        self._ref_target_points_3d = None

        self._ref_number = None

        self._cam_origin_axis = numpy.array([[0., -1., 0., 0.],
                                             [1., 0., 0., 0.],
                                             [0., 0., 1., 0.],
                                             [0., 0., 0., 1.]])

        self._camera_top = camera_top

    def fit_function(self, x0):
        err = 0

        cam_focal_length_x, cam_focal_length_y, \
        cam_pos_x, cam_pos_y, cam_pos_z, \
        cam_rot_x, cam_rot_y, cam_rot_z = x0

        frame_camera_top = self.camera_frame(
            cam_pos_x, cam_pos_y, cam_pos_z,
            cam_rot_x, cam_rot_y, cam_rot_z,
            self._cam_origin_axis)

        def projection_camera_top(pt_3d):
            return CalibrationCamera.pixel_coordinates(
                frame_camera_top.local_point(pt_3d),
                self._cam_width_image,
                self._cam_height_image,
                cam_focal_length_x,
                cam_focal_length_y)

        for i in xrange(len(self._ref_target_points_2d)):
            pt = projection_camera_top(self._ref_target_points_3d[i])

            err += numpy.linalg.norm(
                numpy.array(pt) - self._ref_target_points_2d[i]).sum()

        if self._verbose:
            print err

        return err

    def find_parameters(self, number_of_repetition):
        best_parameters = None
        min_err = float('inf')
        for i in range(number_of_repetition + 1):

            if self._camera_top is not None:
                cam_focal_length_x = self._camera_top._cam_focal_length_x
                cam_focal_length_y = self._camera_top._cam_focal_length_y
                cam_pos_x = self._camera_top._cam_pos_x
                cam_pos_y = self._camera_top._cam_pos_y
                cam_pos_z = self._camera_top._cam_pos_z
                cam_rot_x = self._camera_top._cam_rot_x
                cam_rot_y = self._camera_top._cam_rot_y
                cam_rot_z = self._camera_top._cam_rot_z
            else:
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
                print 'Result : ', parameters
                print 'Err : ', err / self._ref_number

        return best_parameters

    def project_points_3d(self, points_3d):

        fr_cam = self.camera_frame(
            self._cam_pos_x, self._cam_pos_y, self._cam_pos_z,
            self._cam_rot_x, self._cam_rot_y, self._cam_rot_z,
            self._cam_origin_axis)

        pts = map(lambda pt: self.pixel_coordinates(
            fr_cam.local_point(pt),
            self._cam_width_image,
            self._cam_height_image,
            self._cam_focal_length_x,
            self._cam_focal_length_y), points_3d)

        return pts

    @staticmethod
    def load(file_path):
        with open(file_path + '.json', 'r') as input_file:
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
            print 'Result : ', parameters
            print 'Err : ', err, ' -- ', err / self._ref_number

        self._verbose = False

        return err / self._ref_number


class CalibrationCameraTopPosition(CalibrationCamera):
    def __init__(self, camera_top=None):
        CalibrationCamera.__init__(self)
        self._verbose = False

        self._ref_target_points_local_3d = None
        self._ref_target_points_2d = None
        self._ref_target_points_3d = None

        self._ref_number = None

        self._cam_origin_axis = numpy.array([[0., -1., 0., 0.],
                                             [1., 0., 0., 0.],
                                             [0., 0., 1., 0.],
                                             [0., 0., 0., 1.]])

        self._camera_top = camera_top

        if camera_top is not None:
            self._cam_focal_length_x = self._camera_top._cam_focal_length_x
            self._cam_focal_length_y = self._camera_top._cam_focal_length_y

        else:
            self._cam_focal_length_x = 3785
            self._cam_focal_length_y = 3772

    def fit_function(self, x0):
        err = 0

        cam_pos_x, cam_pos_y, cam_pos_z, \
            cam_rot_x, cam_rot_y, cam_rot_z = x0

        fr_cam = self.camera_frame(
            cam_pos_x, cam_pos_y, cam_pos_z,
            cam_rot_x, cam_rot_y, cam_rot_z,
            self._cam_origin_axis)

        for i in xrange(len(self._ref_target_points_2d)):
            pts = map(lambda pt: self.pixel_coordinates(
                fr_cam.local_point(pt),
                self._cam_width_image,
                self._cam_height_image,
                self._cam_focal_length_x,
                self._cam_focal_length_y), self._ref_target_points_3d[i])

            err += numpy.linalg.norm(
                numpy.array(pts) - self._ref_target_points_2d[i], axis=1).sum()

        if self._verbose:
            print err

        return err

    def find_parameters(self, number_of_repetition):
        best_parameters = None
        min_err = float('inf')
        for i in range(number_of_repetition + 1):

            if self._camera_top is not None:
                cam_pos_x = self._camera_top._cam_pos_x
                cam_pos_y = self._camera_top._cam_pos_y
                cam_pos_z = self._camera_top._cam_pos_z
                cam_rot_x = self._camera_top._cam_rot_x
                cam_rot_y = self._camera_top._cam_rot_y
                cam_rot_z = self._camera_top._cam_rot_z

                print cam_pos_x, cam_pos_y, cam_pos_z
            else:
                cam_pos_x = numpy.random.uniform(-500.0, 500.0)
                cam_pos_y = numpy.random.uniform(-500.0, 500.0)
                cam_pos_z = numpy.random.uniform(0.0, 10000.0)
                cam_rot_x = 0.0
                cam_rot_y = 0.0
                cam_rot_z = 0.0

            parameters = [cam_pos_x, cam_pos_y, cam_pos_z,
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
                print 'Result : ', parameters
                print 'Err : ', err / self._ref_number

        return best_parameters

    def project_points_3d(self, points_3d):

        fr_cam = self.camera_frame(
            self._cam_pos_x, self._cam_pos_y, self._cam_pos_z,
            self._cam_rot_x, self._cam_rot_y, self._cam_rot_z,
            self._cam_origin_axis)

        pts = map(lambda pt: self.pixel_coordinates(
            fr_cam.local_point(pt),
            self._cam_width_image,
            self._cam_height_image,
            self._cam_focal_length_x,
            self._cam_focal_length_y), points_3d)

        return pts

    @staticmethod
    def load(file_path):
        with open(file_path + '.json', 'r') as input_file:
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

        for i in [3, 4, 5]:
            parameters[i] %= math.pi * 2.0

        self._cam_pos_x = parameters[0]
        self._cam_pos_y = parameters[1]
        self._cam_pos_z = parameters[2]
        self._cam_rot_x = parameters[3]
        self._cam_rot_y = parameters[4]
        self._cam_rot_z = parameters[5]

        err = self.fit_function(parameters)
        if self._verbose:
            print 'Result : ', parameters
            print 'Err : ', err, ' -- ', err / self._ref_number

        self._verbose = False

        return err / self._ref_number


class CalibrationCameraTopFocal(CalibrationCamera):
    def __init__(self, camera_top=None):
        CalibrationCamera.__init__(self)
        self._verbose = False

        self._ref_target_points_local_3d = None
        self._ref_target_points_2d = None
        self._ref_target_points_3d = None

        self._ref_number = None

        if camera_top is not None:

            self._cam_origin_axis = camera_top._cam_origin_axis

            self._cam_pos_x = camera_top._cam_pos_x
            self._cam_pos_y = camera_top._cam_pos_y
            self._cam_pos_z = camera_top._cam_pos_z
            self._cam_rot_x = camera_top._cam_rot_x
            self._cam_rot_y = camera_top._cam_rot_y
            self._cam_rot_z = camera_top._cam_rot_z
        else:
            self._cam_origin_axis = numpy.array([[0., -1., 0., 0.],
                                                 [1., 0., 0., 0.],
                                                 [0., 0., 1., 0.],
                                                 [0., 0., 0., 1.]])
        self._cam_focal_length_x = None
        self._cam_focal_length_y = None

    def fit_function(self, x0):
        err = 0

        cam_focal_length_x, cam_focal_length_y = x0

        frame_camera_top = self.camera_frame(
            self._cam_pos_x, self._cam_pos_y, self._cam_pos_z,
            self._cam_rot_x, self._cam_rot_y, self._cam_rot_z,
            self._cam_origin_axis)

        def projection_camera_top(pt_3d):
            return CalibrationCamera.pixel_coordinates(
                frame_camera_top.local_point(pt_3d),
                self._cam_width_image,
                self._cam_height_image,
                cam_focal_length_x,
                cam_focal_length_y)

        for i in xrange(len(self._ref_target_points_2d)):
            pt = projection_camera_top(self._ref_target_points_3d[i])

            err += numpy.linalg.norm(
                numpy.array(pt) - self._ref_target_points_2d[i]).sum()

        if self._verbose:
            print err

        return err

    def find_parameters(self, number_of_repetition):
        best_parameters = None
        min_err = float('inf')
        for i in range(number_of_repetition + 1):

            cam_focal_length_x = numpy.random.uniform(0.0, 10000.0)
            cam_focal_length_y = numpy.random.uniform(0.0, 10000.0)

            parameters = [cam_focal_length_x, cam_focal_length_y]

            # Optimization
            parameters = scipy.optimize.minimize(
                self.fit_function, parameters, method='BFGS').x

            # Compute error compare with min_err
            err = self.fit_function(parameters)
            if err < min_err:
                min_err = err
                best_parameters = parameters

            if self._verbose:
                print 'Result : ', parameters
                print 'Err : ', err / self._ref_number

        return best_parameters

    def project_points_3d(self, points_3d):

        fr_cam = self.camera_frame(
            self._cam_pos_x, self._cam_pos_y, self._cam_pos_z,
            self._cam_rot_x, self._cam_rot_y, self._cam_rot_z,
            self._cam_origin_axis)

        pts = map(lambda pt: self.pixel_coordinates(
            fr_cam.local_point(pt),
            self._cam_width_image,
            self._cam_height_image,
            self._cam_focal_length_x,
            self._cam_focal_length_y), points_3d)

        return pts

    @staticmethod
    def load(file_path):
        with open(file_path + '.json', 'r') as input_file:
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

        self._cam_focal_length_x = parameters[0]
        self._cam_focal_length_y = parameters[1]

        err = self.fit_function(parameters)
        if self._verbose:
            print 'Result : ', parameters
            print 'Err : ', err, ' -- ', err / self._ref_number

        self._verbose = False

        return err / self._ref_number


class CalibrationCameraSideWith1Target(CalibrationCamera):
    def __init__(self):
        CalibrationCamera.__init__(self)
        self._verbose = False
        self._ref_target_points_local_3d = None
        self._ref_number = None
        self._ref_target_points_2d = None

        self._cam_pos_z = 0.0
        self._cam_origin_axis = numpy.array([[0., 0., 1., 0.],
                                             [1., 0., 0., 0.],
                                             [0., 1., 0., 0.],
                                             [0., 0., 0., 1.]])

        self._target_pos_x = None
        self._target_pos_y = None
        self._target_pos_z = None
        self._target_rot_x = None
        self._target_rot_y = None
        self._target_rot_z = None

    def __str__(self):
        out = ''
        out += CalibrationCamera.__str__(self)

        out += 'Target : \n'
        out += '\tPosition X : ' + str(self._target_pos_x) + '\n'
        out += '\tPosition Y : ' + str(self._target_pos_y) + '\n'
        out += '\tPosition Z : ' + str(self._target_pos_z) + '\n\n'
        out += '\tRotation X : ' + str(self._target_rot_x) + '\n'
        out += '\tRotation Y : ' + str(self._target_rot_y) + '\n'
        out += '\tRotation Z : ' + str(self._target_rot_z) + '\n\n'

        return out

    def fit_function(self, x0):
        err = 0

        cam_focal_length_x, cam_focal_length_y, \
            cam_pos_x, cam_pos_y, \
            cam_rot_x, cam_rot_y, cam_rot_z, \
            angle_factor, \
            target_pos_x, target_pos_y, target_pos_z, \
            target_rot_x, target_rot_y, target_rot_z = x0

        fr_cam = self.camera_frame(
            cam_pos_x, cam_pos_y, self._cam_pos_z,
            cam_rot_x, cam_rot_y, cam_rot_z,
            self._cam_origin_axis)

        for alpha, ref_pts in self._ref_target_points_2d.items():
            fr_target = self.target_frame(
                target_pos_x, target_pos_y, target_pos_z,
                target_rot_x, target_rot_y, target_rot_z,
                math.radians(alpha * angle_factor))

            target_pts = map(lambda pt: fr_target.global_point(pt),
                             self._ref_target_points_local_3d)

            pts = map(lambda pt: self.pixel_coordinates(
                fr_cam.local_point(pt),
                self._cam_width_image,
                self._cam_height_image,
                cam_focal_length_x,
                cam_focal_length_y), target_pts)

            err += numpy.linalg.norm(numpy.array(pts) - ref_pts, axis=1).sum()

        if self._verbose:
            print err

        return err

    def find_parameters(self, number_of_repetition):

        best_parameters = None
        min_err = float('inf')
        for i in range(number_of_repetition + 1):

            cam_focal_length_x = numpy.random.uniform(1000.0, 10000.0)
            cam_focal_length_y = numpy.random.uniform(1000.0, 10000.0)
            cam_pos_x = numpy.random.uniform(1000.0, 10000.0)
            cam_pos_y = 0.0
            cam_rot_x = 0.0
            cam_rot_y = 0.0
            cam_rot_z = 0.0

            angle_factor = 1.0

            target_pos_x = numpy.random.uniform(-1000.0, 1000.0)
            target_pos_y = numpy.random.uniform(-1000.0, 1000.0)
            target_pos_z = numpy.random.uniform(0, 1000.0)
            target_rot_x = 0.0
            target_rot_y = 0.0
            target_rot_z = 0.0

            parameters = [cam_focal_length_x, cam_focal_length_y,
                          cam_pos_x, cam_pos_y,
                          cam_rot_x, cam_rot_y, cam_rot_z,
                          angle_factor,
                          target_pos_x, target_pos_y, target_pos_z,
                          target_rot_x, target_rot_y, target_rot_z]

            parameters = scipy.optimize.minimize(
                self.fit_function, parameters, method='BFGS').x

            err = self.fit_function(parameters)
            if err < min_err:
                min_err = err
                best_parameters = parameters

            if self._verbose:
                err = self.fit_function(parameters)
                print 'Result : ', parameters
                print 'Err : ', err / self._ref_number

        return best_parameters

    def calibrate(self,
                  ref_target_points_2d,
                  ref_target_points_local_3d,
                  size_image,
                  number_of_repetition=1,
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

        self._ref_target_points_2d = ref_target_points_2d.copy()
        self._ref_target_points_local_3d = ref_target_points_local_3d
        self._ref_number = len(ref_target_points_2d)

        self._cam_width_image = size_image[0]
        self._cam_height_image = size_image[1]

        parameters = self.find_parameters(number_of_repetition)

        for i in [4, 5, 6, 11, 12, 13]:
            parameters[i] %= math.pi* 2.0

        # Camera Parameters
        self._cam_focal_length_x = parameters[0]
        self._cam_focal_length_y = parameters[1]
        self._cam_pos_x = parameters[2]
        self._cam_pos_y = parameters[3]
        self._cam_rot_x = parameters[4]
        self._cam_rot_y = parameters[5]
        self._cam_rot_z = parameters[6]

        self._angle_factor = parameters[7]

        # Target Parameters
        self._target_pos_x = parameters[8]
        self._target_pos_y = parameters[9]
        self._target_pos_z = parameters[10]
        self._target_rot_x = parameters[11]
        self._target_rot_y = parameters[12]
        self._target_rot_z = parameters[13]

        err = self.fit_function(parameters)
        if self._verbose:
            print 'Result : ', parameters
            print 'Err : ', err, ' -- ', err / self._ref_number

        self._verbose = False
        return err / self._ref_number

    @staticmethod
    def load(file_path):
        with open(file_path + '.json', 'r') as input_file:
            save_class = json.load(input_file)

            c = CalibrationCameraSideWith1Target()

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

            c._target_pos_x = save_class['target_pos_x']
            c._target_pos_y = save_class['target_pos_y']
            c._target_pos_z = save_class['target_pos_z']
            c._target_rot_x = save_class['target_rot_x']
            c._target_rot_y = save_class['target_rot_y']
            c._target_rot_z = save_class['target_rot_z']

        return c

    def dump(self, file_path):
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
            (16, )).tolist()

        save_class['target_pos_x'] = self._target_pos_x
        save_class['target_pos_y'] = self._target_pos_y
        save_class['target_pos_z'] = self._target_pos_z
        save_class['target_rot_x'] = self._target_rot_x
        save_class['target_rot_y'] = self._target_rot_y
        save_class['target_rot_z'] = self._target_rot_z

        with open(file_path + '.json', 'w') as output_file:
            json.dump(save_class, output_file,
                      sort_keys=True,
                      indent=4,
                      separators=(',', ': '))

    def get_ref_points_global_3d(self, alpha, ref_points_local_3d):

        fr_target = CalibrationCamera.target_frame(
            self._target_pos_x, self._target_pos_y, self._target_pos_z,
            self._target_rot_x, self._target_rot_y, self._target_rot_z,
            math.radians(alpha * self._angle_factor))

        return map(lambda pt: fr_target.global_point(pt), ref_points_local_3d)

    def get_target_projected(self, alpha, ref_target_1_points_local_3d):

        fr_cam = self.camera_frame(
            self._cam_pos_x, self._cam_pos_y, self._cam_pos_z,
            self._cam_rot_x, self._cam_rot_y, self._cam_rot_z,
            self._cam_origin_axis)

        fr_target = self.target_frame(self._target_pos_x,
                                      self._target_pos_y,
                                      self._target_pos_z,
                                      self._target_rot_x,
                                      self._target_rot_y,
                                      self._target_rot_z,
                                      math.radians(alpha * self._angle_factor))

        target_pts = map(lambda pt: fr_target.global_point(pt),
                         ref_target_1_points_local_3d)

        pts = map(lambda pt: self.pixel_coordinates(
            fr_cam.local_point(pt),
            self._cam_width_image,
            self._cam_height_image,
            self._cam_focal_length_x,
            self._cam_focal_length_y), target_pts)

        return pts


class CalibrationCameraSideWith2Target(CalibrationCamera):
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
        self._cam_origin_axis = numpy.array([[0., 0., 1., 0.],
                                             [1., 0., 0., 0.],
                                             [0., 1., 0., 0.],
                                             [0., 0., 0., 1.]])

        # self._cam_origin_axis = numpy.array([[0., 0., -1., 0.],
        #                                      [1., 0., 0., 0.],
        #                                      [0., 1., 0., 0.],
        #                                      [0., 0., 0., 1.]])

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
            target_1_pos_x, target_1_pos_y, target_1_pos_z,\
            target_1_rot_x, target_1_rot_y, target_1_rot_z,\
            target_2_pos_x, target_2_pos_y, target_2_pos_z,\
            target_2_rot_x, target_2_rot_y, target_2_rot_z = x0

        # angle_factor = abs(angle_factor)

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

            target_pts = map(lambda pt: fr_target.global_point(pt),
                             self._ref_target_1_points_local_3d)

            pts = map(lambda pt: self.pixel_coordinates(
                fr_cam.local_point(pt),
                self._cam_width_image,
                self._cam_height_image,
                cam_focal_length_x,
                cam_focal_length_y), target_pts)

            err += numpy.linalg.norm(numpy.array(pts) - ref_pts, axis=1).sum()

        for alpha, ref_pts in self._ref_target_2_points_2d.items():

            fr_target = self.target_frame(target_2_pos_x,
                                          target_2_pos_y,
                                          target_2_pos_z,
                                          target_2_rot_x,
                                          target_2_rot_y,
                                          target_2_rot_z,
                                          math.radians(alpha * angle_factor))

            target_pts = map(lambda pt: fr_target.global_point(pt),
                             self._ref_target_2_points_local_3d)

            pts = map(lambda pt: self.pixel_coordinates(
                fr_cam.local_point(pt),
                self._cam_width_image,
                self._cam_height_image,
                cam_focal_length_x,
                cam_focal_length_y), target_pts)

            err += numpy.linalg.norm(numpy.array(pts) - ref_pts, axis=1).sum()

        if self._verbose:
            print err

        return err

    def find_parameters(self, number_of_repetition):

        best_parameters = None
        min_err = float('inf')
        for i in range(number_of_repetition + 1):

            cam_focal_length_x = numpy.random.uniform(1000.0, 10000.0)
            cam_focal_length_y = numpy.random.uniform(1000.0, 10000.0)
            cam_pos_x = numpy.random.uniform(1000.0, 10000.0)
            cam_pos_y = 0.0
            cam_rot_x = 0.0
            cam_rot_z = 0.0

            angle_factor = 1.0

            target_1_pos_x = numpy.random.uniform(-1000.0, 1000.0)
            target_1_pos_y = numpy.random.uniform(-1000.0, 1000.0)
            target_1_pos_z = numpy.random.uniform(0, 1000.0)
            target_1_rot_x = 0
            target_1_rot_y = 0
            target_1_rot_z = 0

            target_2_pos_x = - target_1_pos_x
            target_2_pos_y = - target_1_pos_y
            target_2_pos_z = numpy.random.uniform(0, 1000.0)
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
                print 'Result : ', parameters
                print 'Err : ', err / self._ref_number

        return best_parameters

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

        self._ref_number = (len(ref_target_1_points_2d) +
                            len(ref_target_2_points_2d))

        self._ref_target_1_points_2d = ref_target_1_points_2d.copy()
        self._ref_target_2_points_2d = ref_target_2_points_2d.copy()

        self._cam_width_image = size_image[0]
        self._cam_height_image = size_image[1]

        parameters = self.find_parameters(number_of_repetition)

        for i in [4, 5, 10, 11, 12, 16, 17, 18]:
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
            print 'Result : ', parameters
            print 'Err : ', err, ' -- ', err / self._ref_number

        self._verbose = False

        return err / self._ref_number

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

        target_pts = map(lambda pt: fr_target.global_point(pt),
                         ref_target_1_points_local_3d)

        pts = map(lambda pt: self.pixel_coordinates(
            fr_cam.local_point(pt),
            self._cam_width_image,
            self._cam_height_image,
            self._cam_focal_length_x,
            self._cam_focal_length_y), target_pts)

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

        target_pts = map(lambda pt: fr_target.global_point(pt),
                         ref_target_2_points_local_3d)

        pts = map(lambda pt: self.pixel_coordinates(
            fr_cam.local_point(pt),
            self._cam_width_image,
            self._cam_height_image,
            self._cam_focal_length_x,
            self._cam_focal_length_y), target_pts)

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

        return map(lambda pt: fr_target.global_point(pt),
                   ref_target_1_points_local_3d)

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

        return map(lambda pt: fr_target.global_point(pt),
                   ref_target_2_points_local_3d)

    def dump(self, file_path):
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
            (16, )).tolist()

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

        with open(file_path + '.json', 'w') as output_file:
            json.dump(save_class, output_file,
                      sort_keys=True,
                      indent=4,
                      separators=(',', ': '))

    @staticmethod
    def load(file_path):
        with open(file_path + '.json', 'r') as input_file:
            save_class = json.load(input_file)

            c = CalibrationCameraSideWith2Target()

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

        self._cam_rot_z = 0.0
        self._cam_rot_y = 0.0
        self._cam_origin_axis = numpy.array([[1., 0., 0., 0.],
                                             [0., 0., -1., 0.],
                                             [0., 1., 0., 0.],
                                             [0., 0., 0., 1.]])

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

            target_pts = map(lambda pt: fr_target.global_point(pt),
                             self._ref_target_1_points_local_3d)

            pts = map(lambda pt: self.pixel_coordinates(
                fr_cam.local_point(pt),
                self._cam_width_image,
                self._cam_height_image,
                cam_focal_length_x,
                cam_focal_length_y), target_pts)

            err += numpy.linalg.norm(numpy.array(pts) - ref_pts, axis=1).sum()

        for alpha, ref_pts in self._ref_target_2_points_2d.items():
            fr_target = self.target_frame(target_2_pos_x,
                                          target_2_pos_y,
                                          target_2_pos_z,
                                          target_2_rot_x,
                                          target_2_rot_y,
                                          target_2_rot_z,
                                          math.radians(alpha * angle_factor))

            target_pts = map(lambda pt: fr_target.global_point(pt),
                             self._ref_target_2_points_local_3d)

            pts = map(lambda pt: self.pixel_coordinates(
                fr_cam.local_point(pt),
                self._cam_width_image,
                self._cam_height_image,
                cam_focal_length_x,
                cam_focal_length_y), target_pts)

            err += numpy.linalg.norm(numpy.array(pts) - ref_pts, axis=1).sum()

        if self._verbose:
            print err

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
                print 'Result : ', parameters
                print 'Err : ', err / self._ref_number

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

        target_pts = map(lambda pt: fr_target.global_point(pt),
                         ref_target_1_points_local_3d)

        pts = map(lambda pt: self.pixel_coordinates(
            fr_cam.local_point(pt),
            self._cam_width_image,
            self._cam_height_image,
            self._cam_focal_length_x,
            self._cam_focal_length_y), target_pts)

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

        target_pts = map(lambda pt: fr_target.global_point(pt),
                         ref_target_2_points_local_3d)

        pts = map(lambda pt: self.pixel_coordinates(
            fr_cam.local_point(pt),
            self._cam_width_image,
            self._cam_height_image,
            self._cam_focal_length_x,
            self._cam_focal_length_y), target_pts)

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

        return map(lambda pt: fr_target.global_point(pt),
                   ref_target_1_points_local_3d)

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

        return map(lambda pt: fr_target.global_point(pt),
                   ref_target_2_points_local_3d)

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
            print 'Result : ', parameters
            print 'Err : ', err, ' -- ', err / self._ref_number

        self._verbose = False

        return err / self._ref_number

    def dump(self, file_path):
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

        with open(file_path + '.json', 'w') as output_file:
            json.dump(save_class, output_file,
                      sort_keys=True,
                      indent=4,
                      separators=(',', ': '))

    @staticmethod
    def load(file_path):
        with open(file_path + '.json', 'r') as input_file:
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


class CalibrationCameraSideCameraTopWith2Target(object):
    def __init__(self):

        self._verbose = False

        self._ref_target_1_points_local_3d = None
        self._ref_target_2_points_local_3d = None

        self._ref_number = None

        self._ref_target_1_side_points_2d = None
        self._ref_target_2_side_points_2d = None
        self._ref_target_1_top_points_2d = None
        self._ref_target_2_top_points_2d = None

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

        self._cam_side_width_image = None
        self._cam_side_height_image = None
        self._cam_side_focal_length_x = None
        self._cam_side_focal_length_y = None
        self._cam_side_pos_x = None
        self._cam_side_pos_y = None
        self._cam_side_pos_z = 0.0
        self._cam_side_rot_x = None
        self._cam_side_rot_y = 0.0
        self._cam_side_rot_z = None
        self._cam_side_origin_axis = numpy.array([[0., 0., 1., 0.],
                                                  [1., 0., 0., 0.],
                                                  [0., 1., 0., 0.],
                                                  [0., 0., 0., 1.]])

        self._cam_top_width_image = None
        self._cam_top_height_image = None
        self._cam_top_focal_length_x = None
        self._cam_top_focal_length_y = None
        self._cam_top_pos_x = None
        self._cam_top_pos_y = None
        self._cam_top_pos_z = None
        self._cam_top_rot_x = None
        self._cam_top_rot_y = None
        self._cam_top_rot_z = None
        self._cam_top_origin_axis = numpy.array([[0., -1., 0., 0.],
                                                 [1., 0., 0., 0.],
                                                 [0., 0., 1., 0.],
                                                 [0., 0., 0., 1.]])

        self._angle_factor = None

    def fit_function(self, x0):
        err = 0

        cam_side_focal_length_x, cam_side_focal_length_y, \
        cam_side_pos_x, cam_side_pos_y, \
        cam_side_rot_x, cam_side_rot_z, \
        cam_top_focal_length_x, cam_top_focal_length_y, \
        cam_top_pos_x, cam_top_pos_y, cam_top_pos_z, \
        cam_top_rot_x, cam_top_rot_y, cam_top_rot_z, \
        angle_factor, \
        target_1_pos_x, target_1_pos_y, target_1_pos_z, \
        target_1_rot_x, target_1_rot_y, target_1_rot_z, \
        target_2_pos_x, target_2_pos_y, target_2_pos_z, \
        target_2_rot_x, target_2_rot_y, target_2_rot_z = x0

        # cam_pos_y = max(min(cam_pos_y, 500), -500)

        fr_cam_side = CalibrationCamera.camera_frame(
            cam_side_pos_x, cam_side_pos_y, self._cam_side_pos_z,
            cam_side_rot_x, self._cam_side_rot_y, cam_side_rot_z,
            self._cam_side_origin_axis)

        for alpha, ref_pts in self._ref_target_1_points_2d.items():
            fr_target = CalibrationCamera.target_frame(target_1_pos_x,
                                                       target_1_pos_y,
                                                       target_1_pos_z,
                                                       target_1_rot_x,
                                                       target_1_rot_y,
                                                       target_1_rot_z,
                                                       math.radians(
                                                           alpha * angle_factor))

            target_pts = map(lambda pt: fr_target.global_point(pt),
                             self._ref_target_1_points_local_3d)

            pts = map(lambda pt: CalibrationCamera.pixel_coordinates(
                fr_cam_side.local_point(pt),
                self._cam_side_width_image,
                self._cam_side_height_image,
                cam_side_focal_length_x,
                cam_side_focal_length_y), target_pts)

            err += numpy.linalg.norm(numpy.array(pts) - ref_pts, axis=1).sum()

        for alpha, ref_pts in self._ref_target_2_points_2d.items():
            fr_target = CalibrationCamera.target_frame(target_2_pos_x,
                                                       target_2_pos_y,
                                                       target_2_pos_z,
                                                       target_2_rot_x,
                                                       target_2_rot_y,
                                                       target_2_rot_z,
                                                       math.radians(
                                                           alpha * angle_factor))

            target_pts = map(lambda pt: fr_target.global_point(pt),
                             self._ref_target_2_points_local_3d)

            pts = map(lambda pt: CalibrationCamera.pixel_coordinates(
                fr_cam_side.local_point(pt),
                self._cam_side_width_image,
                self._cam_side_height_image,
                cam_side_focal_length_x,
                cam_side_focal_length_y), target_pts)

            err += numpy.linalg.norm(numpy.array(pts) - ref_pts, axis=1).sum()





        if self._verbose:
            print err

        return err

    def find_parameters(self, number_of_repetition):

        best_parameters = None
        min_err = float('inf')
        for i in range(number_of_repetition + 1):

            cam_side_focal_length_x = numpy.random.uniform(1000.0, 10000.0)
            cam_side_focal_length_y = numpy.random.uniform(1000.0, 10000.0)
            cam_side_pos_x = numpy.random.uniform(4000.0, 10000.0)
            cam_side_pos_y = 0.0
            cam_side_rot_x = 0.0
            cam_side_rot_z = 0.0

            angle_factor = 1.0

            target_1_pos_x = numpy.random.uniform(-1000.0, 1000.0)
            target_1_pos_y = numpy.random.uniform(-1000.0, 1000.0)
            target_1_pos_z = numpy.random.uniform(0, 1000.0)
            target_1_rot_x = 0.0
            target_1_rot_y = 0.0
            target_1_rot_z = 0.0

            target_2_pos_x = -target_1_pos_x
            target_2_pos_y = -target_1_pos_y
            target_2_pos_z = numpy.random.uniform(0, 1000.0)
            target_2_rot_x = 0.0
            target_2_rot_y = 0.0
            target_2_rot_z = 0.0

            parameters = [cam_side_focal_length_x, cam_side_focal_length_y,
                          cam_side_pos_x, cam_side_pos_y,
                          cam_side_rot_x, cam_side_rot_z,
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
                print 'Result : ', parameters
                print 'Err : ', err / self._ref_number

        return best_parameters

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

        self._ref_number = (len(ref_target_1_points_2d) +
                            len(ref_target_2_points_2d))

        self._ref_target_1_points_2d = ref_target_1_points_2d.copy()
        self._ref_target_2_points_2d = ref_target_2_points_2d.copy()

        self._cam_side_width_image = size_image[0]
        self._cam_side_height_image = size_image[1]

        parameters = self.find_parameters(number_of_repetition)

        for i in [4, 5, 10, 11, 12, 16, 17, 18]:
            parameters[i] %= math.pi* 2.0

        # Camera Parameters
        self._cam_side_focal_length_x = parameters[0]
        self._cam_side_focal_length_y = parameters[1]
        self._cam_side_pos_x = parameters[2]
        self._cam_side_pos_y = parameters[3]
        self._cam_side_rot_x = parameters[4]
        self._cam_side_rot_z = parameters[5]

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
            print 'Result : ', parameters
            print 'Err : ', err, ' -- ', err / self._ref_number

        self._verbose = False

        return err / self._ref_number

    def dump(self, file_path):
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

        with open(file_path + '.json', 'w') as output_file:
            json.dump(save_class, output_file,
                      sort_keys=True,
                      indent=4,
                      separators=(',', ': '))

    @staticmethod
    def load(file_path):
        with open(file_path + '.json', 'r') as input_file:
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


class RegistrationCameraTop(object):
    def __init__(self, camera_top):

        self._verbose = False

        self._ref_target_points_local_3d = None
        self._ref_target_points_2d = None
        self._ref_target_points_3d = None

        self._camera_top = camera_top

        self._alpha_cam_pos_x = 0.0
        self._alpha_cam_pos_y = 0.0
        self._alpha_cam_pos_z = 0.0
        self._alpha_cam_rot_x = 0.0
        self._alpha_cam_rot_y = 0.0
        self._alpha_cam_rot_z = 0.0
        self._alpha_cam_focal_length_x = 0.0
        self._alpha_cam_focal_length_y = 0.0

    def __str__(self):

        # TODO: remove that

        print self._alpha_cam_focal_length_x
        print self._alpha_cam_focal_length_y
        print self._alpha_cam_pos_x
        print self._alpha_cam_pos_y
        print self._alpha_cam_pos_z
        print self._alpha_cam_rot_x
        print self._alpha_cam_rot_y
        print self._alpha_cam_rot_z

        return ""

    def fit_function(self, x0):
        err = 0

        frame_camera_top = CalibrationCamera.camera_frame(
            self._camera_top._cam_pos_x + x0[2],
            self._camera_top._cam_pos_y + x0[3],
            self._camera_top._cam_pos_z + x0[4],
            self._camera_top._cam_rot_x + x0[5],
            self._camera_top._cam_rot_y + x0[6],
            self._camera_top._cam_rot_z + x0[7],
            self._camera_top._cam_origin_axis)

        def projection_camera_top(pt_3d):
            return CalibrationCamera.pixel_coordinates(
                frame_camera_top.local_point(pt_3d),
                self._camera_top._cam_width_image,
                self._camera_top._cam_height_image,
                self._camera_top._cam_focal_length_x,
                self._camera_top._cam_focal_length_y)

        for i in xrange(len(self._ref_target_points_2d)):
            pt = projection_camera_top(self._ref_target_points_3d[i])

            err += numpy.linalg.norm(
                numpy.array(pt) - self._ref_target_points_2d[i]).sum()

        if self._verbose:
            print err

        return err

    def find_parameters(self, number_of_repetition):
        best_parameters = None
        min_err = float('inf')
        for i in range(number_of_repetition + 1):

            parameters = [0.0] * 8

            parameters = scipy.optimize.minimize(
                self.fit_function, parameters, method='BFGS').x

            # bounds = [(-100, 100),
            #           (-100, 100),
            #           (-100, 100),
            #           (-100, 100),
            #           (-100, 100),
            #           (-math.pi, math.pi),
            #           (-math.pi, math.pi),
            #           (-math.pi, math.pi)]
            #
            # parameters = scipy.optimize.differential_evolution(
            #     self.fit_function, bounds, popsize=100).x


            # Compute error compare with min_err
            err = self.fit_function(parameters)
            if err < min_err:
                min_err = err
                best_parameters = parameters

            if self._verbose:
                print 'Result : ', parameters
                print 'Err : ', err / self._ref_number

        return best_parameters

    @staticmethod
    def load(file_path):
        with open(file_path + '.json', 'r') as input_file:
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

        self._alpha_cam_focal_length_x = parameters[0]
        self._alpha_cam_focal_length_y = parameters[1]
        self._alpha_cam_pos_x = parameters[2]
        self._alpha_cam_pos_y = parameters[3]
        self._alpha_cam_pos_z = parameters[4]
        self._alpha_cam_rot_x = parameters[5]
        self._alpha_cam_rot_y = parameters[6]
        self._alpha_cam_rot_z = parameters[7]


        err = self.fit_function(parameters)
        if self._verbose:
            print 'Result : ', parameters
            print 'Err : ', err, ' -- ', err / self._ref_number

        self._verbose = False

        return err / self._ref_number


class RegistrationCameraTopTmp(object):
    def __init__(self, camera_top):

        self._verbose = False

        self._ref_target_points_local_3d = None
        self._ref_target_points_2d = None
        self._ref_target_points_3d = None

        self._camera_top = camera_top

        self._alpha_cam_pos_x = 0.0
        self._alpha_cam_pos_y = 0.0
        self._alpha_cam_pos_z = 0.0
        self._alpha_cam_rot_x = 0.0
        self._alpha_cam_rot_y = 0.0
        self._alpha_cam_rot_z = 0.0
        self._alpha_cam_focal_length_x = 0.0
        self._alpha_cam_focal_length_y = 0.0

    def __str__(self):

        # TODO: remove that

        print self._alpha_cam_focal_length_x
        print self._alpha_cam_focal_length_y
        print self._alpha_cam_pos_x
        print self._alpha_cam_pos_y
        print self._alpha_cam_pos_z
        print self._alpha_cam_rot_x
        print self._alpha_cam_rot_y
        print self._alpha_cam_rot_z

        return ""

    def fit_function(self, x0):
        err = 0

        frame_camera_top = CalibrationCamera.camera_frame(
            self._camera_top._cam_pos_x + x0[2],
            self._camera_top._cam_pos_y + x0[3],
            self._camera_top._cam_pos_z + x0[4],
            self._camera_top._cam_rot_x + x0[5],
            self._camera_top._cam_rot_y + x0[6],
            self._camera_top._cam_rot_z + x0[7],
            self._camera_top._cam_origin_axis)

        def projection_camera_top(pt_3d):
            return CalibrationCamera.pixel_coordinates(
                frame_camera_top.local_point(pt_3d),
                self._camera_top._cam_width_image,
                self._camera_top._cam_height_image,
                self._camera_top._cam_focal_length_x,
                self._camera_top._cam_focal_length_y)

        for i in xrange(len(self._ref_target_points_2d)):
            pt = projection_camera_top(self._ref_target_points_3d[i])

            err += numpy.linalg.norm(
                numpy.array(pt) - self._ref_target_points_2d[i]).sum()

        if self._verbose:
            print err

        return err

    def find_parameters(self, number_of_repetition):
        best_parameters = None
        min_err = float('inf')
        for i in range(number_of_repetition + 1):

            parameters = [0.0] * 8

            parameters = scipy.optimize.minimize(
                self.fit_function, parameters, method='BFGS').x

            # bounds = [(-100, 100),
            #           (-100, 100),
            #           (-100, 100),
            #           (-100, 100),
            #           (-100, 100),
            #           (-math.pi, math.pi),
            #           (-math.pi, math.pi),
            #           (-math.pi, math.pi)]
            #
            # parameters = scipy.optimize.differential_evolution(
            #     self.fit_function, bounds, popsize=100).x

            # Compute error compare with min_err
            err = self.fit_function(parameters)
            if err < min_err:
                min_err = err
                best_parameters = parameters

            if self._verbose:
                print 'Result : ', parameters
                print 'Err : ', err / self._ref_number

        return best_parameters

    @staticmethod
    def load(file_path):
        with open(file_path + '.json', 'r') as input_file:
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
                  size_image,
                  angle_factor,
                  number_of_repetition=1,
                  verbose=False):

        self._verbose = verbose
        self._angle_factor = angle_factor

        self._ref_target_points_2d = ref_target_points_2d
        self._ref_number = len(ref_target_points_2d)

        self._cam_width_image = size_image[0]
        self._cam_height_image = size_image[1]

        parameters = self.find_parameters(number_of_repetition)

        for i in [5, 6, 7]:
            parameters[i] %= math.pi * 2.0

        self._alpha_cam_focal_length_x = parameters[0]
        self._alpha_cam_focal_length_y = parameters[1]
        self._alpha_cam_pos_x = parameters[2]
        self._alpha_cam_pos_y = parameters[3]
        self._alpha_cam_pos_z = parameters[4]
        self._alpha_cam_rot_x = parameters[5]
        self._alpha_cam_rot_y = parameters[6]
        self._alpha_cam_rot_z = parameters[7]

        err = self.fit_function(parameters)
        if self._verbose:
            print 'Result : ', parameters
            print 'Err : ', err, ' -- ', err / self._ref_number

        self._verbose = False

        return err / self._ref_number


def find_position_3d_points(pt2d, calibrations, verbose=False):

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

    # parameters = [0, 0, -600]
    # parameters = scipy.optimize.minimize(
    #     fit_function, parameters, method='Nelder-Mead').x

    parameters = scipy.optimize.basinhopping(fit_function, parameters).x

    # parameters = scipy.optimize.leastsq(
    #     fit_function, parameters)[0]

    print "Err : ", fit_function(parameters)
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

    def reproject(x0, verbose=False):
        err = 0

        sf = soil_frame(0, 0, x0[0],
                        x0[1], x0[2], x0[3])

        for i in xrange(len(pts)):
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
                            print "ID CAMERA & ANGLE", id_camera, angle
                            print 'pt3d : ', pos_x, pos_y, pos_z
                            print "Repro", pt
                            print "Ref", pt2d[id_camera][angle]
                            print "dist :", numpy.linalg.norm(
                                numpy.array(pt - pt2d[id_camera][angle]).sum())
                            print "\n\n"

        print err
        return err

    def fit_function(x0):
        return reproject(x0)

    # def fit_function(x0):
    #     # err = 0
    #     # for func in func_min_list:
    #     #     err += func(x0)
    #     # return err
    #     return [func(x0) for func in func_min_list]

    # parameters = [0.0] * 3
    # parameters = [-37.49083212, -243.80771245, 386.97793387]
    # print fit_function(parameters)

    parameters = [0,
                  0, 0, 0]

    parameters += [0] * 2 * len(pts)

    # parameters = scipy.optimize.minimize(
    #     fit_function, parameters, method='Nelder-Mead').x

    parameters = scipy.optimize.basinhopping(fit_function,
                                             parameters,
                                             niter=10).x

    print "Err : ", fit_function(parameters)
    print "Err : ", reproject(parameters)

    # for i in [1, 2, 3]:
    #     parameters[i] %= math.pi * 2.0

    print parameters


    print reproject(parameters, verbose=True)



    # parameters = scipy.optimize.leastsq(
    #     fit_function, parameters)[0]

    return parameters

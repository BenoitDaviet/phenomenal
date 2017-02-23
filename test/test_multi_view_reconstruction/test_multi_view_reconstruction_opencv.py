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
from alinea.phenomenal.calibration.calibration_opencv import (
    CalibrationCameraOpenCv)

from alinea.phenomenal.data_access.plant_1 import (
    plant_1_params_camera_opencv_path)


from alinea.phenomenal.data_access.data_creation import (
    build_object_1,
    build_images_1)

from alinea.phenomenal.multi_view_reconstruction.multi_view_reconstruction\
    import (project_voxel_centers_on_image,
            reconstruction_3d,
            error_reconstruction)
# ==============================================================================


def test_multi_view_reconstruction_opencv_1():
    # ==========================================================================
    size = 10
    voxel_size = 10
    voxel_center = (0, 0, 0)
    voxel_centers = build_object_1(size, voxel_size, voxel_center)

    # ==========================================================================
    calibration = CalibrationCameraOpenCv.load(plant_1_params_camera_opencv_path())

    images_projections = list()
    shape_image = (2454, 2056)
    for angle in [0, 30, 60, 90]:

        projection = calibration.get_projection(angle)

        img = project_voxel_centers_on_image(voxel_centers,
                                             voxel_size,
                                             shape_image,
                                             projection)

        images_projections.append((img, projection))

    # ==========================================================================
    voxel_size = 20
    voxel_centers = reconstruction_3d(images_projections,
                                      voxels_size=voxel_size,
                                      verbose=True)

    assert len(voxel_centers) == 465
    volume = len(voxel_centers) * voxel_size**3
    assert volume == 3720000


def test_multi_view_reconstruction_opencv_2():
    voxel_size = 8
    calibration = CalibrationCameraOpenCv.load(
        plant_1_params_camera_opencv_path())

    images = build_images_1()

    images_projections = list()
    for angle in [0, 30, 60, 90]:
        projection = calibration.get_projection(angle)
        img = images[angle]
        images_projections.append((img, projection))

    voxel_centers = reconstruction_3d(
        images_projections, voxels_size=voxel_size, verbose=True)

    assert len(voxel_centers) == 9929

    for image, projection in images_projections:
        err = error_reconstruction(
            image, projection, voxel_centers, voxel_size)

        assert err < 9000


# ==============================================================================

if __name__ == "__main__":
    for func_name in dir():
        if func_name.startswith('test_'):
            print("{func_name}".format(func_name=func_name))
            eval(func_name)()
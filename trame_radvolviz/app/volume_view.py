import numpy as np

from vtkmodules.vtkCommonDataModel import vtkImageData
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkInteractionWidgets import vtkOrientationMarkerWidget
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor
from vtkmodules.vtkRenderingCore import (
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkVolume,
    vtkVolumeProperty,
)
from vtkmodules.vtkRenderingVolumeOpenGL2 import vtkSmartVolumeMapper
import vtkmodules.util.numpy_support as np_s


class VolumeView:
    def __init__(self):
        # Set up the VTK volume
        ren = vtkRenderer()
        ren_win = vtkRenderWindow()
        ren_win.AddRenderer(ren)
        ren_win.OffScreenRenderingOn()

        # White background
        # ren.SetBackground(1, 1, 1)

        iren = vtkRenderWindowInteractor()
        iren.SetInteractorStyle(vtkInteractorStyleTrackballCamera())
        iren.SetRenderWindow(ren_win)

        axes = vtkAxesActor()
        orientation_marker = vtkOrientationMarkerWidget()
        orientation_marker.SetOrientationMarker(axes)
        orientation_marker.SetInteractor(iren)

        # The property describes how the data will look.
        volume_property = vtkVolumeProperty()
        volume_property.IndependentComponentsOff()

        # Fix the scalar opacity to be a no-op
        pwf = volume_property.GetScalarOpacity()
        pwf.RemoveAllPoints()
        pwf.AddPoint(0, 0)
        pwf.AddPoint(1, 1)

        volume_data = vtkImageData()
        volume_mapper = vtkSmartVolumeMapper()
        volume_mapper.SetInputData(volume_data)

        volume = vtkVolume()
        volume.SetMapper(volume_mapper)
        volume.SetProperty(volume_property)

        ren.AddVolume(volume)

        # Pitch the camera by 90 degrees to start
        ren.GetActiveCamera().Pitch(90)
        ren.GetActiveCamera().OrthogonalizeViewUp()

        # Store needed variables on self
        self.orientation_marker = orientation_marker
        self.renderer = ren
        self.render_window = ren_win
        self.volume_data = volume_data

    def set_data(self, data):
        # FIXME: how do I figure this shape out?
        shape = (43, 31, 52)
        num_voxels = np.prod(shape)

        # Already raveled...
        raveled = data

        # FIXME: would it be faster to set the data on the existing
        # vtkArray, rather than create a new vtkArray each time?
        vtk_array = np_s.numpy_to_vtk(raveled, deep=True)

        self.volume_data.SetDimensions(shape)
        pd = self.volume_data.GetPointData()

        # Remove all other arrays
        while pd.GetNumberOfArrays() > 0:
            pd.RemoveArray(0)

        # Add the array
        pd.SetScalars(vtk_array)
        self.volume_data.Modified()
        self.render_window.Render()

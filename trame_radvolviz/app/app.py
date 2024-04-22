from pathlib import Path

import numpy as np

from trame.app import get_server
from trame.decorators import TrameApp, change
from trame.ui.vuetify3 import SinglePageWithDrawerLayout
from trame.widgets import client, html, vtk, vuetify3 as v
from trame_radvolviz.widgets import radvolviz

from .compute import compute_gbc, gbc_to_rgb
from .io import load_csv_dataset
from .volume_view import VolumeView

DATA_FILE = Path(__file__).parent.parent.parent / 'data/data10.csv'


@TrameApp()
class App:
    def __init__(self, server=None):
        self.server = get_server(server, client_type='vue3')
        self.volume_view = VolumeView()

        self.gbc_data = None
        self.rgb_data = None
        self.first_render = True

        self.load_data()
        self.ui = self._build_ui()

    def load_data(self):
        header, data = load_csv_dataset(DATA_FILE)

        self.state.components = header

        # FIXME: for now, sending the whole dataset to the client
        # The client can do computations on the dataset faster than we can
        # do them on the server and send updates. However, we might want
        # to explore this more in the future so we don't have to send the
        # full dataset over.
        self.state.data = data.tolist()

        # Store the header and the data in the app too
        self.header = header
        self.data = data

    @change('w_rotation')
    def update_voxel_colors(self, **kwargs):
        gbc, components = compute_gbc(self.data,
                                      np.radians(self.state.w_rotation))
        self.gbc_data = gbc
        self.rgb_data = gbc_to_rgb(gbc)

        self.update_volume_data()

    @change('lens_center', 'w_lens', 'w_lradius')
    def update_volume_data(self, **kwargs):
        if any(x is None for x in (self.rgb_data, self.gbc_data)):
            return

        rgb = self.rgb_data
        alpha = self.compute_alpha()

        # Transpose and add alpha channel
        rgba = np.hstack((rgb.T, alpha[..., np.newaxis]))

        # Set the data on the volume
        self.volume_view.set_data(rgba)

        # Reset the camera if it is the first render
        self.reset_camera_on_first_render()

        # Update the view
        self.ctrl.view_update()

    @property
    def state(self):
        return self.server.state

    @property
    def ctrl(self):
        return self.server.controller

    @property
    def render_window(self):
        return self.volume_view.render_window

    @property
    def lens_enabled(self):
        return self.state.w_lens

    def reset_camera_on_first_render(self):
        if not self.first_render:
            # Already had the first render
            return

        self.volume_view.renderer.ResetCameraClippingRange()
        self.volume_view.renderer.ResetCamera()
        self.ctrl.reset_camera()
        self.first_render = False

    def compute_alpha(self):
        gbc_data = self.gbc_data
        if gbc_data is None:
            # Can't do anything
            return None

        if not self.lens_enabled:
            # All opaque
            return np.ones(gbc_data.shape[0])

        # These are in unit cell coordinates
        r = self.state.w_lradius
        x, y = self.state.lens_center

        # Compute distance formula to lens center
        distances = np.sqrt((gbc_data - (x, y))**2).sum(axis=1)

        # Any distances less than the radius are within the lens
        return (distances < r).astype(float)

    def _build_ui(self):
        self.state.setdefault('lens_center', [0, 0])

        server = self.server
        ctrl = self.ctrl

        with SinglePageWithDrawerLayout(
            server, full_height=True
        ) as layout:
            client.Style('html { overflow-y: hidden; }')

            with layout.toolbar.clear():
                v.VAppBarNavIcon(click='main_drawer = !main_drawer')
                v.VAppBarTitle('RadVolViz')
                v.VSpacer()
                html.Div('{{ lens_center }}')

            with layout.drawer as drawer:
                drawer.width = 400
                # add new widget
                v.VSlider(
                    label='Widget rotation',
                    v_model='w_rotation',
                    min=0,
                    max=360,
                    step=5,
                    density='compact',
                    hide_details=True,
                )
                v.VSlider(
                    label='Sample size',
                    v_model='w_sample_size',
                    min=100,
                    max=10000,
                    step=500,
                    density='compact',
                    hide_details=True,
                )
                v.VSlider(
                    label='Number of bins',
                    v_model='w_bins',
                    min=1,
                    max=10,
                    step=1,
                    density='compact',
                    hide_details=True,
                )
                v.VSwitch(
                    label='Lens',
                    v_model='w_lens',
                )
                v.VSlider(
                    label='Lens radius',
                    v_model='w_lradius',
                    min=0.001,
                    max=1.0,
                    step=0.001,
                    density='compact',
                    hide_details=True,
                )

                radvolviz.NdColorMap(
                    data=('data', []),
                    components=('components', []),
                    size=drawer.width,
                    rotation=('w_rotation', 0),
                    sample_size=('w_sample_size', 100),
                    number_of_bins=('w_bins', 6),
                    show_lens=('w_lens', False),
                    lens_radius=('w_lradius', 0.5),
                    lens='lens_center = $event',
                )

            with layout.content:
                html_view = vtk.VtkRemoteView(self.render_window,
                                              interactive_ratio=1)

                ctrl.reset_camera = html_view.reset_camera
                ctrl.view_update = html_view.update

from pathlib import Path

import numba
import numpy as np

from trame.app import get_server
from trame.decorators import TrameApp, change
from trame.ui.vuetify3 import VAppLayout
from trame.widgets import client, html, vtk, vuetify3 as v
from trame_radvolviz.widgets import radvolviz

from .compute import (
    compute_gbc,
    data_topology_reduction,
    gbc_to_rgb,
    rotate_coordinates,
)
from .io import load_dataset
from .volume_view import VolumeView


DATA_FILE = Path(__file__).parent.parent.parent / 'data/12CeCoFeGd.png'
# DATA_FILE = Path(__file__).parent.parent.parent / 'data/CoMnNiO.npz'


@TrameApp()
class App:
    def __init__(self, server=None):
        self.server = get_server(server, client_type='vue3')

        # CLI
        self.server.cli.add_argument(
            "--data", help="Path to the file to load", default=None
        )
        self.server.cli.add_argument(
            "--enable-preprocessing",
            help="Enable additional control on data pre-processing",
            dest="preprocess",
            action='store_true',
        )

        args, _ = self.server.cli.parse_known_args()
        self.enable_preprocessing = args.preprocess
        file_to_load = args.data
        if file_to_load is None:
            file_to_load = DATA_FILE

        self.volume_view = VolumeView()

        self.unrotated_gbc = None
        self.unrotated_components = None

        self.gbc_data = None
        self.rgb_data = None
        self.first_render = True

        self.ui = self._build_ui()
        self.load_data(file_to_load)

        if self.server.hot_reload:
            self.ctrl.on_server_reload.add(self._build_ui)

    def load_data(self, file_to_load):
        header, data = load_dataset(Path(file_to_load))

        self.state.component_labels = header

        if self.enable_preprocessing:
            self.state.data_channels = {}
            # FIXME fill the data channels
            # => { key: { color: "", clamp: [0, 1], scale: 1 }, ... }
            self.state.data_channels["R"] = {
                "color": "rgb(100, 50, 245)",
                "scale": 1,
                "clamp": [0, 1],
            }
        else:
            self.state.data_channels = None

        # Remove padding so it will render faster.
        # This removes faces that are all zeros recursively until
        # the first non-zero voxel is hit.
        # Our sample data has a *lot* of padding.
        data = _remove_padding_uniform(data)

        # Remember the data shape (without the multichannel part)
        self.data_shape = data.shape[:-1]
        self.num_channels = data.shape[-1]

        # Normalize the data to be between 0 and 1
        data = _normalize_data(data)

        # Store the data in a flattened form. It is easier to work with.
        flattened_data = data.reshape(
            np.prod(self.data_shape), self.num_channels
        )
        self.nonzero_indices = ~np.all(np.isclose(flattened_data, 0), axis=1)

        # Only store nonzero data. We will reconstruct the zeros later.
        self.nonzero_data = flattened_data[self.nonzero_indices]

        # Trigger an update of the data
        self.update_gbc()

    def update_gbc(self):
        gbc, components = compute_gbc(self.nonzero_data)

        self.unrotated_gbc = gbc
        self.state.unrotated_component_coords = components.tolist()

        self.update_bin_data()
        self.update_voxel_colors()

    @change('w_bins', 'w_sample_size')
    def update_bin_data(self, **kwargs):
        num_samples = self.state.w_sample_size
        num_bins = self.state.w_bins

        # Perform random sampling
        sample_idx = np.random.choice(
            len(self.unrotated_gbc), size=num_samples
        )
        data = self.unrotated_gbc[sample_idx]
        unrotated_bin_data = data_topology_reduction(data, num_bins)
        self.state.unrotated_bin_data = unrotated_bin_data.tolist()

    @change('w_rotation')
    def update_voxel_colors(self, **kwargs):
        angle = np.radians(self.state.w_rotation)
        gbc = rotate_coordinates(self.unrotated_gbc, angle)

        # ---------------------------------------------------------------------
        # FIXME: update color for each channels in self.state.data_channels
        # ---------------------------------------------------------------------
        if self.enable_preprocessing:
            # Dummy example code
            if "R" in self.state.data_channels:
                r = (
                    int(2.8 * self.state.w_rotation)
                    if self.state.w_rotation < 90
                    else 128
                )
                g = (
                    int(2.8 * (self.state.w_rotation - 90))
                    if 90 < self.state.w_rotation < 180
                    else 128
                )
                b = (
                    int(2.8 * (self.state.w_rotation - 180))
                    if 180 < self.state.w_rotation < 270
                    else 128
                )
                self.state.data_channels["R"]["color"] = f"rgb({r}, {g}, {b})"
            self.state.dirty("data_channels")
        # ---------------------------------------------------------------------

        self.gbc_data = gbc
        self.rgb_data = gbc_to_rgb(gbc)

        self.update_volume_data()

    def update_volume_data(self, **kwargs):
        if any(x is None for x in (self.rgb_data, self.gbc_data)):
            return

        rgb = self.rgb_data

        # Reconstruct full data with rgba values
        full_data = np.zeros((np.prod(self.data_shape), 4))
        full_data[self.nonzero_indices, :3] = rgb.T

        # Make nonzero voxels have an alpha of the mean of the channels.
        full_data[self.nonzero_indices, 3] = self.nonzero_data.mean(axis=1)
        full_data = full_data.reshape((*self.data_shape, 4))

        # Set the data on the volume
        self.volume_view.set_data(full_data)

        # Reset the camera if it is the first render
        self.reset_camera_on_first_render()

        # Update the mask data too. This will trigger an update.
        self.update_mask_data()

    @change(
        'lens_center',
        'show_groups',
        'w_lradius',
        'w_clip_x',
        'w_clip_y',
        'w_clip_z',
    )
    def update_mask_data(self, **kwargs):
        if any(x is None for x in (self.rgb_data, self.gbc_data)):
            return

        alpha = self.compute_alpha()
        mask_ref = self.volume_view.mask_reference
        mask_ref[self.nonzero_indices] = alpha
        self.volume_view.mask_data.Modified()

        # Update the view
        self.ctrl.view_update()

    @change("data_channels")
    def on_data_change(self, data_channels, **_):
        print("data_channels", data_channels)

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
        return "lens" in self.state.show_groups

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

        min_clip_x, max_clip_x = self.state.w_clip_x
        min_clip_y, max_clip_y = self.state.w_clip_y
        min_clip_z, max_clip_z = self.state.w_clip_z
        if max_clip_x < 1:
            # Make a mask the shape of the original data
            clip_mask = np.ones(self.data_shape, dtype=bool)
            # Compute the max index, after which data is clipped
            max_idx = int(np.round(self.data_shape[0] * max_clip_x))
            # Apply clip
            clip_mask[max_idx:, :, :] = False
            # Reshape into the flat form and remove any zero index data
            clip_flattened = clip_mask.reshape(np.prod(self.data_shape))
            # If we perform any other operations, we can logical_and them
            alpha = clip_flattened[self.nonzero_indices]
        else:
            # All opaque
            alpha = np.ones(gbc_data.shape[0], dtype=bool)

        if not self.lens_enabled:
            # Only apply clipping
            return alpha

        # These are in unit circle coordinates
        r = self.state.w_lradius
        x, y = self.state.lens_center

        lens_alpha = _compute_alpha(np.array([x, y]), r, gbc_data)

        # Combine the lens alpha with the current alpha
        return np.logical_and(alpha, lens_alpha)

    def _build_ui(self):
        self.state.setdefault('lens_center', [0, 0])

        # FIXME
        # self.state.setdefault(
        #     'data_channels',
        #     {
        #         "A test something super long": {
        #             "color": "red",
        #             "clamp": [0, 1],
        #             "scale": 1,
        #         },
        #         "B igger text": {
        #             "color": "green",
        #             "clamp": [0, 1],
        #             "scale": 1,
        #         },
        #         "G": {
        #             "color": "blue",
        #             "clamp": [0, 1],
        #             "scale": 1,
        #         },
        #         "R": {
        #             "color": "purple",
        #             "clamp": [0, 1],
        #             "scale": 1,
        #         },
        #     },
        # )

        server = self.server
        ctrl = self.ctrl

        with VAppLayout(server, full_height=True) as layout:
            client.Style('html { overflow-y: hidden; }')

            with vtk.VtkRemoteView(
                self.render_window, interactive_ratio=1
            ) as html_view:
                ctrl.reset_camera = html_view.reset_camera
                ctrl.view_update = html_view.update

                with v.VCard(
                    classes=(
                        "{ 'ma-4': 1, 'rounded-xl': !show_control_panel }",
                    ),
                    style="z-index: 1; position: absolute; top: 0.2rem; left: 0.2rem; max-height: calc(100vh - 2.4rem); overflow: auto;",
                ):
                    with v.VToolbar(
                        density="compact", style="position: sticky; top: 0;"
                    ):
                        v.VProgressLinear(
                            color="primary",
                            indeterminate=("trame__busy",),
                            v_show="trame__busy",
                            absolute=True,
                            style="bottom: 0; top: none;",
                        )
                        v.VBtn(
                            icon="mdi-cogs",
                            click="show_control_panel = !show_control_panel",
                            density="compact",
                            classes="mx-3",
                        )
                        v.VSpacer()

                        with v.VBtnToggle(
                            v_show=("show_control_panel", True),
                            v_model=("show_groups", []),
                            # base_color="grey-darken-1",
                            # color="grey-darken-4",
                            variant="outlined",
                            density="conpact",
                            multiple=True,
                            divided=True,
                            classes="mr-4",
                        ):
                            v.VBtn(icon="mdi-magnify", value="lens")
                            v.VBtn(icon="mdi-palette", value="color")
                            v.VBtn(
                                icon="mdi-chart-histogram", value="sampling"
                            )
                            v.VBtn(icon="mdi-crop", value="clip")
                            v.VBtn(
                                icon="mdi-tune-variant",
                                value="tune-data",
                                v_if="data_channels && Object.keys(data_channels).length",
                            )

                        v.VSpacer()

                        if self.server.hot_reload:
                            v.VBtn(
                                v_show=("show_control_panel", True),
                                icon="mdi-refresh",
                                click=self.ctrl.on_server_reload,
                                density="compact",
                            )

                        v.VBtn(
                            icon="mdi-crop-free",
                            density="compact",
                            classes="mr-3",
                            click=ctrl.reset_camera,
                        )

                    # Main widget
                    radvolviz.NdColorMap(
                        v_show="show_control_panel",
                        component_labels=('component_labels', []),
                        unrotated_bin_data=('unrotated_bin_data', []),
                        unrotated_component_coords=(
                            'unrotated_component_coords',
                            [],
                        ),
                        size=400,
                        rotation=('w_rotation', 0),
                        sample_size=('w_sample_size', 6000),
                        number_of_bins=('w_bins', 6),
                        show_lens=("show_groups.includes('lens')",),
                        lens_radius=('w_lradius', 0.5),
                        lens='lens_center = $event',
                        # style="position: sticky; top: 3rem; z-index: 1; background: white;",
                    )

                    # Lense control
                    with v.VCard(
                        flat=True,
                        v_show="show_control_panel && show_groups.includes('lens')",
                        classes="py-1",
                    ):
                        v.VSlider(
                            v_model='w_lradius',
                            min=0.001,
                            max=1.0,
                            step=0.001,
                            density='compact',
                            prepend_icon="mdi-radius-outline",
                            messages="Adjust lens size",
                        )

                    # Data sampling

                    # Color / Rotation management
                    with v.VCard(
                        flat=True,
                        v_show="show_control_panel && show_groups.includes('color')",
                        classes="py-1",
                    ):
                        v.VSlider(
                            v_model='w_rotation',
                            min=0,
                            max=360,
                            step=5,
                            density='compact',
                            prepend_icon="mdi-rotate-360",
                            messages="Rotate color wheel",
                        )

                    with v.VCard(
                        flat=True,
                        v_show="show_control_panel && show_groups.includes('sampling')",
                        classes="py-1",
                    ):
                        v.VSlider(
                            v_model='w_sample_size',
                            min=100,
                            max=10000,
                            step=500,
                            density='compact',
                            prepend_icon="mdi-blur-radial",
                            messages="Adjust sampling size",
                        )
                        v.VSlider(
                            v_model='w_bins',
                            min=1,
                            max=10,
                            step=1,
                            density='compact',
                            prepend_icon="mdi-chart-scatter-plot-hexbin",
                            messages="Number of bins for the sampling algorithm",
                        )

                    # Cropping
                    with v.VCard(
                        flat=True,
                        v_show="show_control_panel && show_groups.includes('clip')",
                        classes="py-1 pr-4",
                    ):
                        v.VLabel("Crop dataset", classes="text-body-2 ml-1")
                        v.VDivider(classes="mr-n4")
                        v.VRangeSlider(
                            label='X',
                            v_model=('w_clip_x', [0, 1]),
                            min=0.0,
                            max=1.0,
                            step=0.001,
                            density='compact',
                            hide_details=True,
                        )
                        v.VRangeSlider(
                            label='Y',
                            v_model=('w_clip_y', [0, 1]),
                            min=0.0,
                            max=1.0,
                            step=0.001,
                            density='compact',
                            hide_details=True,
                        )
                        v.VRangeSlider(
                            label='Z',
                            v_model=('w_clip_z', [0, 1]),
                            min=0.0,
                            max=1.0,
                            step=0.001,
                            density='compact',
                            hide_details=True,
                        )

                    # Data tuning
                    with v.VCard(
                        v_if="data_channels",
                        flat=True,
                        v_show="show_control_panel && show_groups.includes('tune-data')",
                        classes="py-1",
                    ):
                        v.VLabel(
                            "Data pre-processing", classes="text-body-2 ml-1"
                        )
                        v.VDivider(classes="mr-n4")
                        with v.VRow(
                            v_for=("data, name in data_channels"),
                            key="name",
                            classes="mx-0 my-1",
                        ):
                            with v.VCol(
                                cols="1", align_self="center pa-0 ma-0"
                            ):
                                html.Div(
                                    "{{ name }}",  # : Scale({{ data.scale }}) Clamp({{ data.clamp[0] }}, {{ data.clamp[1] }})
                                    classes="text-body-2 text-center text-truncate",
                                    style="transform: rotate(-90deg) translateY(calc(-100% - 0.2rem));  width: 5.5rem;",
                                )
                            with v.VCol(
                                classes="border-s-lg",
                                style=(
                                    "`border-color: ${data.color} !important;`",
                                ),
                            ):
                                v.VRangeSlider(
                                    model_value=('data.clamp',),
                                    min=0.0,
                                    max=1.0,
                                    step=0.001,
                                    density='compact',
                                    hide_details=True,
                                    prepend_icon="mdi-scissors-cutting",
                                    update_modelValue="data_channels[name].clamp = $event; flushState('data_channels')",
                                )
                                v.VSlider(
                                    model_value=('data.scale', 1),
                                    min=0.001,
                                    max=5,
                                    step=0.001,
                                    density='compact',
                                    hide_details=True,
                                    prepend_icon="mdi-magnify",
                                    update_modelValue="data_channels[name].scale = $event; flushState('data_channels')",
                                )


@numba.njit(cache=True, nogil=True)
def _compute_alpha(center, radius, gbc_data):
    # Compute distance formula to lens center
    distances = np.sqrt(((gbc_data - center) ** 2).sum(axis=1))

    # Any distances less than the radius are within the lens
    return distances < radius


@numba.njit(cache=True, nogil=True)
def _remove_padding_uniform(data: np.ndarray) -> np.ndarray:
    num_channels = data.shape[-1]
    zero_data = np.isclose(data, 0).sum(axis=3) == num_channels

    # This is the number to crop
    n = 0
    indices = np.array([n, -n - 1])
    while (
        zero_data[indices].all()
        & zero_data[:, indices].all()
        & zero_data[:, :, indices].all()
    ):
        n += 1
        indices = np.array([n, -n - 1])

    if n != 0:
        data = data[n : -n - 1, n : -n - 1, n : -n - 1]

    return data


@numba.njit(cache=True, nogil=True)
def _normalize_data(data: np.ndarray, new_min: float = 0, new_max: float = 1):
    max_val = data.max()
    min_val = data.min()

    return (new_max - new_min) * (data.astype(np.float64) - min_val) / (
        max_val - min_val
    ) + new_min

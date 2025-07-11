from pathlib import Path

import numba
import numpy as np

import plotly.graph_objects as go

from trame.app import TrameApp
from trame.assets.remote import download_file_from_google_drive
from trame.decorators import change, life_cycle
from trame.ui.vuetify3 import VAppLayout
from trame.widgets import client, html, plotly, vtk, vuetify3 as v
from multivariate_view.widgets import radvolviz
from .assets import ASSETS

from .compute import (
    compute_gbc,
    data_topology_reduction,
    gbc_to_rgb,
    rotate_coordinates,
)
from .io import load_dataset
from .volume_view import VolumeView


# We will cache downloaded data examples in this directory.
EXAMPLE_DATA_DIR = Path(__file__).parent.parent.parent / 'data'
EXAMPLE_DATA_PATH = (
    EXAMPLE_DATA_DIR / 'CeCoFeGd_doi_10.1038_s43246-022-00259-x.h5'
)
EXAMPLE_GOOGLE_DRIVE_ID = '1nI_hzrqbGBypUU7jMbWnF7-PkqNMiwqB'
EXAMPLE_DATA_REF = 'https://doi.org/10.1038/s43246-022-00259-x'


class App(TrameApp):
    def __init__(self, server=None):
        super().__init__(server, client_type='vue3')

        # CLI
        self.server.cli.add_argument(
            "--data", help="Path to the file to load", default=None
        )
        self.server.cli.add_argument(
            "--nan", help="Replace NaN to specific value", default=0
        )
        self.server.cli.add_argument(
            "--enable-preprocessing",
            help="Enable additional control on data pre-processing",
            dest="preprocess",
            action='store_true',
            default=True,
        )
        self.server.cli.add_argument(
            "--normalize-channels",
            help="Normalize each channel to be between 0 and 1",
            action="store_true",
            default=False,
        )
        self.server.cli.add_argument(
            "--opacity-channel",
            help="Set the specified channel to be opacity only",
            default=None,
        )
        self.server.cli.add_argument(
            "--label-map",
            help="Set a path to a label map file",
            default=None,
        )

        args, _ = self.server.cli.parse_known_args()
        self.enable_preprocessing = args.preprocess
        self.nan_replacement = args.nan
        self.normalize_channels = args.normalize_channels
        self.opacity_channel = args.opacity_channel
        self.label_map_file = args.label_map
        self.label_map = None

        if self.label_map_file is not None:
            # Load the label map
            # We assume this is the same shape as the data with
            # the padding removed.
            self.label_map = np.load(self.label_map_file)

        # Set this if you want label map names other than "0, 1, 2, ..."
        self.label_map_names = None

        file_to_load = args.data
        if file_to_load is None:
            EXAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)

            print(
                '\nData path was not provided using `--data`'
                f'\nDefaulting to example: {EXAMPLE_DATA_PATH.name}'
            )

            citation_str = f'* Example data citation: {EXAMPLE_DATA_REF} *'
            boundary_str = '*' * len(citation_str)
            print(f'\n{boundary_str}\n{citation_str}\n{boundary_str}\n')

            if not EXAMPLE_DATA_PATH.exists():
                # Automatically download the example dataset, and put it in the
                # data directory.
                print(f'Downloading example dataset to: {EXAMPLE_DATA_PATH}')
                download_file_from_google_drive(
                    EXAMPLE_GOOGLE_DRIVE_ID, EXAMPLE_DATA_PATH
                )

            file_to_load = EXAMPLE_DATA_PATH

        self.volume_view = VolumeView()

        self.unrotated_gbc = None
        self.unrotated_components = None

        self.gbc_data = None
        self.rgb_data = None
        self.opacity_data = None

        self.ui = self._build_ui()
        self.load_data(file_to_load)
        self.create_table()

        if self.server.hot_reload:
            self.ctrl.on_server_reload.add(self._build_ui)

    def load_data(self, file_to_load):
        header, data = load_dataset(Path(file_to_load))

        # Handle NaN if provided
        if self.nan_replacement is not None:
            data[np.isnan(data)] = float(self.nan_replacement)

        # Remove padding so it will render faster.
        # This removes faces that are all zeros recursively until
        # the first non-zero voxel is hit.
        # Our sample data has a *lot* of padding.
        data = _remove_padding_uniform(data)

        if self.opacity_channel is not None:
            # Extract the opacity data
            opacity_idx = header.index(self.opacity_channel)
            self.opacity_data = _normalize_data(data[:, :, :, opacity_idx])

            # Set all data less than 80% to 0, and then re-normalize
            # self.opacity_data[self.opacity_data < 0.8] = 0
            # self.opacity_data = _normalize_data(self.opacity_data**5)

            header.pop(opacity_idx)
            data = np.delete(data, opacity_idx, axis=3)

        self.state.component_labels = header

        # Remember the data shape (without the multichannel part)
        self.data_shape = data.shape[:-1]
        self.num_channels = data.shape[-1]

        self.raw_unpadded_flattened_data = data.reshape(
            np.prod(self.data_shape), self.num_channels
        )

        if self.normalize_channels:
            # Normalize each channel to be between 0 and 1
            for i in range(data.shape[-1]):
                data[:, :, :, i] = _normalize_data(data[:, :, :, i])
        else:
            data = _normalize_data(data)

        fields = None
        if self.enable_preprocessing:
            self.arrays_raw = {}
            fields = {}

            all_zero_voxels = np.all(np.isclose(data, 0), axis=3)
            for idx, name in enumerate(header):
                array = data[:, :, :, idx]
                min_val = np.nanmin(array)
                max_val = np.nanmax(array)
                fields[name] = {
                    "label": name,
                    "data_range": [min_val, max_val],
                    "focus_range": [min_val, max_val],
                    "histogram": None,
                    "enabled": True,
                    "color": "black",
                }

                # Save array for later processing
                self.arrays_raw[name] = array

        # Provide control on data arrays
        self.state.data_channels = fields

        # Store the data in a flattened form. It is easier to work with.
        flattened_data = data.reshape(
            np.prod(self.data_shape), self.num_channels
        )
        self.nonzero_indices = ~np.all(np.isclose(flattened_data, 0), axis=1)

        # Only store nonzero data. We will reconstruct the zeros later.
        self.nonzero_data = flattened_data[self.nonzero_indices]

        # Trigger an update of the data
        self.update_gbc()

    def create_table(self):
        if self.label_map is None:
            # Nothing to do
            return

        # Fake table data for now
        table_headers = [{"title": "Name", "value": "name"}]
        for i, name in enumerate(self.state.component_labels):
            table_headers.append({
                "title": f'{name} (%)',
                "value": str(i),
                "align": "end",
            })

        table_content = []

        label_values = np.unique(self.label_map)

        data = self.raw_unpadded_flattened_data.reshape(
              (*self.data_shape, self.num_channels)
        )
        if self.normalize_channels:
            # Normalize all channels separately
            for i in range(data.shape[-1]):
                data[:, :, :, i] = _normalize_data(data[:, :, :, i])
        else:
            # Normalize them all together
            data = _normalize_data(data)

        if self.label_map_names:
            labels = self.label_map_names
        else:
            labels = list(map(str, label_values))

        for name, value in zip(labels, label_values):
            # Calculate the percent of each element
            matching_voxels = data[self.label_map == value]

            # Remove voxels that are all close to zero
            matching_voxels = matching_voxels[
                ~np.all(np.isclose(matching_voxels, 0), axis=1)]

            mean_values = matching_voxels.mean(axis=0)
            # Get each mean to add up to 1
            mean_values /= mean_values.sum()

            row = {"id": value.item(), "name": name}
            for i in range(len(self.state.component_labels)):
                row[str(i)] = f'{mean_values[i] * 100:6.2f}'

            table_content.append(row)

        self.state.table_headers = table_headers
        self.state.table_content = table_content

    def update_histograms(self, use_log_histogram):
        # histogram always use the full spectrum of the data
        # TODO: should we then store the two instances (log/non-log) instead of re-calculating ?
        nonzero_indices = ~np.all(
            np.isclose(self.raw_unpadded_flattened_data, 0), axis=1
        )
        nonzero_data = self.raw_unpadded_flattened_data[nonzero_indices]

        for idx, name in enumerate(self.state.component_labels):
            histogram_array = nonzero_data[:, idx]
            hist_count = np.histogram(histogram_array, bins=200)[0].astype(
                float
            )

            zero_counts = np.isclose(hist_count, 0)
            # Perform log scaling, as that is easier to see. Ignore zeros.
            if use_log_histogram:
                hist_count[~zero_counts] = np.log10(hist_count[~zero_counts])
            max_count = hist_count.max()
            hist = [int(v / max_count * 100) for v in hist_count.tolist()]
            self.state.data_channels[name]['histogram'] = hist

    def update_gbc(self):
        gbc, components = compute_gbc(self.nonzero_data)

        self.unrotated_gbc = gbc
        self.state.unrotated_component_coords = components.tolist()

        self.update_bin_data()
        self.update_voxel_colors()

    @change('use_log_histogram')
    def on_use_log_histogram(self, use_log_histogram, **kwargs):
        self.update_histograms(use_log_histogram)
        # make data_channels dirty so that the UI element of the histogram is updated
        self.state.dirty("data_channels")

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

        self.gbc_data = gbc
        self.rgb_data = gbc_to_rgb(gbc)

        self.update_volume_data()

    @change(
        "table_selection",
        "unselected_opacity_multiplier",
    )
    def update_volume_data(self, **kwargs):
        if any(x is None for x in (self.rgb_data, self.gbc_data)):
            return

        rgb = self.rgb_data

        # Reconstruct full data with rgba values
        full_data = np.zeros((np.prod(self.data_shape), 4))
        full_data[self.nonzero_indices, :3] = rgb.T

        if self.opacity_data is None:
            # Make nonzero voxels have an alpha of the mean of the channels.
            full_data[self.nonzero_indices, 3] = self.nonzero_data.mean(axis=1)
            if self.state.table_selection:
                idx = self.state.table_selection[0]
                # Significantly decrease opacity of non-selected voxels
                selected_voxels = self.label_map == idx
                multiplier = self.state.unselected_opacity_multiplier
                full_data[~selected_voxels.flatten(), 3] *= multiplier
        else:
            full_data[self.nonzero_indices, 3] = self.opacity_data.flatten()[
                self.nonzero_indices
            ]

        full_data = full_data.reshape((*self.data_shape, 4))

        # Set the data on the volume
        self.volume_view.set_data(full_data)

        # Update the mask data too. This will trigger an update.
        self.update_mask_data()

    @change(
        'lens_center',
        'show_groups',
        'w_lradius',
        'w_linvert',
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

        # Also update the statistics
        self.update_displayed_voxel_means()

    @change("show_groups")
    def update_displayed_voxel_means(self, **kwargs):
        first_call = not hasattr(self, '_initial_display_voxel_means_call')
        if not first_call and not self.voxel_means_enabled:
            # Only perform this on the first call if voxel means is not enabled
            return

        if first_call:
            self._initial_display_voxel_means_call = False

        alpha = self.volume_view.mask_reference[self.nonzero_indices]
        raw_nonzero = self.raw_unpadded_flattened_data[self.nonzero_indices]

        display_data = raw_nonzero[alpha == 1]
        if display_data.shape[0] > 0:
            # divide each row with the row sum to create percentages for each voxel
            row_sums = display_data.sum(axis=1)
            percentage_per_voxel = np.divide(
                display_data,
                row_sums[:, None],
                out=np.zeros_like(display_data),
                where=row_sums[:, None] != 0,
            )
            means = (
                100.0
                * percentage_per_voxel.sum(axis=0)
                / percentage_per_voxel.shape[0]
            )
        else:
            means = np.zeros(display_data.shape[1])

        labels = self.state.component_labels
        displayed_voxel_means = {k: v for k, v in zip(labels, means.tolist())}
        self.state.displayed_voxel_means = displayed_voxel_means
        self.server.controller.figure_update(_bar_plot(displayed_voxel_means))

    @change("data_channels")
    @change("normalize_ranges")
    def on_data_change(self, data_channels, **_):
        if not self.state.array_modified:
            # No updates were actually made. Just return
            return

        print("data_channels - changed")
        self.state.component_labels = [
            item.get("label")
            for item in data_channels.values()
            if item.get("enabled")
        ]

        arrays = []

        # Set a voxel to be zero in all channels if one channel
        # is outside the focus range.
        set_to_zero = np.zeros(self.data_shape, dtype=bool)
        for key, item in data_channels.items():
            if item.get("enabled"):
                array = self.arrays_raw[key]

                focus_range = item["focus_range"]
                set_to_zero[array < focus_range[0]] = True
                set_to_zero[array > focus_range[1]] = True

                arrays.append(array)

        # Update rest of pipeline
        data = np.stack(arrays, axis=3)

        if self.state.normalize_ranges:
            # Set any invalid voxels to zero before normalizing
            data[set_to_zero] = 0

        if self.normalize_channels:
            # Normalize all channels separately
            for i in range(data.shape[-1]):
                data[:, :, :, i] = _normalize_data(data[:, :, :, i])
        else:
            # Normalize them all together
            data = _normalize_data(data)

        if not self.state.normalize_ranges:
            # The invalid voxels are set to zero after normalizing instead
            data[set_to_zero] = 0

        # Store the data in a flattened form. It is easier to work with.
        flattened_data = data.reshape(np.prod(self.data_shape), len(arrays))
        self.nonzero_indices = ~np.all(np.isclose(flattened_data, 0), axis=1)

        # Only store nonzero data. We will reconstruct the zeros later.
        self.nonzero_data = flattened_data[self.nonzero_indices]

        # Trigger an update of the data
        self.update_gbc()

    @change("w_rendering_shadow", "w_rendering_bg")
    def on_rendering_settings(
        self, w_rendering_shadow, w_rendering_bg, **kwargs
    ):
        self.volume_view.volume_property.SetShade(
            1 if w_rendering_shadow else 0
        )
        if w_rendering_bg:
            self.volume_view.renderer.SetBackground(1, 1, 1)
        else:
            self.volume_view.renderer.SetBackground(0, 0, 0)
        self.ctrl.view_update()

    @property
    def render_window(self):
        return self.volume_view.render_window

    @property
    def lens_enabled(self):
        return "lens" in self.state.show_groups

    @property
    def voxel_means_enabled(self):
        return ("voxel-means" in self.state.show_groups) or (
            "voxel-means-plot" in self.state.show_groups
        )

    @life_cycle.server_ready
    def initial_reset_camera(self, **kwargs):
        self.volume_view.renderer.ResetCameraClippingRange()
        self.volume_view.renderer.ResetCamera()

    @property
    def clip_ranges(self):
        return [
            self.state.w_clip_x,
            self.state.w_clip_y,
            self.state.w_clip_z,
        ]

    def compute_alpha(self):
        gbc_data = self.gbc_data
        if gbc_data is None:
            # Can't do anything
            return None

        clip_mask = np.zeros(self.data_shape, dtype=bool)
        slices = []
        for i, (min_clip, max_clip) in enumerate(self.clip_ranges):
            min_idx = int(np.round(self.data_shape[i] * min_clip))
            max_idx = int(np.round(self.data_shape[i] * max_clip))
            slices.append(np.s_[min_idx:max_idx])

        clip_mask[slices[0], slices[1], slices[2]] = True

        # Reshape into the flat form and remove any zero index data
        clip_flattened = clip_mask.reshape(np.prod(self.data_shape))
        # If we perform any other operations, we can logical_and them
        alpha = clip_flattened[self.nonzero_indices]

        if not self.lens_enabled:
            # Only apply clipping
            return alpha

        # These are in unit circle coordinates
        r = self.state.w_lradius
        x, y = self.state.lens_center

        lens_alpha = _compute_alpha(np.array([x, y]), r, gbc_data)
        if self.state.w_linvert:
            lens_alpha = np.invert(lens_alpha)

        # Combine the lens alpha with the current alpha
        return np.logical_and(alpha, lens_alpha)

    def _build_ui(self):
        self.state.setdefault('lens_center', [0, 0])
        self.state.setdefault("array_modified", '')
        self.state.setdefault('normalize_ranges', False)
        self.state.setdefault("unselected_opacity_multiplier", 0.1)

        server = self.server
        ctrl = self.ctrl

        self.state.trame__title = "MultivariateView"
        self.state.trame__favicon = ASSETS.favicon

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
                        density="compact",
                        style="position: sticky; top: 0;",
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
                            v.VBtn(
                                icon="mdi-database",
                                value="tune-data",
                                v_if="data_channels && Object.keys(data_channels).length",
                            )
                            v.VBtn(icon="mdi-magnify", value="lens")
                            v.VBtn(icon="mdi-palette", value="color")
                            v.VBtn(
                                icon="mdi-eye-settings-outline",
                                value="rendering",
                            )
                            v.VBtn(
                                icon="mdi-chart-histogram", value="sampling"
                            )
                            v.VBtn(icon="mdi-crop", value="clip")
                            v.VBtn(
                                icon="mdi-sigma",
                                value="voxel-means",
                            )
                            v.VBtn(
                                icon="mdi-align-vertical-bottom",
                                value="voxel-means-plot",
                            )
                            v.VBtn(
                                icon="mdi-table",
                                value="table",
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
                        size=600,
                        rotation=('w_rotation', 0),
                        sample_size=('w_sample_size', 1100),
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
                        v.VSwitch(
                            label="Invert lens",
                            v_model=('w_linvert', False),
                            messages="Invert lens",
                            density="compact",
                            hide_details=True,
                            inset=True,
                            color="green",
                            classes="ml-2",
                        )

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

                    # Rendering settings
                    with v.VCard(
                        flat=True,
                        v_show="show_control_panel && show_groups.includes('rendering')",
                        classes="py-1",
                    ):
                        with v.VCol():
                            v.VSwitch(
                                label="Use shadow",
                                v_model=('w_rendering_shadow', True),
                                density='compact',
                            )
                            v.VSwitch(
                                label="Use white background",
                                v_model=('w_rendering_bg', False),
                                density='compact',
                            )

                    # Data sampling
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
                        v.VSwitch(
                            v_model=("use_log_histogram", True),
                            density='compact',
                            hide_details=True,
                            inset=True,
                            color="green",
                            classes="ml-2",
                            label="log scale (histograms)",
                            true_icon="mdi-check",
                            false_icon="mdi-close",
                        )
                        v.VDivider(classes="mr-n4")
                        v.VSwitch(
                            v_model=('normalize_ranges', True),
                            density='compact',
                            hide_details=True,
                            inset=True,
                            color="green",
                            classes="ml-2",
                            label="Rescale channels after range edits",
                            true_icon="mdi-check",
                            false_icon="mdi-close",
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
                                with v.VRow(classes="mx-0"):
                                    v.VTextField(
                                        model_value=("data.label",),
                                        density='compact',
                                        hide_details=True,
                                        prepend_icon="mdi-tag-outline",
                                        variant="outlined",
                                        update_modelValue="data_channels[name].label = $event; array_modified='';flushState('data_channels')",
                                    )
                                    v.VSwitch(
                                        model_value=("data.enabled",),
                                        density='compact',
                                        hide_details=True,
                                        inset=True,
                                        color="green",
                                        classes="ml-2",
                                        true_icon="mdi-check",
                                        false_icon="mdi-close",
                                        update_modelValue="data_channels[name].enabled = $event; array_modified=''; flushState('data_channels')",
                                    )
                                with html.Div(
                                    style="height: 4rem;",
                                    classes="align-baseline d-flex mt-5 ml-12 mr-2 mb-n3",
                                ):
                                    html.Div(
                                        v_for="v, idx in data.histogram",
                                        key="idx",
                                        style=(
                                            "`height: ${v}%; width: 0.5%;`",
                                        ),
                                        classes="d-flex bg-blue",
                                    )
                                v.VRangeSlider(
                                    model_value=('data.focus_range',),
                                    min=("data.data_range[0]",),
                                    max=("data.data_range[1]",),
                                    step=(
                                        "(data.data_range[1] - data.data_range[0]) / 255",
                                    ),
                                    density='compact',
                                    hide_details=True,
                                    prepend_icon="mdi-magnify",
                                    update_modelValue="data_channels[name].focus_range = $event; array_modified=name; flushState('data_channels')",
                                )

                    with v.VCard(
                        flat=True,
                        v_show="show_control_panel && show_groups.includes('voxel-means')",
                        classes="py-1",
                    ):
                        with v.VTable(density="compact"):
                            with html.Tbody():
                                with html.Tr(
                                    v_for="v, k in displayed_voxel_means",
                                    key="k",
                                ):
                                    html.Td("{{ k }}", classes="text-caption")
                                    html.Td(
                                        "{{ v.toFixed(2) }}%",
                                        classes="text-caption",
                                        style="text-align: right; padding-right: 10rem;",
                                    )

                    with v.VCard(
                        flat=True,
                        v_show="show_control_panel && show_groups.includes('voxel-means-plot')",
                        classes="py-1",
                    ):
                        with html.Div(style="width: 100%; height: 10rem;"):
                            figure = plotly.Figure(
                                display_logo=False,
                                display_mode_bar="true",
                            )
                            self.server.controller.figure_update = (
                                figure.update
                            )

                    if self.label_map is not None:
                        # Table (phase selection)
                        with v.VCard(
                            flat=True,
                            v_show="show_control_panel && show_groups.includes('table')",
                            classes="py-1 pr-4",
                            v_if="table_content",
                        ):
                            v.VLabel("Label Map", classes="text-body-2 ml-1")
                            v.VDivider(classes="mr-n4")
                            v.VSlider(
                                v_model='unselected_opacity_multiplier',
                                min=0,
                                max=1,
                                step=0.01,
                                density='compact',
                                prepend_icon="mdi-chart-scatter-plot-hexbin",
                                messages="Unselected Voxels Opacity Multiplier",
                            )
                            v.VDataTable(
                                headers=("table_headers", []),
                                items=("table_content", None),
                                density="compact",
                                item_value="id",
                                item_selectable=True,
                                select_strategy="single",  # all / single
                                show_select=True,
                                v_model=("table_selection", []),
                                hide_default_footer=True,
                            )

            # print(layout)
            return layout


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


def _bar_plot(key_values):
    return go.Figure(
        data=go.Bar(x=list(key_values.keys()), y=list(key_values.values()))
    ).update_layout(yaxis_title="%", margin=dict(l=10, r=10, t=25, b=10))

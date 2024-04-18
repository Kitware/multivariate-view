import csv
from pathlib import Path

from trame.app import get_server
from trame.decorators import TrameApp, change
from trame.ui.vuetify3 import SinglePageWithDrawerLayout
from trame.widgets import vuetify3 as v, html
from trame_radvolviz.widgets import radvolviz

from .io import load_csv_dataset

DATA_FILE = Path(__file__).parent.parent.parent / "data/data10.csv"


@TrameApp()
class App:
    def __init__(self, server=None):
        self.server = get_server(server, client_type="vue3")
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

    @property
    def state(self):
        return self.server.state

    @change("lens_data")
    def update_opacity(self, lens_data, **kwargs):
        print(f"{lens_data=}")

    def _build_ui(self):
        self.state.setdefault("lens_data", None)

        with SinglePageWithDrawerLayout(
            self.server, full_height=True
        ) as layout:
            with layout.toolbar.clear():
                v.VAppBarNavIcon(click="main_drawer = !main_drawer")
                v.VAppBarTitle("RadVolViz")
                v.VSpacer()
                html.Div("{{ lens_data }}")

            with layout.drawer as drawer:
                drawer.width = 400
                # add new widget
                v.VSlider(
                    label="Widget size",
                    v_model="w_size",
                    min=150,
                    max=600,
                    step=50,
                    density="compact",
                    hide_details=True,
                )
                v.VSlider(
                    label="Widget rotation",
                    v_model="w_rotation",
                    min=0,
                    max=360,
                    step=5,
                    density="compact",
                    hide_details=True,
                )
                v.VSlider(
                    label="Sample size",
                    v_model="w_sample_size",
                    min=100,
                    max=10000,
                    step=500,
                    density="compact",
                    hide_details=True,
                )
                v.VSlider(
                    label="Number of bins",
                    v_model="w_bins",
                    min=1,
                    max=10,
                    step=1,
                    density="compact",
                    hide_details=True,
                )
                v.VSwitch(
                    label="Lens",
                    v_model="w_lens",
                )
                v.VSlider(
                    label="Lens radius",
                    v_model="w_lradius",
                    min=5,
                    max=100,
                    step=1,
                    density="compact",
                    hide_details=True,
                )

            with layout.content:
                radvolviz.NdColorMap(
                    data=("data", []),
                    components=("components", []),
                    size=("w_size", 200),
                    rotation=("w_rotation", 0),
                    sample_size=("w_sample_size", 100),
                    number_of_bins=("w_bins", 6),
                    show_lens=("w_lens", False),
                    lens_radius=("w_lradius", 10),
                    lens="lens_data = $event",
                )

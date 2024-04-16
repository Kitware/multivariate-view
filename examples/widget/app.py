from trame.app import get_server
from trame.ui.vuetify3 import SinglePageWithDrawerLayout
from trame.widgets import vuetify3 as v, html


class TestApp:
    def __init__(self, server=None):
        self.server = get_server(server, client_type="vue3")
        self.ui = self._build_ui()

    def _build_ui(self):
        with SinglePageWithDrawerLayout(
            self.server, full_height=True
        ) as layout:
            with layout.toolbar.clear():
                v.VAppBarNavIcon(click="main_drawer = !main_drawer")
                v.VAppBarTitle("RadVolViz")
                v.VSpacer()

            with layout.drawer as drawer:
                drawer.width = 200
                # add new widget
                html.Div("Drawer")

            with layout.content:
                html.Div("content")


def main():
    app = TestApp()
    app.server.start()


if __name__ == "__main__":
    main()

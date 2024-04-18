from trame_client.widgets.core import AbstractElement
from trame_radvolviz import module

__all__ = [
    "NdColorMap",
]


class HtmlElement(AbstractElement):
    def __init__(self, _elem_name, children=None, **kwargs):
        super().__init__(_elem_name, children, **kwargs)
        if self.server:
            self.server.enable_module(module)


class NdColorMap(HtmlElement):
    def __init__(self, children=None, **kwargs):
        super().__init__("nd-color-map", children, **kwargs)
        self._attr_names += [
            "labels",
            "rotation",
            "size",
            ("brush_mode", "brushMode"),
            ("data_to_draw", "dataToDraw"),
            ("label_coordinates", "labelCoordinates"),
            ("lens_radius", "lensRadius"),
            ("number_of_bins", "numberOfBins"),
            ("sample_size", "sampleSize"),
            ("show_lens", "showLens"),
        ]
        self._event_names += [
            "lens",
        ]

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
            "components",
            "data",
            "size",
            "rotation",
            ("brush_mode", "brushMode"),
            ("sample_size", "sampleSize"),
            ("number_of_bins", "numberOfBins"),
            ("show_lens", "showLens"),
            ("lens_radius", "lensRadius"),
        ]
        self._event_names += [
            "lens",
        ]

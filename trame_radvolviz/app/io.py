import csv

import numpy as np
from PIL import Image

from trame_radvolviz.typing import PathLike


def load_csv_dataset(path: PathLike) -> tuple[list[str], np.ndarray]:
    """Load a CSV dataset and return the labels and the data"""
    # First, load the labels
    with open(path) as f:
        reader = csv.reader(f)
        labels = next(reader)

    data = np.loadtxt(path, delimiter=',', skiprows=1)

    return labels, data


def load_png_dataset(path: PathLike) -> tuple[list[str], np.ndarray]:
    img = Image.open(path)
    data = (
        np.array(img)
        .reshape((16, 256, 16, 256, 4))
        .swapaxes(1, 2)
        .reshape((256, 256, 256, 4))
    )

    # What is the slice shape?
    # FIXME: can we figure out the actual labels?
    labels = ['R', 'B', 'G', 'A']

    return labels, data

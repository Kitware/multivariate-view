import csv
from pathlib import Path
import re
from typing import Callable

import numpy as np
from PIL import Image

from trame_radvolviz.typing import PathLike


def load_dataset(path: PathLike) -> tuple[list[str], np.ndarray]:
    """Automatically determine format and load a dataset

    Labels and data are returned
    """
    loader = identify_loader_function(path)
    return loader(path)


def identify_loader_function(
    path: PathLike,
) -> Callable[[PathLike], np.ndarray]:
    """Identify the loader function for the specified file"""

    extension = Path(path).suffix[1:]
    for regex, func in READERS.items():
        if re.match(regex, extension):
            return func

    msg = f'Unable to identify loader for file: {path}'
    raise Exception(msg)


def load_csv_dataset(path: PathLike) -> tuple[list[str], np.ndarray]:
    """Load a CSV dataset and return the labels and the data"""
    # First, load the labels
    with open(path) as f:
        reader = csv.reader(f)
        labels = next(reader)

    data = np.loadtxt(path, delimiter=',', skiprows=1)

    return labels, data


def load_npz_dataset(path: PathLike) -> tuple[list[str], np.ndarray]:
    # This assumes each channel is saved as a separate array in the npz file
    datasets = {}
    with np.load(path) as f:
        for k, v in f.items():
            # Transpose to Fortran indexing
            datasets[k] = v

    # Stack the datasets together
    data = np.ascontiguousarray(np.stack(list(datasets.values()), axis=3))
    labels = list(datasets)

    return labels, data


def load_radvolviz_png_dataset(path: PathLike) -> tuple[list[str], np.ndarray]:
    # Load a radvolviz-style multi-channel PNG dataset
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


# The key for these readers is the regular expression
# that the extension should match.
READERS = {
    r'^png$': load_radvolviz_png_dataset,
    r'^npz$': load_npz_dataset,
    r'^csv$': load_csv_dataset,
}

# Compile the regular expressions (and make them case-insensitive)
READERS = {re.compile(k, re.I): v for k, v in READERS.items()}

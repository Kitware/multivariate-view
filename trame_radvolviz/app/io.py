import csv

import numpy as np

from trame_radvolviz.typing import PathLike


def load_csv_dataset(path: PathLike) -> tuple[list[str], np.ndarray]:
    """Load a CSV dataset and return the labels and the data"""
    # First, load the labels
    with open(path) as f:
        reader = csv.reader(f)
        labels = next(reader)

    data = np.loadtxt(path, delimiter=',', skiprows=1)

    return labels, data

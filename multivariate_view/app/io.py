import csv
from pathlib import Path
import re
from typing import Callable

import h5py
import numpy as np
from PIL import Image
from vtkmodules.vtkIOXML import vtkXMLImageDataReader
from vtkmodules.util import numpy_support as np_s

from multivariate_view.typing import PathLike


# First is a list of labels, second is an array
LoadReturnType = tuple[list[str], np.ndarray]


def load_dataset(path: PathLike) -> LoadReturnType:
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


def load_csv_dataset(path: PathLike) -> LoadReturnType:
    """Load a CSV dataset and return the labels and the data"""
    # First, load the labels
    with open(path) as f:
        reader = csv.reader(f)
        labels = next(reader)

    data = np.loadtxt(path, delimiter=',', skiprows=1)

    return labels, data


def load_npz_dataset(path: PathLike) -> LoadReturnType:
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


def load_radvolviz_png_dataset(path: PathLike) -> LoadReturnType:
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
    labels = ['R', 'G', 'B', 'A']

    return labels, data


def load_vti_dataset(path: PathLike) -> LoadReturnType:
    reader = vtkXMLImageDataReader()
    reader.SetFileName(path)
    reader.Update()
    image_data = reader.GetOutput()

    vtk_array = image_data.GetPointData().GetScalars()
    data_shape = image_data.GetDimensions()
    num_components = vtk_array.GetNumberOfComponents()
    labels = [vtk_array.GetComponentName(i) for i in range(num_components)]
    data = np_s.vtk_to_numpy(vtk_array).reshape(*data_shape, num_components)

    # This is in fortran ordering, but our program expects C ordering.
    # So transpose to C ordering
    data = data.reshape(*(data_shape[::-1]), num_components).transpose(
        2, 1, 0, 3
    )
    data = np.ascontiguousarray(data)

    return labels, data


def load_hdf5_dataset(path: PathLike) -> LoadReturnType:
    labels = []
    data = []

    with h5py.File(path, 'r') as f:
        for key in f:
            labels.append(key)
            data.append(f[key][()])

    data = np.stack(data, axis=3)

    return labels, data


# The key for these readers is the regular expression
# that the extension should match.
READERS = {
    r'^png$': load_radvolviz_png_dataset,
    r'^npz$': load_npz_dataset,
    r'^csv$': load_csv_dataset,
    r'^vti$': load_vti_dataset,
    r'^h5$': load_hdf5_dataset,
}

# Compile the regular expressions (and make them case-insensitive)
READERS = {re.compile(k, re.I): v for k, v in READERS.items()}

from pathlib import Path

import numpy as np
import pytest

from multivariate_view.app.io import load_csv_dataset


@pytest.fixture
def test_dir():
    return Path(__file__).parent


@pytest.fixture
def data_path(test_dir):
    return test_dir / 'test_data/data10.csv'


@pytest.fixture
def ref_dir(test_dir):
    return test_dir / 'test_output'


@pytest.fixture
def sample_dataset_labels_and_data(data_path):
    return load_csv_dataset(data_path)


@pytest.fixture
def sample_dataset_labels(sample_dataset_labels_and_data):
    return sample_dataset_labels_and_data[0]


@pytest.fixture
def sample_dataset_data(sample_dataset_labels_and_data):
    return sample_dataset_labels_and_data[1]

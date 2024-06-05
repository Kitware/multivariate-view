import numpy as np

from multivariate_view.app.compute.gbc import compute_gbc, rotate_coordinates


def test_gbc(sample_dataset_data, ref_dir):
    test_files = [
        'gbc1.npz',
        'gbc2.npz',
        'gbc3.npz',
    ]

    for filename in test_files:
        ref = np.load(ref_dir / filename)

        num_rows = ref['num_rows']
        ref_components = ref['components']
        ref_gbc = ref['data']
        rotation = ref['rotation_angle']

        # We only use up to num_rows of the data
        data = sample_dataset_data[:num_rows]
        gbc, components = compute_gbc(data)

        # Perform the rotation
        gbc = rotate_coordinates(gbc, rotation)
        components = rotate_coordinates(components, rotation)

        assert np.allclose(components, ref_components)
        assert np.allclose(gbc, ref_gbc)

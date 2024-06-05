import numpy as np

from multivariate_view.app.compute.bin import data_topology_reduction


def test_binning(ref_dir):
    # Use the GBC data as input
    input_files = [
        'gbc1.npz',
        'gbc2.npz',
        'gbc3.npz',
    ]

    ref_files = [
        'bins1.npz',
        'bins2.npz',
        'bins3.npz',
    ]

    for gbc_filename, ref_filename in zip(input_files, ref_files):
        gbc = np.load(ref_dir / gbc_filename)
        gbc_data = gbc['data']

        ref = np.load(ref_dir / ref_filename)
        ref_q = ref['q']
        num_bins = ref['num_bins']

        # Copy the rand function used in RadVolViz, so we will get an
        # identical result

        seed = 1

        def rand():
            nonlocal seed
            x = np.sin(seed) * 10000
            seed += 1
            return x - np.floor(x)

        q = data_topology_reduction(gbc_data, num_bins, rand_func=rand)
        assert np.allclose(q, ref_q)

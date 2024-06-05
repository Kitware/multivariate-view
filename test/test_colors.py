import colorsys

import numpy as np

from multivariate_view.app.compute.hsl import gbc_to_hsl, hsl_to_rgb


def test_hsl_to_rgb(sample_dataset_data, ref_dir):
    test_files = [
        'gbc1.npz',
        'gbc2.npz',
        'gbc3.npz',
    ]

    for filename in test_files:
        ref = np.load(ref_dir / filename)
        gbc = ref['data']

        # Convert the GBC data to HSL, and then to RGB
        hsl = gbc_to_hsl(gbc)
        rgb = hsl_to_rgb(hsl)

        # Now verify that colorsys matches all HSL to RGB conversions
        for entry, result in zip(hsl.T, rgb.T):
            ref = colorsys.hls_to_rgb(entry[0], entry[2], entry[1])
            assert np.allclose(ref, result)

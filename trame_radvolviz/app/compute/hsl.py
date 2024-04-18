import numpy as np


def gbc_to_hsl(gbc: np.ndarray, lightness=0.55) -> np.ndarray:
    # Make a copy to modify
    gbc = gbc.copy()
    radius = np.sqrt((gbc**2).sum(axis=1))
    invalid = radius > 1

    if np.any(invalid):
        gbc[invalid] /= radius[invalid]

    hue = np.arctan2(gbc[:, 1], gbc[:, 0]) + np.pi / 2
    hue = np.floor(np.mod(hue, np.pi * 2) / np.pi * 180)

    saturation = np.sqrt((gbc**2).sum(axis=1))

    hsl = np.vstack((hue, saturation, np.repeat(lightness, len(hue))))
    return hsl

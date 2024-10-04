import numba
import numpy as np


def gbc_to_rgb(gbc: np.ndarray, lightness=0.55) -> np.ndarray:
    hsl = gbc_to_hsl(gbc, lightness)
    return hsl_to_rgb(hsl)


def gbc_to_hsl(gbc: np.ndarray, lightness=0.55) -> np.ndarray:
    # Make a copy to modify
    gbc = gbc.copy()
    radius = np.sqrt((gbc**2).sum(axis=1))
    invalid = radius > 1

    if np.any(invalid):
        gbc[invalid] /= radius[invalid, np.newaxis]

    hue = np.arctan2(gbc[:, 1], gbc[:, 0]) + np.pi / 2
    hue = np.mod(hue, np.pi * 2) / (np.pi * 2)

    saturation = np.sqrt((gbc**2).sum(axis=1))

    return np.vstack((hue, saturation, np.repeat(lightness, len(hue))))


@numba.njit(cache=True, nogil=True)
def hsl_to_rgb(hsl):
    h, s, l = hsl  # noqa: E741

    # Compute m2
    m2 = np.empty(len(h))

    small_l = l <= 0.5
    lower_l = l[small_l]
    lower_s = s[small_l]

    upper_l = l[~small_l]
    upper_s = s[~small_l]

    m2[small_l] = lower_l * (1 + lower_s)
    m2[~small_l] = upper_l + upper_s - (upper_l * upper_s)

    # Compute m1
    m1 = 2 * l - m2

    # Compute r, g, and b
    result = np.empty(hsl.shape)
    result[0] = _v(m1, m2, h + (1 / 3))
    result[1] = _v(m1, m2, h)
    result[2] = _v(m1, m2, h - (1 / 3))

    # Finally, just set anything with a saturation of 0 to be lightness
    zero_saturation = s == 0
    if np.any(zero_saturation):
        result[:, zero_saturation] = l

    return result


@numba.njit(cache=True, nogil=True)
def _v(m1, m2, h):
    result = np.empty(len(h))

    h = np.mod(h, 1.0)
    sixth = h < (1 / 6)
    half = ~sixth & (h < 0.5)
    two_third = ~sixth & ~half & (h < (2 / 3))
    none = ~sixth & ~half & ~two_third

    m_diff = m2 - m1

    result[sixth] = m1[sixth] + m_diff[sixth] * h[sixth] * 6
    result[half] = m2[half]
    result[two_third] = (
        m1[two_third] + m_diff[two_third] * ((2 / 3) - h[two_third]) * 6
    )
    result[none] = m1[none]

    return result

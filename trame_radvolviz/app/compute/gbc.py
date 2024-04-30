import numba
import numpy as np


@numba.njit(cache=True, nogil=True)
def compute_gbc(data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # Compute dimensions
    m, n = data.shape

    # Compute angles and components
    angle = np.empty((n,))
    angle[0] = np.pi / 2

    components = np.empty((n, 2))
    components[0, 0] = np.cos(angle[0])
    components[0, 1] = np.sin(angle[0])

    for i in range(1, n):
        angle[i] = angle[i - 1] - (2 * np.pi) / n
        components[i, 0] = np.cos(angle[i]) * 0.997
        components[i, 1] = np.sin(angle[i]) * 0.997

    # Wrap to the 0 to 2*pi range
    angle = np.mod(angle, np.pi * 2)
    angle = np.sort(angle)

    # Compute GBC
    gbc = np.zeros((m, 2))
    for i in range(m):
        tempsum = data[i].sum()
        if tempsum == 0:
            continue

        for k in range(n):
            gbc[i] += data[i, k] * components[k] / tempsum

        tempangle = np.arctan2(gbc[i, 1], gbc[i, 0])
        tempangle = np.mod(tempangle, np.pi * 2)

        flag = False
        temp_a = 0
        temp_b = 0
        for j in range(n - 1):
            if angle[j] <= tempangle < angle[j + 1]:
                temp_a = angle[j + 1]
                temp_b = angle[j]
                flag = True
                break

        if not flag:
            temp_a = angle[0] + np.pi * 2
            temp_b = angle[n - 1]

        lth = (
            np.sqrt(gbc[i, 0] ** 2 + gbc[i, 1] ** 2)
            / np.cos((temp_a - temp_b) / 2)
            * np.cos(-(temp_a + temp_b) / 2 + tempangle)
        )
        gbc[i, 0] = lth * np.cos(tempangle)
        gbc[i, 1] = lth * np.sin(tempangle)

    return gbc, components


@numba.njit(cache=True, nogil=True)
def rotate_coordinates(coords, angle):
    """Rotate coordinates by the angle (radians) about the origin"""
    mat = np.array(
        [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]]
    )

    return (mat @ coords.T).T

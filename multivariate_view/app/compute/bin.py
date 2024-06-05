import numpy as np


def data_topology_reduction(
    data: np.ndarray, num_bins: int, rand_func=None
) -> np.ndarray:
    if rand_func is None:
        rand_func = np.random.rand

    bins = []
    bin_map = {}
    for i in range(num_bins):
        bin_map[i] = {}
        for j in range(num_bins):
            bin_map[i][j] = []
            bins.append(bin_map[i][j])

    delta = 2 / num_bins
    c_min = 0
    c_max = num_bins - 1
    for entry in data:
        i, j = np.clip(np.floor((entry + 1) / delta), c_min, c_max)
        bin_map[i][j].append(entry)

    q = []
    for entries in bins:
        num_entries = len(entries)
        if num_entries == 0:
            # Skip empty bins
            continue

        sample_idx = set()
        target_size = num_entries / 2
        if target_size > 1000:
            target_size = 5 * np.log2(num_entries)
        elif target_size > 100:
            target_size = np.log2(num_entries)

        while len(sample_idx) < target_size:
            rd = int(np.floor(rand_func() * num_entries))
            if rd in sample_idx:
                continue

            sample_idx.add(rd)
            q.append(entries[rd])

    return np.asarray(q)

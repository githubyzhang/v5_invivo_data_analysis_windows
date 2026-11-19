"""
==============================================================================
Author: Yuchang Zhang (yzhang6@g.harvard.edu)
File Name: shank.py
Date Created: 2025-12-12
Last Modified:
Version     Comment                                         Date
    1.0     Initially created.                              2025-12-12

Description:
    Reshaping channels into correct spatial coordinates on shanks.

Copyright (c) 2025, Yuchang Zhang. All rights reserved.
==============================================================================
"""

import numpy as np
from utility.file_read_write import tuple_to_id
from typing import Iterable


def look_up_table() -> list[tuple[int, int]]:
    """Creates a lookup table mapping channel_id (0..2047) -> (shank_idx, pad_idx)."""
    lookup_table: list[tuple[int, int]] = []

    for row in range(32):
        for col in range(64):
            array_idx = row * 64 + col  # 0..2047

            vertical_count = col * 32 + row
            shank_idx = vertical_count // 512
            col_idx = vertical_count // 128
            row_idx = vertical_count % 128

            if col_idx > 10:
                row_idx = 127 - row_idx

            pad_idx = row_idx * 4 + (col_idx % 4)
            lookup_table.append((shank_idx, pad_idx))

    return lookup_table


def ch_id_to_shank_coordinates(ch_id: int | list[int], lookup_table: list[tuple[int, int]] | None = None):
    if lookup_table is None:
        lookup_table = look_up_table()

    def one(i: int) -> tuple[int, int]:
        i = int(i)
        if not (0 <= i < 2048):
            raise ValueError(f"channel id out of range: {i} (expected 0..2047)")
        return lookup_table[i]

    if isinstance(ch_id, (int, np.integer)):
        return one(ch_id)

    if isinstance(ch_id, list):
        return [one(i) for i in ch_id]

    return None


def reverse_look_up_table() -> np.ndarray:
    """
    Creates a reverse lookup table mapping (shank_idx, pad_idx) -> channel_id.

    Returns:
        rev: ndarray shape (4, 512), dtype int32
             rev[shank_idx, pad_idx] = channel_id
    """
    rev = np.full((4, 512), -1, dtype=np.int32)

    # Build from the same mapping (guaranteed consistent)
    ch = 0
    for row in range(32):
        for col in range(64):
            vertical_count = col * 32 + row
            shank_idx = vertical_count // 512
            col_idx = vertical_count // 128
            row_idx = vertical_count % 128

            if col_idx > 10:
                row_idx = 127 - row_idx

            pad_idx = row_idx * 4 + (col_idx % 4)
            rev[shank_idx, pad_idx] = ch
            ch += 1

    return rev


def shank_coordinates_to_ch_id(
    coords: tuple[int, int] | list[tuple[int, int]],
    reverse_table: np.ndarray | None = None
) -> int | list[int]:
    """
    Convert (shank_idx, pad_idx) back to channel_id using a reverse lookup table.

    Args:
        coords: (shank_idx, pad_idx) or a list of them
        reverse_table: optional precomputed table from reverse_look_up_table()

    Returns:
        channel_id (int) or list of ints
    """
    if reverse_table is None:
        reverse_table = reverse_look_up_table()

    def one(c: tuple[int, int]) -> int:
        s, p = c
        s = int(s); p = int(p)
        if not (0 <= s < 4) or not (0 <= p < 512):
            raise ValueError(f"Invalid coordinates: {(s, p)}")
        ch = int(reverse_table[s, p])
        if ch < 0:
            raise ValueError(f"Coordinates not mapped: {(s, p)}")
        return ch

    if isinstance(coords, tuple):
        return one(coords)

    if isinstance(coords, list):
        return [one(c) for c in coords]

    return None


""" LUT map method, but very slow so nevermind """
def build_shank_inverse_index() -> np.ndarray:
    """
    inv[shank_linear] = array_idx
    where shank_linear = shank_idx*512 + pad_idx
    """
    lut = look_up_table()  # your function: length 2048, entries (shank_idx, pad_idx)
    inv = np.empty(2048, dtype=np.int32)
    for array_idx, (s, p) in enumerate(lut):
        inv[s * 512 + p] = array_idx
    return inv
# def reshape_data_into_shanks(array, shank, inv: np.ndarray | None = None):
#     if inv is None:
#         inv = build_shank_inverse_index()
#
#     array = np.asarray(array)
#     shank = np.asarray(shank)
#
#     if array.ndim not in (1, 2) or shank.ndim not in (2, 3):
#         return
#     if array.shape[0] != 2048 or shank.shape[0] != 4 or shank.shape[1] != 512:
#         return
#     if array.dtype != shank.dtype:
#         return
#
#     array_N = 1 if array.ndim == 1 else array.shape[1]
#     shank_N = 1 if shank.ndim == 2 else shank.shape[2]
#     if array_N != shank_N:
#         return
#
#     array2 = array[:, None] if array.ndim == 1 else array        # (2048, N)
#     shank3 = shank[:, :, None] if shank.ndim == 2 else shank     # (4, 512, N)
#
#     # Flatten shank to (2048, N) in shank-linear order (shank_idx*512 + pad_idx)
#     shank_flat = shank3.reshape(2048, array_N)
#
#     # One bulk reorder-copy
#     shank_flat[:] = array2[inv, :]


""" Loop method """
def reshape_data_into_shanks(array, shank):
    """
    Reshapes recording array into shank shapes.

    Supported:
      array: (2048,) or (2048, N)
      shank: (4, 512) or (4, 512, N)

    Mapping is identical to the original implementation.
    """
    array = np.asarray(array)
    shank = np.asarray(shank)

    # ---- validate dims (allow N=1 / no depth dimension) ----
    if array.ndim not in (1, 2) or shank.ndim not in (2, 3):
        return
    if array.shape[0] != 2048 or shank.shape[0] != 4 or shank.shape[1] != 512:
        return
    if array.dtype != shank.dtype:
        return

    # Determine depth N
    array_N = 1 if array.ndim == 1 else array.shape[1]
    shank_N = 1 if shank.ndim == 2 else shank.shape[2]
    if array_N != shank_N:
        return

    # Create views that always have an explicit depth dimension
    array2 = array[:, None] if array.ndim == 1 else array         # (2048, N)
    shank3 = shank[:, :, None] if shank.ndim == 2 else shank      # (4, 512, N)

    for col in range(64):
        for row in range(32):
            array_idx = row * 64 + col

            vertical_count = col * 32 + row
            shank_idx = vertical_count // 512
            col_idx = vertical_count // 128
            row_idx = vertical_count % 128

            if col_idx > 10:
                row_idx = 127 - row_idx

            dst = shank3[shank_idx, row_idx * 4 + (col_idx % 4), :]
            src = array2[array_idx, :]
            np.copyto(dst, src)


def array_addr_to_shank_addr(addr):
    ch = tuple_to_id(addr)
    pos = ch_id_to_shank_coordinates(ch)
    shank_id = pos[0] + 1
    row, col = pos[1] // 4 + 1, pos[1] % 4 + 1

    print(f'shank-{shank_id}, row-{row}, col-{col}')
    return shank_id, row, col

# def bench_reshape(N=1000, repeats=50, dtype=np.float64):
#     # input + output buffers
#     array = np.random.randn(2048, N).astype(dtype, copy=False)
#     sh1 = np.empty((4, 512, N), dtype=dtype)
#     sh2 = np.empty((4, 512, N), dtype=dtype)
#
#     inv = build_shank_inverse_index()
#
#     # ---- warmup (avoid first-call overhead) ----
#     reshape_data_into_shanks_loop(array, sh1)
#     reshape_data_into_shanks(array, sh2, inv)
#
#     # ---- correctness check ----
#     if not np.allclose(sh1, sh2):
#         raise RuntimeError("Mismatch: reshape_data_into_shanks_loop != reshape_data_into_shanks")
#
#     # ---- timing helper ----
#     def time_fn(fn, out_buf):
#         ts = []
#         for _ in range(repeats):
#             t0 = time.perf_counter()
#             fn(array, out_buf, inv)
#             ts.append(time.perf_counter() - t0)
#         return np.mean(ts), np.std(ts)
#
#     mean_loop, std_loop = time_fn(reshape_data_into_shanks_loop, sh1)
#     mean_new,  std_new  = time_fn(reshape_data_into_shanks,      sh2)
#
#     speedup = mean_loop / mean_new if mean_new > 0 else np.inf
#
#     print(f"N={N:6d}  loop: {mean_loop*1e3:8.3f}±{std_loop*1e3:6.3f} ms   "
#           f"new: {mean_new*1e3:8.3f}±{std_new*1e3:6.3f} ms   "
#           f"speedup(loop/new): {speedup:6.2f}x")
#
#
# if __name__ == "__main__":
#     # Try a few depths (pick ones relevant to your pipeline)
#     for N in [1, 10, 100, 1000, 5000, 60000]:
#         bench_reshape(N=N, repeats=50, dtype=np.float64)
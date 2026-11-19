"""
==============================================================================
Company: Harvard University - Donhee Ham Research Group
Author: Yuchang Zhang (yzhang6@g.harvard.edu)
File Name: utility.py
Date Created: 2025-04-04
Last Modified:
Version     Comment                                         Date
    1.0     Initially created.                              2025-04-04

Description:
    This file contains utility functions used by various Classes.

Copyright (c) 2024, DONHEE HAM RESEARCH GROUP. All rights reserved.
==============================================================================
"""
# =============================================================================
# IMPORTS
# =============================================================================
import h5py
import numpy as np
import os
import zarr
import shutil
import re


EXTRACELLULAR_GAIN  = -460
INTRACELLULAR_GAIN  = -36

# =============================================================================
# Data Recording methods
# =============================================================================

def append_array_to_h5(file_path, array, dataset_name):
    """
    Appends a NumPy array to an existing dataset within an HDF5 file.
    If the dataset does not exist, it creates a new dataset.

    If the array is 1D, it appends along axis 0.
    If the array is 2D, it appends along axis 1 (columns).

    Args:
        file_path       (str): Path to the .h5 file.
        array           (np.ndarray): NumPy array to append.
        dataset_name    (str): Name of the dataset within the .h5 file.
    """
    array = np.asarray(array)

    with h5py.File(file_path, 'a') as file:
        if dataset_name in file:
            dataset = file[dataset_name]
            original_shape = dataset.shape

            if array.ndim == 1:
                # Append along axis 0
                new_shape = (original_shape[0] + array.shape[0],)
                dataset.resize(new_shape)
                dataset[original_shape[0]:] = array

            elif array.ndim == 2:
                if original_shape[0] != array.shape[0]:
                    raise ValueError(f"First dimension mismatch: dataset has {original_shape[0]}, array has {array.shape[0]}")
                # Append along axis 1 (columns)
                new_shape = (original_shape[0], original_shape[1] + array.shape[1])
                dataset.resize(new_shape)
                dataset[:, original_shape[1]:] = array

            else:
                raise ValueError("Only 1D or 2D arrays are supported.")

        else:
            # Create dataset with maxshape allowing unlimited growth in appropriate axis
            if array.ndim == 1:
                maxshape = (None,)
            elif array.ndim == 2:
                maxshape = (array.shape[0], None)
            else:
                raise ValueError("Only 1D or 2D arrays are supported.")
            file.create_dataset(dataset_name, data=array, maxshape=maxshape, chunks=True)


def append_array_to_zarr(file_path, array, dataset_name):
    """
    Appends a NumPy array to an existing dataset within a zarr file.
    If the dataset does not exist, it creates a new dataset.
    Arthur: this function is written by Nadir.

    If the array is 1D, it appends along axis 0.
    If the array is 2D, it appends along axis 1 (columns).

    Args:
        file_path       (str): Path to the .zarr file.
        array           (np.ndarray): NumPy array to append. (4096, 1000)
        dataset_name    (str): Name of the dataset within the .zarr file.
    """
    array = np.asarray(array)

    # Open or create the Zarr store
    store = zarr.DirectoryStore(file_path)
    root = zarr.open(store, mode='a')

    if dataset_name in root:
        dataset = root[dataset_name]
        original_shape = dataset.shape

        if array.ndim == 1:
            # Append along axis 0
            new_shape = (original_shape[0] + array.shape[0],)
            dataset.resize(new_shape)
            dataset[original_shape[0]:] = array

        elif array.ndim == 2:
            if original_shape[0] != array.shape[0]:
                raise ValueError(
                    f"First dimension mismatch: dataset has {original_shape[0]}, array has {array.shape[0]}")
            # Append along axis 1 (columns)
            new_shape = (original_shape[0], original_shape[1] + array.shape[1])
            dataset.resize(new_shape)
            dataset[:, original_shape[1]:] = array

        else:
            raise ValueError("Only 1D or 2D arrays are supported.")

    else:
        # Create dataset with maxshape allowing unlimited growth in appropriate axis
        if array.ndim == 1:
            maxshape = (None,)
        elif array.ndim == 2:
            maxshape = (array.shape[0], None)
        else:
            raise ValueError("Only 1D or 2D arrays are supported.")

        # Need to define the chunks appropriately for fast and efficient data saving
        root.create_dataset(dataset_name, data=array, shape=array.shape, maxshape=maxshape, chunks=True)


# def reset_file(filename):
#     """
#     Check if a file with the specified name exists.
#     If it does, clear its contents; if not, create an empty file.
#     If the folder does not exist, create the necessary directories.
#     """
#     folder = os.path.dirname(filename)
#
#     # Ensure the directory exists
#     if folder and not os.path.exists(folder):
#         os.makedirs(folder)
#
#     # Create or clear the file
#     open(filename, 'w').close()

def reset_file(filename):
    """
    Reset the target path:
    - If it's a .zarr path, it is treated as a directory. If it exists, it is deleted and recreated.
    - Otherwise, it's treated as a file. If it exists, it is cleared. If not, it is created.
    In both cases, any necessary parent directories are created.
    """
    is_zarr = filename.endswith('.zarr')
    folder = filename if is_zarr else os.path.dirname(filename)

    # Ensure the parent directory exists
    if folder and not os.path.exists(folder):
        os.makedirs(folder)

    if is_zarr:
        # Handle .zarr directory store
        if os.path.exists(filename):
            shutil.rmtree(filename)
        os.makedirs(filename)
    else:
        # Handle regular file
        open(filename, 'w').close()


# =============================================================================
# pixel address
# =============================================================================
def is_addr_entry_valid(entry: str) -> bool:
    """
    Checks if entry is valid.

    Args:
        entry (str): string containing pixel address, separated by ',' if multiple.

    Returns:
        bool: True if valid, False if not.
    """
    # Regular expression to match the string format
    pattern = r'^(\d{4}(,\d{4})*)$'
    match = re.match(pattern, entry)
    if match:
        # Additional check to ensure all numbers are between 0101 and 6464
        numbers = entry.split(',')
        for number in numbers:
            row, col = int(number[:2]), int(number[2:4])
            if not (1 <= row <= 64 and 1 <= col <= 64):
                return False
        return True
    return False


def get_addr_from_string_entry(entry) -> list:
    """
    get address entry in a list.

    Args:
        entry (str): string containing address entries.

    Returns:
        list: list of pixel addresses in tuple, [(row, col), ...]
    """
    numbers = entry.split(',')
    address = []
    for number in numbers:
        row = int(number[:2])
        col = int(number[2:])
        address.append((row, col))
    return address


def tuple_to_id(addr):
    """
    Convert a tuple address to an integer pid

    Args:
        addr (tuple): tuple consisting address (row, col), range from 1 to 64

    Returns:
        pid (int): integer pid, range from 0 to 4095
    """
    pid = (addr[0]-1) * 64 + (addr[1]-1)
    return pid


def id_to_tuple(pid):
    """
    Convert integer pid to tuple address

    Args:
        pid (int): integer from 0 to 4095.

    Returns:
        addr (tuple): tuple consisting address (row, col), range from 1 to 64
    """
    addr = (pid // 64 + 1, pid % 64 + 1)
    return addr


def convert_raw_to_float(data, multiplier, offset, gain):
    data = np.multiply(data, multiplier)
    np.add(data, offset, out=data)
    np.divide(data, gain, out=data)
    if len(data.shape) > 1:
        median = np.median(data, axis=1, keepdims=True)
    else:
        median = np.median(data)
    np.subtract(data, median, out=data)
    return data
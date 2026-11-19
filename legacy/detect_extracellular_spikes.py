import h5py
from utility.data_conversion import compute_moving_average
from utility.spike_detection import *
from utility.file_read_write import append_array_to_h5, reset_file
from utility.pca import *
from os import path
from tqdm import tqdm


DIRECTORY       = "/Volumes/YZ/recording/invivo/26-11-06/0192/"
FILE_NAME       = "extra_4_signals"
FILE_TYPE       = ".h5"
OUTPUT_FOLDER   = 'spikes'
OUTPUT_NAME     = "extra_4_spikes"
OUTPUT_ENABLE   = True
num_of_channels = 2048

fs  = 10_000   # true sampling frequency is 10kHz * 100.8 / 100
DATA_SET_NAME       = 'signals'

# spike detection parameters
chunk_size      = None      # disable chunking
t_win           = 1         # window_length
refractory_ms   = 5
spike_polarity  = "neg"
threshold_factor = 5.0
moving_average_size = 200

if __name__ == "__main__":
    signal_file = path.join(DIRECTORY, FILE_NAME + FILE_TYPE)
    output_file = path.join(DIRECTORY, OUTPUT_FOLDER, OUTPUT_NAME + FILE_TYPE)
    if OUTPUT_ENABLE:
        reset_file(output_file)

    """ scan through channels parallel """
    with h5py.File(signal_file, 'r') as file:
        window_size = fs * t_win
        recording_length = file[DATA_SET_NAME].shape[1]
        num_windows = recording_length // window_size

        window_spike_count = np.zeros(num_of_channels, dtype=np.uint64)
        spike_count = np.zeros(num_of_channels, dtype=np.uint64)

        # noise_threshold = setting['noise_threshold']
        for window in tqdm(range(num_windows), desc="spike detection", unit="window"):
            signals = file[DATA_SET_NAME][:num_of_channels, window * window_size:(window + 1) * window_size]
            mva = compute_moving_average(signals, moving_average_size)

            # detect spikes
            spikes = detect_spikes(
                signals-mva, fs,
                chunk_size=chunk_size,
                polarity=spike_polarity,
                thr_k=threshold_factor,
                refractory_ms=refractory_ms,
                center=False,
                apply_median_noise=True
            )

            # accumulate spike counts
            np.sum(spikes, axis=1, dtype=np.uint64, out=window_spike_count)
            spike_count += window_spike_count

            # compress to 1ms interval (10x compression)
            # spikes_1ms_interval = compress_spikes_bin(spikes, 10)
            # spikes_5ms_interval = compress_spikes_bin(spikes, 50)
            # spikes_10ms_interval = compress_spikes_bin(spikes, 100)

            # write into file
            if OUTPUT_ENABLE:
                append_array_to_h5(output_file, spikes, 'spikes')
                # append_array_to_h5(output_file, spikes_1ms_interval, 'spikes_1ms_interval')
                # append_array_to_h5(output_file, spikes_5ms_interval, 'spikes_5ms_interval')
                # append_array_to_h5(output_file, spikes_5ms_interval, 'spikes_10ms_interval')

        # Create a boolean mask where values > 100 are True
        mask = spike_count > 100

        # Sum the True values in the mask to get the total count
        count = np.sum(mask)

        print(f'total number of channels with greater than 100 spikes: {count}')

        # write spike counts
        if OUTPUT_ENABLE:
            append_array_to_h5(output_file, spike_count, 'spike_count')

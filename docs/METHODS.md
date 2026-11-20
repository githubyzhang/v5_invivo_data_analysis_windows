# Detection methods

## Input and time convention

Converted HDF5 input has a floating-point `signals` dataset ordered `(channels, samples)`. The current source recordings have 2,048 channels and 3,000,000 samples per channel, stored as float16. Conversion is trusted; the pipeline does not reinterpret gain or calibrate ADC rails.

All event times are `sample_index / 10000`. Physical sampling is 10,080 Hz, retained in metadata. A 3,000,000-sample file is therefore 300 nominal seconds; nominal timestamps are not exact physical elapsed times.

## Baseline subtraction

The default residual is the stored signal minus its centered 50-sample moving average. For an even window, the alignment is 25 samples before the current sample, the current sample, and 24 samples after it. A compiled uniform filter implements this efficiently. MA100 and MA200 have the corresponding alignment.

Processing chunks use actual neighboring data. The practical pipeline reads 510 context samples on each side where available, sufficient for both MA200 and the clipping guard. The first 25 and final 24 samples of an MA50 recording are excluded because a complete physical moving-average window is unavailable. No artificial padding boundary is inserted between processing chunks.

A smaller MA window changes both the waveform residual and its noise estimate. It is not equivalent to the previously tested 300 Hz Butterworth high-pass filter. HP300 is not part of the default detection residual or its noise calibration.

## Noise and thresholds

For eligible residual samples `r` in a nominal second:

```text
sigma = median(abs(r - median(r))) / 0.67448975
threshold = 5 * max(sigma, median sigma across valid channels)
```

Noise estimation excludes suspected-flat guards and physical filter-edge exclusions. A window needs at least half its samples and at least 250 usable samples, with a finite positive MAD. Otherwise it is unavailable for detection. This rule also applies to a final partial second; a very short unsupported tail is explicitly unavailable rather than silently discarded.

Adaptive mode recalculates the channel noise and the across-channel median each second. The practical runner uses MA-only support. It does not require other filter estimates or quiet-reference eligibility, unlike some controlled comparison experiments.

Fixed mode loads one threshold per channel from the existing calibration for the selected MA size. That threshold already includes the reference across-channel median floor and stays constant over time. Calibration-unavailable channels are excluded. The target-window support checks remain in place as a conservative observability requirement. The source identity and calibration provenance are checked before use.

The fixed-reference study screened one-second windows in three five-second intervals per recording. It required no suspected-flat guard or shared20 warning, limited baseline movement and fast variability, at least two qualifying intervals, and a largest/smallest interval MAD ratio ≤1.5 for every tested MA filter. These choices are exploratory. Stable reference estimates can still contain persistent noise.

## Candidate selection and chunk boundaries

Local negative peaks must cross the applicable threshold. Candidates from all processing chunks are collected per channel before amplitude-priority spacing is applied across the entire recording. Peaks must be at least 50 samples apart. Equal-amplitude ties favor the earlier candidate.

This is a peak-spacing choice, not an assertion that each electrode records one neuron. It can suppress nearby events from different neurons. Tests compare chunked processing with a whole-signal reference and cover peaks on either side of a chunk/second boundary.

## Quality and observability

Exact repeated stored values lasting at least 10 samples are marked per channel. Their intervals are expanded by 500 samples on each side. Such guards exclude samples from noise estimation and detection. They are a clipping proxy: float16 quantization, disconnected channels or missing data can also cause flatness. Information lost during real clipping is not reconstructed.

Shared-disturbance research combined same-sign baseline changes and high-pass excursions across many eligible channels, with 10 or 20 ms padding. These flags mean that a candidate warrants disturbance review, not that it is a proven false spike.

The full runner imports the existing frozen 10/20 ms annotations only for intervals already evaluated. Their source metadata and mask agreement are checked. Other times have `shared_warning_available = false`; a false warning flag there must not be interpreted as a clean-data finding. No global warning removes candidates by default. Full-recording shared-disturbance evaluation is deferred and clearly distinguished from completed spike detection.

Fast-noise warning experiments did not provide reliable cleanup. No fast-noise subtraction, automatic local-warning exclusion, or stimulation-artifact correction is enabled.

## Saved candidates and validation

The runner makes two bounded-memory passes: noise/observability estimation, then threshold crossing and global peak spacing. It does not load the whole recording into memory. Final HDF5 output is published only after validating indices, ordering, spacing, thresholds, observability, flat-guard exclusion and shared-warning annotations. Source size and modification time must remain unchanged during the run.

Saved events are candidate eAPs. Waveform labels are expert judgments on selected examples; no ground-truth sensitivity, precision or unit identity has been established. Waveforms are not embedded in the output and can be retrieved from the source using sample indices.

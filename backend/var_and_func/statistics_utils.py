"""
Extended statistical calculations for OrcaFlex time-history data.

Adds secondary statistics beyond the basic max/min/mean/std already provided
by ``calculate_statistics_summary`` in ``time_history.py``:

- Frequency distribution (histogram) of a variable's values
- Skewness and kurtosis (distribution shape)
- RMS and significant value (average of the highest 1/3 of peaks)
- Frequency-domain (power spectral density) analysis of a time history

These operate on plain pandas Series / numpy arrays, so they work with the
output of any extraction function in this package (time history, multi-object,
range graph, etc.) and are shared by both the Flask API and the Streamlit app.
"""
import numpy as np
import pandas as pd
from scipy.signal import find_peaks, welch


def compute_histogram(values, bins=50):
    """Compute a frequency distribution (histogram) for a 1D array of values.

    Args:
        values: Array-like of numeric values (NaNs are dropped).
        bins: Number of histogram bins, or explicit bin-edges array.

    Returns:
        dict with:
            bin_edges: bin edge values (length = n_bins + 1)
            bin_centers: bin center values (length = n_bins)
            counts: raw count per bin
            density: probability density per bin (integrates to 1)
    """
    clean = pd.to_numeric(pd.Series(values), errors='coerce').dropna().to_numpy()
    if clean.size == 0:
        return {'bin_edges': [], 'bin_centers': [], 'counts': [], 'density': []}

    counts, edges = np.histogram(clean, bins=bins)
    density, _ = np.histogram(clean, bins=edges, density=True)
    centers = (edges[:-1] + edges[1:]) / 2

    return {
        'bin_edges': edges.tolist(),
        'bin_centers': centers.tolist(),
        'counts': counts.tolist(),
        'density': density.tolist(),
    }


def compute_significant_value(values):
    """Average of the highest 1/3 of local peaks (offshore-engineering convention).

    Mirrors the significant-wave-height style definition (H_1/3): detect local
    maxima in the signal, then average the top third of them. Falls back to
    4 * RMS (the standard narrow-band Gaussian approximation) when fewer than
    3 peaks are found, e.g. very short or near-constant series.
    """
    clean = pd.to_numeric(pd.Series(values), errors='coerce').dropna().to_numpy()
    if clean.size < 3:
        return float('nan')

    peak_idx, _ = find_peaks(clean)
    peaks = clean[peak_idx]

    if peaks.size < 3:
        rms = float(np.sqrt(np.mean(np.square(clean))))
        return 4.0 * rms

    top_third_n = max(1, len(peaks) // 3)
    top_peaks = np.sort(peaks)[-top_third_n:]
    return float(np.mean(top_peaks))


def compute_extended_statistics(values):
    """Compute extended descriptive statistics for a 1D array of values.

    Adds RMS, significant value, skewness, and kurtosis on top of the
    max/min/mean/std already covered by ``calculate_statistics_summary``.

    Returns:
        dict with keys: rms, significant_value, skewness, kurtosis
        (kurtosis is *excess* kurtosis, where 0 = normal distribution)
    """
    series = pd.to_numeric(pd.Series(values), errors='coerce').dropna()
    if series.empty or len(series) < 2:
        return {'rms': None, 'significant_value': None, 'skewness': None, 'kurtosis': None}

    rms = float(np.sqrt(np.mean(np.square(series.to_numpy()))))

    return {
        'rms': round(rms, 4),
        'significant_value': round(compute_significant_value(series.to_numpy()), 4),
        'skewness': round(float(series.skew()), 4),
        'kurtosis': round(float(series.kurt()), 4),
    }


def compute_extended_statistics_summary(data_df, variable_name=""):
    """Extended companion to ``calculate_statistics_summary`` in time_history.py.

    Args:
        data_df: DataFrame with a 'Time' column and one column per object.
        variable_name: Optional variable name, used to label columns.

    Returns:
        DataFrame with columns: Object, RMS, Significant Value, Skewness, Kurtosis
    """
    suffix = f" ({variable_name})" if variable_name else ""
    columns = [
        'Object',
        f'RMS{suffix}',
        f'Significant Value{suffix}',
        f'Skewness{suffix}',
        f'Kurtosis{suffix}',
    ]

    if data_df is None or data_df.empty:
        return pd.DataFrame(columns=columns)

    object_columns = [c for c in data_df.columns if c != 'Time']
    rows = []
    for col in object_columns:
        stats = compute_extended_statistics(data_df[col])
        rows.append({
            'Object': col,
            f'RMS{suffix}': stats['rms'],
            f'Significant Value{suffix}': stats['significant_value'],
            f'Skewness{suffix}': stats['skewness'],
            f'Kurtosis{suffix}': stats['kurtosis'],
        })

    return pd.DataFrame(rows, columns=columns)


def compute_power_spectral_density(time_values, signal_values, nperseg=None):
    """Estimate the power spectral density (PSD) of a time-domain signal.

    Uses Welch's method for a smoothed spectral estimate. This is a
    post-processing FFT-based analysis of time-domain simulation results,
    distinct from OrcFxAPI's native frequency-domain *analysis type*
    (``GetFrequencyDomainTimeHistory``), which requires the model itself to
    have been solved in the frequency domain. This function works on the
    output of any time-domain extraction (e.g. ``TimeHistory``) regardless
    of how the simulation was solved.

    Args:
        time_values: Array-like of time stamps in seconds (assumed ~uniformly sampled).
        signal_values: Array-like of the variable's values at each time stamp.
        nperseg: Segment length for Welch's method; defaults to min(256, n_samples).

    Returns:
        dict with:
            frequency: frequency bins in Hz
            psd: PSD estimate per bin (units^2/Hz)
            peak_frequency: frequency (Hz) at maximum PSD, or None
            peak_period: 1 / peak_frequency in seconds, or None
    """
    time_arr = np.asarray(time_values, dtype=float)
    signal_arr = pd.to_numeric(pd.Series(signal_values), errors='coerce').to_numpy()

    valid = ~np.isnan(signal_arr)
    time_arr, signal_arr = time_arr[valid], signal_arr[valid]

    if signal_arr.size < 4:
        return {'frequency': [], 'psd': [], 'peak_frequency': None, 'peak_period': None}

    dt = float(np.median(np.diff(time_arr))) if time_arr.size > 1 else 0.0
    if not np.isfinite(dt) or dt <= 0:
        return {'frequency': [], 'psd': [], 'peak_frequency': None, 'peak_period': None}

    sample_rate = 1.0 / dt
    segment_length = min(nperseg or 256, signal_arr.size)

    freq, psd = welch(signal_arr, fs=sample_rate, nperseg=segment_length)

    if psd.size == 0:
        return {'frequency': [], 'psd': [], 'peak_frequency': None, 'peak_period': None}

    peak_idx = int(np.argmax(psd))
    peak_frequency = float(freq[peak_idx])
    peak_period = (1.0 / peak_frequency) if peak_frequency > 0 else None

    return {
        'frequency': freq.tolist(),
        'psd': psd.tolist(),
        'peak_frequency': peak_frequency,
        'peak_period': peak_period,
    }

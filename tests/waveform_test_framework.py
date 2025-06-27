#!/usr/bin/env python3
"""
Waveform testing framework for transient analysis.

Provides utilities for comparing waveforms with interpolation, plotting,
and golden file management for time-domain simulations.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Tuple, Optional, Union
import unittest


class WaveformTestFramework:
    """Framework for waveform testing with golden file support."""
    
    def __init__(self, test_case: unittest.TestCase):
        """Initialize with reference to test case for assertions."""
        self.test_case = test_case
        self.golden_dir = Path(os.path.dirname(__file__)) / "golden_waveforms"
        self.plots_dir = Path(os.path.dirname(__file__)) / "generated_plots"
        
        # Create directories if they don't exist
        self.golden_dir.mkdir(exist_ok=True)
        self.plots_dir.mkdir(exist_ok=True)
    
    def compare_waveform_against_file(self, golden_file: str, x_values: np.ndarray, 
                                    values: Union[np.ndarray, List[np.ndarray]], 
                                    trace_names: Tuple[str, ...] = ('V(output)',),
                                    update_golden: bool = False) -> None:
        """
        Compare waveform against golden file, with automatic creation if missing.
        
        Args:
            golden_file: Name of the golden file (will be saved in golden_waveforms/)
            x_values: X-axis values (typically time)
            values: Y-axis values (single array or list of arrays for multiple traces)
            trace_names: Names for each trace
            update_golden: If True, update the golden file with current data
        """
        # Ensure values is a list of arrays
        if isinstance(values, np.ndarray):
            values = [values]
        
        # Create DataFrame with current data
        data_dict = {'x': x_values}
        for name, value_array in zip(trace_names, values):
            data_dict[name] = value_array
        actual_df = pd.DataFrame(data_dict)
        
        golden_path = self.golden_dir / golden_file
        
        if update_golden or not golden_path.exists():
            # Save current data as golden file
            actual_df.to_csv(golden_path, index=False)
            if not golden_path.exists():
                self.test_case.fail(f"Golden waveform file {golden_file} created. Run test again to validate.")
            return
        
        # Load expected data and compare
        expected_df = pd.read_csv(golden_path)
        
        # Compare each trace
        for name in trace_names:
            if name not in expected_df.columns:
                self.test_case.fail(f"Trace {name} not found in golden file {golden_file}")
            
            self.assert_waveforms_close(
                x_values, actual_df[name].values,
                expected_df['x'].values, expected_df[name].values,
                tolerance=1e-3, trace_name=name
            )
    
    def resample_waveforms(self, time1: np.ndarray, values1: np.ndarray, 
                          time2: np.ndarray, values2: np.ndarray, 
                          num_points: int = 1000) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Resample two waveforms onto a common time grid using linear interpolation.
        
        Args:
            time1: Time points of the first waveform
            values1: Values of the first waveform
            time2: Time points of the second waveform
            values2: Values of the second waveform
            num_points: Number of points for the common time grid
            
        Returns:
            common_time: Common time grid
            resampled1: Resampled values for the first waveform
            resampled2: Resampled values for the second waveform
        """
        t_min = max(min(time1), min(time2))  # Start from latest start time
        t_max = min(max(time1), max(time2))  # End at earliest end time
        
        common_time = np.linspace(t_min, t_max, num_points)
        resampled1 = np.interp(common_time, time1, values1)
        resampled2 = np.interp(common_time, time2, values2)
        
        return common_time, resampled1, resampled2
    
    def compare_waveforms(self, values1: np.ndarray, values2: np.ndarray, 
                         tolerance: float = 1e-3, method: str = "mse") -> Tuple[bool, float]:
        """
        Compare two resampled waveforms within a specified tolerance.
        
        Args:
            values1: Resampled values of the first waveform
            values2: Resampled values of the second waveform
            tolerance: Allowed tolerance for comparison
            method: Method for comparison ("mse", "max_diff", or "area_diff")
            
        Returns:
            is_close: Boolean indicating whether the waveforms are within tolerance
            metric: Calculated metric value used for comparison
        """
        if method == "mse":
            metric = np.mean((values1 - values2) ** 2)
        elif method == "max_diff":
            metric = np.max(np.abs(values1 - values2))
        elif method == "area_diff":
            metric = np.trapz(np.abs(values1 - values2))
        else:
            raise ValueError(f"Unknown comparison method: {method}")
        
        is_close = metric <= tolerance
        return is_close, metric
    
    def assert_waveforms_close(self, time1: np.ndarray, values1: np.ndarray,
                              time2: np.ndarray, values2: np.ndarray,
                              tolerance: float = 1e-3, method: str = "mse",
                              trace_name: str = "waveform") -> Tuple[bool, float]:
        """
        Assert that two waveforms are close within a specified tolerance.
        
        Args:
            time1: Time points of the first waveform
            values1: Values of the first waveform
            time2: Time points of the second waveform  
            values2: Values of the second waveform
            tolerance: Allowed tolerance for comparison
            method: Method for comparison ("mse", "max_diff", or "area_diff")
            trace_name: Name of the trace for error messages
            
        Returns:
            is_close: Boolean indicating success
            metric: Calculated metric value
            
        Raises:
            AssertionError if the waveforms are not close within tolerance
        """
        common_time, resampled1, resampled2 = self.resample_waveforms(time1, values1, time2, values2)
        is_close, metric = self.compare_waveforms(resampled1, resampled2, tolerance, method)
        
        if not is_close:
            self.test_case.fail(
                f"Waveforms for {trace_name} are not close! "
                f"Metric ({method}) = {metric:.6f}, Tolerance = {tolerance}"
            )
        
        return is_close, metric
    
    def plot_transient(self, times: np.ndarray, traces: List[np.ndarray], 
                      value_names: Tuple[str, ...] = ('V(output)',),
                      title: str = "Transient Analysis",
                      save_as: Optional[str] = None,
                      show_plot: bool = True) -> None:
        """
        Plot transient analysis results.
        
        Args:
            times: Time values
            traces: List of voltage/current traces
            value_names: Names for each trace
            title: Plot title
            save_as: Filename to save plot (optional)
            show_plot: Whether to display the plot
        """
        plt.figure(figsize=(10, 6))
        
        for trace, name in zip(traces, value_names):
            plt.plot(times, trace, label=name, linewidth=2)
        
        plt.xlabel('Time (s)')
        plt.ylabel('Voltage (V)')
        plt.title(title)
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        if save_as:
            save_path = self.plots_dir / save_as
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Plot saved to: {save_path}")
        
        if show_plot:
            plt.show()
        else:
            plt.close()
    
    def plot_dc_sweep(self, v1: np.ndarray, traces: List[np.ndarray],
                     value_names: Tuple[str, ...] = ('V(output)',),
                     title: str = "DC Sweep Analysis",
                     save_as: Optional[str] = None,
                     show_plot: bool = True) -> None:
        """
        Plot DC sweep analysis results.
        
        Args:
            v1: Sweep voltage values
            traces: List of output traces
            value_names: Names for each trace
            title: Plot title
            save_as: Filename to save plot (optional)
            show_plot: Whether to display the plot
        """
        plt.figure(figsize=(10, 6))
        
        for trace, name in zip(traces, value_names):
            plt.plot(v1, trace, label=name, linewidth=2)
        
        plt.xlabel('Input Voltage (V)')
        plt.ylabel('Output Voltage (V)')
        plt.title(title)
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        if save_as:
            save_path = self.plots_dir / save_as
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Plot saved to: {save_path}")
        
        if show_plot:
            plt.show()
        else:
            plt.close()


class WaveformTestMixin:
    """Mixin class to add waveform testing capabilities to test cases."""
    
    def setUp(self):
        """Set up waveform test framework."""
        super().setUp()
        self.waveform = WaveformTestFramework(self)
        # Check environment variable for updating golden waveforms
        self.update_golden_waveforms = os.environ.get('UPDATE_GOLDEN_WAVEFORMS', '').lower() in ('1', 'true', 'yes')
    
    def assert_waveform_matches_golden(self, golden_file: str, x_values: np.ndarray,
                                     values: Union[np.ndarray, List[np.ndarray]],
                                     trace_names: Tuple[str, ...] = ('V(output)',)) -> None:
        """Helper to compare waveform against golden file."""
        self.waveform.compare_waveform_against_file(
            golden_file, x_values, values, trace_names, self.update_golden_waveforms
        )
    
    def plot_and_save_transient(self, times: np.ndarray, traces: List[np.ndarray],
                               value_names: Tuple[str, ...] = ('V(output)',),
                               title: str = "Transient Analysis",
                               filename: str = "transient_plot.png") -> None:
        """Helper to plot and save transient results."""
        self.waveform.plot_transient(times, traces, value_names, title, filename, show_plot=True) 
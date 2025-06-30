#!/usr/bin/env python3
"""
Waveform testing framework for transient analysis.

Provides utilities for comparing waveforms with interpolation, plotting,
and golden file management for time-domain simulations.
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Tuple, Optional, Union
import unittest
from .unified_plotting_mixin import UnifiedPlottingMixin


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
        
        # Detect verbose mode for unified plotting behavior
        self.verbose_mode = '-v' in sys.argv or '--verbose' in sys.argv
    
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
        
        # Compare each trace, with comparison plot on failure in verbose mode
        try:
            for name in trace_names:
                if name not in expected_df.columns:
                    self.test_case.fail(f"Trace {name} not found in golden file {golden_file}")
                
                self.assert_waveforms_close(
                    x_values, actual_df[name].values,
                    expected_df['x'].values, expected_df[name].values,
                    tolerance=1e-3, trace_name=name, golden_file=golden_file
                )
        except Exception as e:
            # If comparison fails and we're in verbose mode, create a comparison plot
            if self.verbose_mode:
                self._create_comparison_plot_on_failure(
                    golden_file, x_values, values, trace_names, 
                    expected_df, actual_df
                )
            # Re-raise the exception to maintain normal test failure behavior
            raise e
    
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
                              trace_name: str = "waveform", golden_file: str = None) -> Tuple[bool, float]:
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
            golden_file: Name of the golden file being compared against (optional)
            
        Returns:
            is_close: Boolean indicating success
            metric: Calculated metric value
            
        Raises:
            AssertionError if the waveforms are not close within tolerance
        """
        common_time, resampled1, resampled2 = self.resample_waveforms(time1, values1, time2, values2)
        is_close, metric = self.compare_waveforms(resampled1, resampled2, tolerance, method)
        
        if not is_close:
            golden_info = f" (from {golden_file})" if golden_file else ""
            self.test_case.fail(
                f"Waveforms for {trace_name}{golden_info} are not close! "
                f"Metric ({method}) = {metric:.6f}, Tolerance = {tolerance}"
            )
        
        return is_close, metric
    
    def _create_comparison_plot_on_failure(self, golden_file: str, x_values: np.ndarray,
                                         actual_values: Union[np.ndarray, List[np.ndarray]],
                                         trace_names: Tuple[str, ...],
                                         expected_df: pd.DataFrame,
                                         actual_df: pd.DataFrame) -> None:
        """
        Create a comparison plot showing both actual and expected waveforms when validation fails.
        
        Args:
            golden_file: Name of the golden file
            x_values: X-axis values (typically time)
            actual_values: Actual waveform values
            trace_names: Names for each trace
            expected_df: DataFrame with expected (golden) data
            actual_df: DataFrame with actual data
        """
        print(f"\n🔍 COMPARISON FAILURE: Creating comparison plot for {golden_file}")
        
        # Ensure actual_values is a list
        if isinstance(actual_values, np.ndarray):
            actual_values = [actual_values]
        
        # Create comparison plot
        fig = plt.figure(figsize=(12, 8))
        
        # Plot each trace comparison
        for i, name in enumerate(trace_names):
            if name in expected_df.columns and i < len(actual_values):
                # Get expected and actual data
                expected_x = expected_df['x'].values
                expected_y = expected_df[name].values
                actual_x = x_values
                actual_y = actual_values[i]
                
                # Plot expected (golden) waveform
                plt.plot(expected_x, expected_y, 
                        label=f'{name} (Expected - Golden)', 
                        linewidth=2.5, linestyle='-', alpha=0.8)
                
                # Plot actual (received) waveform
                plt.plot(actual_x, actual_y, 
                        label=f'{name} (Actual - Received)', 
                        linewidth=2, linestyle='--', alpha=0.9)
        
        plt.xlabel('Time (s)')
        plt.ylabel('Voltage (V)')
        plt.title(f'COMPARISON FAILURE: Expected vs Actual Waveforms ({golden_file})')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Add text box with failure information
        textstr = f'❌ Validation Failed\n📁 Golden File: {golden_file}\n📊 Traces: {", ".join(trace_names)}'
        props = dict(boxstyle='round', facecolor='lightcoral', alpha=0.8)
        plt.text(0.02, 0.98, textstr, transform=plt.gca().transAxes, fontsize=10,
                verticalalignment='top', bbox=props)
        
        # Save the comparison plot
        comparison_filename = golden_file.replace('.csv', '_comparison_failure.png')
        save_path = self.plots_dir / comparison_filename
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"📊 Comparison plot saved to: {save_path}")
        
        # Show the plot in verbose mode
        if self.verbose_mode:
            plt.show(block=True)
            print(f"🔍 Displaying comparison plot: Expected vs Actual waveforms for {golden_file}")
        else:
            plt.close(fig)
    
    def plot_transient(self, times: np.ndarray, traces: List[np.ndarray], 
                      value_names: Tuple[str, ...] = ('V(output)',),
                      title: str = "Transient Analysis",
                      save_as: Optional[str] = None,
                      show_plot: Optional[bool] = None) -> None:
        """
        Plot transient analysis results using unified plotting approach.
        
        Args:
            times: Time values
            traces: List of voltage/current traces
            value_names: Names for each trace
            title: Plot title
            save_as: Filename to save plot (optional)
            show_plot: Whether to display the plot (None = auto-detect from verbose mode)
        """
        fig = plt.figure(figsize=(10, 6))
        
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
        
        # Use unified plotting behavior
        if show_plot is None:
            show_plot = self.verbose_mode
        
        if show_plot:
            plt.show(block=True)
        else:
            plt.close(fig)
    
    def plot_dc_sweep(self, v1: np.ndarray, traces: List[np.ndarray],
                     value_names: Tuple[str, ...] = ('V(output)',),
                     title: str = "DC Sweep Analysis",
                     save_as: Optional[str] = None,
                     show_plot: Optional[bool] = None) -> None:
        """
        Plot DC sweep analysis results using unified plotting approach.
        
        Args:
            v1: Sweep voltage values
            traces: List of output traces
            value_names: Names for each trace
            title: Plot title
            save_as: Filename to save plot (optional)
            show_plot: Whether to display the plot (None = auto-detect from verbose mode)
        """
        fig = plt.figure(figsize=(10, 6))
        
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
        
        # Use unified plotting behavior
        if show_plot is None:
            show_plot = self.verbose_mode
        
        if show_plot:
            plt.show(block=True)
        else:
            plt.close(fig)


class WaveformTestMixin(UnifiedPlottingMixin):
    """Mixin class to add waveform testing capabilities to test cases."""
    
    def setUp(self):
        """Set up waveform test framework."""
        super().setUp()
        self.waveform = WaveformTestFramework(self)
        # Check environment variable for updating golden waveforms
        self.update_golden_waveforms = os.environ.get('UPDATE_GOLDEN_WAVEFORMS', '').lower() in ('1', 'true', 'yes')
    
    def assert_waveform_matches_golden(self, golden_file: str, x_values: np.ndarray,
                                     values: Union[np.ndarray, List[np.ndarray]],
                                     trace_names: Tuple[str, ...] = ('V(output)',),
                                     auto_plot: bool = True,
                                     plot_title: Optional[str] = None) -> None:
        """
        Helper to compare waveform against golden file with integrated plotting.
        
        Args:
            golden_file: Name of the golden file to compare against
            x_values: X-axis values (typically time)
            values: Y-axis values (single array or list of arrays for multiple traces)
            trace_names: Names for each trace
            auto_plot: Whether to automatically plot the waveform (default: True)
            plot_title: Custom title for the plot (if None, auto-generated from golden_file)
        """
        # First, plot the waveform if requested (BEFORE comparison)
        # This ensures we get visual feedback even if the comparison fails
        if auto_plot:
            # Ensure values is a list for consistent handling
            if isinstance(values, np.ndarray):
                values_list = [values]
            else:
                values_list = values
            
            # Generate plot title from golden file name if not provided
            if plot_title is None:
                # Convert golden file name to a readable title
                # e.g., "rc_charging_1k_1uF.csv" -> "RC Charging 1k 1uF - Golden Waveform"
                base_name = golden_file.replace('.csv', '').replace('_', ' ').title()
                plot_title = f"{base_name} - Golden Waveform Validation"
            else:
                # If custom title provided, still include the golden file name
                plot_title = f"{plot_title} ({golden_file})"
            
            # Generate plot filename from golden file name
            plot_filename = golden_file.replace('.csv', '_golden_validation.png')
            
            # Plot using the unified plotting system
            self.create_simple_plot(
                x_values, values_list, trace_names, 
                plot_title, plot_filename
            )
            
            # Print informative message about the plot
            print(f"📊 Waveform plot saved as: {plot_filename}")
        
        # Then, compare against golden file (after plotting)
        self.waveform.compare_waveform_against_file(
            golden_file, x_values, values, trace_names, self.update_golden_waveforms
        )
        
        # Print validation success message only if we get here (no exception thrown)
        print(f"✓ Golden waveform validation completed for: {golden_file}")
    
    def plot_and_save_transient(self, times: np.ndarray, traces: List[np.ndarray],
                               value_names: Tuple[str, ...] = ('V(output)',),
                               title: str = "Transient Analysis",
                               filename: str = "transient_plot.png") -> str:
        """Helper to plot and save transient results using unified plotting."""
        return self.create_simple_plot(times, traces, value_names, title, filename) 
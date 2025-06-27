#!/usr/bin/env python3
"""
Unified plotting mixin for test files.

Provides consistent plotting behavior across all test files:
- Always saves plots to generated_plots/ directory
- Conditionally displays plots based on verbose mode (-v flag)
- Handles memory management to prevent matplotlib accumulation
"""

import os
import sys
import matplotlib.pyplot as plt
from typing import Callable, Optional, List, Tuple


class UnifiedPlottingMixin:
    """Mixin class to add unified plotting capabilities to test cases."""
    
    def setUp(self):
        """Set up unified plotting framework."""
        super().setUp()
        
        # Detect if running in verbose mode
        self.verbose_mode = '-v' in sys.argv or '--verbose' in sys.argv
        
        # Set up plots directory
        self.plots_dir = os.path.join(os.path.dirname(__file__), "generated_plots")
        os.makedirs(self.plots_dir, exist_ok=True)
    
    def create_and_show_plot(self, plot_func: Callable[[], plt.Figure], 
                           filename: str, title: str = "Circuit Analysis") -> str:
        """
        Unified plotting method that handles saving and conditional display.
        
        Args:
            plot_func: Function that creates the plot (should return the figure)
            filename: Name of the file to save (will be saved in generated_plots/)
            title: Title for the plot window
            
        Returns:
            plot_path: Path to the saved plot file
        """
        # Create the plot
        fig = plot_func()
        
        # Always save the plot
        plot_path = os.path.join(self.plots_dir, filename)
        fig.savefig(plot_path, dpi=150, bbox_inches='tight')
        print(f"Plot saved to: {plot_path}")
        
        # Conditionally display the plot based on verbose mode
        if self.verbose_mode:
            print(f"Displaying plot: {title}")
            plt.show(block=True)  # Block for user interaction in verbose mode
        else:
            # In non-verbose mode, just ensure plots don't accumulate in memory
            plt.close(fig)
        
        return plot_path
    
    def create_simple_plot(self, times, traces, value_names, title: str, filename: str,
                          xlabel: str = "Time (s)", ylabel: str = "Voltage (V)",
                          figsize: tuple = (10, 6)) -> str:
        """
        Create a simple line plot with the unified plotting system.
        
        Args:
            times: X-axis data (time values)
            traces: List of Y-axis data arrays (voltage traces)
            value_names: Names for each trace
            title: Plot title
            filename: Filename to save
            xlabel: X-axis label
            ylabel: Y-axis label
            figsize: Figure size tuple
            
        Returns:
            plot_path: Path to the saved plot file
        """
        def create_plot():
            fig = plt.figure(figsize=figsize)
            
            for trace, name in zip(traces, value_names):
                plt.plot(times, trace, label=name, linewidth=2)
            
            plt.xlabel(xlabel)
            plt.ylabel(ylabel)
            plt.title(title)
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            return fig
        
        return self.create_and_show_plot(create_plot, filename, title) 
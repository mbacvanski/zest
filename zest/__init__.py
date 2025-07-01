"""
Zest: A Pythonic Object-Oriented Wrapper for PySpice

Zest makes circuit building intuitive with auto-naming, auto-registration,
and terminal-based connections for clean, readable circuit descriptions.
"""

from .circuit import Circuit, CircuitRoot, SubCircuitDef, SubCircuitInst, NetlistBlock, NodeMapper
from .components import Component, Terminal, GroundTerminal, VoltageSource, PiecewiseLinearVoltageSource, PulsedVoltageSource, Resistor, Capacitor, Inductor, SubCircuit, CurrentSource, ExternalSubCircuit, gnd
from .simulation import CircuitSimulator, SimulatedCircuit, check_simulation_requirements, SimulatorBackend, SpicelibBackend

__version__ = "0.1.0"

# Utility functions
def cleanup_temp_files(directory="temp_spice_sim", dry_run=False, verbose=False):
    """
    Clean up temporary SPICE simulation files.
    
    Args:
        directory: Directory to clean (default: temp_spice_sim)
        dry_run: If True, just show what would be deleted without deleting
        verbose: If True, show detailed output
    
    Returns:
        tuple: (files_found, files_deleted)
        
    Example:
        >>> import zest
        >>> zest.cleanup_temp_files()  # Clean temp files
        >>> zest.cleanup_temp_files(dry_run=True)  # Show what would be cleaned
    """
    import os
    import glob
    
    if not os.path.exists(directory):
        if verbose:
            print(f"📁 Directory {directory} doesn't exist - nothing to clean")
        return 0, 0
    
    # File patterns to clean up
    patterns = ["*.net", "*.fail", "*.raw", "*.log"]
    
    # Use set to avoid duplicates from overlapping patterns
    files_to_delete = set()
    for pattern in patterns:
        files_to_delete.update(glob.glob(os.path.join(directory, pattern)))
    
    # Convert back to sorted list
    files_to_delete = sorted(list(files_to_delete))
    files_found = len(files_to_delete)
    
    if files_found == 0:
        if verbose:
            print(f"✅ Directory {directory} is already clean")
        return 0, 0
    
    if verbose:
        print(f"🧹 Found {files_found} temporary files in {directory}:")
    
    files_deleted = 0
    for file_path in files_to_delete:
        file_name = os.path.basename(file_path)
        
        # Check if file still exists (might have been deleted by previous pattern)
        if not os.path.exists(file_path):
            continue
            
        file_size = os.path.getsize(file_path)
        
        if dry_run:
            if verbose:
                print(f"   📄 Would delete: {file_name} ({file_size} bytes)")
        else:
            try:
                os.remove(file_path)
                if verbose:
                    print(f"   ✅ Deleted: {file_name} ({file_size} bytes)")
                files_deleted += 1
            except OSError as e:
                if verbose:
                    print(f"   ❌ Failed to delete {file_name}: {e}")
    
    if verbose:
        if dry_run:
            print(f"🔍 Dry run complete - {files_found} files would be deleted")
        else:
            print(f"✅ Cleanup complete - {files_deleted}/{files_found} files deleted")
    
    return files_found, files_deleted

__all__ = [
    # Core circuit classes
    "Circuit", "CircuitRoot", "SubCircuitDef", "SubCircuitInst", "NetlistBlock", "NodeMapper",
    # Component classes
    "Component", "Terminal", "GroundTerminal", "VoltageSource", "PiecewiseLinearVoltageSource", "PulsedVoltageSource", "Resistor", "Capacitor", "Inductor", "SubCircuit", "CurrentSource", "ExternalSubCircuit",
    # Ground reference
    "gnd",
    # Simulation classes
    "CircuitSimulator", "SimulatedCircuit", "check_simulation_requirements", "SimulatorBackend", "SpicelibBackend",
    # Utilities
    "cleanup_temp_files"
] 
"""
Simulation capabilities for Zest circuits using spicelib/NGspice.
"""

import numpy as np
from pathlib import Path
import tempfile
from abc import ABC, abstractmethod

# PySpice imports removed - now using SpicelibBackend exclusively


class SimulatorBackend(ABC):
    """
    Abstract base class for circuit simulation backends.
    
    This defines the interface that all simulation backends must implement.
    """
    
    @abstractmethod
    def run(self, netlist: str, analyses: list[str], **kwargs):
        """
        Run simulation analyses on a SPICE netlist.
        
        Args:
            netlist: Complete SPICE netlist string
            analyses: List of analysis types (e.g., ["op"], ["transient"], etc.)
            **kwargs: Additional simulation parameters
            
        Returns:
            SimulatedCircuit: Simulation results
        """
        pass



class SpicelibBackend(SimulatorBackend):
    """
    Simulation backend using spicelib with NGspice.
    
    This backend generates SPICE netlists and runs them through NGspice
    using the spicelib library, which provides clean access to simulation results.
    """
    
    def run(self, netlist: str, analyses: list[str], **kwargs):
        """
        Run simulation analyses using spicelib with NGspice.
        
        Args:
            netlist: Complete SPICE netlist string
            analyses: List of analysis types (currently supports 'transient')
            **kwargs: Additional simulation parameters like step_time, end_time, etc.
                     keep_temp_files: Boolean to keep temporary files for debugging (default: False)
            
        Returns:
            SimulatedCircuit: Simulation results
        """
        try:
            from spicelib import SimRunner, RawRead
            from spicelib.simulators.ngspice_simulator import NGspiceSimulator
            import tempfile
            import os
            
            # Add analysis commands to netlist based on requested analyses
            modified_netlist = self._add_analysis_commands(netlist, analyses, **kwargs)
            
            # Create temporary netlist file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.net', delete=False) as f:
                f.write(modified_netlist)
                netlist_file = f.name
            
            # Variable to track output files for cleanup
            result = None
            raw_file = None
            
            try:
                # Create spicelib runner with consistent output folder
                import os
                # Use absolute path to ensure consistent temp directory regardless of working directory
                output_folder = os.path.join(os.getcwd(), 'temp_spice_sim')
                # If we're in a subdirectory (like tests/), go up to project root
                if os.path.basename(os.getcwd()) == 'tests':
                    output_folder = os.path.join(os.path.dirname(os.getcwd()), 'temp_spice_sim')
                
                runner = SimRunner(simulator=NGspiceSimulator, output_folder=output_folder)
                
                # Run simulation
                result = runner.run_now(netlist_file)
                
                if not result or not result[0]:
                    raise RuntimeError("Simulation failed: no results returned")
                
                # Read simulation results
                raw_file = result[0]
                raw_data = RawRead(raw_file)
                
                # Get available traces
                trace_names = raw_data.get_trace_names()
                
                # Extract time vector (common to all analyses)
                time_trace = None
                if 'time' in trace_names:
                    time_trace = raw_data.get_trace('time')
                
                # Create SimulatedCircuit result
                # Map analysis types to expected format
                analysis_type_map = {
                    'transient': 'Transient Analysis',
                    'ac': 'AC Analysis', 
                    'dc': 'DC Sweep',
                    'op': 'DC Operating Point'
                }
                analysis_type = analysis_type_map.get(analyses[0], 'Transient Analysis') if analyses else 'Transient Analysis'
                
                return SimulatedCircuit(
                    circuit=kwargs.get('circuit', None),  # Pass circuit for node name resolution
                    analysis_type=analysis_type,
                    time=time_trace.data if time_trace else None,
                    raw_data=raw_data,  # Store raw data for node voltage extraction
                    trace_names=trace_names
                )
                
            finally:
                # Clean up temporary files (unless user wants to keep them for debugging)
                keep_temp_files = kwargs.get('keep_temp_files', False)
                debug_cleanup = kwargs.get('debug_cleanup', False)
                
                if not keep_temp_files:
                    files_to_clean = [netlist_file]
                    
                    # Add output files from spicelib simulation
                    if result and result[0]:
                        raw_file_path = str(result[0])
                        files_to_clean.append(raw_file_path)  # Convert Path to string
                        
                        # Also clean up the corresponding .log file
                        log_file = raw_file_path.replace('.raw', '.log')
                        if os.path.exists(log_file):
                            files_to_clean.append(log_file)
                            
                        # Also clean up the corresponding .net file in the output directory
                        net_file = raw_file_path.replace('.raw', '.net')
                        if os.path.exists(net_file):
                            files_to_clean.append(net_file)
                    
                    # Look for any .fail files from failed simulations (common pattern: tmpXXXXXX_1.fail)
                    base_name = os.path.splitext(os.path.basename(netlist_file))[0]  # Get tmp part without extension
                    output_folder = os.path.join(os.getcwd(), 'temp_spice_sim')
                    if os.path.basename(os.getcwd()) == 'tests':
                        output_folder = os.path.join(os.path.dirname(os.getcwd()), 'temp_spice_sim')
                    
                    # Check for .fail files with similar naming pattern
                    import glob
                    fail_pattern = os.path.join(output_folder, f"{base_name}*.fail")
                    fail_files = glob.glob(fail_pattern)
                    files_to_clean.extend(fail_files)
                    
                    if debug_cleanup:
                        print(f"🧹 Cleanup: Found {len(files_to_clean)} files to clean:")
                        for f in files_to_clean:
                            print(f"  - {f} (exists: {os.path.exists(f)})")
                    
                    # Clean up all temporary files
                    cleaned_count = 0
                    for file_path in files_to_clean:
                        if os.path.exists(file_path):
                            try:
                                os.unlink(file_path)
                                cleaned_count += 1
                                if debug_cleanup:
                                    print(f"  ✅ Cleaned: {file_path}")
                            except OSError as e:
                                if debug_cleanup:
                                    print(f"  ❌ Failed to clean {file_path}: {e}")
                                pass
                    
                    if debug_cleanup:
                        print(f"🧹 Cleanup completed: {cleaned_count}/{len(files_to_clean)} files removed")
                    
        except ImportError:
            raise RuntimeError("spicelib not installed. Run: pip install spicelib")
        except Exception as e:
            raise RuntimeError(f"Simulation failed: {e}")
    
    def _add_analysis_commands(self, netlist: str, analyses: list[str], **kwargs) -> str:
        """
        Add analysis commands to the SPICE netlist.
        
        Args:
            netlist: Base SPICE netlist
            analyses: List of requested analyses
            **kwargs: Analysis parameters
            
        Returns:
            Modified netlist with analysis commands
        """
        # Remove existing .end and add analysis commands
        lines = netlist.rstrip().rstrip('.end').strip().split('\n')
        
        for analysis in analyses:
            if analysis == 'transient':
                step_time = kwargs.get('step_time', 1e-6)
                end_time = kwargs.get('end_time', 1e-3)
                lines.append(f'.tran {step_time} {end_time} UIC')
            elif analysis == 'ac':
                start_freq = kwargs.get('start_freq', 1)
                end_freq = kwargs.get('end_freq', 1e6)
                points_per_decade = kwargs.get('points_per_decade', 10)
                lines.append(f'.ac dec {points_per_decade} {start_freq} {end_freq}')
            elif analysis == 'dc':
                # DC sweep analysis
                source = kwargs.get('source_name', kwargs.get('source', 'V1'))
                start = kwargs.get('start', 0)
                stop = kwargs.get('stop', 5)
                step = kwargs.get('step', 0.1)
                lines.append(f'.dc {source} {start} {stop} {step}')
            elif analysis == 'op':
                lines.append('.op')
        
        lines.append('.end')
        return '\n'.join(lines)
    



class SimulatedCircuit:
    """
    A simulated circuit that can return component-specific simulation results.
    
    This class allows you to query simulation results for specific component instances
    that were used to build the circuit, returning all attributes that the simulation
    calculated for that component.
    """
    
    def __init__(self, circuit=None, analysis_type=None, **spicelib_kwargs):
        self.circuit = circuit
        self.analysis_type = analysis_type
        
        # Store the raw simulation results
        self.nodes = {}
        self.branches = {}
        
        # SpiceLib initialization
        if 'time' in spicelib_kwargs:
            self.time = spicelib_kwargs['time']
        if 'raw_data' in spicelib_kwargs:
            self.raw_data = spicelib_kwargs['raw_data']
        if 'trace_names' in spicelib_kwargs:
            self.trace_names = spicelib_kwargs['trace_names']
            # Parse spicelib results to populate nodes and branches dictionaries
            self._parse_spicelib_results()
    

    
    def _parse_spicelib_results(self):
        """Parse spicelib results and populate nodes and branches dictionaries."""
        if not hasattr(self, 'raw_data') or not self.raw_data or not hasattr(self, 'trace_names'):
            return
        
        # Extract node voltages and branch currents from spicelib raw data
        for trace_name in self.trace_names:
            # Look for voltage traces (node voltages)
            if trace_name.startswith('v(') and trace_name.endswith(')'):
                # Extract node name from v(node_name) format
                node_name = trace_name[2:-1]  # Remove 'v(' and ')'
                try:
                    trace = self.raw_data.get_trace(trace_name)
                    if trace and hasattr(trace, 'data'):
                        self.nodes[node_name] = trace.data
                except Exception:
                    # If we can't get the trace, skip it
                    continue
            elif trace_name.startswith('V(') and trace_name.endswith(')'):
                # Handle uppercase version V(node_name)
                node_name = trace_name[2:-1]  # Remove 'V(' and ')'
                try:
                    trace = self.raw_data.get_trace(trace_name)
                    if trace and hasattr(trace, 'data'):
                        self.nodes[node_name] = trace.data
                except Exception:
                    continue
            # Look for current traces (branch currents)
            elif trace_name.startswith('i(') and trace_name.endswith(')'):
                # Extract component name from i(component_name) format
                component_name = trace_name[2:-1]  # Remove 'i(' and ')'
                try:
                    trace = self.raw_data.get_trace(trace_name)
                    if trace and hasattr(trace, 'data'):
                        self.branches[component_name] = trace.data
                except Exception:
                    # If we can't get the trace, skip it
                    continue
            elif trace_name.startswith('I(') and trace_name.endswith(')'):
                # Handle uppercase version I(component_name)
                component_name = trace_name[2:-1]  # Remove 'I(' and ')'
                try:
                    trace = self.raw_data.get_trace(trace_name)
                    if trace and hasattr(trace, 'data'):
                        self.branches[component_name] = trace.data
                except Exception:
                    continue
    
    def get_component_results(self, component):
        """
        Get all simulation results for a specific component instance.
        
        Args:
            component: The component instance that was used to build the circuit
            
        Returns:
            dict: Dictionary containing all available simulation data for this component
        """
        if component not in self.circuit.components:
            raise ValueError(f"Component {component} is not part of this circuit")
        
        # Delegate to the component to extract its own simulation results
        return component.extract_simulation_results(self)
    
    def _get_node_voltage_value(self, node_name):
        """
        Get the voltage value for a node name using deterministic naming.
        
        Args:
            node_name: The SPICE node name (e.g., 'N1', 'N2', 'gnd')
            
        Returns:
            float or array: The voltage value(s) at the node
        """
        # Handle ground explicitly
        if node_name == 'gnd':
            return 0.0
        
        if hasattr(self, 'raw_data') and self.raw_data and hasattr(self, 'trace_names'):
            # Use deterministic naming: v(node_name.lower())
            trace_name = f'v({node_name.lower()})'
            if trace_name in self.trace_names:
                trace = self.raw_data.get_trace(trace_name)
                return trace.data
                
        raise ValueError(f"Node {node_name} not found in simulation results")
    
    def _get_branch_current_value(self, branch_name):
        """
        Get the current value for a branch name using deterministic naming.
        
        Args:
            branch_name: The SPICE branch name (component name in lowercase)
            
        Returns:
            float or array or None: The current value(s) or None if not found
        """
        # Use deterministic naming: component_name.lower()
        if branch_name in self.branches:
            branch_value = self.branches[branch_name]
            return self._extract_value(branch_value)
        
        # No match found
        return None
    
    def get_component_current(self, component):
        """
        Get the current through a specific component.
        
        First tries to get SPICE current (for active components like voltage sources),
        then falls back to calculated current from component's derived results
        (for passive components like resistors).
        
        Args:
            component: The component instance
            
        Returns:
            float or array: The current value(s) through the component
        """
        if self.circuit is None:
            raise ValueError("Cannot get component current without circuit reference")
        
        if component not in self.circuit.components:
            raise ValueError(f"Component {component} is not part of this circuit")
        
        # First try to get SPICE current (for active components)
        component_name = self.circuit.get_component_name(component)
        branch_name = component_name.lower()
        
        current_value = self._get_branch_current_value(branch_name)
        if current_value is not None:
            return current_value
        
        # Fall back to calculated current from component's derived results
        # (for passive components like resistors where SPICE doesn't provide current)
        try:
            component_results = self.get_component_results(component)
            if 'current' in component_results:
                return component_results['current']
        except Exception:
            pass
        
        raise ValueError(f"Current for component {component_name} not available in simulation results or component calculations")
    
    def get_terminal_current(self, terminal):
        """
        Get the current flowing into a specific terminal.
        
        This determines which component the terminal belongs to and returns
        the current through that component.
        
        Args:
            terminal: The terminal object
            
        Returns:
            float or array: The current value(s) flowing into the terminal
        """
        if self.circuit is None:
            raise ValueError("Cannot get terminal current without circuit reference")
        
        # Find which component this terminal belongs to
        for component in self.circuit.components:
            for terminal_name, comp_terminal in component.get_terminals():
                if comp_terminal is terminal:
                    return self.get_component_current(component)
        
        raise ValueError(f"Terminal {terminal} not found in any circuit component")
    
    def _extract_value(self, node_value):
        """Extract numeric value from SpiceLib simulation data."""
        # Handle numpy arrays from SpiceLib
        if hasattr(node_value, 'shape') and hasattr(node_value, '__getitem__'):
            # For DC analysis, return scalar if single value
            if len(node_value) == 1:
                return float(node_value[0])
            else:
                # Multiple values - return as numpy array for transient/AC analysis
                return np.array(node_value, dtype=float)
        elif hasattr(node_value, '__float__'):
            return float(node_value)
        elif hasattr(node_value, '__iter__') and not isinstance(node_value, str):
            # For other array-like objects
            if len(node_value) == 1:
                return float(node_value[0])
            else:
                return np.array(node_value)
        else:
            return node_value
    
    def get_node_voltage(self, terminal):
        """
        Get the voltage at a specific terminal/node.
        
        Args:
            terminal: Terminal object or gnd
            
        Returns:
            Voltage value at the terminal
        """
        if self.circuit is None:
            raise ValueError("Cannot get node voltage without circuit reference")
        
        node_name = self.circuit.get_spice_node_name(terminal)
        return self._get_node_voltage_value(node_name)
    
    def list_components(self):
        """List all components in the circuit."""
        return [(comp, self.circuit.get_component_name(comp)) for comp in self.circuit.components]
    
    def __repr__(self):
        return f"SimulatedCircuit({self.analysis_type}, {len(self.circuit.components)} components, {len(self.nodes)} nodes, {len(self.branches)} branches)"

    def get_time_vector(self):
        """
        Get the time vector from transient analysis results.
        
        Returns:
            numpy.ndarray: Time values, or None if not transient analysis
        """
        if self.analysis_type != "Transient Analysis":
            return None
        
        return getattr(self, 'time', None)


class CircuitSimulator:
    """
    Legacy simulator wrapper for backward compatibility.
    
    This class is deprecated. Use the new backend-based simulation methods
    on CircuitRoot instead: circuit.simulate_operating_point(), etc.
    """
    
    def __init__(self, circuit):
        self.circuit = circuit
        
        # Use the new spicelib backend internally
        self._backend = SpicelibBackend()
    

    
    def operating_point(self, temperature=25, add_current_probes=False):
        """Run DC operating point analysis (legacy method)."""
        return self.circuit.simulate_operating_point(
            backend=self._backend, 
            temperature=temperature, 
            add_current_probes=add_current_probes
        )
    
    def dc_sweep(self, source_name, start, stop, step, temperature=25):
        """Run DC sweep analysis (legacy method)."""
        return self.circuit.simulate_dc_sweep(
            source_name=source_name,
            start=start,
            stop=stop,
            step=step,
            backend=self._backend,
            temperature=temperature
        )
    
    def ac_analysis(self, start_freq=1, stop_freq=1e6, points_per_decade=10, temperature=25):
        """Run AC analysis (legacy method)."""
        return self.circuit.simulate_ac(
            start_freq=start_freq,
            stop_freq=stop_freq,
            points_per_decade=points_per_decade,
            backend=self._backend,
            temperature=temperature
        )
    
    def transient_analysis(self, step_time, end_time, start_time=0, temperature=25):
        """Run transient analysis (legacy method)."""
        return self.circuit.simulate_transient(
            step_time=step_time,
            end_time=end_time,
            start_time=start_time,
            backend=self._backend,
            temperature=temperature
        )


def check_simulation_requirements():
    """Check if simulation requirements are available."""
    try:
        from spicelib import SimRunner
        from spicelib.simulators.ngspice_simulator import NGspiceSimulator
        return True, "Simulation requirements satisfied (spicelib available)"
    except ImportError:
        return False, "spicelib is not installed. Install with: pip install spicelib"
    
    # Could add more checks here (ngspice installation, etc.) 
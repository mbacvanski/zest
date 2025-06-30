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
    
    def get_node_voltage(self, result, node_name: str):
        """
        Extract node voltage from spicelib simulation results.
        
        Args:
            result: SimulatedCircuit from spicelib simulation
            node_name: Name of the node (e.g., 'N1', 'N2')
            
        Returns:
            numpy array of voltage values or single voltage value
        """
        if not hasattr(result, 'raw_data') or not result.raw_data:
            return 0.0
        
        # Try different node name formats
        possible_names = [
            f'v({node_name.lower()})',  # v(n1)
            f'V({node_name.upper()})',  # V(N1) 
            f'v({node_name})',          # v(N1)
            node_name.lower(),          # n1
            node_name.upper()           # N1
        ]
        
        for name in possible_names:
            if name in result.trace_names:
                trace = result.raw_data.get_trace(name)
                return trace.data
        
        # If no trace found, return 0.0 (fallback)
        return 0.0


class SimulatedCircuit:
    """
    A simulated circuit that can return component-specific simulation results.
    
    This class allows you to query simulation results for specific component instances
    that were used to build the circuit, returning all attributes that the simulation
    calculated for that component.
    """
    
    def __init__(self, circuit=None, analysis_type=None, pyspice_results=None, **spicelib_kwargs):
        self.circuit = circuit
        self.analysis_type = analysis_type
        self.pyspice_results = pyspice_results
        
        # Store the raw simulation results
        self.nodes = {}
        self.branches = {}
        
        # Support spicelib-style initialization
        if 'time' in spicelib_kwargs:
            self.time = spicelib_kwargs['time']
        if 'raw_data' in spicelib_kwargs:
            self.raw_data = spicelib_kwargs['raw_data']
        if 'trace_names' in spicelib_kwargs:
            self.trace_names = spicelib_kwargs['trace_names']
            # Parse spicelib results to populate nodes dictionary
            self._parse_spicelib_results()
        
        if pyspice_results is not None:
            self._parse_results(pyspice_results)
    
    def _parse_results(self, results):
        """Parse PySpice results into more accessible format."""
        if hasattr(results, 'nodes'):
            for node_name, node_value in results.nodes.items():
                self.nodes[str(node_name)] = node_value
        
        if hasattr(results, 'branches'):
            for branch_name, branch_value in results.branches.items():
                self.branches[str(branch_name)] = branch_value
    
    def _parse_spicelib_results(self):
        """Parse spicelib results and populate nodes dictionary."""
        if not hasattr(self, 'raw_data') or not self.raw_data or not hasattr(self, 'trace_names'):
            return
        
        # Extract node voltages from spicelib raw data
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
        Get the voltage value for a node name, handling both PySpice and spicelib formats.
        
        Args:
            node_name: The SPICE node name (e.g., 'N1', 'N2')
            
        Returns:
            float or array: The voltage value(s) at the node
        """
        # Handle ground explicitly
        if node_name == 'gnd':
            return 0.0
        
        # For spicelib backend, try to get trace directly
        if hasattr(self, 'raw_data') and self.raw_data and hasattr(self, 'trace_names'):
            # Try different node name formats for spicelib
            possible_names = [
                f'v({node_name.lower()})',  # v(n1), v(n2)
                f'V({node_name.upper()})',  # V(N1), V(N2)
                f'v({node_name})',          # v(N1), v(N2)
                node_name.lower(),          # n1, n2
                node_name.upper()           # N1, N2
            ]
            
            for name in possible_names:
                if name in self.trace_names:
                    trace = self.raw_data.get_trace(name)
                    return trace.data
        
        # Fall back to PySpice method for PySpice backend
        # First try exact match
        if node_name in self.nodes:
            node_value = self.nodes[node_name]
            return self._extract_value(node_value)
        
        # Try case-insensitive match
        for sim_node_name, sim_node_value in self.nodes.items():
            if node_name.lower() == sim_node_name.lower():
                return self._extract_value(sim_node_value)
        
        # If no match found, assume ground (0V)
        return 0.0
    
    def _get_branch_current_value(self, branch_name):
        """
        Get the current value for a branch name, handling case sensitivity.
        
        Args:
            branch_name: The SPICE branch name
            
        Returns:
            float or array or None: The current value(s) or None if not found
        """
        # First try exact match
        if branch_name in self.branches:
            branch_value = self.branches[branch_name]
            return self._extract_value(branch_value)
        
        # Try case-insensitive match
        for sim_branch_name, sim_branch_value in self.branches.items():
            if branch_name.lower() == sim_branch_name.lower():
                return self._extract_value(sim_branch_value)
        
        # No match found
        return None
    
    def _extract_value(self, node_value):
        """Extract numeric value from PySpice waveform or other objects."""
        # Handle PySpice WaveForm objects with units
        if hasattr(node_value, 'as_ndarray'):
            # This is a PySpice UnitValues/WaveForm object
            try:
                # Extract the raw numpy array without units
                raw_array = node_value.as_ndarray()
                
                # For DC analysis, return the scalar value if it's just one point
                if hasattr(raw_array, 'shape') and len(raw_array.shape) == 0:
                    # It's a scalar wrapped in an array
                    return float(raw_array.item()) if hasattr(raw_array, 'item') else float(raw_array)
                elif len(raw_array) == 1:
                    # Single value array - extract the scalar
                    return float(raw_array[0])
                else:
                    # Multiple values - return as numpy array for transient/AC analysis
                    return np.array(raw_array, dtype=float)
            except:
                # Fallback for PySpice objects
                try:
                    # Try to convert to float directly
                    return float(node_value)
                except:
                    # Last resort: return the raw value
                    return node_value
        
        # Handle regular numpy arrays and array-like objects
        elif hasattr(node_value, 'shape') and hasattr(node_value, '__getitem__'):
            try:
                # For DC analysis, return the scalar value if it's just one point
                if hasattr(node_value, 'shape') and len(node_value.shape) == 0:
                    # It's a scalar wrapped in an array
                    return float(node_value.item()) if hasattr(node_value, 'item') else float(node_value)
                elif len(node_value) == 1:
                    # Single value array - extract the scalar
                    return float(node_value[0])
                else:
                    # Multiple values - return as numpy array for transient/AC analysis
                    return np.array([float(val) for val in node_value])
            except:
                # Fallback: try to extract single value or return array
                try:
                    if hasattr(node_value, 'item'):
                        return float(node_value.item())
                    elif len(node_value) == 1:
                        return float(node_value[0])
                    else:
                        return np.array(node_value)
                except:
                    return np.array(node_value)
        elif hasattr(node_value, '__float__'):
            try:
                return float(node_value)
            except:
                # Handle the numpy array scalar deprecation warning
                if hasattr(node_value, 'item'):
                    return float(node_value.item())
                else:
                    return 0.0
        elif hasattr(node_value, '__iter__') and not isinstance(node_value, str):
            # For other array-like objects
            try:
                # For DC analysis, if it's a single value, extract it
                if len(node_value) == 1:
                    return float(node_value[0])
                else:
                    return np.array(node_value) if hasattr(np, 'array') else list(node_value)
            except:
                return node_value
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
        # Handle spicelib backend case (circuit is None, use raw_data directly)
        if hasattr(self, 'raw_data') and self.raw_data and self.circuit is None:
            # For spicelib, we need to figure out the node name differently
            # For now, try common node naming patterns
            possible_names = []
            
            # If terminal has a string representation, try that
            if hasattr(terminal, '__str__'):
                term_str = str(terminal)
                if 'N1' in term_str or 'N2' in term_str or 'N3' in term_str:
                    # Extract node number from terminal string
                    import re
                    match = re.search(r'N(\d+)', term_str)
                    if match:
                        node_num = match.group(1)
                        possible_names.extend([f'v(n{node_num})', f'V(N{node_num})', f'n{node_num}', f'N{node_num}'])
            
            # Try different node name formats
            for name in possible_names:
                if name in self.trace_names:
                    trace = self.raw_data.get_trace(name)
                    return trace.data
            
            # Fallback: try to match by index or pattern
            for trace_name in self.trace_names:
                if 'v(' in trace_name.lower() and ('n1' in trace_name.lower() or 'n2' in trace_name.lower()):
                    trace = self.raw_data.get_trace(trace_name)
                    return trace.data
            
            return 0.0
        
        # Handle PySpice backend case (circuit is available)
        elif self.circuit is not None:
            node_name = self.circuit.get_spice_node_name(terminal)
            return self._get_node_voltage_value(node_name)
        
        else:
            return 0.0
    
    def list_components(self):
        """List all components in the circuit."""
        return [(comp, self.circuit.get_component_name(comp)) for comp in self.circuit.components]
    
    def __repr__(self):
        return f"SimulatedCircuit({self.analysis_type}, {len(self.circuit.components)} components, {len(self.nodes)} nodes, {len(self.branches)} branches)"

    def get_time_vector(self):
        """
        Get the time vector from transient analysis results.
        
        Returns:
            numpy.ndarray: Time values, or None if not available
        """
        if self.analysis_type != "Transient Analysis":
            return None
        
        # For spicelib backend, time is stored directly
        if hasattr(self, 'time') and self.time is not None:
            return self.time
        
        # Legacy PySpice support (for backward compatibility)
        if hasattr(self, 'pyspice_results') and self.pyspice_results is not None:
            # Try to extract time vector from PySpice results
            if hasattr(self.pyspice_results, 'time'):
                return self._extract_value(self.pyspice_results.time)
            elif hasattr(self.pyspice_results, 'abscissa'):
                return self._extract_value(self.pyspice_results.abscissa)
        
        return None


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
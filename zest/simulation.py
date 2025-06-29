"""
Simulation capabilities for Zest circuits using PySpice.
"""

import numpy as np
from pathlib import Path
import tempfile

try:
    import PySpice.Logging.Logging as Logging
    from PySpice.Spice.Netlist import Circuit as PySpiceCircuit
    from PySpice.Unit import *
    PYSPICE_AVAILABLE = True
except ImportError:
    PYSPICE_AVAILABLE = False


class SimulatedCircuit:
    """
    A simulated circuit that can return component-specific simulation results.
    
    This class allows you to query simulation results for specific component instances
    that were used to build the circuit, returning all attributes that the simulation
    calculated for that component.
    """
    
    def __init__(self, circuit, analysis_type, pyspice_results=None):
        self.circuit = circuit
        self.analysis_type = analysis_type
        self.pyspice_results = pyspice_results
        
        # Store the raw simulation results
        self.nodes = {}
        self.branches = {}
        
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
        Get the voltage value for a node name, handling case sensitivity and ground.
        
        Args:
            node_name: The SPICE node name
            
        Returns:
            float or array: The voltage value(s) at the node
        """
        # Handle ground explicitly
        if node_name == 'gnd':
            return 0.0
        
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
            numpy.ndarray: Time values, or None if not available
        """
        if self.analysis_type != "Transient Analysis":
            return None
        
        if self.pyspice_results is None:
            return None
        
        # Try to extract time vector from PySpice results
        if hasattr(self.pyspice_results, 'time'):
            return self._extract_value(self.pyspice_results.time)
        elif hasattr(self.pyspice_results, 'abscissa'):
            return self._extract_value(self.pyspice_results.abscissa)
        else:
            return None


class CircuitSimulator:
    """PySpice-based simulator for Zest circuits."""
    
    def __init__(self, circuit):
        if not PYSPICE_AVAILABLE:
            raise ImportError("PySpice is required for simulation. Install with: pip install PySpice")
        
        self.circuit = circuit
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup PySpice logging."""
        try:
            logger = Logging.setup_logging()
        except:
            pass  # Logging setup might fail, but simulation can still work
    
    def _create_pyspice_circuit(self, add_current_probes=False):
        """Convert Zest circuit to PySpice circuit."""
        # Ensure component names are assigned first
        self.circuit._assign_component_names()
        for component in self.circuit.components:
            component.name = self.circuit.get_component_name(component)
        
        # Create PySpice circuit
        pyspice_circuit = PySpiceCircuit(self.circuit.name)
        
        # Add .INCLUDE statements for external model files
        from .components import SubCircuit
        all_includes = set(self.circuit.includes)
        circuits_to_scan = [self.circuit]
        scanned_definitions = {self.circuit}

        while circuits_to_scan:
            current_circuit = circuits_to_scan.pop()
            for component in current_circuit.components:
                if isinstance(component, SubCircuit):
                    definition = component.definition
                    if definition not in scanned_definitions:
                        all_includes.update(definition.includes)
                        scanned_definitions.add(definition)
                        circuits_to_scan.append(definition)

        if all_includes:
            for include_path in sorted(list(all_includes)):
                pyspice_circuit.raw_spice += f'.INCLUDE "{include_path}"\n'
        
        # Add external models/subcircuits to raw SPICE (legacy support)
        if self.circuit._include_models:
            for model_text in sorted(self.circuit._include_models):
                pyspice_circuit.raw_spice += f"{model_text}\n"
        
        # Add subcircuit definitions
        from .components import SubCircuit
        unique_definitions = {
            comp.definition for comp in self.circuit.components if isinstance(comp, SubCircuit)
        }
        
        # Filter out external-only subcircuits (defined in .INCLUDE files)
        internal_definitions = {
            definition for definition in unique_definitions
            if not getattr(definition, '_is_external_only', False)
        }
        
        if internal_definitions:
            for definition in sorted(list(internal_definitions), key=lambda c: c.name):
                subckt_spice = definition._compile_as_subcircuit()
                pyspice_circuit.raw_spice += f"{subckt_spice}\n"
        
        # Add components from our circuit
        for component in self.circuit.components:
            self._add_component_to_pyspice(pyspice_circuit, component, add_current_probes)
        
        # Add initial conditions using raw SPICE directives
        if self.circuit._initial_conditions:
            # Group initial conditions by node
            node_ics = {}
            for terminal, voltage in self.circuit._initial_conditions.items():
                node_name = self.circuit.get_spice_node_name(terminal)
                if node_name != "gnd":  # Skip ground (always 0V)
                    node_ics[node_name] = voltage
            
            # Add .IC directive for each node using raw_spice
            for node_name, voltage in node_ics.items():
                pyspice_circuit.raw_spice += f".IC V({node_name})={voltage}\n"
        
        return pyspice_circuit
    
    def _add_component_to_pyspice(self, pyspice_circuit, component, add_current_probes=False):
        """Add a Zest component to PySpice circuit."""
        from .components import VoltageSource, Resistor, Capacitor, Inductor, SubCircuit
        
        # For SubCircuit and other components that compile to SPICE,
        # we handle them through the raw SPICE interface
        if isinstance(component, SubCircuit) or hasattr(component, 'to_spice'):
            # Check if this is a basic component we can handle directly
            if not isinstance(component, (VoltageSource, Resistor, Capacitor, Inductor)):
                # This is a component that needs to be handled as raw SPICE
                spice_line = component.to_spice(self.circuit)
                pyspice_circuit.raw_spice += f"{spice_line}\n"
                return
        
        if isinstance(component, VoltageSource):
            # Get SPICE node names for the terminals
            pos_node = self.circuit.get_spice_node_name(component.pos)
            neg_node = self.circuit.get_spice_node_name(component.neg)
            
            # Convert 'gnd' to PySpice ground
            if pos_node == 'gnd':
                pos_node = pyspice_circuit.gnd
            if neg_node == 'gnd':
                neg_node = pyspice_circuit.gnd
            
            # PySpice adds a "V" prefix to voltage source names, so we need to remove 
            # the "V" from our component name to avoid "VV1" 
            vs_name = component.name[1:] if component.name.startswith('V') else component.name
            pyspice_circuit.V(vs_name, pos_node, neg_node, component.voltage@u_V)
            
        elif isinstance(component, Resistor):
            # Get SPICE node names for the terminals
            n1_node = self.circuit.get_spice_node_name(component.n1)
            n2_node = self.circuit.get_spice_node_name(component.n2)
            
            # Convert 'gnd' to PySpice ground
            if n1_node == 'gnd':
                n1_node = pyspice_circuit.gnd
            if n2_node == 'gnd':
                n2_node = pyspice_circuit.gnd
            
            # PySpice adds an "R" prefix to resistor names
            r_name = component.name[1:] if component.name.startswith('R') else component.name    
            resistor = pyspice_circuit.R(r_name, n1_node, n2_node, component.resistance@u_Ω)
            
            # Add current probe if requested
            if add_current_probes:
                resistor.minus.add_current_probe(pyspice_circuit)
            
        elif isinstance(component, Capacitor):
            # Get SPICE node names for the terminals
            pos_node = self.circuit.get_spice_node_name(component.pos)
            neg_node = self.circuit.get_spice_node_name(component.neg)
            
            # Convert 'gnd' to PySpice ground
            if pos_node == 'gnd':
                pos_node = pyspice_circuit.gnd
            if neg_node == 'gnd':
                neg_node = pyspice_circuit.gnd
            
            # PySpice adds a "C" prefix to capacitor names
            c_name = component.name[1:] if component.name.startswith('C') else component.name
            pyspice_circuit.C(c_name, pos_node, neg_node, component.capacitance@u_F)
            
        elif isinstance(component, Inductor):
            # Get SPICE node names for the terminals
            n1_node = self.circuit.get_spice_node_name(component.n1)
            n2_node = self.circuit.get_spice_node_name(component.n2)
            
            # Convert 'gnd' to PySpice ground
            if n1_node == 'gnd':
                n1_node = pyspice_circuit.gnd
            if n2_node == 'gnd':
                n2_node = pyspice_circuit.gnd
            
            # PySpice adds an "L" prefix to inductor names
            l_name = component.name[1:] if component.name.startswith('L') else component.name
            pyspice_circuit.L(l_name, n1_node, n2_node, component.inductance@u_H)
            
        else:
            raise ValueError(f"Unsupported component type: {type(component)}")
    
    def operating_point(self, temperature=25, add_current_probes=False):
        """Run DC operating point analysis."""
        pyspice_circuit = self._create_pyspice_circuit(add_current_probes=add_current_probes)
        simulator = pyspice_circuit.simulator(temperature=temperature, nominal_temperature=temperature)
        
        try:
            analysis = simulator.operating_point()
            return SimulatedCircuit(self.circuit, "DC Operating Point", analysis)
        except Exception as e:
            raise RuntimeError(f"Simulation failed: {e}")
    
    def dc_sweep(self, source_name, start, stop, step, temperature=25):
        """Run DC sweep analysis."""
        pyspice_circuit = self._create_pyspice_circuit()
        simulator = pyspice_circuit.simulator(temperature=temperature, nominal_temperature=temperature)
        
        try:
            # PySpice newer API uses keyword arguments with slice notation
            # PySpice expects the exact component name for sweeps
            sweep_kwargs = {source_name: slice(start, stop, step)}
            analysis = simulator.dc(**sweep_kwargs)
            return SimulatedCircuit(self.circuit, "DC Sweep", analysis)
        except Exception as e:
            raise RuntimeError(f"DC sweep simulation failed: {e}")
    
    def ac_analysis(self, start_freq=1, stop_freq=1e6, points_per_decade=10, temperature=25):
        """Run AC analysis."""
        pyspice_circuit = self._create_pyspice_circuit()
        simulator = pyspice_circuit.simulator(temperature=temperature, nominal_temperature=temperature)
        
        try:
            analysis = simulator.ac(start_frequency=start_freq@u_Hz, 
                                  stop_frequency=stop_freq@u_Hz, 
                                  number_of_points=points_per_decade,  
                                  variation='dec')
            return SimulatedCircuit(self.circuit, "AC Analysis", analysis)
        except Exception as e:
            raise RuntimeError(f"AC analysis failed: {e}")
    
    def transient_analysis(self, step_time, end_time, start_time=0, temperature=25):
        """Run transient analysis."""
        pyspice_circuit = self._create_pyspice_circuit()
        simulator = pyspice_circuit.simulator(temperature=temperature, nominal_temperature=temperature)
        
        try:
            # Use initial conditions if they exist
            use_initial_condition = len(self.circuit._initial_conditions) > 0
            
            analysis = simulator.transient(step_time=step_time@u_s, 
                                         end_time=end_time@u_s,
                                         start_time=start_time@u_s,
                                         use_initial_condition=use_initial_condition)
            return SimulatedCircuit(self.circuit, "Transient Analysis", analysis)
        except Exception as e:
            raise RuntimeError(f"Transient analysis failed: {e}")


def check_simulation_requirements():
    """Check if simulation requirements are available."""
    if not PYSPICE_AVAILABLE:
        return False, "PySpice is not installed. Install with: pip install PySpice"
    
    # Could add more checks here (ngspice installation, etc.)
    return True, "Simulation requirements satisfied" 
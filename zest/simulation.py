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


class SimulationResults:
    """Container for simulation results."""
    
    def __init__(self, analysis_type, results=None):
        self.analysis_type = analysis_type
        self.results = results
        self.nodes = {}
        self.branches = {}
        
        if results is not None:
            self._parse_results(results)
    
    def _parse_results(self, results):
        """Parse PySpice results into more accessible format."""
        if hasattr(results, 'nodes'):
            for node_name, node_value in results.nodes.items():
                self.nodes[str(node_name)] = float(node_value)
        
        if hasattr(results, 'branches'):
            for branch_name, branch_value in results.branches.items():
                self.branches[str(branch_name)] = float(branch_value)
    
    def __repr__(self):
        return f"SimulationResults({self.analysis_type}, {len(self.nodes)} nodes, {len(self.branches)} branches)"


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
        if hasattr(node_value, '__float__'):
            try:
                return float(node_value)
            except:
                # Handle the numpy array scalar deprecation warning
                if hasattr(node_value, 'item'):
                    return float(node_value.item())
                else:
                    return 0.0
        elif hasattr(node_value, '__iter__') and not isinstance(node_value, str):
            # For transient/AC analysis, might be arrays
            try:
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
        
        # Add components from our circuit
        for component in self.circuit.components:
            self._add_component_to_pyspice(pyspice_circuit, component, add_current_probes)
        
        return pyspice_circuit
    
    def _add_component_to_pyspice(self, pyspice_circuit, component, add_current_probes=False):
        """Add a Zest component to PySpice circuit."""
        from .components import VoltageSource, Resistor, Capacitor, Inductor
        
        if isinstance(component, VoltageSource):
            # Get SPICE node names for the terminals
            pos_node = self.circuit.get_spice_node_name(component.pos)
            neg_node = self.circuit.get_spice_node_name(component.neg)
            
            # Convert 'gnd' to PySpice ground
            if pos_node == 'gnd':
                pos_node = pyspice_circuit.gnd
            if neg_node == 'gnd':
                neg_node = pyspice_circuit.gnd
                
            pyspice_circuit.V(component.name, pos_node, neg_node, component.voltage@u_V)
            
        elif isinstance(component, Resistor):
            # Get SPICE node names for the terminals
            n1_node = self.circuit.get_spice_node_name(component.n1)
            n2_node = self.circuit.get_spice_node_name(component.n2)
            
            # Convert 'gnd' to PySpice ground
            if n1_node == 'gnd':
                n1_node = pyspice_circuit.gnd
            if n2_node == 'gnd':
                n2_node = pyspice_circuit.gnd
                
            resistor = pyspice_circuit.R(component.name, n1_node, n2_node, component.resistance@u_Ω)
            
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
                
            pyspice_circuit.C(component.name, pos_node, neg_node, component.capacitance@u_F)
            
        elif isinstance(component, Inductor):
            # Get SPICE node names for the terminals
            n1_node = self.circuit.get_spice_node_name(component.n1)
            n2_node = self.circuit.get_spice_node_name(component.n2)
            
            # Convert 'gnd' to PySpice ground
            if n1_node == 'gnd':
                n1_node = pyspice_circuit.gnd
            if n2_node == 'gnd':
                n2_node = pyspice_circuit.gnd
                
            pyspice_circuit.L(component.name, n1_node, n2_node, component.inductance@u_H)
            
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
            analysis = simulator.dc(source_name, start@u_V, stop@u_V, step@u_V)
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
            analysis = simulator.transient(step_time=step_time@u_s, 
                                         end_time=end_time@u_s,
                                         start_time=start_time@u_s)
            return SimulatedCircuit(self.circuit, "Transient Analysis", analysis)
        except Exception as e:
            raise RuntimeError(f"Transient analysis failed: {e}")


def check_simulation_requirements():
    """Check if simulation requirements are available."""
    if not PYSPICE_AVAILABLE:
        return False, "PySpice is not installed. Install with: pip install PySpice"
    
    # Could add more checks here (ngspice installation, etc.)
    return True, "Simulation requirements satisfied" 
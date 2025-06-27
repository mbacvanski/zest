"""
Circuit class for representing and manipulating electronic circuits as graphs.
"""

from .nodes import Node, gnd

# Global registry to track current circuit for component auto-registration
_current_circuit = None


def get_current_circuit():
    """Get the current circuit context."""
    return _current_circuit


def set_current_circuit(circuit):
    """Set the current circuit context."""
    global _current_circuit
    _current_circuit = circuit


class Circuit:
    """
    Represents an electronic circuit as a graph where components are nodes
    and wires are edges connecting component terminals.
    """
    
    def __init__(self, name="Untitled Circuit"):
        self.name = name
        self.components = []
        self.wires = []  # List of (terminal1, terminal2) wire connections
        self.gnd = gnd   # Circuit's ground reference
        self._component_names = {}  # Maps component -> final name
        self._initial_conditions = {}  # Maps terminal -> initial voltage
        
        # Set this circuit as the current circuit for component auto-registration
        set_current_circuit(self)
    
    def add_component(self, component):
        """Add a component to the circuit."""
        if component not in self.components:
            self.components.append(component)
    
    def remove_component(self, component):
        """Remove a component from the circuit."""
        if component in self.components:
            self.components.remove(component)
            # Clear cached name
            if component in self._component_names:
                del self._component_names[component]
    
    def wire(self, terminal1, terminal2):
        """
        Connect two terminals with a wire.
        
        Args:
            terminal1: First terminal (Terminal object or gnd)
            terminal2: Second terminal (Terminal object or gnd)
        """
        from .components import Terminal
        
        # Validate inputs
        if not (isinstance(terminal1, Terminal) or terminal1 is gnd):
            raise ValueError(f"terminal1 must be a Terminal or gnd, got {type(terminal1)}")
        if not (isinstance(terminal2, Terminal) or terminal2 is gnd):
            raise ValueError(f"terminal2 must be a Terminal or gnd, got {type(terminal2)}")
        
        # Register components with the circuit if they have terminals
        if isinstance(terminal1, Terminal) and terminal1.component not in self.components:
            self.add_component(terminal1.component)
        if isinstance(terminal2, Terminal) and terminal2.component not in self.components:
            self.add_component(terminal2.component)
        
        # Add wire connection - prevent duplicate wires between same endpoints
        wire = (terminal1, terminal2)
        reverse_wire = (terminal2, terminal1)
        
        # Only add if this exact wire doesn't already exist
        if wire not in self.wires and reverse_wire not in self.wires:
            self.wires.append(wire)
    
    def set_initial_condition(self, terminal, voltage):
        """
        Set the initial voltage of a node/terminal for transient analysis.
        
        Args:
            terminal: Terminal object or gnd to set initial voltage for
            voltage: Initial voltage value in volts
        """
        from .components import Terminal
        
        if terminal is gnd:
            if voltage != 0.0:
                raise ValueError("Ground terminal must have 0V initial condition")
            return  # Ground is always 0V, no need to store
        
        if not isinstance(terminal, Terminal):
            raise ValueError(f"terminal must be a Terminal or gnd, got {type(terminal)}")
        
        self._initial_conditions[terminal] = voltage
    
    def get_initial_condition(self, terminal):
        """
        Get the initial voltage for a terminal.
        
        Args:
            terminal: Terminal object or gnd
            
        Returns:
            float: Initial voltage, or None if not set
        """
        if terminal is gnd:
            return 0.0
        
        return self._initial_conditions.get(terminal, None)
    
    def _assign_component_names(self):
        """Assign final names to components based on their types."""
        # Clear any existing cached names
        self._component_names.clear()
        
        # Count components by type prefix
        type_counts = {}
        
        for component in self.components:
            # Use requested name if provided, otherwise auto-generate
            if component._requested_name:
                self._component_names[component] = component._requested_name
            else:
                prefix = component.get_component_type_prefix()
                type_counts[prefix] = type_counts.get(prefix, 0) + 1
                self._component_names[component] = f"{prefix}{type_counts[prefix]}"
    
    def get_component_name(self, component):
        """Get the final assigned name for a component."""
        if component not in self._component_names:
            self._assign_component_names()
        return self._component_names[component]
    
    def get_spice_node_name(self, terminal):
        """
        Get the SPICE node name for a terminal based on the circuit's wiring.
        
        Args:
            terminal: Terminal object or gnd
            
        Returns:
            str: SPICE node name
        """
        if terminal is gnd:
            return "gnd"
        
        # Find all terminals connected to this terminal through wires
        connected_terminals = self._find_connected_terminals(terminal)
        
        # If any terminal in the connected set is connected to ground, use "gnd"
        if gnd in connected_terminals:
            return "gnd"
        
        # Otherwise, use the first terminal's name as the representative node name
        representative = min(connected_terminals, key=lambda t: str(t) if hasattr(t, '__str__') else "")
        if hasattr(representative, '__str__'):
            return str(representative).replace('.', '_')  # Replace dots for SPICE compatibility
        else:
            return f"n{id(representative) % 10000}"  # Fallback node name
    
    def _find_connected_terminals(self, start_terminal):
        """
        Find all terminals connected to start_terminal through wires.
        
        Args:
            start_terminal: Starting terminal
            
        Returns:
            set: Set of all connected terminals (including start_terminal)
        """
        visited = set()
        to_visit = [start_terminal]
        
        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue
            
            visited.add(current)
            
            # Find all directly connected terminals
            for wire in self.wires:
                terminal1, terminal2 = wire
                if terminal1 == current and terminal2 not in visited:
                    to_visit.append(terminal2)
                elif terminal2 == current and terminal1 not in visited:
                    to_visit.append(terminal1)
        
        return visited
    
    def compile_to_spice(self):
        """Compile the circuit to SPICE netlist format."""
        # Assign component names first
        self._assign_component_names()
        
        # Update component names to match our assignments
        for component in self.components:
            component.name = self.get_component_name(component)
        
        lines = []
        lines.append(f"* Circuit: {self.name}")
        lines.append("")
        
        # Add components
        for component in self.components:
            lines.append(component.to_spice(self))
        
        # Add initial conditions if any are set
        if self._initial_conditions:
            lines.append("")
            lines.append("* Initial Conditions")
            
            # Group initial conditions by node
            node_ics = {}
            for terminal, voltage in self._initial_conditions.items():
                node_name = self.get_spice_node_name(terminal)
                if node_name != "gnd":  # Skip ground (always 0V)
                    node_ics[node_name] = voltage
            
            # Add .IC directive for each node
            for node_name, voltage in node_ics.items():
                lines.append(f".IC V({node_name})={voltage}")
        
        lines.append("")
        lines.append(".end")
        
        return "\n".join(lines)
    
    def get_simulator(self):
        """Get a simulator for this circuit."""
        from .simulation import CircuitSimulator
        return CircuitSimulator(self)
    
    def simulate_operating_point(self, temperature=25, add_current_probes=False):
        """Run DC operating point analysis."""
        simulator = self.get_simulator()
        return simulator.operating_point(temperature=temperature, add_current_probes=add_current_probes)
    
    def simulate_dc_sweep(self, source_name, start, stop, step, temperature=25):
        """Run DC sweep analysis."""
        simulator = self.get_simulator()
        return simulator.dc_sweep(source_name, start, stop, step, temperature=temperature)
    
    def simulate_ac(self, start_freq=1, stop_freq=1e6, points_per_decade=10, temperature=25):
        """Run AC analysis."""
        simulator = self.get_simulator()
        return simulator.ac_analysis(start_freq, stop_freq, points_per_decade, temperature)
    
    def simulate_transient(self, step_time, end_time, start_time=0, temperature=25):
        """Run transient analysis."""
        simulator = self.get_simulator()
        return simulator.transient_analysis(step_time, end_time, start_time, temperature)
    
    def __repr__(self):
        return f"Circuit('{self.name}', {len(self.components)} components, {len(self.wires)} wires)" 
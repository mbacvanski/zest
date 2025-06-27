"""
Component classes for electronic circuit elements.
"""

from .nodes import Node


class Terminal:
    """Represents a connection terminal on a component."""
    
    def __init__(self, component, terminal_name):
        self.component = component
        self.terminal_name = terminal_name
        # The terminal itself is a node in the circuit graph
        self._node = Node(f"{id(component)}.{terminal_name}")  # Use component ID for unique node name
    
    def __str__(self):
        # Use actual component name when available, fallback to component class + ID
        if hasattr(self.component, 'name') and self.component.name != "UNNAMED":
            return f"{self.component.name}.{self.terminal_name}"
        else:
            return f"{self.component.__class__.__name__}_{id(self.component) % 10000}.{self.terminal_name}"
    
    def __repr__(self):
        return f"Terminal({self})"


class Component:
    """Base class for all circuit components."""
    
    def __init__(self, name=None):
        # Store the requested name (or None for auto-generation by circuit)
        self._requested_name = name
        self.name = name or "UNNAMED"  # Temporary name until circuit assigns proper one
        
        # Components must be explicitly added to circuits
    
    def get_component_type_prefix(self):
        """Get the SPICE prefix for this component type."""
        # This will be overridden by subclasses
        return "X"
    
    def to_spice(self, circuit):
        """Convert to SPICE netlist format using circuit's node mapping."""
        raise NotImplementedError("Subclasses must implement to_spice()")
    
    def get_terminals(self):
        """Get list of (terminal_name, terminal) tuples for this component."""
        raise NotImplementedError("Subclasses must implement get_terminals()")
    
    def extract_simulation_results(self, simulated_circuit):
        """
        Extract simulation results specific to this component type.
        
        Args:
            simulated_circuit: The SimulatedCircuit object containing simulation data
            
        Returns:
            dict: Component-specific simulation results
        """
        # Base implementation provides common data for all components
        results = {
            'component': self,
            'component_name': simulated_circuit.circuit.get_component_name(self),
            'analysis_type': simulated_circuit.analysis_type
        }
        
        # Get terminal voltages
        terminal_voltages = {}
        for terminal_name, terminal in self.get_terminals():
            voltage_value = simulated_circuit._get_node_voltage_value(
                simulated_circuit.circuit.get_spice_node_name(terminal)
            )
            terminal_voltages[terminal_name] = voltage_value
        
        results['terminal_voltages'] = terminal_voltages
        
        # Let subclasses add their specific results
        self._add_derived_results(results, simulated_circuit)
        
        return results
    
    def _add_derived_results(self, results, simulated_circuit):
        """
        Add component-specific derived results. Override in subclasses.
        
        Args:
            results: The results dictionary to add to
            simulated_circuit: The SimulatedCircuit object
        """
        pass  # Base implementation does nothing
    
    def __repr__(self):
        return f"{self.__class__.__name__}({self.name})"


class VoltageSource(Component):
    """DC voltage source component."""
    
    def __init__(self, voltage=0.0, name=None):
        self.voltage = voltage
        super().__init__(name)
        
        # Create terminals - these are the nodes in the graph
        self.pos = Terminal(self, "pos")
        self.neg = Terminal(self, "neg")
        
        # Aliases for convenience
        self.positive = self.pos
        self.negative = self.neg
    
    def get_component_type_prefix(self):
        return "V"
    
    def get_terminals(self):
        return [('pos', self.pos), ('neg', self.neg)]
    
    def to_spice(self, circuit):
        """Convert to SPICE format using circuit's node mapping."""
        pos_node = circuit.get_spice_node_name(self.pos)
        neg_node = circuit.get_spice_node_name(self.neg)
        return f"{self.name} {pos_node} {neg_node} DC {self.voltage}"
    
    def _add_derived_results(self, results, simulated_circuit):
        """Add voltage source specific results: current and voltage across."""
        # Look for current through the voltage source
        component_name = simulated_circuit.circuit.get_component_name(self)
        source_current_key = f"v{component_name.lower()}"
        current_value = simulated_circuit._get_branch_current_value(source_current_key)
        if current_value is not None:
            results['current'] = current_value
        
        # Calculate voltage across the source
        terminal_voltages = results['terminal_voltages']
        v_pos = terminal_voltages.get('pos', 0.0)
        v_neg = terminal_voltages.get('neg', 0.0)
        if isinstance(v_pos, (int, float)) and isinstance(v_neg, (int, float)):
            results['voltage_across'] = v_pos - v_neg


class Resistor(Component):
    """Resistor component."""
    
    def __init__(self, resistance=1000.0, name=None):
        self.resistance = resistance
        super().__init__(name)
        
        # Create terminals - these are the nodes in the graph
        self.n1 = Terminal(self, "n1")
        self.n2 = Terminal(self, "n2")
        
        # Aliases for convenience
        self.a = self.n1
        self.b = self.n2
    
    def get_component_type_prefix(self):
        return "R"
    
    def get_terminals(self):
        return [('n1', self.n1), ('n2', self.n2)]
    
    def to_spice(self, circuit):
        """Convert to SPICE format using circuit's node mapping."""
        n1_node = circuit.get_spice_node_name(self.n1)
        n2_node = circuit.get_spice_node_name(self.n2)
        return f"{self.name} {n1_node} {n2_node} {self.resistance}"
    
    def _add_derived_results(self, results, simulated_circuit):
        """Add resistor specific results: voltage across, current, and power."""
        terminal_voltages = results['terminal_voltages']
        v_n1 = terminal_voltages.get('n1', 0.0)
        v_n2 = terminal_voltages.get('n2', 0.0)
        
        if isinstance(v_n1, (int, float)) and isinstance(v_n2, (int, float)):
            voltage_across = v_n1 - v_n2
            results['voltage_across'] = voltage_across
            # Calculate current using Ohm's law
            results['current'] = voltage_across / self.resistance
            # Calculate power dissipation
            results['power'] = voltage_across**2 / self.resistance


class Capacitor(Component):
    """Capacitor component."""
    
    def __init__(self, capacitance=1e-6, name=None):
        self.capacitance = capacitance
        super().__init__(name)
        
        # Create terminals - these are the nodes in the graph
        self.pos = Terminal(self, "pos")
        self.neg = Terminal(self, "neg")
        
        # Aliases for convenience
        self.positive = self.pos
        self.negative = self.neg
    
    def get_component_type_prefix(self):
        return "C"
    
    def get_terminals(self):
        return [('pos', self.pos), ('neg', self.neg)]
    
    def to_spice(self, circuit):
        """Convert to SPICE format using circuit's node mapping."""
        pos_node = circuit.get_spice_node_name(self.pos)
        neg_node = circuit.get_spice_node_name(self.neg)
        return f"{self.name} {pos_node} {neg_node} {self.capacitance}"
    
    def _add_derived_results(self, results, simulated_circuit):
        """Add capacitor specific results: voltage across."""
        terminal_voltages = results['terminal_voltages']
        v_pos = terminal_voltages.get('pos', 0.0)
        v_neg = terminal_voltages.get('neg', 0.0)
        
        if isinstance(v_pos, (int, float)) and isinstance(v_neg, (int, float)):
            results['voltage_across'] = v_pos - v_neg


class Inductor(Component):
    """Inductor component."""
    
    def __init__(self, inductance=1e-3, name=None):
        self.inductance = inductance
        super().__init__(name)
        
        # Create terminals - these are the nodes in the graph
        self.n1 = Terminal(self, "n1")
        self.n2 = Terminal(self, "n2")
        
        # Aliases for convenience
        self.a = self.n1
        self.b = self.n2
    
    def get_component_type_prefix(self):
        return "L"
    
    def get_terminals(self):
        return [('n1', self.n1), ('n2', self.n2)]
    
    def to_spice(self, circuit):
        """Convert to SPICE format using circuit's node mapping."""
        n1_node = circuit.get_spice_node_name(self.n1)
        n2_node = circuit.get_spice_node_name(self.n2)
        return f"{self.name} {n1_node} {n2_node} {self.inductance}"
    
    def _add_derived_results(self, results, simulated_circuit):
        """Add inductor specific results: voltage across."""
        terminal_voltages = results['terminal_voltages']
        v_n1 = terminal_voltages.get('n1', 0.0)
        v_n2 = terminal_voltages.get('n2', 0.0)
        
        if isinstance(v_n1, (int, float)) and isinstance(v_n2, (int, float)):
            results['voltage_across'] = v_n1 - v_n2


class SubCircuit(Component):
    """
    Represents an instance of a subcircuit definition, behaving like a single component.
    """
    def __init__(self, definition, name=None):
        from .circuit import Circuit
        super().__init__(name)
        if not isinstance(definition, Circuit):
            raise TypeError("Subcircuit definition must be a 'Circuit' object.")
        if not definition.pins:
            raise ValueError(f"The subcircuit definition '{definition.name}' has no external pins defined. "
                             "Use the `add_pin()` method on the definition circuit.")

        self.definition = definition
        self._terminals = {}

        # Dynamically create terminals on this instance based on the definition's pins.
        for pin_name in self.definition.pins.keys():
            terminal = Terminal(self, pin_name)
            self._terminals[pin_name] = terminal
            setattr(self, pin_name, terminal)  # Allows access like my_op_amp.vcc

    def get_component_type_prefix(self):
        return "X"

    def get_terminals(self):
        return list(self._terminals.items())

    def to_spice(self, circuit):
        """Generates the SPICE 'X' line for this subcircuit instance."""
        # The node names are resolved in the context of the PARENT circuit.
        pin_order = self.definition.pins.keys()
        node_names_in_parent = [
            circuit.get_spice_node_name(getattr(self, pin_name))
            for pin_name in pin_order
        ]

        return f"{self.name} {' '.join(node_names_in_parent)} {self.definition.name}" 
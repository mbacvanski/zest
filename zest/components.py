"""
Component classes for electronic circuit elements.
"""


class Terminal:
    """Represents a connection terminal/node in a circuit."""
    _terminal_counter = 0
    
    def __init__(self, component=None, terminal_name=None):
        self.component = component
        self.terminal_name = terminal_name
        
        # Generate unique terminal name for SPICE
        if component is not None and terminal_name is not None:
            # Component terminal: use component ID and terminal name
            self.name = f"{id(component)}.{terminal_name}"
        else:
            # Standalone terminal (like ground): use auto-generated name
            Terminal._terminal_counter += 1
            self.name = f"t{Terminal._terminal_counter}"
    
    def __str__(self):
        if self.component is not None:
            # Use actual component name when available, fallback to component class + ID
            if hasattr(self.component, 'name') and self.component.name != "UNNAMED":
                return f"{self.component.name}.{self.terminal_name}"
            else:
                return f"{self.component.__class__.__name__}_{id(self.component) % 10000}.{self.terminal_name}"
        else:
            # Standalone terminal
            return self.name
    
    def __repr__(self):
        return f"Terminal({self})"


class GroundTerminal(Terminal):
    """Special terminal representing circuit ground."""
    
    def __init__(self):
        super().__init__(component=None, terminal_name=None)
        self.name = "gnd"
    
    def __str__(self):
        return "gnd"
    
    def __repr__(self):
        return "GroundTerminal()"


# Create a global ground terminal instance
gnd = GroundTerminal()


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
    
    def to_spice(self, mapper, *, forced_name=None):
        """Convert to SPICE netlist format using NodeMapper."""
        raise NotImplementedError("Subclasses must implement to_spice()")
    
    def get_terminals(self):
        """Get list of (terminal_name, terminal) tuples for this component."""
        raise NotImplementedError("Subclasses must implement get_terminals()")
    
    def terminals(self):
        """Get all terminals for this component as an iterable."""
        for terminal_name, terminal in self.get_terminals():
            yield terminal
    
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
    
    def to_spice(self, mapper, *, forced_name=None):
        """Convert to SPICE format using NodeMapper."""
        pos_node = mapper.name_for(self.pos)
        neg_node = mapper.name_for(self.neg)
        return f"{forced_name or self.name} {pos_node} {neg_node} DC {self.voltage}"
    
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
    
    def to_spice(self, mapper, *, forced_name=None):
        """Convert to SPICE format using NodeMapper."""
        n1_node = mapper.name_for(self.n1)
        n2_node = mapper.name_for(self.n2)
        return f"{forced_name or self.name} {n1_node} {n2_node} {self.resistance}"
    
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
    
    def to_spice(self, mapper, *, forced_name=None):
        """Convert to SPICE format using NodeMapper."""
        pos_node = mapper.name_for(self.pos)
        neg_node = mapper.name_for(self.neg)
        return f"{forced_name or self.name} {pos_node} {neg_node} {self.capacitance}"
    
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
    
    def to_spice(self, mapper, *, forced_name=None):
        """Convert to SPICE format using NodeMapper."""
        n1_node = mapper.name_for(self.n1)
        n2_node = mapper.name_for(self.n2)
        return f"{forced_name or self.name} {n1_node} {n2_node} {self.inductance}"
    
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
    This is a backwards-compatibility wrapper around the new SubCircuitDef/SubCircuitInst system.
    """
    def __init__(self, definition, name=None):
        from .circuit import Circuit, SubCircuitDef
        super().__init__(name)
        
        # Handle both old Circuit and new SubCircuitDef definitions
        if isinstance(definition, SubCircuitDef):
            self.definition = definition
        elif isinstance(definition, Circuit):
            # Wrap old Circuit in SubCircuitDef for compatibility
            subckt_def = SubCircuitDef(definition.name)
            # Copy all attributes from the circuit
            subckt_def.components = definition.components[:]
            subckt_def.wires = definition.wires[:]
            subckt_def.pins = definition.pins.copy()
            subckt_def._include_models = definition._include_models.copy()
            subckt_def.includes = definition.includes[:]
            subckt_def._initial_conditions = definition._initial_conditions.copy()
            self.definition = subckt_def
        else:
            raise TypeError("Subcircuit definition must be a 'Circuit' or 'SubCircuitDef' object.")
        
        if not self.definition.pins:
            raise ValueError(f"The subcircuit definition '{self.definition.name}' has no external pins defined. "
                             "Use the `add_pin()` method on the definition circuit.")

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

    def to_spice(self, mapper, *, forced_name=None):
        """Generates the SPICE 'X' line for this subcircuit instance."""
        # Handle backward compatibility: if mapper is actually a circuit, adapt it
        if hasattr(mapper, 'get_spice_node_name'):
            # Old interface: mapper is actually a circuit
            circuit = mapper
            pin_order = self.definition.pins.keys()
            node_names_in_parent = [
                circuit.get_spice_node_name(getattr(self, pin_name))
                for pin_name in pin_order
            ]
        else:
            # New interface: mapper is a NodeMapper
            pin_order = self.definition.pins.keys()
            node_names_in_parent = [
                mapper.name_for(getattr(self, pin_name))
                for pin_name in pin_order
            ]

        return f"{forced_name or self.name} {' '.join(node_names_in_parent)} {self.definition.name}" 
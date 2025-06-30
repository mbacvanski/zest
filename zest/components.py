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
        # Use the new deterministic current method
        try:
            current_value = simulated_circuit.get_component_current(self)
            results['current'] = current_value
        except ValueError:
            # Current not available in simulation results
            pass
        
        # Calculate voltage across the source
        terminal_voltages = results['terminal_voltages']
        v_pos_raw = terminal_voltages.get('pos', 0.0)
        v_neg_raw = terminal_voltages.get('neg', 0.0)
        
        # Extract scalar values from simulation data (handles both scalars and arrays)
        v_pos = simulated_circuit._extract_value(v_pos_raw)
        v_neg = simulated_circuit._extract_value(v_neg_raw)
        
        results['voltage_across'] = v_pos - v_neg


class PiecewiseLinearVoltageSource(Component):
    """Piecewise linear voltage source component for time-varying signals."""
    
    def __init__(self, time_voltage_pairs=None, name=None):
        """
        Initialize a piecewise linear voltage source.
        
        Args:
            time_voltage_pairs: List of (time, voltage) tuples defining the waveform.
                              If None, defaults to [(0, 0)] for a 0V constant source.
            name: Optional component name
            
        Examples:
            # Step function: 0V -> 5V at 1ms
            pwl_vs = PiecewiseLinearVoltageSource([(0, 0), (1e-3, 5)])
            
            # Triangle wave: 0V -> 5V -> 0V -> -5V
            pwl_vs = PiecewiseLinearVoltageSource([
                (0, 0), (1e-3, 5), (2e-3, 0), (3e-3, -5)
            ])
        """
        if time_voltage_pairs is None:
            time_voltage_pairs = [(0, 0)]
        
        # Validate input
        if not isinstance(time_voltage_pairs, (list, tuple)) or len(time_voltage_pairs) < 1:
            raise ValueError("time_voltage_pairs must be a non-empty list or tuple of (time, voltage) pairs")
        
        # Validate each pair
        for i, pair in enumerate(time_voltage_pairs):
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise ValueError(f"Element {i} must be a (time, voltage) pair, got {pair}")
            
            time, voltage = pair
            if not isinstance(time, (int, float)) or not isinstance(voltage, (int, float)):
                raise ValueError(f"Time and voltage must be numbers, got {pair}")
            
            if time < 0:
                raise ValueError(f"Time values must be non-negative, got {time}")
        
        # Sort by time to ensure proper ordering
        self.time_voltage_pairs = sorted(time_voltage_pairs, key=lambda x: x[0])
        
        # Validate that times are strictly increasing (no duplicates) after sorting
        for i in range(1, len(self.time_voltage_pairs)):
            if self.time_voltage_pairs[i][0] == self.time_voltage_pairs[i-1][0]:
                raise ValueError(f"Time values must be strictly increasing. "
                               f"Found duplicate time value: {self.time_voltage_pairs[i][0]}")
        
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
        """Convert to SPICE PWL format using NodeMapper."""
        pos_node = mapper.name_for(self.pos)
        neg_node = mapper.name_for(self.neg)
        
        # Build PWL string: PWL(t1 v1 t2 v2 ...)
        pwl_values = []
        for time, voltage in self.time_voltage_pairs:
            pwl_values.append(str(time))
            pwl_values.append(str(voltage))
        
        pwl_string = "PWL(" + " ".join(pwl_values) + ")"
        
        return f"{forced_name or self.name} {pos_node} {neg_node} {pwl_string}"
    
    def _add_derived_results(self, results, simulated_circuit):
        """Add PWL voltage source specific results: current and voltage across."""
        # Use the new deterministic current method
        try:
            current_value = simulated_circuit.get_component_current(self)
            results['current'] = current_value
        except ValueError:
            # Current not available in simulation results
            pass
        
        # Calculate voltage across the source
        terminal_voltages = results['terminal_voltages']
        v_pos_raw = terminal_voltages.get('pos', 0.0)
        v_neg_raw = terminal_voltages.get('neg', 0.0)
        
        # Extract scalar values from simulation data (handles both scalars and arrays)
        v_pos = simulated_circuit._extract_value(v_pos_raw)
        v_neg = simulated_circuit._extract_value(v_neg_raw)
        
        results['voltage_across'] = v_pos - v_neg
    
    def get_voltage_at_time(self, t):
        """
        Calculate the voltage at a specific time using linear interpolation.
        
        Args:
            t: Time value
            
        Returns:
            float: Interpolated voltage at time t
        """
        if t < 0:
            raise ValueError("Time must be non-negative")
        
        # Before first point: use first voltage
        if t <= self.time_voltage_pairs[0][0]:
            return self.time_voltage_pairs[0][1]
        
        # After last point: use last voltage
        if t >= self.time_voltage_pairs[-1][0]:
            return self.time_voltage_pairs[-1][1]
        
        # Find the two points to interpolate between
        for i in range(len(self.time_voltage_pairs) - 1):
            t1, v1 = self.time_voltage_pairs[i]
            t2, v2 = self.time_voltage_pairs[i + 1]
            
            if t1 <= t <= t2:
                # Linear interpolation: v = v1 + (v2-v1) * (t-t1)/(t2-t1)
                if t2 == t1:  # Avoid division by zero (shouldn't happen due to validation)
                    return v1
                return v1 + (v2 - v1) * (t - t1) / (t2 - t1)
        
        # Shouldn't reach here due to the bounds checks above
        return self.time_voltage_pairs[-1][1]
    
    def __repr__(self):
        return f"PiecewiseLinearVoltageSource({self.name}, {len(self.time_voltage_pairs)} points)"


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
        v_n1_raw = terminal_voltages.get('n1', 0.0)
        v_n2_raw = terminal_voltages.get('n2', 0.0)
        
        # Extract scalar values from simulation data (handles both scalars and arrays)
        v_n1 = simulated_circuit._extract_value(v_n1_raw)
        v_n2 = simulated_circuit._extract_value(v_n2_raw)
        
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
        v_pos_raw = terminal_voltages.get('pos', 0.0)
        v_neg_raw = terminal_voltages.get('neg', 0.0)
        
        # Extract scalar values from simulation data (handles both scalars and arrays)
        v_pos = simulated_circuit._extract_value(v_pos_raw)
        v_neg = simulated_circuit._extract_value(v_neg_raw)
        
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
        v_n1_raw = terminal_voltages.get('n1', 0.0)
        v_n2_raw = terminal_voltages.get('n2', 0.0)
        
        # Extract scalar values from simulation data (handles both scalars and arrays)
        v_n1 = simulated_circuit._extract_value(v_n1_raw)
        v_n2 = simulated_circuit._extract_value(v_n2_raw)
        
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
            # Preserve external-only flag if it exists
            if hasattr(definition, '_is_external_only'):
                subckt_def._is_external_only = definition._is_external_only
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


class CurrentSource(Component):
    """DC current source component."""
    
    def __init__(self, current=1e-6, name=None):
        self.current = current
        super().__init__(name)
        
        # Create terminals - these are the nodes in the graph
        self.pos = Terminal(self, "pos")
        self.neg = Terminal(self, "neg")
        
        # Aliases for convenience
        self.positive = self.pos
        self.negative = self.neg
    
    def get_component_type_prefix(self):
        return "I"
    
    def get_terminals(self):
        return [('pos', self.pos), ('neg', self.neg)]
    
    def to_spice(self, mapper, *, forced_name=None):
        """Convert to SPICE format using NodeMapper."""
        pos_node = mapper.name_for(self.pos)
        neg_node = mapper.name_for(self.neg)
        return f"{forced_name or self.name} {pos_node} {neg_node} DC {self.current}"
    
    def _add_derived_results(self, results, simulated_circuit):
        """Add current source specific results: voltage across and power."""
        terminal_voltages = results['terminal_voltages']
        v_pos_raw = terminal_voltages.get('pos', 0.0)
        v_neg_raw = terminal_voltages.get('neg', 0.0)
        
        # Extract scalar values from simulation data (handles both scalars and arrays)
        v_pos = simulated_circuit._extract_value(v_pos_raw)
        v_neg = simulated_circuit._extract_value(v_neg_raw)
        
        voltage_across = v_pos - v_neg
        results['voltage_across'] = voltage_across
        # Current is fixed by the source value
        results['current'] = self.current
        # Calculate power delivered by the source
        results['power'] = voltage_across * self.current


class ExternalSubCircuit(Component):
    """
    A subcircuit that references an external definition (from a library file).
    This doesn't need a local definition - it just references the name.
    """
    def __init__(self, subckt_name, pin_names, name=None, **params):
        super().__init__(name)
        self.subckt_name = subckt_name
        self.pin_names = pin_names
        self.params = params  # Store parameters like W=2e-6, L=0.18e-6
        
        # Create terminals for each pin
        self._terminals = {}
        for pin_name in pin_names:
            terminal = Terminal(self, pin_name)
            self._terminals[pin_name] = terminal
            setattr(self, pin_name, terminal)  # Allows access like mosfet.D, mosfet.G, etc.
    
    def get_component_type_prefix(self):
        return "X"
    
    def get_terminals(self):
        return list(self._terminals.items())
    
    def to_spice(self, mapper, *, forced_name=None):
        """Generates the SPICE 'X' line for this external subcircuit instance."""
        # Get node names in the order specified by pin_names
        node_names = [mapper.name_for(self._terminals[pin_name]) for pin_name in self.pin_names]
        
        # Format parameters
        param_str = ""
        if self.params:
            param_parts = []
            for key, value in self.params.items():
                param_parts.append(f"{key}={value}")
            param_str = " " + " ".join(param_parts)
        
        return f"{forced_name or self.name} {' '.join(node_names)} {self.subckt_name}{param_str}" 
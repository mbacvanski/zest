"""
Circuit class for representing and manipulating electronic circuits as graphs.
"""

from .components import gnd
from abc import ABC, abstractmethod

# No global circuit registry - components must be explicitly added to circuits


class NodeMapper:
    """Helper class for mapping terminals to SPICE node names."""
    
    def __init__(self, pin_overrides=None):
        """
        Initialize with optional pin name overrides.
        
        Args:
            pin_overrides: dict mapping Terminal -> str for custom pin names
        """
        self.pin_overrides = pin_overrides or {}
    
    def name_for(self, terminal):
        """
        Get the SPICE node name for a terminal.
        
        Args:
            terminal: Terminal object or gnd
            
        Returns:
            str: SPICE node name
        """
        # Use override if available
        if terminal in self.pin_overrides:
            return self.pin_overrides[terminal]
        
        # Special case for ground
        if terminal is gnd:
            return "gnd"
        
        # Otherwise, use the default logic
        if hasattr(terminal, '__str__'):
            return str(terminal).replace('.', '_')  # Replace dots for SPICE compatibility
        else:
            return f"n{id(terminal) % 10000}"  # Fallback node name


class NetlistBlock(ABC):
    """
    Abstract base class for circuit-like structures that can hold components, 
    wires, and pins, and be compiled to SPICE netlists.
    """
    
    def __init__(self, name="Untitled Block"):
        self.name = name
        self.components = []
        self.wires = []  # List of (terminal1, terminal2) wire connections
        self.gnd = gnd   # Circuit's ground reference
        self._component_names = {}  # Maps component -> final name
        self._initial_conditions = {}  # Maps terminal -> initial voltage
        self.pins = {}  # Maps pin name -> Terminal for subcircuit definitions
        self._include_models = set()  # Set of external SPICE model text to include
        self.includes = []  # List of external SPICE file dependencies
    
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
        if isinstance(terminal1, Terminal) and terminal1.component is not None and terminal1.component not in self.components:
            self.add_component(terminal1.component)
        if isinstance(terminal2, Terminal) and terminal2.component is not None and terminal2.component not in self.components:
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
    
    def add_pin(self, name, terminal):
        """
        Exposes an internal terminal as an external pin of the circuit.
        This is necessary when this circuit is used as a subcircuit definition.

        Args:
            name: The external name for the pin (e.g., "input", "output", "vcc").
            terminal: The internal Terminal object to expose.
        """
        from .components import Terminal  # Avoid circular import issues
        if not isinstance(terminal, Terminal):
            raise TypeError(f"Pin must be connected to a Terminal, not {type(terminal)}.")
        if terminal.component is not None and terminal.component not in self.components:
            raise ValueError("Cannot add a pin to a terminal of a component that is not in this circuit.")

        self.pins[name] = terminal
    
    def include_model(self, model_text):
        """
        Include external SPICE model definitions in this circuit.
        
        Args:
            model_text: Raw SPICE text containing .SUBCKT/.MODEL definitions
        """
        if isinstance(model_text, str) and model_text.strip():
            self._include_models.add(model_text.strip())
    
    def add_include(self, path: str):
        """
        Registers an external SPICE file (.INCLUDE) dependency for this circuit.
        Paths should be relative to the simulation execution directory.

        Args:
            path: The path to the .lib, .mod, or .inc file.
        """
        if path not in self.includes:
            self.includes.append(path)
    
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
            prefix = component.get_component_type_prefix()
            if component._requested_name:
                self._component_names[component] = f"{prefix}{component._requested_name}"
            else:
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
    
    def all_terminals(self):
        """Get all terminals from all components in this block."""
        for component in self.components:
            for terminal_name, terminal in component.get_terminals():
                yield terminal
    
    def _compile_as_subcircuit(self):
        """Legacy method for backwards compatibility with old SubCircuit system."""
        # This compilation must happen in a 'sandboxed' way. Node names inside the
        # subcircuit should be relative to its pins, not the parent circuit's wiring.
        self._assign_component_names()
        
        # Update component names to match our assignments
        for component in self.components:
            component.name = self.get_component_name(component)

        pin_order = list(self.pins.keys())
        header = f".SUBCKT {self.name} {' '.join(pin_order)}"

        body_lines = []
        
        # Store reference to the original method before any overrides
        original_get_node_method = self.get_spice_node_name
        
        for component in self.components:
            # IMPORTANT: For node name resolution, we need a mapping from internal terminals
            # to the public pin names.

            # Create a temporary mapping for this subcircuit's compilation.
            def get_subcircuit_node_name(terminal):
                # Check if this terminal (or any terminal it's connected to) is an exposed pin.
                for pin_name, pin_terminal in self.pins.items():
                    # The `_find_connected_terminals` method correctly finds all electrically
                    # common points within this circuit's context.
                    if pin_terminal in self._find_connected_terminals(terminal):
                        return pin_name

                # If not a pin, it's an internal node. Use the standard naming scheme,
                # but ensure it's unique within the context of this subcircuit.
                # Call the original method directly to avoid recursion.
                return original_get_node_method(terminal)

            # Temporarily override the get_spice_node_name method for this component's to_spice call
            self.get_spice_node_name = get_subcircuit_node_name

            try:
                body_lines.append(component.to_spice(self))
            finally:
                # Restore the original method
                self.get_spice_node_name = original_get_node_method

        footer = f".ENDS {self.name}"

        return "\n".join([header] + body_lines + [footer])

    @abstractmethod
    def compile(self, mapper=None):
        """
        Compile this netlist block to SPICE format.
        
        Args:
            mapper: NodeMapper instance for custom node naming
            
        Returns:
            str: SPICE netlist representation
        """
        pass


class CircuitRoot(NetlistBlock):
    """
    Represents a top-level electronic circuit for simulation.
    This is the main circuit that can be simulated.
    """
    
    def __init__(self, name="Untitled Circuit"):
        super().__init__(name)
        # Components must be explicitly added to circuits
    
    def compile(self, mapper=None):
        """
        Compile this circuit root to SPICE format for simulation.
        
        Args:
            mapper: NodeMapper instance (ignored for top-level circuits)
            
        Returns:
            str: Complete SPICE netlist ready for simulation
        """
        return self.compile_to_spice()
    
    def compile_to_spice(self):
        """Compile the circuit to SPICE netlist format, including subcircuits and includes."""
        from .components import SubCircuit

        # 1. Recursively collect all unique include paths from the entire design.
        #    Using a set handles de-duplication automatically.
        all_includes = set(self.includes)
        circuits_to_scan = [self]
        scanned_definitions = {self.name: self}

        while circuits_to_scan:
            current_circuit = circuits_to_scan.pop()
            for component in current_circuit.components:
                if isinstance(component, (SubCircuit, SubCircuitInst)):
                    definition = component.definition
                    if definition.name not in scanned_definitions:
                        all_includes.update(definition.includes)
                        scanned_definitions[definition.name] = definition
                        circuits_to_scan.append(definition) # Scan for nested subcircuits

        # 2. Assign component names for the entire circuit.
        self._assign_component_names()
        for component in self.components:
            component.name = self.get_component_name(component)

        # 3. Build the netlist string.
        lines = [f"* Circuit: {self.name}", ""]

        # 4. Write the clean, de-duplicated .INCLUDE block first.
        if all_includes:
            lines.append("* ===== Model Includes ===== *")
            for include_path in sorted(list(all_includes)):
                lines.append(f'.INCLUDE "{include_path}"')
            lines.append("")

        # Add external model includes (legacy support)
        if self._include_models:
            lines.append("* ===== External Model Definitions ===== *")
            for model_text in sorted(self._include_models):
                lines.append(model_text)
                lines.append("")

        # 5. Find and write all unique .SUBCKT definitions.
        unique_definitions = {}  # Use dict to track by name for deduplication
        for component in self.components:
            if isinstance(component, (SubCircuit, SubCircuitInst)):
                definition = component.definition
                # Only add if we haven't seen this definition name before
                if definition.name not in unique_definitions:
                    unique_definitions[definition.name] = definition
        
        # Filter out external-only subcircuits (defined in .INCLUDE files)
        internal_definitions = {
            name: definition for name, definition in unique_definitions.items()
            if not getattr(definition, '_is_external_only', False)
        }
        
        if internal_definitions:
            lines.append("* ===== Subcircuit Definitions ===== *")
            # Sort for consistent output in golden file testing
            for name in sorted(internal_definitions.keys()):
                definition = internal_definitions[name]
                if hasattr(definition, 'compile_as_subckt'):
                    # New SubCircuitDef
                    lines.append(definition.compile_as_subckt())
                else:
                    # Legacy Circuit with _compile_as_subcircuit method
                    lines.append(definition._compile_as_subcircuit())
                lines.append("")
            lines.append("* ===== Main Circuit Components ===== *")

        # 6. Write the main circuit component and instance lines.
        for component in self.components:
            lines.append(component.to_spice(self))

        # 7. Add initial conditions if any.
        if self._initial_conditions:
            lines.append("")
            lines.append("* Initial Conditions")
            node_ics = {}
            for terminal, voltage in self._initial_conditions.items():
                node_name = self.get_spice_node_name(terminal)
                if node_name != "gnd":
                    node_ics[node_name] = voltage
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


class SubCircuitDef(NetlistBlock):
    """
    Represents a reusable subcircuit definition that can be instantiated.
    This corresponds to a .SUBCKT definition in SPICE.
    """
    
    def __init__(self, name="Untitled SubCircuit"):
        super().__init__(name)
    
    def create_instance(self, name=None):
        """
        Create an instance of this subcircuit definition.
        
        Args:
            name: Name for the instance (optional)
            
        Returns:
            SubCircuitInst: Instance that can be used as a component
        """
        return SubCircuitInst(definition=self, name=name)
    
    def compile(self, mapper=None):
        """
        Compile this subcircuit definition to .SUBCKT format.
        
        Args:
            mapper: NodeMapper instance for custom pin naming
            
        Returns:
            str: .SUBCKT definition
        """
        return self.compile_as_subckt(mapper)
    
    def compile_as_subckt(self, mapper=None):
        """
        Compile this subcircuit into a .SUBCKT block.
        
        Args:
            mapper: NodeMapper instance for pin naming overrides
            
        Returns:
            str: .SUBCKT definition
        """
        # Create pin name overrides for the mapper
        pin_overrides = {}
        if mapper:
            pin_overrides.update(mapper.pin_overrides)
        
        # Add our pins to the overrides
        for pin_name, pin_terminal in self.pins.items():
            # Find all terminals connected to this pin
            connected_terminals = self._find_connected_terminals(pin_terminal)
            for terminal in connected_terminals:
                pin_overrides[terminal] = pin_name
        
        # Create mapper with pin overrides
        subckt_mapper = NodeMapper(pin_overrides)
        
        # Assign component names
        self._assign_component_names()
        for component in self.components:
            component.name = self.get_component_name(component)
        
        # Build the .SUBCKT definition
        pin_order = list(self.pins.keys())
        header = f".SUBCKT {self.name} {' '.join(pin_order)}"
        
        body_lines = []
        for component in self.components:
            body_lines.append(component.to_spice_with_mapper(subckt_mapper))
        
        footer = f".ENDS {self.name}"
        
        return "\n".join([header] + body_lines + [footer])


class SubCircuitInst:
    """
    Represents an instance of a subcircuit definition.
    Behaves like a Component but delegates to its definition.
    """
    
    def __init__(self, definition, name=None):
        if not isinstance(definition, SubCircuitDef):
            raise TypeError("definition must be a SubCircuitDef instance")
        if not definition.pins:
            raise ValueError(f"The subcircuit definition '{definition.name}' has no external pins defined.")
        
        self.definition = definition
        self._requested_name = name
        self.name = name or "UNNAMED"
        
        # Create terminals for each pin
        from .components import Terminal
        self.terminals = {}
        for pin_name in definition.pins.keys():
            terminal = Terminal(self, pin_name)
            self.terminals[pin_name] = terminal
            setattr(self, pin_name, terminal)  # Allow access like instance.vcc
    
    def get_component_type_prefix(self):
        """Get the SPICE prefix for subcircuit instances."""
        return "X"
    
    def get_terminals(self):
        """Get list of (terminal_name, terminal) tuples."""
        return list(self.terminals.items())
    
    def to_spice(self, circuit):
        """Generate SPICE line for this subcircuit instance."""
        # Get node names in parent circuit context
        pin_order = list(self.definition.pins.keys())
        node_names = [
            circuit.get_spice_node_name(self.terminals[pin_name])
            for pin_name in pin_order
        ]
        return f"{self.name} {' '.join(node_names)} {self.definition.name}"
    
    def to_spice_with_mapper(self, mapper):
        """Generate SPICE line using NodeMapper."""
        pin_order = list(self.definition.pins.keys())
        node_names = [
            mapper.name_for(self.terminals[pin_name])
            for pin_name in pin_order
        ]
        return f"{self.name} {' '.join(node_names)} {self.definition.name}"
    
    def extract_simulation_results(self, simulated_circuit):
        """Extract simulation results for this subcircuit instance."""
        # Reuse Component's implementation
        from .components import Component
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
        return results
    
    def __repr__(self):
        return f"SubCircuitInst({self.name}, definition={self.definition.name})"


# Backwards compatibility: Circuit is an alias for CircuitRoot
Circuit = CircuitRoot
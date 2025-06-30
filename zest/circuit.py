"""
Circuit class for representing and manipulating electronic circuits as graphs.
"""

from .components import gnd
from abc import ABC, abstractmethod
from typing import Callable, Iterable, Mapping

# No global circuit registry - components must be explicitly added to circuits


class NodeMapper:
    """
    Pure helper that maps Terminal objects (and anything electrically connected
    to them) to deterministic SPICE node names.
    """

    def __init__(
        self,
        connectivity_fn: Callable,
        pin_aliases: Mapping = None,
    ):
        self._connected = connectivity_fn       # injected from NetlistBlock
        self._pin_aliases = dict(pin_aliases or {})
        self._cache = {}  # dict[Terminal, str] = {}
        self._counter = 1                       # for auto N1, N2, …

    def name_for(self, t):
        """Get SPICE node name for terminal t."""
        # Special case for ground - handle before other logic
        if t is gnd:
            return "gnd"
        
        # Check if this terminal is connected to ground
        connected_terminals = self._connected(t)
        if gnd in connected_terminals:
            return "gnd"
        
        # 1. Check if this terminal (or any connected terminal) is an external pin
        for pin_terminal, pin_name in self._pin_aliases.items():
            if pin_terminal in connected_terminals:
                return pin_name

        # 2. if already assigned (by equivalence), reuse
        for k, name in self._cache.items():
            if t in self._connected(k):
                return name

        # 3. Generate generic node name
        spice_name = f"N{self._counter}"
        self._counter += 1
        
        self._cache[t] = spice_name
        return spice_name


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
        self._node_mapper = None  # Cached NodeMapper instance for backward compatibility
    
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
    
    def _assign_component_names_pure(self):
        """
        Assign names to components without mutating them.
        Returns dict mapping component -> assigned name.
        """
        name_table = {}
        type_counts = {}
        
        for component in self.components:
            # Use requested name if provided, otherwise auto-generate
            prefix = component.get_component_type_prefix()
            if component._requested_name:
                name_table[component] = f"{prefix}{component._requested_name}"
            else:
                type_counts[prefix] = type_counts.get(prefix, 0) + 1
                name_table[component] = f"{prefix}{type_counts[prefix]}"
        
        return name_table
    
    def get_spice_node_name(self, terminal):
        """
        Get the SPICE node name for a terminal based on the circuit's wiring.
        This method is kept for backward compatibility and uses NodeMapper internally.
        
        Args:
            terminal: Terminal object or gnd
            
        Returns:
            str: SPICE node name
        """
        # Create a cached NodeMapper for consistency across calls
        if self._node_mapper is None:
            self._node_mapper = NodeMapper(self._find_connected_terminals)
        return self._node_mapper.name_for(terminal)
    
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
        # Implement the subcircuit compilation logic for CircuitRoot
        # A. deterministic pin order
        pin_order = list(self.pins.keys())

        # B. assign component names without side-effects
        name_table = self._assign_component_names_pure()
        
        # C. Temporarily set component names for NodeMapper to work correctly
        original_names = {}
        for comp, assigned_name in name_table.items():
            original_names[comp] = comp.name
            comp.name = assigned_name

        try:
            # D. create mapper with pin aliases
            mapper = NodeMapper(
                connectivity_fn=self._find_connected_terminals,
                pin_aliases={term: pin for pin, term in self.pins.items()},
            )

            # E. emit body
            body_lines = []
            for comp in self.components:
                body_lines.append(
                    comp.to_spice(mapper, forced_name=name_table[comp])
                )
        finally:
            # F. restore original component names (pure function requirement)
            for comp, original_name in original_names.items():
                comp.name = original_name

        # G. wrap
        header = f".SUBCKT {self.name} " + " ".join(pin_order)
        footer = f".ENDS {self.name}"
        return "\n".join([header, *body_lines, footer])

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

        # 2. Create mapper and assign component names for the entire circuit.
        mapper = NodeMapper(self._find_connected_terminals)
        name_table = self._assign_component_names_pure()
        
        # For backward compatibility, also update component.name attributes
        for component, assigned_name in name_table.items():
            component.name = assigned_name
        
        # Cache the NodeMapper used for compilation to ensure consistency with result extraction
        self._node_mapper = mapper

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

        # 5. Use the recursively collected subcircuit definitions.
        # Remove the main circuit itself and filter out external-only subcircuits
        internal_definitions = {
            name: definition for name, definition in scanned_definitions.items()
            if name != self.name and not getattr(definition, '_is_external_only', False)
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
            lines.append(component.to_spice(mapper, forced_name=name_table[component]))

        # 7. Add initial conditions if any.
        if self._initial_conditions:
            lines.append("")
            lines.append("* Initial Conditions")
            node_ics = {}
            for terminal, voltage in self._initial_conditions.items():
                node_name = mapper.name_for(terminal)
                if node_name != "gnd":  # Use "gnd" instead of "0" for ground
                    node_ics[node_name] = voltage
            for node_name, voltage in node_ics.items():
                lines.append(f".IC V({node_name})={voltage}")

        lines.append("")
        lines.append(".end")
        return "\n".join(lines)
    
    def get_simulator(self):
        """Get a simulator for this circuit (legacy compatibility)."""
        from .simulation import CircuitSimulator
        return CircuitSimulator(self)
    
    def simulate_operating_point(self, backend=None, temperature=25, add_current_probes=False, keep_temp_files=False, debug_cleanup=False):
        """Run DC operating point analysis."""
        if backend is None:
            from .simulation import SpicelibBackend
            backend = SpicelibBackend()
        
        netlist = self.compile_to_spice()
        return backend.run(
            netlist, 
            analyses=["op"], 
            temperature=temperature,
            circuit=self,
            keep_temp_files=keep_temp_files,
            debug_cleanup=debug_cleanup
        )
    
    def simulate_dc_sweep(self, source_name, start, stop, step, backend=None, temperature=25, keep_temp_files=False):
        """Run DC sweep analysis."""
        if backend is None:
            from .simulation import SpicelibBackend
            backend = SpicelibBackend()
        
        netlist = self.compile_to_spice()
        return backend.run(
            netlist,
            analyses=["dc"],
            temperature=temperature,
            circuit=self,
            source_name=source_name,
            start=start,
            stop=stop,
            step=step,
            keep_temp_files=keep_temp_files
        )
    
    def simulate_ac(self, start_freq=1, stop_freq=1e6, points_per_decade=10, backend=None, temperature=25, keep_temp_files=False):
        """Run AC analysis."""
        if backend is None:
            from .simulation import SpicelibBackend
            backend = SpicelibBackend()
        
        netlist = self.compile_to_spice()
        return backend.run(
            netlist,
            analyses=["ac"],
            temperature=temperature,
            circuit=self,
            start_freq=start_freq,
            stop_freq=stop_freq,
            points_per_decade=points_per_decade,
            keep_temp_files=keep_temp_files
        )
    
    def simulate_transient(self, step_time, end_time, start_time=0, backend=None, temperature=25, keep_temp_files=False):
        """Run transient analysis."""
        if backend is None:
            from .simulation import SpicelibBackend
            backend = SpicelibBackend()
        
        netlist = self.compile_to_spice()
        return backend.run(
            netlist,
            analyses=["transient"],
            temperature=temperature,
            circuit=self,
            step_time=step_time,
            end_time=end_time,
            start_time=start_time,
            keep_temp_files=keep_temp_files
        )
    
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
        Pure function: return a `.SUBCKT / .ENDS` string.
        Must NOT mutate self or child components.
        
        Args:
            mapper: NodeMapper instance for pin naming overrides (unused for now)
            
        Returns:
            str: .SUBCKT definition
        """
        # A. deterministic pin order
        pin_order = list(self.pins.keys())

        # B. assign component names without side-effects
        name_table = self._assign_component_names_pure()
        
        # C. Temporarily set component names for NodeMapper to work correctly
        original_names = {}
        for comp, assigned_name in name_table.items():
            original_names[comp] = comp.name
            comp.name = assigned_name

        try:
            # D. create mapper with pin aliases
            mapper = NodeMapper(
                connectivity_fn=self._find_connected_terminals,
                pin_aliases={term: pin for pin, term in self.pins.items()},
            )

            # E. emit body
            body_lines = []
            for comp in self.components:
                body_lines.append(
                    comp.to_spice(mapper, forced_name=name_table[comp])
                )
        finally:
            # F. restore original component names (pure function requirement)
            for comp, original_name in original_names.items():
                comp.name = original_name

        # G. wrap
        header = f".SUBCKT {self.name} " + " ".join(pin_order)
        footer = f".ENDS {self.name}"
        return "\n".join([header, *body_lines, footer])


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
    
    def to_spice(self, mapper, *, forced_name=None):
        """Generate SPICE line for this subcircuit instance."""
        # Handle backward compatibility: if mapper is actually a circuit, adapt it
        if hasattr(mapper, 'get_spice_node_name'):
            # Old interface: mapper is actually a circuit
            circuit = mapper
            pin_order = list(self.definition.pins.keys())
            node_names = [
                circuit.get_spice_node_name(self.terminals[pin_name])
                for pin_name in pin_order
            ]
        else:
            # New interface: mapper is a NodeMapper
            pin_order = list(self.definition.pins.keys())
            node_names = [
                mapper.name_for(self.terminals[pin_name])
                for pin_name in pin_order
            ]
        return f"{forced_name or self.name} {' '.join(node_names)} {self.definition.name}"
    
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
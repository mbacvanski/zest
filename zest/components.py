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
        
        # Auto-register with current circuit if one exists
        from .circuit import get_current_circuit
        current_circuit = get_current_circuit()
        if current_circuit:
            current_circuit.add_component(self)
    
    def get_component_type_prefix(self):
        """Get the SPICE prefix for this component type."""
        # This will be overridden by subclasses
        return "X"
    
    def to_spice(self, circuit):
        """Convert to SPICE netlist format using circuit's node mapping."""
        raise NotImplementedError("Subclasses must implement to_spice()")
    
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
    
    def to_spice(self, circuit):
        """Convert to SPICE format using circuit's node mapping."""
        pos_node = circuit.get_spice_node_name(self.pos)
        neg_node = circuit.get_spice_node_name(self.neg)
        return f"{self.name} {pos_node} {neg_node} DC {self.voltage}"


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
    
    def to_spice(self, circuit):
        """Convert to SPICE format using circuit's node mapping."""
        n1_node = circuit.get_spice_node_name(self.n1)
        n2_node = circuit.get_spice_node_name(self.n2)
        return f"{self.name} {n1_node} {n2_node} {self.resistance}"


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
    
    def to_spice(self, circuit):
        """Convert to SPICE format using circuit's node mapping."""
        pos_node = circuit.get_spice_node_name(self.pos)
        neg_node = circuit.get_spice_node_name(self.neg)
        return f"{self.name} {pos_node} {neg_node} {self.capacitance}"


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
    
    def to_spice(self, circuit):
        """Convert to SPICE format using circuit's node mapping."""
        n1_node = circuit.get_spice_node_name(self.n1)
        n2_node = circuit.get_spice_node_name(self.n2)
        return f"{self.name} {n1_node} {n2_node} {self.inductance}" 
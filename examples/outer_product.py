from zest.circuit import Circuit, SubCircuitDef
from zest.components import Component, Terminal, SubCircuit
import numpy as np
import matplotlib.pyplot as plt
import os


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


def create_comparator_subcircuit_def():
    """Create a proper differential pair comparator subcircuit definition."""
    lif = SubCircuitDef("comparator")

    # Use relative path like in working test
    lif.add_include("examples/models/mosfets.lib")

    # Add external pins for the comparator
    pin_in1 = Terminal()
    pin_in2 = Terminal()
    pin_out = Terminal()
    pin_vdd = Terminal()
    pin_vss = Terminal()
    
    lif.add_pin("IN1", pin_in1)
    lif.add_pin("IN2", pin_in2)
    lif.add_pin("OUT", pin_out)
    lif.add_pin("VDD", pin_vdd)
    lif.add_pin("VSS", pin_vss)
    
    # Create internal nodes
    n1_terminal = Terminal()  # Common source node for differential pair
    n2_terminal = Terminal()  # Drain of M1 (reference side)
    
    # Current source: I1 from N1 to VSS (bias for differential pair)
    i1 = CurrentSource(current=10e-6, name="I1")  # 10µA
    lif.add_component(i1)
    lif.wire(i1.pos, n1_terminal)  # Positive to common source
    lif.wire(i1.neg, pin_vss)      # Negative to VSS
    
    # PROPER DIFFERENTIAL PAIR: Sources connected together
    # M1: Reference side (Drain=N2, Gate=IN1, Source=N1, Bulk=VSS)
    m1 = ExternalSubCircuit("NMOS_SUBCKT", ["D", "G", "S", "B"], name="M1", W="2u", L="0.18u")
    lif.add_component(m1)
    lif.wire(m1.D, n2_terminal)  # Drain to N2 (reference)
    lif.wire(m1.G, pin_in1)      # Gate to IN1
    lif.wire(m1.S, n1_terminal)  # Source to N1 (common source) ← KEY FIX!
    lif.wire(m1.B, pin_vss)      # Bulk to VSS
    
    # M2: Output side (Drain=OUT, Gate=IN2, Source=N1, Bulk=VSS)
    m2 = ExternalSubCircuit("NMOS_SUBCKT", ["D", "G", "S", "B"], name="M2", W="2u", L="0.18u")
    lif.add_component(m2)
    lif.wire(m2.D, pin_out)      # Drain to OUT ← This will switch!
    lif.wire(m2.G, pin_in2)      # Gate to IN2
    lif.wire(m2.S, n1_terminal)  # Source to N1 (common source) ← KEY FIX!
    lif.wire(m2.B, pin_vss)      # Bulk to VSS
    
    # PMOS CURRENT MIRROR LOAD (proper active load)
    # M3: Current mirror reference (Drain=N2, Gate=N2, Source=VDD, Bulk=VDD)
    m3 = ExternalSubCircuit("PMOS_SUBCKT", ["D", "G", "S", "B"], name="M3", W="2u", L="0.18u")
    lif.add_component(m3)
    lif.wire(m3.D, n2_terminal)  # Drain to N2
    lif.wire(m3.G, n2_terminal)  # Gate to N2 (diode connection)
    lif.wire(m3.S, pin_vdd)      # Source to VDD
    lif.wire(m3.B, pin_vdd)      # Bulk to VDD
    
    # M4: Current mirror output (Drain=OUT, Gate=N2, Source=VDD, Bulk=VDD)
    m4 = ExternalSubCircuit("PMOS_SUBCKT", ["D", "G", "S", "B"], name="M4", W="2u", L="0.18u")
    lif.add_component(m4)
    lif.wire(m4.D, pin_out)      # Drain to OUT
    lif.wire(m4.G, n2_terminal)  # Gate to N2 (current mirror)
    lif.wire(m4.S, pin_vdd)      # Source to VDD
    lif.wire(m4.B, pin_vdd)      # Bulk to VDD
    
    return lif


def create_comparator_test_circuit(vin1_voltage=0.9, vin2_voltage=0.8):
    """Create a test circuit for the comparator with specified input voltages."""
    from zest.components import VoltageSource
    
    # Create the test circuit
    test_circuit = Circuit("ComparatorTest")
    
    # Use relative path like in working test
    test_circuit.add_include("examples/models/mosfets.lib")
    
    # Create comparator subcircuit definition
    comparator_def = create_comparator_subcircuit_def()
    
    # Add voltage sources
    vdd = VoltageSource(voltage=1.8, name="VDD")
    vss = VoltageSource(voltage=0.0, name="VSS") 
    vin1 = VoltageSource(voltage=vin1_voltage, name="VIN1")
    vin2 = VoltageSource(voltage=vin2_voltage, name="VIN2")
    
    # Create comparator instance
    comp = SubCircuit(definition=comparator_def, name="COMP1")
    
    # Wire up the test circuit
    test_circuit.wire(vdd.neg, test_circuit.gnd)
    test_circuit.wire(vss.pos, test_circuit.gnd)
    test_circuit.wire(vin1.neg, test_circuit.gnd)
    test_circuit.wire(vin2.neg, test_circuit.gnd)
    
    test_circuit.wire(comp.VDD, vdd.pos)
    test_circuit.wire(comp.VSS, vss.neg)
    test_circuit.wire(comp.IN1, vin1.pos)
    test_circuit.wire(comp.IN2, vin2.pos)
    
    return test_circuit, comp, vin1, vin2

def demo_comparator_dc_sweep_simulation():
    """Use zest's built-in DC sweep to analyze the comparator."""
    print("\n⚡ DC Sweep Simulation (Built-in)")
    print("=" * 50)
    
    # Create circuit with VIN1 as the swept source
    circuit, comp, vin1_src, vin2_src = create_comparator_test_circuit(0.8, 0.8)
    
    # Use zest's DC sweep functionality
    print("Running DC sweep of VIN1 from 0.5V to 1.1V...")
    
    # Get the component name for the voltage source
    vin1_name = circuit.get_component_name(vin1_src)
    
    simulated_circuit = circuit.simulate_dc_sweep(
        source_name=vin1_name,
        start=0.5,
        stop=1.1, 
        step=0.001
    )
    
    print("✅ DC sweep simulation completed!")
    
    # Get sweep results
    sweep_var = simulated_circuit.get_sweep_variable()
    vout_sweep = simulated_circuit.get_node_voltage(comp.OUT)
    
    print(f"Sweep variable: {len(sweep_var)} points from {sweep_var[0]:.2f}V to {sweep_var[-1]:.2f}V")
    print(f"Output voltage range: {min(vout_sweep):.3f}V to {max(vout_sweep):.3f}V")
    
    # Find switching point
    mid_voltage = 0.9  # VDD/2 as switching threshold
    crossing_indices = []
    for i in range(len(vout_sweep) - 1):
        if (vout_sweep[i] < mid_voltage < vout_sweep[i+1]) or (vout_sweep[i] > mid_voltage > vout_sweep[i+1]):
            crossing_indices.append(i)
    
    if crossing_indices:
        switch_voltage = sweep_var[crossing_indices[0]]
        print(f"🎯 Switching point found at VIN1 ≈ {switch_voltage:.3f}V")
    
    # Plot DC sweep results
    plt.figure(figsize=(10, 6))
    plt.plot(sweep_var, vout_sweep, 'b-', linewidth=2, label='VOUT')
    plt.axhline(y=mid_voltage, color='r', linestyle='--', alpha=0.7, label='Switching threshold')
    plt.axvline(x=0.8, color='g', linestyle='--', alpha=0.7, label='VIN2 = 0.8V')
    plt.xlabel('VIN1 (V)')
    plt.ylabel('VOUT (V)')
    plt.title('Comparator DC Sweep Analysis')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.xlim(0.5, 1.1)
    plt.ylim(0, 1.8)
    
    plt.savefig('comparator_dc_sweep.png', dpi=150, bbox_inches='tight')
    print(f"📊 DC sweep plot saved as 'comparator_dc_sweep.png'")
    plt.show()

def main():
    # Create the comparator subcircuit definition
    comparator_def = create_comparator_subcircuit_def()
    
    # Test the subcircuit by creating a simple test circuit
    test_circuit = Circuit("ComparatorTest")
    
    # Use relative path like in working test
    test_circuit.add_include("examples/models/mosfets.lib")
    
    # Add voltage sources for testing
    from zest.components import VoltageSource
    
    vdd = VoltageSource(voltage=1.8, name="VDD")
    vss = VoltageSource(voltage=0.0, name="VSS") 
    vin1 = VoltageSource(voltage=0.9, name="VIN1")
    vin2 = VoltageSource(voltage=0.8, name="VIN2")
    
    # Create comparator instance
    comp = SubCircuit(definition=comparator_def, name="COMP1")
    
    # Wire up the test circuit
    test_circuit.wire(vdd.neg, test_circuit.gnd)
    test_circuit.wire(vss.pos, test_circuit.gnd)
    test_circuit.wire(vin1.neg, test_circuit.gnd)
    test_circuit.wire(vin2.neg, test_circuit.gnd)
    
    test_circuit.wire(comp.VDD, vdd.pos)
    test_circuit.wire(comp.VSS, vss.neg)
    test_circuit.wire(comp.IN1, vin1.pos)
    test_circuit.wire(comp.IN2, vin2.pos)
    
    print("Comparator subcircuit created successfully!")
    print("SPICE netlist preview:")
    print(test_circuit.compile_to_spice())
    
    # Run simulation demos
    print("\n" + "="*60)
    print("🚀 RUNNING COMPARATOR SIMULATION DEMOS")
    print("="*60)
    
    # Demo 3: Built-in DC sweep
    demo_comparator_dc_sweep_simulation()


if __name__ == "__main__":
    main()
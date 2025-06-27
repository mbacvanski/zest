#!/usr/bin/env python3
"""
Example demonstrating how easy it is to add new component types 
with the refactored object-oriented design.
"""

from zest.components import Component, Terminal
from zest import Circuit, VoltageSource, Resistor, gnd


class Diode(Component):
    """Example of a new component type - diode."""
    
    def __init__(self, is_value=1e-12, vf=0.7, name=None):
        self.is_value = is_value  # Saturation current
        self.vf = vf  # Forward voltage drop
        super().__init__(name)
        
        # Create terminals
        self.anode = Terminal(self, "anode")
        self.cathode = Terminal(self, "cathode")
    
    def get_component_type_prefix(self):
        return "D"
    
    def get_terminals(self):
        return [('anode', self.anode), ('cathode', self.cathode)]
    
    def to_spice(self, circuit):
        """Convert to SPICE format - simplified ideal diode model."""
        anode_node = circuit.get_spice_node_name(self.anode)
        cathode_node = circuit.get_spice_node_name(self.cathode)
        # For this example, we'll model as a voltage source + resistor
        return f"* {self.name} (Diode) {anode_node} {cathode_node}"
    
    def _add_derived_results(self, results, simulated_circuit):
        """Add diode-specific simulation results."""
        terminal_voltages = results['terminal_voltages']
        v_anode = terminal_voltages.get('anode', 0.0)
        v_cathode = terminal_voltages.get('cathode', 0.0)
        
        if isinstance(v_anode, (int, float)) and isinstance(v_cathode, (int, float)):
            forward_voltage = v_anode - v_cathode
            results['forward_voltage'] = forward_voltage
            results['is_forward_biased'] = forward_voltage > 0.1  # Simple threshold
            results['voltage_drop'] = abs(forward_voltage) if forward_voltage > 0 else 0.0


def main():
    print("🔧 Demonstrating Easy Component Extension")
    print("=" * 50)
    
    # Create a circuit with our new Diode component
    circuit = Circuit("Diode Test Circuit")
    
    # Traditional components
    vs = VoltageSource(voltage=5.0, name="V_supply")
    r1 = Resistor(resistance=1000, name="R_current_limit")
    
    # NEW component type - works seamlessly!
    d1 = Diode(name="D_led")
    
    # Wire the circuit: V_supply -> R1 -> Diode -> Ground
    circuit.wire(vs.pos, r1.n1)
    circuit.wire(r1.n2, d1.anode)
    circuit.wire(vs.neg, gnd)
    circuit.wire(d1.cathode, gnd)
    
    print(f"Circuit created with {len(circuit.components)} components:")
    for comp in circuit.components:
        print(f"  - {comp}")
    print()
    
    print("Generated SPICE netlist:")
    print("-" * 25)
    spice_netlist = circuit.compile_to_spice()
    print(spice_netlist)
    print("-" * 25)
    print()
    
    # Simulate the circuit (this won't run actual SPICE since we didn't implement
    # proper SPICE model for diode, but we can show the API)
    print("🎯 Component Extension Benefits:")
    print("-" * 30)
    
    print("✅ New Diode component:")
    print(f"   - Has terminals: {[name for name, _ in d1.get_terminals()]}")
    print(f"   - Implements get_terminals(): {d1.get_terminals()}")
    print(f"   - Has _add_derived_results() method for custom simulation data")
    print(f"   - SPICE prefix: {d1.get_component_type_prefix()}")
    print()
    
    print("✅ SimulatedCircuit compatibility:")
    print("   - No changes needed to SimulatedCircuit class!")
    print("   - get_component_results() will automatically work with Diode")
    print("   - Polymorphic design handles the new component type")
    print()
    
    # Mock what the simulation results would look like
    print("✅ Example simulation results for Diode:")
    mock_results = {
        'component': d1,
        'component_name': 'D_led',
        'analysis_type': 'DC Operating Point',
        'terminal_voltages': {'anode': 2.3, 'cathode': 0.0},
        'forward_voltage': 2.3,
        'is_forward_biased': True,
        'voltage_drop': 2.3
    }
    
    for key, value in mock_results.items():
        if key != 'component':
            print(f"   {key}: {value}")
    print()
    
    print("🎉 Key Benefits of the Refactored Design:")
    print("   • Add new components without modifying SimulatedCircuit")
    print("   • Each component encapsulates its own simulation logic")
    print("   • Clean polymorphic design with no isinstance checks")
    print("   • Easy to extend and maintain")
    print("   • Follows SOLID principles")


if __name__ == "__main__":
    main() 
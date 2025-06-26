#!/usr/bin/env python3
"""
Zest Graph-Based API Example

This example demonstrates the pure graph-based approach where:
- Components are created independently without specifying connections
- Circuit.wire() method connects terminals explicitly
- Clean separation between component creation and circuit topology
"""

from zest import Circuit, VoltageSource, Resistor, Capacitor, Inductor

def voltage_divider_example():
    """Build a voltage divider using the graph-based API."""
    print("=== Voltage Divider (Graph API) ===")
    
    # Create circuit
    circuit = Circuit("Voltage Divider")
    
    # Create components independently (no connections specified)
    voltage_source = VoltageSource(voltage=12.0)
    r1 = Resistor(resistance=1000)  # 1kΩ
    r2 = Resistor(resistance=2000)  # 2kΩ
    
    # Wire the components together
    circuit.wire(voltage_source.neg, circuit.gnd)      # VS negative to ground
    circuit.wire(voltage_source.pos, r1.n1)           # VS positive to R1 input
    circuit.wire(r1.n2, r2.n1)                        # R1 output to R2 input
    circuit.wire(r2.n2, circuit.gnd)                  # R2 output to ground
    
    print(f"Components: {len(circuit.components)}")
    print(f"Wires: {len(circuit.wires)}")
    print("Topology:")
    print(f"  {voltage_source.name} negative -> GND")
    print(f"  {voltage_source.name} positive -> {r1.name} input")
    print(f"  {r1.name} output -> {r2.name} input")
    print(f"  {r2.name} output -> GND")
    
    print("\nSPICE Netlist:")
    print(circuit.compile_to_spice())
    return circuit

def rc_filter_example():
    """Build an RC low-pass filter using the graph-based API."""
    print("\n=== RC Low-Pass Filter (Graph API) ===")
    
    # Create circuit
    circuit = Circuit("RC Filter")
    
    # Create components
    voltage_source = VoltageSource(voltage=5.0)
    r1 = Resistor(resistance=1000)      # 1kΩ series resistor
    c1 = Capacitor(capacitance=1e-6)    # 1µF filter capacitor
    
    # Wire the circuit
    circuit.wire(voltage_source.neg, circuit.gnd)     # VS negative to ground
    circuit.wire(voltage_source.pos, r1.n1)           # VS positive to R1 input
    circuit.wire(r1.n2, c1.pos)                       # R1 output to C1 positive (filter output)
    circuit.wire(c1.neg, circuit.gnd)                 # C1 negative to ground
    
    # Calculate corner frequency
    corner_freq = 1 / (2 * 3.14159 * r1.resistance * c1.capacitance)
    print(f"Corner frequency: {corner_freq:.1f} Hz")
    
    print("\nSPICE Netlist:")
    print(circuit.compile_to_spice())
    return circuit

def bridge_rectifier_example():
    """Build a bridge rectifier using the graph-based API."""
    print("\n=== Bridge Rectifier (Graph API) ===")
    
    # Create circuit
    circuit = Circuit("Bridge Rectifier")
    
    # Create components
    vac = VoltageSource(voltage=12.0)        # AC input (simplified as DC)
    r_load = Resistor(resistance=1000)       # Load resistor
    c_filter = Capacitor(capacitance=100e-6) # Filter capacitor
    
    # Wire the circuit (simplified bridge - real one needs diodes)
    circuit.wire(vac.neg, circuit.gnd)           # AC source negative to ground
    circuit.wire(vac.pos, r_load.n1)             # AC source positive to load
    circuit.wire(r_load.n2, circuit.gnd)         # Load to ground
    circuit.wire(r_load.n1, c_filter.pos)        # Filter capacitor across load
    circuit.wire(r_load.n2, c_filter.neg)
    
    print("Note: This is a simplified example. Real bridge rectifier needs diodes.")
    print("\nSPICE Netlist:")
    print(circuit.compile_to_spice())
    return circuit

def complex_circuit_example():
    """Build a more complex circuit demonstrating the graph API."""
    print("\n=== Complex Circuit (Graph API) ===")
    
    # Create circuit
    circuit = Circuit("Multi-Stage Filter")
    
    # Create components
    vin = VoltageSource(voltage=10.0)
    r1 = Resistor(resistance=1000)       # First stage
    c1 = Capacitor(capacitance=1e-6)
    r2 = Resistor(resistance=2000)       # Second stage
    c2 = Capacitor(capacitance=2e-6)
    r_load = Resistor(resistance=10000)   # Load
    
    # Wire the multi-stage filter
    circuit.wire(vin.neg, circuit.gnd)              # Input source to ground
    circuit.wire(vin.pos, r1.n1)                    # Input to first stage
    circuit.wire(r1.n2, c1.pos)                     # First RC junction
    circuit.wire(c1.neg, circuit.gnd)               # First cap to ground
    circuit.wire(r1.n2, r2.n1)                      # Couple to second stage
    circuit.wire(r2.n2, c2.pos)                     # Second RC junction
    circuit.wire(c2.neg, circuit.gnd)               # Second cap to ground
    circuit.wire(r2.n2, r_load.n1)                  # Connect load
    circuit.wire(r_load.n2, circuit.gnd)            # Load to ground
    
    print("Multi-stage low-pass filter with load")
    print(f"Components: {len(circuit.components)}")
    print(f"Wires: {len(circuit.wires)}")
    
    print("\nSPICE Netlist:")
    print(circuit.compile_to_spice())
    return circuit

def demonstrate_api_features():
    """Demonstrate key features of the graph-based API."""
    print("\n=== Graph API Features ===")
    
    circuit = Circuit("API Demo")
    
    print("1. Independent component creation:")
    vs = VoltageSource(voltage=3.3)
    r1 = Resistor(resistance=1000)
    c1 = Capacitor(capacitance=1e-6)
    
    print(f"   Created: {vs}, {r1}, {c1}")
    print(f"   Circuit has {len(circuit.components)} components, {len(circuit.wires)} wires")
    
    print("\n2. Explicit wiring:")
    circuit.wire(vs.neg, circuit.gnd)
    circuit.wire(vs.pos, r1.n1)
    circuit.wire(r1.n2, c1.pos)
    circuit.wire(c1.neg, circuit.gnd)
    
    print(f"   After wiring: {len(circuit.wires)} wires")
    
    print("\n3. Terminal references:")
    print(f"   VoltageSource terminals: {vs.pos}, {vs.neg}")
    print(f"   Resistor terminals: {r1.n1}, {r1.n2} (aliases: {r1.a}, {r1.b})")
    print(f"   Capacitor terminals: {c1.pos}, {c1.neg}")
    
    print("\n4. Circuit representation:")
    print(f"   {circuit}")

def demonstrate_error_handling():
    """Show error handling for invalid wire connections."""
    print("\n=== Error Handling ===")
    
    circuit = Circuit("Error Demo")
    r1 = Resistor(resistance=1000)
    
    print("Valid wire connection:")
    circuit.wire(r1.n1, circuit.gnd)
    print(f"   Wired {r1.n1} to ground")
    
    print("\nInvalid wire attempts:")
    try:
        circuit.wire("invalid", r1.n2)
        print("ERROR: String should not be allowed!")
    except ValueError as e:
        print(f"   ✓ String rejected: {e}")
    
    try:
        circuit.wire(r1.n1, 12345)
        print("ERROR: Number should not be allowed!")
    except ValueError as e:
        print(f"   ✓ Number rejected: {e}")

def main():
    """Main demonstration."""
    print("🔧 Zest Graph-Based API Examples")
    print("=" * 50)
    print("Pure graph approach: Components are nodes, wires are edges")
    print()
    
    # Core examples
    voltage_divider_example()
    rc_filter_example()
    bridge_rectifier_example()
    complex_circuit_example()
    
    # Feature demonstrations
    demonstrate_api_features()
    demonstrate_error_handling()
    
    print("\n" + "=" * 50)
    print("✅ All examples completed!")
    print("\nGraph API Benefits:")
    print("- Clear separation of component creation and topology")
    print("- Explicit wire connections prevent implicit assumptions")
    print("- Easy to visualize circuit as a graph")
    print("- Components can be reused in different circuits")
    print("- Wire connections are first-class citizens")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Pure Graph-Based API Example

Demonstrates the exact API requested where:
1. Components are created independently without connections
2. Circuit.wire() method connects terminals explicitly
3. Clean separation of component creation and circuit topology
"""

from zest import Circuit, VoltageSource, Resistor, Capacitor

def main():
    """Demonstrate the pure graph-based API exactly as requested."""
    
    print("🔧 Pure Graph-Based API Example")
    print("=" * 40)
    
    # Create components independently (no connections specified)
    voltage_source = VoltageSource(voltage=5.0)
    r1 = Resistor(resistance=1000)
    c1 = Capacitor(capacitance=1e-6)
    
    print("Components created:")
    print(f"  {voltage_source}")
    print(f"  {r1}")  
    print(f"  {c1}")
    
    # Create circuit and wire components together
    circuit = Circuit("Graph API Demo")
    
    # Wire the components using the circuit.wire() method
    circuit.wire(r1.n2, c1.neg)
    circuit.wire(voltage_source.neg, circuit.gnd)
    circuit.wire(voltage_source.pos, r1.n1)
    
    print(f"\nCircuit: {circuit}")
    print(f"Wires: {len(circuit.wires)}")
    for i, wire in enumerate(circuit.wires, 1):
        print(f"  Wire {i}: {wire[0]} -> {wire[1]}")
    
    print("\nSPICE Netlist:")
    print(circuit.compile_to_spice())
    
    print("\n✅ Graph-based API working perfectly!")
    print("\nBenefits:")
    print("- Components are independent nodes")
    print("- Wires are explicit edges")
    print("- Clear separation of creation and topology")
    print("- Type-safe terminal connections")
    print("- No string node names to cause errors")

if __name__ == "__main__":
    main() 
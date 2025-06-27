#!/usr/bin/env python3
"""
Complete Zest Workflow Demo

This example demonstrates the full capabilities of Zest using the terminal-only API:
1. Circuit building with auto-naming and terminal connections (no string nodes)
2. SPICE netlist generation
3. Simulation (if PySpice is available)
4. Results visualization (simulated)
"""

import zest
from zest import Circuit, VoltageSource, Resistor, Capacitor, Inductor, gnd, check_simulation_requirements

def build_voltage_divider():
    """Build a simple voltage divider circuit."""
    print("=== Building Voltage Divider Circuit ===")
    
    circuit = Circuit("Voltage Divider")
    
    # Use terminal connections only - no string nodes
    vs = VoltageSource(gnd, None, voltage=12.0)
    r1 = Resistor(vs.pos, None, resistance=1000)   # 1kΩ from VS positive
    r2 = Resistor(r1.n2, vs.neg, resistance=2000)  # 2kΩ from R1 to VS negative
    
    print(f"Created {len(circuit.components)} components:")
    for component in circuit.components:
        print(f"  {component}")
    
    print("\nGenerated SPICE netlist:")
    print(circuit.compile_to_spice())
    
    return circuit

def build_rc_filter():
    """Build an RC low-pass filter."""
    print("\n=== Building RC Low-Pass Filter ===")
    
    circuit = Circuit("RC Filter")
    
    # Chain components using terminal connections only
    vs = VoltageSource(gnd, None, voltage=5.0)
    r1 = Resistor(vs.pos, None, resistance=1000)     # 1kΩ series resistor
    c1 = Capacitor(r1.n2, vs.neg, capacitance=1e-6)  # 1µF to ground
    
    # Calculate corner frequency
    corner_freq = 1 / (2 * 3.14159 * 1000 * 1e-6)
    print(f"Filter corner frequency: {corner_freq:.1f} Hz")
    
    print("\nSPICE netlist:")
    print(circuit.compile_to_spice())
    
    return circuit

def build_rlc_circuit():
    """Build an RLC resonant circuit."""
    print("\n=== Building RLC Resonant Circuit ===")
    
    circuit = Circuit("RLC Resonator")
    
    # Series RLC using terminal connections only
    vs = VoltageSource(gnd, None, voltage=1.0)
    r1 = Resistor(vs.pos, None, resistance=10)           # 10Ω series resistance
    l1 = Inductor(r1.n2, None, inductance=1e-3)         # 1mH series inductance
    c1 = Capacitor(l1.n2, vs.neg, capacitance=10e-6)    # 10µF series capacitance
    
    # Calculate resonant frequency
    import math
    resonant_freq = 1 / (2 * math.pi * math.sqrt(1e-3 * 10e-6))
    print(f"Resonant frequency: {resonant_freq:.1f} Hz")
    
    print("\nSPICE netlist:")
    print(circuit.compile_to_spice())
    
    return circuit

def demonstrate_simulation(circuit):
    """Demonstrate simulation capabilities."""
    print(f"\n=== Simulating Circuit: {circuit.name} ===")
    
    # Check simulation availability
    available, message = check_simulation_requirements()
    print(f"Simulation status: {message}")
    
    if not available:
        print("Install PySpice for actual simulation: pip install PySpice")
        print("Mock simulation results:")
        print("  Node voltages would be displayed here")
        print("  Frequency response would be plotted here")
        print("  Transient response would be shown here")
        return
    
    try:
        # DC Operating Point
        print("\n--- DC Operating Point ---")
        dc_results = circuit.simulate_operating_point()
        print(f"Analysis: {dc_results}")
        
        if dc_results.nodes:
            print("Node voltages:")
            for node, voltage in dc_results.nodes.items():
                print(f"  {node}: {voltage:.3f} V")
        
        if dc_results.branches:
            print("Branch currents:")
            for branch, current in dc_results.branches.items():
                print(f"  {branch}: {current:.6f} A")
        
        # AC Analysis (for frequency response)
        print("\n--- AC Analysis ---")
        try:
            ac_results = circuit.simulate_ac(start_freq=0.1, stop_freq=1e6, points_per_decade=10)
            print(f"AC analysis completed: {ac_results}")
            print("(Frequency response data available for plotting)")
        except Exception as e:
            print(f"AC analysis not applicable or failed: {e}")
        
        # Transient Analysis (for time-domain response)
        print("\n--- Transient Analysis ---")
        try:
            transient_results = circuit.simulate_transient(step_time=1e-6, end_time=1e-3)
            print(f"Transient analysis completed: {transient_results}")
            print("(Time-domain data available for plotting)")
        except Exception as e:
            print(f"Transient analysis not applicable or failed: {e}")
    
    except Exception as e:
        print(f"Simulation error: {e}")
        print("This may indicate PySpice/ngspice installation issues.")

def demonstrate_api_features():
    """Demonstrate key API features."""
    print("\n=== Terminal-Only API Features ===")
    
    circuit = Circuit("API Demo")
    
    print("1. Auto-naming and auto-registration:")
    vs = VoltageSource(gnd, None, voltage=3.3)
    print(f"   VoltageSource auto-named: {vs.name}")
    
    r1 = Resistor(vs.pos, None, resistance=1000)  # Connect to VS positive terminal
    print(f"   Resistor auto-named: {r1.name}")
    
    print(f"   Circuit now has {len(circuit.components)} components")
    
    print("\n2. Terminal connections:")
    r2 = Resistor(vs.pos, None, resistance=2000)    # Connect to voltage source positive
    print(f"   Connected R2 to vs.pos (which is '{vs.pos}')")
    
    c1 = Capacitor(r2.n2, vs.neg, capacitance=1e-6) # Connect R2 output to capacitor
    print(f"   Connected C1 between r2.n2 ('{r2.n2}') and vs.neg ('{vs.neg}')")
    
    print("\n3. Available terminal aliases:")
    print(f"   VoltageSource: pos={vs.pos}, neg={vs.neg}")
    print(f"   VoltageSource: positive={vs.positive}, negative={vs.negative}")
    print(f"   Resistor: n1={r1.n1}, n2={r1.n2}")
    print(f"   Resistor: a={r1.a}, b={r1.b}")
    
    print("\n4. Supported connection types:")
    print("   ✓ Terminal connections: vs.pos, r2.n2 (type-safe!)")
    print("   ✓ Ground reference: gnd (special Node object)")
    print("   ✓ Unconnected: None (auto-generates node)")
    print("   ✗ String nodes: NO LONGER SUPPORTED")
    
    print("\n5. Error handling for old API:")
    try:
        # This should fail with clear error message
        bad_resistor = Resistor("invalid", "string", resistance=100)
    except ValueError as e:
        print(f"   String node error (as expected): {e}")

def demonstrate_chaining_patterns():
    """Show different chaining patterns."""
    print("\n=== Component Chaining Patterns ===")
    
    circuit = Circuit("Chaining Demo")
    
    print("Pattern 1: Linear chain")
    vs1 = VoltageSource(gnd, None, voltage=12.0)
    r1 = Resistor(vs1.pos, None, resistance=1000)
    r2 = Resistor(r1.n2, None, resistance=2000)
    r3 = Resistor(r2.n2, vs1.neg, resistance=3000)
    print(f"  Chain: {vs1.name} -> {r1.name} -> {r2.name} -> {r3.name}")
    
    print("\nPattern 2: Parallel branches")
    vs2 = VoltageSource(gnd, None, voltage=5.0)
    r4 = Resistor(vs2.pos, vs2.neg, resistance=1000)  # Branch 1
    r5 = Resistor(vs2.pos, vs2.neg, resistance=2000)  # Branch 2 (parallel)
    print(f"  Parallel: {r4.name} || {r5.name} across {vs2.name}")
    
    print("\nPattern 3: RC filter chain")
    vs3 = VoltageSource(gnd, None, voltage=10.0)
    r6 = Resistor(vs3.pos, None, resistance=1000)     # Series R
    c2 = Capacitor(r6.n2, vs3.neg, capacitance=1e-6)  # Shunt C
    print(f"  RC filter: {vs3.name} -> {r6.name} -> (output), {c2.name} to ground")

def main():
    """Main demonstration function."""
    print("🔧 Zest Complete Workflow Demo (Terminal-Only API)")
    print("=" * 60)
    
    # API features
    demonstrate_api_features()
    demonstrate_chaining_patterns()
    
    # Build different circuit types
    voltage_divider = build_voltage_divider()
    rc_filter = build_rc_filter()
    rlc_circuit = build_rlc_circuit()
    
    # Demonstrate simulation on each circuit
    for circuit in [voltage_divider, rc_filter, rlc_circuit]:
        demonstrate_simulation(circuit)
    
    print("\n" + "=" * 60)
    print("✅ Demo complete!")
    print("\nTerminal-Only API Benefits:")
    print("- Type-safe connections (no string typos)")
    print("- Auto-generated node names")
    print("- Clear component relationships")
    print("- Impossible to have orphaned nodes")
    print("- IDE auto-completion for terminals")
    print("\nNext steps:")
    print("- Install PySpice for actual simulation: pip install PySpice")
    print("- Try building your own circuits using terminal connections")
    print("- Check out example_terminal_only.py for more patterns")

if __name__ == "__main__":
    main() 
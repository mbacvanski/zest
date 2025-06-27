#!/usr/bin/env python3
"""
Test different PySpice analysis types to see which provide individual component currents.
"""

from zest import Circuit, VoltageSource, Resistor

def test_analysis_types():
    print("🔬 Testing Different PySpice Analysis Types")
    print("=" * 50)
    
    # Create simple test circuit
    circuit = Circuit("Current Analysis Test")
    vs = VoltageSource(voltage=10.0)
    r1 = Resistor(resistance=1000)
    
    circuit.wire(vs.pos, r1.n1)
    circuit.wire(vs.neg, circuit.gnd)
    circuit.wire(r1.n2, circuit.gnd)
    
    print("Circuit: 10V source with 1kΩ resistor (should have 10mA current)")
    print("SPICE netlist:")
    print(circuit.compile_to_spice())
    
    print("\n1. DC Operating Point Analysis:")
    try:
        results = circuit.simulate_operating_point()
        print(f"   Nodes: {results.nodes}")
        print(f"   Branches: {results.branches}")
        for name, current in results.branches.items():
            print(f"   {name} current: {current:.6f}A = {current*1000:.1f}mA")
    except Exception as e:
        print(f"   Failed: {e}")
    
    print("\n2. DC Sweep Analysis (single point):")
    try:
        results = circuit.simulate_dc_sweep("V1", start=10, stop=10, step=1)
        print(f"   Analysis type: {results.analysis_type}")
        print(f"   Nodes: {results.nodes}")
        print(f"   Branches: {results.branches}")
        for name, current in results.branches.items():
            print(f"   {name} current: {current:.6f}A = {current*1000:.1f}mA")
    except Exception as e:
        print(f"   Failed: {e}")
    
    print("\n3. Transient Analysis (short duration to get steady state):")
    try:
        results = circuit.simulate_transient(step_time=1e-6, end_time=1e-3)
        print(f"   Analysis type: {results.analysis_type}")
        print(f"   Nodes: {results.nodes}")
        print(f"   Branches: {results.branches}")
        for name, current in results.branches.items():
            if hasattr(current, '__len__'):  # Array result
                print(f"   {name} final current: {current[-1]:.6f}A = {current[-1]*1000:.1f}mA")
            else:  # Scalar result
                print(f"   {name} current: {current:.6f}A = {current*1000:.1f}mA")
    except Exception as e:
        print(f"   Failed: {e}")

if __name__ == "__main__":
    test_analysis_types() 
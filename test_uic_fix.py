#!/usr/bin/env python3

import sys
sys.path.insert(0, '.')

from zest.circuit import *
from zest.components import *
from zest.simulation import *

def test_uic_fix():
    """Test that UIC is properly added to transient analysis commands."""
    print("=== Testing UIC Fix ===")
    
    # Create RC circuit
    circuit = CircuitRoot('Test RC Circuit')
    v1 = VoltageSource(5.0)
    r1 = Resistor(1000)
    c1 = Capacitor(1e-6)
    
    # Add components and wire
    circuit.add_component(v1)
    circuit.add_component(r1)
    circuit.add_component(c1)
    circuit.wire(v1.pos, r1.n1)
    circuit.wire(r1.n2, c1.pos)
    circuit.wire(v1.neg, circuit.gnd)
    circuit.wire(c1.neg, circuit.gnd)
    circuit.set_initial_condition(c1.pos, 0.0)
    
    # Test the spicelib backend directly
    backend = SpicelibBackend()
    netlist = circuit.compile_to_spice()
    
    print("Base netlist:")
    print(netlist)
    
    # Test _add_analysis_commands method
    modified_netlist = backend._add_analysis_commands(
        netlist, 
        ['transient'], 
        step_time=1e-6, 
        end_time=5e-3
    )
    
    print("\nModified netlist with UIC:")
    print(modified_netlist)
    
    # Check if UIC is in the netlist
    if "UIC" in modified_netlist:
        print("✅ UIC successfully added to transient analysis")
    else:
        print("❌ UIC missing from transient analysis")
    
    # Run full simulation
    print("\nRunning full simulation...")
    result = circuit.simulate_transient(step_time=1e-6, end_time=5e-3)
    
    # Check results
    c1_results = result.get_component_results(c1)
    cap_voltage = c1_results['terminal_voltages']['pos']
    
    print(f"Simulation completed successfully")
    print(f"Capacitor voltage: {cap_voltage[0]:.6f}V → {cap_voltage[-1]:.6f}V")
    print(f"Voltage swing: {cap_voltage[-1] - cap_voltage[0]:.6f}V")
    
    return True

if __name__ == "__main__":
    test_uic_fix() 
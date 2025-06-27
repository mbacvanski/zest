#!/usr/bin/env python3
"""
Example demonstrating Zest's simulation capabilities.

This example shows how to build a circuit using terminal-only connections
and run various types of SPICE simulations using PySpice integration.
"""

import zest
from zest import Circuit, VoltageSource, Resistor, Capacitor, gnd, check_simulation_requirements

def main():
    print("=== Zest Simulation Example (Terminal-Only API) ===\n")
    
    # Check if simulation requirements are met
    available, message = check_simulation_requirements()
    print(f"Simulation availability: {message}")
    
    if not available:
        print("Please install PySpice: pip install PySpice")
        return
    
    print()
    
    # Create a simple voltage divider circuit using only terminal connections
    print("Building voltage divider circuit (terminal-only connections)...")
    circuit = Circuit("Voltage Divider with Capacitor")
    
    # Add components using terminal connections only
    vs = VoltageSource(gnd, None, voltage=10.0)       # 10V source, negative unconnected
    r1 = Resistor(vs.pos, None, resistance=1000)      # 1kΩ from VS positive
    r2 = Resistor(r1.n2, vs.neg, resistance=2000)     # 2kΩ from R1 output to VS negative (ground)
    c1 = Capacitor(r1.n2, vs.neg, capacitance=1e-6)   # 1µF capacitor parallel to R2
    
    print(f"Created circuit with {len(circuit.components)} components")
    print(f"Circuit: {circuit}")
    print()
    
    # Show the SPICE netlist
    print("Generated SPICE netlist:")
    print(circuit.compile_to_spice())
    print()
    
    try:
        # 1. DC Operating Point Analysis
        print("=== DC Operating Point Analysis ===")
        dc_results = circuit.simulate_operating_point()
        print(f"Results: {dc_results}")
        
        print("Node voltages:")
        for node_name, voltage in dc_results.nodes.items():
            print(f"  {node_name}: {voltage:.3f} V")
        
        if dc_results.branches:
            print("Branch currents:")
            for branch_name, current in dc_results.branches.items():
                print(f"  {branch_name}: {current:.6f} A")
        print()
        
        # 2. DC Sweep Analysis
        print("=== DC Sweep Analysis ===")
        print("Sweeping voltage source from 0V to 12V...")
        try:
            dc_sweep = circuit.simulate_dc_sweep(vs.name, 0, 12, 0.5)
            print(f"Sweep results: {dc_sweep}")
            print("(DC sweep data would typically be plotted)")
        except Exception as e:
            print(f"DC sweep failed: {e}")
        print()
        
        # 3. AC Analysis  
        print("=== AC Analysis ===")
        print("Running AC analysis from 1Hz to 1MHz...")
        try:
            ac_results = circuit.simulate_ac(start_freq=1, stop_freq=1e6, points_per_decade=5)
            print(f"AC results: {ac_results}")
            print("(AC frequency response would typically be plotted)")
        except Exception as e:
            print(f"AC analysis failed: {e}")
        print()
        
        # 4. Transient Analysis
        print("=== Transient Analysis ===")
        print("Running transient analysis for 10ms...")
        try:
            transient_results = circuit.simulate_transient(step_time=1e-5, end_time=1e-2)
            print(f"Transient results: {transient_results}")
            print("(Transient data would typically be plotted)")
        except Exception as e:
            print(f"Transient analysis failed: {e}")
        
    except ImportError as e:
        print(f"Simulation error: {e}")
        print("Make sure PySpice is installed and ngspice is available.")
    except Exception as e:
        print(f"Simulation failed: {e}")
        print("Check that ngspice is properly installed on your system.")

def simple_resistor_example():
    """Simple resistor circuit for basic testing."""
    print("\n=== Simple Resistor Test (Terminal-Only) ===")
    
    # Very simple circuit: voltage source and resistor using terminal connections
    circuit = Circuit("Simple Test")
    vs = VoltageSource(gnd, None, voltage=5.0)
    r1 = Resistor(vs.pos, vs.neg, resistance=1000)  # Direct connection from pos to neg through resistor
    
    print("SPICE netlist:")
    print(circuit.compile_to_spice())
    
    try:
        results = circuit.simulate_operating_point()
        print(f"DC results: {results}")
        for node, voltage in results.nodes.items():
            print(f"  Node {node}: {voltage:.3f} V")
    except Exception as e:
        print(f"Simple test failed: {e}")

def rc_filter_simulation():
    """RC filter with simulation demonstration."""
    print("\n=== RC Filter Simulation ===")
    
    circuit = Circuit("RC Low-Pass Filter")
    
    # Build RC filter using terminal connections
    vs = VoltageSource(gnd, None, voltage=5.0)
    r1 = Resistor(vs.pos, None, resistance=1000)      # Series resistor
    c1 = Capacitor(r1.n2, vs.neg, capacitance=1e-6)   # Capacitor to ground
    
    # Calculate expected corner frequency
    corner_freq = 1 / (2 * 3.14159 * 1000 * 1e-6)
    print(f"Expected corner frequency: {corner_freq:.1f} Hz")
    
    print("\nSPICE netlist:")
    print(circuit.compile_to_spice())
    
    # Check simulation availability
    available, _ = check_simulation_requirements()
    if available:
        try:
            # DC operating point
            dc_results = circuit.simulate_operating_point()
            print(f"\nDC operating point: {dc_results}")
            
            # AC analysis for frequency response
            ac_results = circuit.simulate_ac(start_freq=1, stop_freq=10000, points_per_decade=10)
            print(f"AC analysis: {ac_results}")
            print("(Frequency response shows filter characteristics)")
            
        except Exception as e:
            print(f"Simulation failed: {e}")
    else:
        print("Simulation not available - install PySpice to run")

if __name__ == "__main__":
    main()
    simple_resistor_example()
    rc_filter_simulation() 
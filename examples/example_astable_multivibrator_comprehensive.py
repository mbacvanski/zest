#!/usr/bin/env python3
"""
Zest Demo: Astable Multivibrator using Subcircuits

This example demonstrates the power of the subcircuit feature by building
a classic oscillator circuit from reusable RC blocks. The circuit uses
two cross-coupled transistor-RC stages to create a free-running oscillator.

The demonstration shows:
1. How to define reusable subcircuits with external pins
2. How to instantiate subcircuits multiple times in a main circuit  
3. How to run transient simulation on circuits with subcircuits
4. How to analyze and visualize the oscillating waveforms
"""

import sys
import os
import numpy as np

# Add parent directory for local zest imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zest import Circuit, VoltageSource, Resistor, Capacitor, SubCircuit
from zest.simulation import check_simulation_requirements
from tests.test_helpers import SimpleNPN

# Try to import matplotlib for plotting (optional)
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("📊 Note: matplotlib not available - plots will be skipped")


def create_rc_timing_block():
    """
    Creates a reusable RC timing block subcircuit.
    
    This demonstrates how to:
    1. Define a circuit that will be used as a subcircuit
    2. Add internal components (R and C)
    3. Wire components together internally
    4. Expose specific internal nodes as external pins
    
    Returns:
        Circuit: RC timing block with pins: input, output, gnd
    """
    print("🔧 Creating RC timing block subcircuit definition...")
    
    # 1. Create the circuit definition
    rc_block = Circuit("RC_TIMING_BLOCK")
    
    # 2. Add internal components
    timing_resistor = Resistor(resistance=10e3, name="R_TIME")  # 10kΩ (reduced for faster switching)
    timing_capacitor = Capacitor(capacitance=100e-9, name="C_TIME")  # 100nF (increased for better timing)
    
    # 3. Wire internal components (RC low-pass configuration)
    rc_block.wire(timing_resistor.n2, timing_capacitor.pos)
    
    # 4. Expose external interface pins
    rc_block.add_pin("input", timing_resistor.n1)    # Input to the RC network
    rc_block.add_pin("output", timing_resistor.n2)   # Output from RC junction  
    rc_block.add_pin("gnd", timing_capacitor.neg)    # Ground reference
    
    print(f"   ✅ RC block defined with {len(rc_block.components)} components and {len(rc_block.pins)} pins")
    return rc_block


def build_astable_multivibrator():
    """
    Builds the complete astable multivibrator circuit using RC subcircuits.
    
    The circuit topology:
    - VCC powers two collector load resistors
    - Two NPN transistors (Q1, Q2) in cross-coupled configuration
    - Two RC timing blocks provide feedback delays
    - Q1 collector → RC2 → Q2 base (feedback path 1)
    - Q2 collector → RC1 → Q1 base (feedback path 2)
    
    Returns:
        tuple: (main_circuit, components_dict) for easy access to key nodes
    """
    print("🏗️  Building astable multivibrator main circuit...")
    
    # Get the reusable RC block definition
    rc_block_def = create_rc_timing_block()
    
    # Create the main circuit
    main_circuit = Circuit("AstableMultivibrator")
    
    # Power supply
    vcc = VoltageSource(voltage=5.0, name="VCC")
    print("   📡 Added 5V power supply")
    
    # Collector load resistors
    r_load1 = Resistor(resistance=4.7e3, name="RL1")  # 4.7kΩ
    r_load2 = Resistor(resistance=4.7e3, name="RL2")  # 4.7kΩ
    print("   📡 Added collector load resistors (4.7kΩ each)")
    
    # Transistors (using our simplified model)
    q1 = SimpleNPN(name="Q1")
    q2 = SimpleNPN(name="Q2")
    print("   📡 Added NPN transistors Q1 and Q2")
    
    # Instantiate RC timing blocks (this is the key subcircuit feature!)
    rc1 = SubCircuit(definition=rc_block_def, name="RC1")
    rc2 = SubCircuit(definition=rc_block_def, name="RC2")
    print("   🔌 Instantiated two RC timing block subcircuits")
    
    # Note: The NPN transistor SPICE model is automatically included via subcircuit dependencies
    print("   📋 NPN transistor model included automatically via .INCLUDE")
    
    # Add base bias resistors to help start oscillation
    r_bias1 = Resistor(resistance=47e3, name="RB1")  # 47kΩ base bias for Q1
    r_bias2 = Resistor(resistance=47e3, name="RB2")  # 47kΩ base bias for Q2
    print("   📡 Added base bias resistors for startup")
    
    # --- Circuit Wiring ---
    print("   🔌 Wiring the circuit...")
    
    # Power and ground connections
    main_circuit.wire(vcc.neg, main_circuit.gnd)
    main_circuit.wire(q1.emitter, main_circuit.gnd)
    main_circuit.wire(q2.emitter, main_circuit.gnd)
    main_circuit.wire(rc1.gnd, main_circuit.gnd)
    main_circuit.wire(rc2.gnd, main_circuit.gnd)
    
    # Collector loads (VCC → load resistor → transistor collector)
    main_circuit.wire(vcc.pos, r_load1.n1)
    main_circuit.wire(vcc.pos, r_load2.n1)
    main_circuit.wire(r_load1.n2, q1.collector)
    main_circuit.wire(r_load2.n2, q2.collector)
    
    # Base bias connections for startup
    main_circuit.wire(vcc.pos, r_bias1.n1)
    main_circuit.wire(vcc.pos, r_bias2.n1)
    main_circuit.wire(r_bias1.n2, q1.base)
    main_circuit.wire(r_bias2.n2, q2.base)
    
    # Cross-coupling feedback paths (the heart of the oscillator!)
    main_circuit.wire(q1.collector, rc2.input)    # Q1 collector → RC2 input
    main_circuit.wire(rc2.output, q2.base)        # RC2 output → Q2 base (shares with bias)
    main_circuit.wire(q2.collector, rc1.input)    # Q2 collector → RC1 input
    main_circuit.wire(rc1.output, q1.base)        # RC1 output → Q1 base (shares with bias)
    
    # Add initial conditions to kick-start oscillation
    main_circuit.set_initial_condition(q1.base, 0.1)    # Q1 base slightly forward biased
    main_circuit.set_initial_condition(q2.base, 0.7)    # Q2 base more forward biased
    
    components = {
        'vcc': vcc, 'q1': q1, 'q2': q2, 'rc1': rc1, 'rc2': rc2,
        'r_load1': r_load1, 'r_load2': r_load2, 'r_bias1': r_bias1, 'r_bias2': r_bias2
    }
    
    print(f"   ✅ Main circuit built with {len(main_circuit.components)} total components")
    return main_circuit, components


def analyze_circuit_behavior(circuit, components):
    """
    Analyzes the expected behavior of the astable multivibrator.
    """
    print("\n📐 Circuit Analysis:")
    print("   💡 Operating Principle:")
    print("      - When Q1 is ON, its collector is LOW")
    print("      - RC2 begins charging, eventually turning Q2 ON")
    print("      - When Q2 turns ON, its collector goes LOW")
    print("      - RC1 begins charging, eventually turning Q1 OFF")
    print("      - The cycle repeats, creating oscillation")
    
    # Calculate theoretical frequency
    R = 10e3   # 10kΩ
    C = 100e-9 # 100nF
    time_constant = R * C  # 1ms
    period = 1.386 * time_constant  # Astable multivibrator period
    frequency = 1 / period
    
    print(f"   📊 Theoretical Analysis:")
    print(f"      - RC time constant: {time_constant*1000:.1f} ms")
    print(f"      - Expected period: {period*1000:.2f} ms")
    print(f"      - Expected frequency: {frequency:.0f} Hz")
    
    return frequency


def simulate_and_analyze(circuit, components, expected_freq):
    """
    Runs transient simulation and analyzes the results.
    """
    print("\n🚀 Running Transient Simulation...")
    
    # Simulation parameters
    end_time = 20e-3  # 20ms (more cycles to observe)
    step_time = 10e-6  # 10µs time step (larger for stability)
    
    print(f"   📈 Simulating from 0 to {end_time*1000:.1f}ms with {step_time*1e6:.0f}µs steps")
    
    # Run the simulation
    results = circuit.simulate_transient(step_time=step_time, end_time=end_time)
    
    if results is None:
        print("   ❌ Simulation failed!")
        return None, None, None
    
    # Extract time and voltage data
    times = results._extract_value(results.pyspice_results.time)
    q1_collector = results._extract_value(results.get_node_voltage(components['q1'].collector))
    q2_collector = results._extract_value(results.get_node_voltage(components['q2'].collector))
    
    print(f"   ✅ Simulation completed with {len(times)} time points")
    
    # More robust oscillation detection
    print(f"   📊 Voltage Analysis:")
    print(f"      - Q1 collector: min={np.min(q1_collector):.2f}V, max={np.max(q1_collector):.2f}V, avg={np.mean(q1_collector):.2f}V")
    print(f"      - Q2 collector: min={np.min(q2_collector):.2f}V, max={np.max(q2_collector):.2f}V, avg={np.mean(q2_collector):.2f}V")
    
    # Check for voltage swing (oscillation indicator)
    q1_swing = np.max(q1_collector) - np.min(q1_collector)
    q2_swing = np.max(q2_collector) - np.min(q2_collector)
    
    if q1_swing > 1.0 or q2_swing > 1.0:  # At least 1V swing
        print(f"   ✅ Circuit shows voltage swing indicating oscillation!")
        print(f"      - Q1 swing: {q1_swing:.2f}V")
        print(f"      - Q2 swing: {q2_swing:.2f}V")
        
        # Try to measure frequency from the larger swing signal
        signal = q1_collector if q1_swing > q2_swing else q2_collector
        mid_level = np.mean(signal)
        crossings = np.where(np.diff(np.sign(signal - mid_level)))[0]
        
        if len(crossings) >= 4:
            # Calculate frequency from positive-going zero crossings
            pos_crossings = crossings[::2]  # Every other crossing
            if len(pos_crossings) >= 2:
                period_avg = np.mean(np.diff(pos_crossings)) * step_time
                measured_freq = 1 / period_avg
                freq_error = abs(measured_freq - expected_freq) / expected_freq * 100
                
                print(f"      - Detected {len(crossings)} total crossings")
                print(f"      - Measured frequency: {measured_freq:.0f} Hz")
                print(f"      - Expected frequency: {expected_freq:.0f} Hz")
                print(f"      - Frequency error: {freq_error:.1f}%")
            else:
                print(f"      - Too few positive crossings for frequency measurement")
        else:
            print(f"      - Only {len(crossings)} crossings detected")
    else:
        print(f"   ⚠️  No significant voltage swing detected - circuit may not be oscillating")
        print(f"      - Q1 swing: {q1_swing:.2f}V, Q2 swing: {q2_swing:.2f}V")
    
    return times, q1_collector, q2_collector


def plot_results(times, q1_collector, q2_collector):
    """
    Creates plots of the simulation results.
    """
    if not HAS_MATPLOTLIB:
        print("   📊 Plotting skipped (matplotlib not available)")
        return
    
    print("   📊 Creating waveform plots...")
    
    # Create the plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    # Convert time to milliseconds for better readability
    times_ms = times * 1000
    
    # Plot Q1 collector voltage
    ax1.plot(times_ms, q1_collector, 'b-', linewidth=2, label='Q1 Collector')
    ax1.set_ylabel('Voltage (V)')
    ax1.set_title('Astable Multivibrator - Q1 Output')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.set_ylim(-0.5, 5.5)
    
    # Plot Q2 collector voltage
    ax2.plot(times_ms, q2_collector, 'r-', linewidth=2, label='Q2 Collector')
    ax2.set_xlabel('Time (ms)')
    ax2.set_ylabel('Voltage (V)')
    ax2.set_title('Astable Multivibrator - Q2 Output')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    ax2.set_ylim(-0.5, 5.5)
    
    plt.tight_layout()
    plt.suptitle('Astable Multivibrator using Zest Subcircuits', fontsize=14, y=0.98)
    
    # Save the plot
    plt.savefig('astable_multivibrator_demo.png', dpi=300, bbox_inches='tight')
    print(f"   💾 Plot saved as 'astable_multivibrator_demo.png'")
    
    # Show the plot
    plt.show()


def display_spice_netlist(circuit):
    """
    Displays the complete SPICE netlist showing subcircuit usage.
    """
    print("\n📋 Generated SPICE Netlist:")
    print("=" * 60)
    spice_netlist = circuit.compile_to_spice()
    print(spice_netlist)
    print("=" * 60)
    
    # Highlight key subcircuit features
    lines = spice_netlist.split('\n')
    subckt_lines = [line for line in lines if '.SUBCKT' in line or 'X' in line[:2]]
    
    print("\n🔍 Subcircuit Features Highlighted:")
    print("   📋 Subcircuit Definitions:")
    for line in lines:
        if '.SUBCKT' in line:
            print(f"      {line}")
    
    print("   🔌 Subcircuit Instances:")
    for line in lines:
        if line.startswith('X'):
            print(f"      {line}")


def main():
    """
    Main demonstration function.
    """
    print("🎯 Zest Subcircuit Demo: Astable Multivibrator")
    print("=" * 50)
    print("This demo shows how to use zest's subcircuit feature to build")
    print("a classic oscillator circuit from reusable building blocks.\n")
    
    # Check if simulation is available
    available, message = check_simulation_requirements()
    if not available:
        print(f"⚠️  Simulation not available: {message}")
        print("The demo will show circuit construction but skip simulation.\n")
    
    try:
        # Step 1: Build the circuit
        circuit, components = build_astable_multivibrator()
        
        # Step 2: Analyze expected behavior
        expected_freq = analyze_circuit_behavior(circuit, components)
        
        # Step 3: Display the SPICE netlist  
        display_spice_netlist(circuit)
        
        # Step 4: Run simulation (if available)
        if available:
            times, q1_v, q2_v = simulate_and_analyze(circuit, components, expected_freq)
            
            if times is not None:
                # Step 5: Plot results
                plot_results(times, q1_v, q2_v)
                
                print("\n🎉 Demo completed successfully!")
                print("\nKey takeaways from this demo:")
                print("✅ Subcircuits enable modular, reusable circuit design")
                print("✅ Complex circuits can be built from simple building blocks")  
                print("✅ SPICE netlists are automatically generated with proper subcircuit syntax")
                print("✅ Simulation works seamlessly with subcircuit-based designs")
            else:
                print("\n⚠️  Simulation completed but results could not be analyzed")
        else:
            print("\n📋 Circuit construction completed successfully!")
            print("   (Simulation skipped due to missing PySpice)")
    
    except Exception as e:
        print(f"\n❌ Demo encountered an error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 
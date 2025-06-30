#!/usr/bin/env python3
"""
Demo: PiecewiseLinearVoltageSource Component

This example demonstrates how to use the PiecewiseLinearVoltageSource component
to create time-varying voltage signals in Zest circuits.
"""

import sys
import os

# Add parent directory to path for importing zest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zest import Circuit, PiecewiseLinearVoltageSource, Resistor, Capacitor, gnd


def example_step_response():
    """Example 1: Step input to RC circuit"""
    print("=== Example 1: Step Response ===")
    
    # Create a circuit with PWL voltage source
    circuit = Circuit("PWL Step Response")
    
    # Create a step function: 0V -> 5V at 1ms
    step_source = PiecewiseLinearVoltageSource([
        (0, 0),      # Start at 0V
        (1e-3, 5)    # Step to 5V at 1ms
    ], name="V_STEP")
    
    # RC circuit components
    r1 = Resistor(resistance=1000, name="R1")      # 1kΩ
    c1 = Capacitor(capacitance=1e-6, name="C1")   # 1µF
    
    # Add components to circuit
    circuit.add_component(step_source)
    circuit.add_component(r1)
    circuit.add_component(c1)
    
    # Wire the RC circuit
    circuit.wire(step_source.pos, r1.n1)
    circuit.wire(r1.n2, c1.pos)
    circuit.wire(step_source.neg, gnd)
    circuit.wire(c1.neg, gnd)
    
    # Print SPICE netlist
    print("Generated SPICE netlist:")
    print(circuit.compile_to_spice())
    print()


def example_triangle_wave():
    """Example 2: Triangle wave generator"""
    print("=== Example 2: Triangle Wave ===")
    
    circuit = Circuit("Triangle Wave Demo")
    
    # Create a triangle wave: 0V -> 5V -> 0V -> -2V -> 0V
    triangle_source = PiecewiseLinearVoltageSource([
        (0, 0),        # Start at 0V
        (1e-3, 5),     # Rise to 5V at 1ms
        (2e-3, 0),     # Fall to 0V at 2ms
        (3e-3, -2),    # Fall to -2V at 3ms
        (4e-3, 0)      # Return to 0V at 4ms
    ], name="V_TRI")
    
    # Simple resistive load
    load = Resistor(resistance=1000, name="R_LOAD")
    
    circuit.add_component(triangle_source)
    circuit.add_component(load)
    
    # Connect triangle source to load
    circuit.wire(triangle_source.pos, load.n1)
    circuit.wire(triangle_source.neg, gnd)
    circuit.wire(load.n2, gnd)
    
    print("Triangle wave circuit:")
    print(circuit.compile_to_spice())
    print()
    
    # Demonstrate voltage calculation at different times
    print("Triangle wave voltages at different times:")
    test_times = [0, 0.5e-3, 1e-3, 1.5e-3, 2e-3, 2.5e-3, 3e-3, 3.5e-3, 4e-3, 5e-3]
    for t in test_times:
        v = triangle_source.get_voltage_at_time(t)
        print(f"  t={t*1000:4.1f}ms: {v:5.2f}V")
    print()


def example_complex_waveform():
    """Example 3: Complex multi-stage waveform"""
    print("=== Example 3: Complex Waveform ===")
    
    circuit = Circuit("Complex PWL Demo")
    
    # Create a complex control signal
    control_signal = PiecewiseLinearVoltageSource([
        (0, 0),        # Start at 0V
        (0.5e-3, 0),   # Hold 0V until 0.5ms
        (1e-3, 3.3),   # Rise to 3.3V at 1ms
        (3e-3, 3.3),   # Hold 3.3V until 3ms  
        (3.5e-3, 1.2), # Drop to 1.2V at 3.5ms
        (5e-3, 1.2),   # Hold 1.2V until 5ms
        (6e-3, 0),     # Return to 0V at 6ms
        (10e-3, 0)     # Hold 0V until 10ms
    ], name="V_CTRL")
    
    # RC filter to smooth the signal
    r_filter = Resistor(resistance=470, name="R_FILTER")
    c_filter = Capacitor(capacitance=2.2e-6, name="C_FILTER")
    
    circuit.add_component(control_signal)
    circuit.add_component(r_filter)
    circuit.add_component(c_filter)
    
    # Create RC filter
    circuit.wire(control_signal.pos, r_filter.n1)
    circuit.wire(r_filter.n2, c_filter.pos)
    circuit.wire(control_signal.neg, gnd)
    circuit.wire(c_filter.neg, gnd)
    
    print("Complex waveform with RC filter:")
    print(circuit.compile_to_spice())
    print()


def main():
    """Run all PWL voltage source examples"""
    print("🔬 PiecewiseLinearVoltageSource Examples\n")
    
    example_step_response()
    example_triangle_wave()
    example_complex_waveform()
    
    print("💡 Key Features:")
    print("- Arbitrary piecewise linear waveforms")
    print("- Automatic time sorting and validation")
    print("- Linear interpolation between points")
    print("- Proper SPICE PWL syntax generation")
    print("- Integration with existing Zest workflow")
    print("\n🎯 Usage Tips:")
    print("- Use for stimulus signals in transient simulations")
    print("- Ideal for modeling real-world voltage profiles")
    print("- Combine with RC circuits for signal conditioning")
    print("- Can model both positive and negative voltages")


if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Example: Nested Subcircuits in zest
====================================

This example demonstrates how to create subcircuits that contain other subcircuits within them,
showing hierarchical circuit design with proper SPICE generation and simulation.

Example hierarchy:
- Basic RC Stage (building block)
- Two-Stage RC Filter (contains two Basic RC Stage subcircuits)  
- Main Circuit (uses the Two-Stage RC Filter)
"""

from zest import Circuit, Resistor, VoltageSource, SubCircuit, Capacitor


def create_basic_rc_stage():
    """Create a basic RC low-pass filter stage - the fundamental building block."""
    rc_stage = Circuit("BASIC_RC_STAGE")
    
    # Simple RC filter components (1kΩ, 100nF)
    r1 = Resistor(resistance=1000, name="R_stage")  # 1kΩ
    c1 = Capacitor(capacitance=100e-9, name="C_stage")  # 100nF
    
    # Add components to the circuit
    rc_stage.add_component(r1)
    rc_stage.add_component(c1)
    
    # Wire R and C in series (RC low-pass configuration)
    rc_stage.wire(r1.n2, c1.pos)
    
    # Expose external pins
    rc_stage.add_pin("input", r1.n1)    # Input to resistor
    rc_stage.add_pin("output", r1.n2)   # Output from R-C junction
    rc_stage.add_pin("gnd", c1.neg)     # Ground reference
    
    return rc_stage


def create_two_stage_filter():
    """
    Create a two-stage RC filter using nested subcircuits.
    This subcircuit contains two instances of the basic RC stage subcircuit.
    """
    two_stage_filter = Circuit("TWO_STAGE_RC_FILTER")
    
    # Get the basic building block definition
    basic_rc_def = create_basic_rc_stage()
    
    # Create two instances of the basic RC stage
    stage1 = SubCircuit(definition=basic_rc_def, name="STAGE1")
    stage2 = SubCircuit(definition=basic_rc_def, name="STAGE2")
    
    # Add the subcircuit instances to our two-stage filter
    two_stage_filter.add_component(stage1)
    two_stage_filter.add_component(stage2)
    
    # Wire the stages in cascade (stage1 output -> stage2 input)
    two_stage_filter.wire(stage1.output, stage2.input)
    
    # Connect grounds together
    two_stage_filter.wire(stage1.gnd, stage2.gnd)
    
    # Expose external pins for the two-stage filter
    two_stage_filter.add_pin("input", stage1.input)     # Input to first stage
    two_stage_filter.add_pin("output", stage2.output)   # Output from second stage  
    two_stage_filter.add_pin("gnd", stage1.gnd)         # Common ground
    
    return two_stage_filter


def main():
    """Demonstrate nested subcircuits functionality."""
    print("🔧 Creating nested subcircuits example...")
    
    # 1. Create the nested subcircuit definition (contains other subcircuits)
    nested_filter_def = create_two_stage_filter()
    
    # 2. Create main circuit using the nested subcircuit
    main_circuit = Circuit("Nested_Subcircuits_Example")
    v_source = VoltageSource(voltage=3.3)  # 3.3V input
    
    # Create instance of the nested subcircuit
    nested_filter = SubCircuit(definition=nested_filter_def, name="U_NESTED_FILTER")
    
    # Add components to main circuit
    main_circuit.add_component(v_source)
    main_circuit.add_component(nested_filter)
    
    # 3. Wire the main circuit
    main_circuit.wire(v_source.pos, nested_filter.input)
    main_circuit.wire(v_source.neg, main_circuit.gnd)
    main_circuit.wire(nested_filter.gnd, main_circuit.gnd)
    
    # Set initial conditions for clean simulation
    main_circuit.set_initial_condition(nested_filter.output, 0.0)
    
    # 4. Generate and display SPICE output
    spice_output = main_circuit.compile_to_spice()
    print("\n📋 Generated SPICE Netlist:")
    print("=" * 50)
    print(spice_output)
    
    # 5. Verify nested subcircuit structure
    print("\n🔍 Verification:")
    basic_rc_count = spice_output.count(".SUBCKT BASIC_RC_STAGE")
    nested_count = spice_output.count(".SUBCKT TWO_STAGE_RC_FILTER")
    
    print(f"✓ BASIC_RC_STAGE definitions: {basic_rc_count}")
    print(f"✓ TWO_STAGE_RC_FILTER definitions: {nested_count}")
    print(f"✓ Proper hierarchy: {'✓' if basic_rc_count == 1 and nested_count == 1 else '✗'}")
    
    # 6. Run simulation
    print("\n⚡ Running transient simulation...")
    try:
        # Extended simulation time to see full settling (5 time constants = 500μs)
        results = main_circuit.simulate_transient(step_time=1e-6, end_time=500e-6)
        
        if results:
            times = results.get_time_vector()
            if times is None and hasattr(results, 'time'):
                times = results.time
            v_output = results.get_node_voltage(nested_filter.output)
            
            print(f"✓ Simulation completed: {len(times)} time points")
            print(f"✓ Final output voltage: {v_output[-1]:.3f}V")
            print(f"✓ Input voltage: {v_source.voltage}V")
            print(f"✓ Two-stage filtering effect: {(v_output[-1]/v_source.voltage)*100:.1f}% of input")
            
            # Show settling behavior at different time points
            if len(times) >= 5:
                t_25 = len(times) // 4
                t_50 = len(times) // 2  
                t_75 = (3 * len(times)) // 4
                print(f"✓ Settling progression:")
                print(f"  • t=0: {v_output[0]:.3f}V")
                print(f"  • t=25%: {v_output[t_25]:.3f}V")
                print(f"  • t=50%: {v_output[t_50]:.3f}V") 
                print(f"  • t=75%: {v_output[t_75]:.3f}V")
                print(f"  • t=100%: {v_output[-1]:.3f}V")
                
            # Calculate theoretical final value for two-stage RC filter
            # For step input, final value should approach input voltage
            settling_percent = (v_output[-1] / v_source.voltage) * 100
            print(f"✓ Final settling: {settling_percent:.1f}% of input voltage")
            
        else:
            print("⚠️  Simulation failed (might be expected on some systems)")
            
    except Exception as e:
        print(f"⚠️  Simulation error: {e}")
        print("📋 SPICE generation worked correctly (main demonstration)")
    
    print("\n🎉 Nested subcircuits example completed!")
    print("\nKey features demonstrated:")
    print("• Hierarchical subcircuit design")
    print("• Subcircuits containing other subcircuits")
    print("• Proper SPICE netlist generation with all definitions")
    print("• Electrical simulation of nested circuits")


if __name__ == "__main__":
    main() 
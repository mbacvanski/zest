#!/usr/bin/env python3
"""
Example demonstrating the new refactored Circuit and SubCircuit API.

This example shows:
1. The new SubCircuitDef and SubCircuitInst API
2. Backwards compatibility with the old Circuit + SubCircuit API
3. How NodeMapper can be used for custom node naming
"""

from zest import (
    Circuit, CircuitRoot, SubCircuitDef, SubCircuit, NodeMapper,
    Resistor, VoltageSource, Capacitor, gnd
)


def create_voltage_divider_new_api():
    """Create a voltage divider using the new SubCircuitDef API."""
    print("=== Creating voltage divider with NEW API ===")
    
    # Create a subcircuit definition
    divider_def = SubCircuitDef("VOLTAGE_DIVIDER_NEW")
    
    # Add components
    r_top = Resistor(resistance=10000, name="top")    # 10k
    r_bottom = Resistor(resistance=10000, name="bot") # 10k
    divider_def.add_component(r_top)
    divider_def.add_component(r_bottom)
    
    # Wire components
    divider_def.wire(r_top.n2, r_bottom.n1)
    
    # Expose pins
    divider_def.add_pin("vin", r_top.n1)
    divider_def.add_pin("vout", r_top.n2)
    divider_def.add_pin("gnd", r_bottom.n2)
    
    return divider_def


def create_voltage_divider_old_api():
    """Create a voltage divider using the old Circuit + SubCircuit API."""
    print("=== Creating voltage divider with OLD API (backwards compatible) ===")
    
    # Create a circuit definition (old way)
    divider_circuit = Circuit("VOLTAGE_DIVIDER_OLD")
    
    # Add components
    r_top = Resistor(resistance=10000, name="top")    # 10k
    r_bottom = Resistor(resistance=10000, name="bot") # 10k
    divider_circuit.add_component(r_top)
    divider_circuit.add_component(r_bottom)
    
    # Wire components
    divider_circuit.wire(r_top.n2, r_bottom.n1)
    
    # Expose pins
    divider_circuit.add_pin("vin", r_top.n1)
    divider_circuit.add_pin("vout", r_top.n2)
    divider_circuit.add_pin("gnd", r_bottom.n2)
    
    return divider_circuit


def demonstrate_new_api():
    """Demonstrate the new SubCircuitDef and SubCircuitInst API."""
    print("\n" + "="*60)
    print("DEMONSTRATING NEW API")
    print("="*60)
    
    # Create voltage divider definition
    divider_def = create_voltage_divider_new_api()
    
    # Create main circuit
    main_circuit = CircuitRoot("Main_Circuit_New")
    
    # Add voltage source
    v_source = VoltageSource(voltage=15.0, name="supply")
    main_circuit.add_component(v_source)
    
    # Create two instances of the voltage divider
    divider1 = divider_def.create_instance("U1")
    divider2 = divider_def.create_instance("U2")
    main_circuit.add_component(divider1)
    main_circuit.add_component(divider2)
    
    # Wire them in cascade
    main_circuit.wire(v_source.pos, divider1.vin)
    main_circuit.wire(divider1.vout, divider2.vin)
    main_circuit.wire(v_source.neg, divider1.gnd)
    main_circuit.wire(divider1.gnd, divider2.gnd)
    
    # Compile to SPICE
    spice_output = main_circuit.compile_to_spice()
    print("\nNEW API - SPICE Output:")
    print(spice_output)
    
    return main_circuit


def demonstrate_old_api():
    """Demonstrate backwards compatibility with old API."""
    print("\n" + "="*60)
    print("DEMONSTRATING OLD API (BACKWARDS COMPATIBLE)")
    print("="*60)
    
    # Create voltage divider definition (old way)
    divider_circuit = create_voltage_divider_old_api()
    
    # Create main circuit
    main_circuit = Circuit("Main_Circuit_Old")
    
    # Add voltage source
    v_source = VoltageSource(voltage=15.0, name="supply")
    main_circuit.add_component(v_source)
    
    # Create two instances using old SubCircuit class
    divider1 = SubCircuit(definition=divider_circuit, name="U1")
    divider2 = SubCircuit(definition=divider_circuit, name="U2")
    main_circuit.add_component(divider1)
    main_circuit.add_component(divider2)
    
    # Wire them in cascade
    main_circuit.wire(v_source.pos, divider1.vin)
    main_circuit.wire(divider1.vout, divider2.vin)
    main_circuit.wire(v_source.neg, divider1.gnd)
    main_circuit.wire(divider1.gnd, divider2.gnd)
    
    # Compile to SPICE
    spice_output = main_circuit.compile_to_spice()
    print("\nOLD API - SPICE Output:")
    print(spice_output)
    
    return main_circuit


def demonstrate_node_mapper():
    """Demonstrate NodeMapper for custom node naming."""
    print("\n" + "="*60)
    print("DEMONSTRATING NodeMapper")
    print("="*60)
    
    # Create a simple RC filter
    rc_filter = SubCircuitDef("RC_FILTER")
    
    r1 = Resistor(1000, name="R")
    c1 = Capacitor(1e-6, name="C")
    rc_filter.add_component(r1)
    rc_filter.add_component(c1)
    
    rc_filter.wire(r1.n2, c1.pos)
    
    rc_filter.add_pin("input", r1.n1)
    rc_filter.add_pin("output", r1.n2)
    rc_filter.add_pin("gnd", c1.neg)
    
    # Test with custom NodeMapper
    custom_mapper = NodeMapper({
        r1.n1: "IN",
        r1.n2: "OUT", 
        c1.neg: "GND"
    })
    
    print("Standard compilation:")
    print(rc_filter.compile_as_subckt())
    
    print("\nWith custom NodeMapper:")
    print(rc_filter.compile_as_subckt(custom_mapper))


def main():
    """Run all demonstrations."""
    print("Circuit and SubCircuit Refactoring Demonstration")
    print("=" * 60)
    
    # Demonstrate new API
    new_circuit = demonstrate_new_api()
    
    # Demonstrate old API (backwards compatibility)
    old_circuit = demonstrate_old_api()
    
    # Demonstrate NodeMapper
    demonstrate_node_mapper()
    
    print("\n" + "="*60)
    print("KEY BENEFITS OF THE REFACTORING:")
    print("="*60)
    print("✅ Single Responsibility: CircuitRoot for simulation, SubCircuitDef for reusable blocks")
    print("✅ Behavioral Subtyping: NetlistBlock provides common interface")
    print("✅ Composition over Monkey-Patching: NodeMapper replaces method overriding")
    print("✅ Factory Pattern: SubCircuitDef.create_instance() for clean instantiation")
    print("✅ Backwards Compatibility: Old Circuit + SubCircuit API still works")
    print("✅ Unified Terminal Handling: Consistent terminal interface across all classes")


if __name__ == "__main__":
    main() 
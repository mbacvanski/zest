#!/usr/bin/env python3
"""
Example demonstrating the new SimulatedCircuit functionality.

This shows how to query simulation results for specific component instances
after running a simulation.
"""

from zest import Circuit, VoltageSource, Resistor, Capacitor, gnd

def main():
    print("🔬 SimulatedCircuit Demonstration")
    print("=" * 50)
    
    # Create a simple voltage divider circuit
    circuit = Circuit("Voltage Divider with Components")
    
    # Create components with meaningful names
    vs = VoltageSource(voltage=12.0, name="V_source")
    r1 = Resistor(resistance=1000, name="R_top")
    r2 = Resistor(resistance=2000, name="R_bottom")
    c1 = Capacitor(capacitance=1e-6, name="C_filter")
    
    # Wire the circuit
    circuit.wire(vs.pos, r1.n1)
    circuit.wire(r1.n2, r2.n1)  # Middle node
    circuit.wire(r1.n2, c1.pos)  # Connect capacitor in parallel with R2
    circuit.wire(vs.neg, gnd)
    circuit.wire(r2.n2, gnd)
    circuit.wire(c1.neg, gnd)
    
    print(f"Circuit created with {len(circuit.components)} components:")
    print(f"  - {vs}")
    print(f"  - {r1}")
    print(f"  - {r2}")
    print(f"  - {c1}")
    print()
    
    print("Running DC operating point simulation...")
    try:
        # Run simulation - now returns SimulatedCircuit instead of SimulationResults
        simulated_circuit = circuit.simulate_operating_point()
        
        print(f"✅ Simulation successful!")
        print(f"📊 {simulated_circuit}")
        print()
        
        # Demonstrate the new functionality: query results for specific components
        print("🔍 Component-specific simulation results:")
        print("-" * 40)
        
        # Query results for the voltage source
        vs_results = simulated_circuit.get_component_results(vs)
        print(f"💡 Voltage Source ({vs.name}):")
        print(f"   Component name: {vs_results['component_name']}")
        print(f"   Terminal voltages: {vs_results['terminal_voltages']}")
        if 'current' in vs_results:
            print(f"   Current: {vs_results['current']:.6f} A = {vs_results['current']*1000:.3f} mA")
        if 'voltage_across' in vs_results:
            print(f"   Voltage across: {vs_results['voltage_across']:.3f} V")
        print()
        
        # Query results for R1 (top resistor)
        r1_results = simulated_circuit.get_component_results(r1)
        print(f"🔧 Top Resistor ({r1.name}):")
        print(f"   Component name: {r1_results['component_name']}")
        print(f"   Terminal voltages: {r1_results['terminal_voltages']}")
        print(f"   Voltage across: {r1_results['voltage_across']:.3f} V")
        print(f"   Current: {r1_results['current']:.6f} A = {r1_results['current']*1000:.3f} mA")
        print(f"   Power: {r1_results['power']:.6f} W = {r1_results['power']*1000:.3f} mW")
        print()
        
        # Query results for R2 (bottom resistor)
        r2_results = simulated_circuit.get_component_results(r2)
        print(f"🔧 Bottom Resistor ({r2.name}):")
        print(f"   Component name: {r2_results['component_name']}")
        print(f"   Terminal voltages: {r2_results['terminal_voltages']}")
        print(f"   Voltage across: {r2_results['voltage_across']:.3f} V")
        print(f"   Current: {r2_results['current']:.6f} A = {r2_results['current']*1000:.3f} mA")
        print(f"   Power: {r2_results['power']:.6f} W = {r2_results['power']*1000:.3f} mW")
        print()
        
        # Query results for the capacitor
        c1_results = simulated_circuit.get_component_results(c1)
        print(f"🔋 Capacitor ({c1.name}):")
        print(f"   Component name: {c1_results['component_name']}")
        print(f"   Terminal voltages: {c1_results['terminal_voltages']}")
        print(f"   Voltage across: {c1_results['voltage_across']:.3f} V")
        print()
        
        # Show alternative ways to access data
        print("🎯 Alternative access methods:")
        print("-" * 30)
        
        # Get voltage at a specific terminal
        middle_node_voltage = simulated_circuit.get_node_voltage(r1.n2)
        print(f"   Voltage at middle node: {middle_node_voltage:.3f} V")
        
        # List all components in the simulated circuit
        print("   All components in simulation:")
        for component, name in simulated_circuit.list_components():
            print(f"     - {name}: {component}")
        print()
        
        # Verify voltage divider behavior
        expected_divider_voltage = 12.0 * (2000 / (1000 + 2000))  # 8V
        actual_divider_voltage = r2_results['voltage_across']
        print(f"📐 Voltage divider verification:")
        print(f"   Expected divider voltage: {expected_divider_voltage:.3f} V")
        print(f"   Actual divider voltage: {actual_divider_voltage:.3f} V")
        print(f"   Error: {abs(expected_divider_voltage - actual_divider_voltage):.6f} V")
        
        if abs(expected_divider_voltage - actual_divider_voltage) < 0.001:
            print("   ✅ Voltage divider working correctly!")
        else:
            print("   ⚠️  Unexpected voltage divider result")
        
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        print("   Make sure PySpice is installed: pip install PySpice")
        return
    
    print(f"\n🎉 SimulatedCircuit demonstration completed!")
    print("   The SimulatedCircuit object allows you to:")
    print("   • Query results for specific component instances")
    print("   • Get terminal voltages, currents, and power")
    print("   • Access derived values like voltage across components")
    print("   • Maintain the connection between your circuit and simulation results")


if __name__ == "__main__":
    main() 
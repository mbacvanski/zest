#!/usr/bin/env python3
"""
Demonstration of the new branch current functionality in Zest.

This example shows how to get current measurements from simulation results
using the new deterministic methods:
- get_component_current(component): Get current through a specific component
- get_terminal_current(terminal): Get current flowing into a specific terminal

Both methods use deterministic naming conventions and provide clear error messages.
"""

from zest import Circuit, VoltageSource, Resistor, gnd


def main():
    print("🔋 Branch Current Demonstration")
    print("=" * 50)
    
    # Create a simple voltage divider circuit
    circuit = Circuit("Branch Current Demo")
    
    # Create components with explicit names for clarity
    vs = VoltageSource(voltage=12.0, name="supply")
    r1 = Resistor(resistance=1000, name="top")    # 1kΩ  
    r2 = Resistor(resistance=2000, name="bottom") # 2kΩ
    
    # Add components to circuit
    circuit.add_component(vs)
    circuit.add_component(r1)
    circuit.add_component(r2)
    
    # Wire the voltage divider: Vsupply -> R_top -> R_bottom -> GND
    circuit.wire(vs.pos, r1.n1)
    circuit.wire(r1.n2, r2.n1)  # Middle node
    circuit.wire(vs.neg, gnd)
    circuit.wire(r2.n2, gnd)
    
    print("Circuit topology:")
    print("  Vsupply(+) -> R_top -> R_bottom -> GND")
    print("  Vsupply(-) -> GND")
    print()
    
    # Show component names (these determine branch current keys)
    print("Component SPICE names:")
    for component in [vs, r1, r2]:
        component_name = circuit.get_component_name(component)
        print(f"  {component} -> {component_name}")
    print()
    
    print("Expected current calculation:")
    total_resistance = r1.resistance + r2.resistance
    expected_current = -vs.voltage / total_resistance
    print(f"  I = V / R_total = {vs.voltage}V / {total_resistance}Ω = {expected_current:.6f}A = {expected_current*1000:.3f}mA")
    print()
    
    # Run DC operating point simulation
    print("Running DC operating point simulation...")
    try:
        simulated_circuit = circuit.simulate_operating_point()
        print("✓ Simulation completed successfully!")
        print()
        
        # Demonstrate component current access
        print("📊 Component Current Results:")
        print("-" * 30)
        
        for component, description in [(vs, "Voltage Source"), (r1, "Top Resistor"), (r2, "Bottom Resistor")]:
            try:
                current = simulated_circuit.get_component_current(component)
                current_ma = current * 1000  # Convert to mA
                component_name = circuit.get_component_name(component)
                print(f"  {description} ({component_name}): {current_ma:.3f} mA")
                
                # Verify against expected value
                if abs(current - expected_current) < 1e-6:
                    print(f"    ✓ Matches expected current ({expected_current*1000:.3f} mA)")
                else:
                    print(f"    ⚠️  Expected {expected_current*1000:.3f} mA")
                    
            except ValueError as e:
                print(f"  {description}: {e}")
        print()
        
        # Demonstrate terminal current access
        print("📍 Terminal Current Results:")
        print("-" * 30)
        
        terminals_to_check = [
            (vs.pos, "Voltage Source Positive"),
            (vs.neg, "Voltage Source Negative"),
            (r1.n1, "Top Resistor Input"),
            (r1.n2, "Top Resistor Output"), 
            (r2.n1, "Bottom Resistor Input"),
            (r2.n2, "Bottom Resistor Output")
        ]
        
        for terminal, description in terminals_to_check:
            try:
                current = simulated_circuit.get_terminal_current(terminal)
                current_ma = current * 1000  # Convert to mA
                print(f"  {description}: {current_ma:.3f} mA")
            except ValueError as e:
                print(f"  {description}: {e}")
        print()
        
        # Show component results with built-in current (VoltageSource updated to use new method)
        print("🔍 Component Results (including built-in current):")
        print("-" * 50)
        
        vs_results = simulated_circuit.get_component_results(vs)
        # if 'current' in vs_results:
        current_ma = vs_results['current'] * 1000
        print(f"  Voltage Source built-in current: {current_ma:.3f} mA")
        
        # Show terminal voltages for comparison
        print("\n⚡ Terminal Voltages:")
        print("-" * 20)
        for terminal, description in terminals_to_check:
            try:
                voltage = simulated_circuit.get_node_voltage(terminal)
                # Handle both scalar and array voltage values
                if hasattr(voltage, '__len__') and len(voltage) == 1:
                    voltage_val = float(voltage[0])
                elif hasattr(voltage, '__float__'):
                    voltage_val = float(voltage)
                else:
                    voltage_val = voltage
                print(f"  {description}: {voltage_val:.3f} V")
            except Exception as e:
                print(f"  {description}: {e}")
        print()
        
        print("✅ Branch current demonstration completed successfully!")
        
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        print("\nNote: This demo requires spicelib to be installed.")
        print("Install with: pip install spicelib")


if __name__ == "__main__":
    main() 
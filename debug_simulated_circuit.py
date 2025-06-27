#!/usr/bin/env python3
"""
Debug script to examine the SPICE netlist and node mapping.
"""

from zest import Circuit, VoltageSource, Resistor, Capacitor, gnd

def main():
    print("🔍 Debugging SimulatedCircuit node mapping")
    print("=" * 50)
    
    # Create a simple voltage divider circuit
    circuit = Circuit("Debug Voltage Divider")
    
    vs = VoltageSource(voltage=12.0, name="V_source")
    r1 = Resistor(resistance=1000, name="R_top")
    r2 = Resistor(resistance=2000, name="R_bottom")
    
    # Wire the circuit
    circuit.wire(vs.pos, r1.n1)
    circuit.wire(r1.n2, r2.n1)  # Middle node
    circuit.wire(vs.neg, gnd)
    circuit.wire(r2.n2, gnd)
    
    print("Circuit wiring:")
    for i, (t1, t2) in enumerate(circuit.wires, 1):
        print(f"  Wire {i}: {t1} ↔ {t2}")
    print()
    
    print("Generated SPICE netlist:")
    print("-" * 25)
    spice_netlist = circuit.compile_to_spice()
    print(spice_netlist)
    print("-" * 25)
    print()
    
    # Check node mappings
    print("Node mappings:")
    terminals_to_check = [
        ("vs.pos", vs.pos),
        ("vs.neg", vs.neg), 
        ("r1.n1", r1.n1),
        ("r1.n2", r1.n2),
        ("r2.n1", r2.n1),
        ("r2.n2", r2.n2),
        ("gnd", gnd)
    ]
    
    for name, terminal in terminals_to_check:
        node_name = circuit.get_spice_node_name(terminal)
        print(f"  {name} -> {node_name}")
    print()
    
    # Run simulation
    print("Running simulation...")
    try:
        simulated_circuit = circuit.simulate_operating_point()
        
        print("Raw PySpice results investigation:")
        print(f"  Type of pyspice_results: {type(simulated_circuit.pyspice_results)}")
        if hasattr(simulated_circuit.pyspice_results, 'nodes'):
            print(f"  PySpice nodes type: {type(simulated_circuit.pyspice_results.nodes)}")
            print("  Raw PySpice nodes:")
            for key, value in simulated_circuit.pyspice_results.nodes.items():
                print(f"    {key}: {value} (type: {type(value)}, float: {float(value) if hasattr(value, '__float__') else 'N/A'})")
        
        if hasattr(simulated_circuit.pyspice_results, 'branches'):
            print(f"  PySpice branches type: {type(simulated_circuit.pyspice_results.branches)}")
            print("  Raw PySpice branches:")
            for key, value in simulated_circuit.pyspice_results.branches.items():
                print(f"    {key}: {value} (type: {type(value)}, float: {float(value) if hasattr(value, '__float__') else 'N/A'})")
        print()
        
        print("Processed simulation nodes:")
        for node_name, node_value in simulated_circuit.nodes.items():
            print(f"  {node_name}: {node_value} (type: {type(node_value)})")
        
        print("Processed simulation branches:")
        for branch_name, branch_value in simulated_circuit.branches.items():
            print(f"  {branch_name}: {branch_value} (type: {type(branch_value)})")
        print()
        
        # Check node name matching
        print("Node name matching analysis:")
        for name, terminal in terminals_to_check:
            expected_node_name = circuit.get_spice_node_name(terminal)
            print(f"  {name}:")
            print(f"    Expected: '{expected_node_name}'")
            
            # Look for matching nodes in simulation results
            matches = []
            for sim_node in simulated_circuit.nodes.keys():
                if expected_node_name.lower() == sim_node.lower():
                    matches.append(sim_node)
                elif expected_node_name.replace('_', '').lower() == sim_node.replace('_', '').lower():
                    matches.append(sim_node)
            
            if matches:
                print(f"    Found matches: {matches}")
            else:
                print(f"    No matches found")
        print()
        
        # Check specific component results
        print("Component results:")
        vs_results = simulated_circuit.get_component_results(vs)
        print(f"  Voltage source terminal voltages: {vs_results['terminal_voltages']}")
        
        r1_results = simulated_circuit.get_component_results(r1)
        print(f"  R1 terminal voltages: {r1_results['terminal_voltages']}")
        
        r2_results = simulated_circuit.get_component_results(r2)
        print(f"  R2 terminal voltages: {r2_results['terminal_voltages']}")
        
    except Exception as e:
        print(f"Simulation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 
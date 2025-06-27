#!/usr/bin/env python3
"""
Zest Demo: Cascaded RC Filter using Subcircuits
This example demonstrates how to define a reusable functional block (an RC filter),
instantiate it multiple times, and simulate the resulting circuit.
"""
import sys
import os
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zest import Circuit, VoltageSource, SubCircuit, Resistor, Capacitor
from zest.simulation import check_simulation_requirements

# --- Definition for the reusable RC Filter Stage Subcircuit ---
def create_rc_stage_definition() -> Circuit:
    rc_stage_circuit = Circuit("RC_FILTER_STAGE")
    
    # Internal components - use regular resistor for simplicity
    r1 = Resistor(resistance=10e3, name="R_internal")  # 10kΩ
    c1 = Capacitor(capacitance=1e-6, name="C_internal")  # 1µF
    
    # Explicitly add components to the circuit
    rc_stage_circuit.add_component(r1)
    rc_stage_circuit.add_component(c1)
    
    rc_stage_circuit.wire(r1.n2, c1.pos)
    rc_stage_circuit.add_pin("vin", r1.n1)
    rc_stage_circuit.add_pin("vout", r1.n2)
    rc_stage_circuit.add_pin("gnd", c1.neg)
    return rc_stage_circuit

def main():
    print("🚀 Zest Demo: Cascaded RC Filter with Subcircuits 🚀")

    rc_stage_def = create_rc_stage_definition()
    main_circuit = Circuit("Cascaded_RC_Filter_Demo")
    v_in = VoltageSource(voltage=1.0)
    stage1 = SubCircuit(rc_stage_def, "X1")
    stage2 = SubCircuit(rc_stage_def, "X2")
    
    # Explicitly add components to the main circuit
    main_circuit.add_component(v_in)
    main_circuit.add_component(stage1)
    main_circuit.add_component(stage2)

    main_circuit.wire(v_in.neg, main_circuit.gnd)
    main_circuit.wire(stage1.gnd, main_circuit.gnd)
    main_circuit.wire(stage2.gnd, main_circuit.gnd)
    main_circuit.wire(v_in.pos, stage1.vin)
    main_circuit.wire(stage1.vout, stage2.vin)

    print("\n--- Final Compiled SPICE Netlist ---")
    print(main_circuit.compile_to_spice())

    available, message = check_simulation_requirements()
    if not available:
        print(f"\n⚠️ Simulation not available: {message}")
        return

    print("\n--- Running Transient Simulation ---")
    results = main_circuit.simulate_transient(step_time=1e-5, end_time=50e-3)
    print("✅ Simulation complete!")

    # Plotting
    times = results.pyspice_results.time
    v_in_sim = results.get_node_voltage(v_in.pos)
    v_out1 = results.get_node_voltage(stage1.vout)
    v_out2 = results.get_node_voltage(stage2.vout)

    plt.figure(figsize=(12, 7))
    plt.plot(times * 1000, v_in_sim, label="V(in)", color='blue', linewidth=2)
    plt.plot(times * 1000, v_out1, label="V(Stage 1 Output)", color='orange', linewidth=2)
    plt.plot(times * 1000, v_out2, label="V(Stage 2 Output)", color='green', linewidth=2)
    plt.title("Step Response of a Two-Stage Cascaded RC Filter")
    plt.xlabel("Time (ms)"), plt.ylabel("Voltage (V)"), plt.grid(True), plt.legend()
    plt.show()

if __name__ == "__main__":
    main() 
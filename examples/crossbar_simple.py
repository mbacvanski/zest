#!/usr/bin/env python3
"""
Simple Analog Resistive Crossbar Array Simulation

A minimal implementation demonstrating analog matrix-vector multiplication
using resistive crosspoints and op-amp transimpedance amplifiers.

Circuit: V_out = -Rf * G * V_in
where G is the conductance matrix (1/R for each crosspoint).
"""

import numpy as np
from zest.components import VoltageSource, Resistor, SubCircuit
from zest.circuit import Circuit


def create_ideal_opamp():
    """Creates an ideal op-amp subcircuit definition."""
    opamp = Circuit("IDEAL_OPAMP")
    
    # Include the ideal op-amp model (will be included within the subcircuit)
    opamp.include_model("""
EGAIN out 0 VALUE = {LIMIT(1e6*(V(plus)-V(minus)), -1e12, 1e12)}
""")
    
    opamp.add_pin("plus", opamp.gnd)   # Non-inverting input
    opamp.add_pin("minus", opamp.gnd)  # Inverting input  
    opamp.add_pin("out", opamp.gnd)    # Output
    
    return opamp


def build_crossbar_array(input_voltages, resistance_matrix, rf_value=10e3):
    """
    Builds a resistive crossbar array circuit.
    
    Args:
        input_voltages: List of row input voltages [V]
        resistance_matrix: 2D array of crosspoint resistances [Ω]
        rf_value: Feedback resistor value [Ω]
        
    Returns:
        tuple: (circuit, row_sources, col_amplifiers)
    """
    rows, cols = resistance_matrix.shape
    circuit = Circuit("CrossbarArray")
    
    # Create ideal op-amp definition (no duplication needed!)
    opamp_def = create_ideal_opamp()
    
    # Create row voltage sources
    row_sources = []
    for i in range(rows):
        vs = VoltageSource(voltage=input_voltages[i], name=f"V{i}")
        row_sources.append(vs)
        circuit.wire(vs.neg, circuit.gnd)
    
    # Create column transimpedance amplifiers
    col_amplifiers = []
    for j in range(cols):
        # Create op-amp and feedback resistor
        opamp = SubCircuit(definition=opamp_def, name=f"U{j}")
        rf = Resistor(resistance=rf_value, name=f"RF{j}")
        
        # Wire transimpedance amplifier
        circuit.wire(opamp.plus, circuit.gnd)      # Non-inv to ground
        circuit.wire(opamp.out, rf.n1)             # Output to feedback
        circuit.wire(rf.n2, opamp.minus)           # Feedback to inv input
        
        col_amplifiers.append(opamp)
    
    # Create crosspoint resistors and wire array
    for i in range(rows):
        for j in range(cols):
            r_cross = Resistor(resistance=resistance_matrix[i, j], name=f"R{i}{j}")
            circuit.wire(row_sources[i].pos, r_cross.n1)        # Row to resistor
            circuit.wire(r_cross.n2, col_amplifiers[j].minus)   # Resistor to virtual ground
    
    return circuit, row_sources, col_amplifiers


def analyze_theory(input_voltages, resistance_matrix, rf_value):
    """Calculate theoretical output voltages using matrix multiplication."""
    input_vector = np.array(input_voltages)
    conductance_matrix = 1.0 / resistance_matrix
    
    # Each column current: I[j] = sum(V[i] * G[i,j])
    column_currents = conductance_matrix.T @ input_vector
    
    # Output voltages: V_out[j] = -Rf * I[j]
    output_voltages = -rf_value * column_currents
    
    return output_voltages


def simulate_and_compare(circuit, col_amplifiers, theoretical_outputs):
    """Run SPICE simulation and compare with theory."""
    print("Running SPICE simulation...")
    results = circuit.simulate_operating_point()
    
    print(f"\n📊 Results Comparison:")
    simulated_outputs = []
    
    for j, opamp in enumerate(col_amplifiers):
        # Extract simulated voltage
        voltage = results.get_node_voltage(opamp.out)
        if hasattr(voltage, 'item'):
            voltage = float(voltage.item())
        else:
            voltage = float(voltage)
        
        simulated_outputs.append(voltage)
        
        # Compare with theory
        theoretical = theoretical_outputs[j]
        error = abs(voltage - theoretical)
        
        print(f"Column {j}: Simulated={voltage:.3f}V, Theoretical={theoretical:.3f}V, Error={error:.3f}V")
    
    return np.array(simulated_outputs)


def main():
    """Demonstrate crossbar array matrix multiplication."""
    print("🔬 Simple Resistive Crossbar Array")
    print("=" * 40)
    
    # Configuration
    input_voltages = [1.0, 2.0, 1.5]  # Input vector [V]
    
    # Weight matrix (resistance values in Ohms)
    resistance_matrix = np.array([
        [1e3,  5e3,  10e3],  # Row 0
        [10e3, 1e3,  5e3],   # Row 1  
        [5e3,  10e3, 1e3]    # Row 2
    ])
    
    rf_value = 10e3  # 10kΩ feedback resistors
    
    print(f"Input vector: {input_voltages}")
    print(f"Feedback resistance: {rf_value/1000}kΩ")
    
    # Build circuit
    circuit, row_sources, col_amplifiers = build_crossbar_array(
        input_voltages, resistance_matrix, rf_value
    )

    print("\n📋 SPICE Netlist:")
    print("=" * 40)
    print(circuit.compile_to_spice())
    
    # Theoretical analysis
    theoretical_outputs = analyze_theory(input_voltages, resistance_matrix, rf_value)
    print(f"\n📐 Theoretical outputs: {theoretical_outputs}")
    
    # Simulation and comparison
    simulated_outputs = simulate_and_compare(circuit, col_amplifiers, theoretical_outputs)
    
    print(f"\n✅ Matrix-vector multiplication complete!")
    print(f"Circuit implements: V_out = -Rf * G * V_in")


if __name__ == "__main__":
    main() 
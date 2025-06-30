#!/usr/bin/env python3
"""
Analog Resistive Crossbar Array Simulation

This example demonstrates a resistive crossbar array circuit commonly used in:
- Analog neural networks
- Matrix-vector multiplication circuits  
- Memristor arrays
- Analog computing systems

Circuit topology:
- Rows driven by voltage sources (input vector)
- Columns implemented with op-amp transimpedance amplifiers (output current-to-voltage conversion)
- Crosspoints implemented by fixed resistors (weight matrix)
- Each column output voltage is proportional to the dot product of the input vector with that column

The circuit performs analog matrix-vector multiplication: V_out = G * V_in
where G is the conductance matrix (1/R for each crosspoint resistor).
"""

import sys
import os
import numpy as np

# Add parent directory for local zest imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zest.components import VoltageSource, Resistor, SubCircuit
from zest.circuit import Circuit, gnd
from zest.simulation import check_simulation_requirements

# Try to import matplotlib for plotting (optional)
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("📊 Note: matplotlib not available - plots will be skipped")


def create_ideal_opamp_definition():
    """
    Creates an ideal op-amp definition similar to the XOR example.
    
    Returns:
        Circuit: Ideal op-amp definition with pins: plus, minus, out
    """
    opamp = Circuit("IDEAL_OPAMP")
    
    # Include the ideal op-amp model directly
    opamp.include_model("""
EGAIN out 0 VALUE = {LIMIT(1e6*(V(plus)-V(minus)), -1e12, 1e12)}
""")
    
    # Create external pins - these are just placeholders that will be remapped when used
    opamp.add_pin("plus", opamp.gnd)   # Non-inverting input
    opamp.add_pin("minus", opamp.gnd)  # Inverting input  
    opamp.add_pin("out", opamp.gnd)    # Output
    
    # Flag as external-only
    opamp._is_external_only = True
    
    return opamp


# Create a global ideal op-amp definition (similar to XOR example)
IDEAL_OPAMP_DEF = None

def get_ideal_opamp_definition():
    """
    Gets the ideal op-amp definition, creating it if it doesn't exist.
    
    Returns:
        Circuit: Ideal op-amp definition with pins: plus, minus, out
    """
    global IDEAL_OPAMP_DEF
    if IDEAL_OPAMP_DEF is None:
        IDEAL_OPAMP_DEF = create_ideal_opamp_definition()
    return IDEAL_OPAMP_DEF


def build_transimpedance_amplifier_in_main_circuit(circuit, rf_value, name_suffix):
    """
    Builds a transimpedance amplifier directly in the main circuit.
    
    This creates an op-amp with feedback resistor to convert current to voltage.
    The non-inverting input is grounded, creating a virtual ground at the 
    inverting input, which is perfect for summing currents.
    
    Args:
        circuit: Main circuit to add components to
        rf_value: Feedback resistor value in ohms
        name_suffix: Suffix for component naming (e.g., "0", "1", "2")
        
    Returns:
        tuple: (opamp_instance, feedback_resistor) - the created components
    """
    # Get the ideal op-amp definition
    opamp_def = get_ideal_opamp_definition()
    
    # Create op-amp instance
    opamp = SubCircuit(definition=opamp_def, name=f"OPAMP_{name_suffix}")
    
    # Create feedback resistor
    rf = Resistor(resistance=rf_value, name=f"RF_{name_suffix}")
    
    # Add components to main circuit
    circuit.add_component(opamp)
    circuit.add_component(rf)
    
    # Wire the transimpedance amplifier
    # Non-inverting input to ground (creates virtual ground at inverting input)
    circuit.wire(opamp.plus, circuit.gnd)
    
    # Feedback: output to inverting input via feedback resistor
    circuit.wire(opamp.out, rf.n1)
    circuit.wire(rf.n2, opamp.minus)
    
    return opamp, rf


def build_crossbar_array(rows=3, cols=3, row_voltages=None, crosspoint_resistances=None, rf_value=10e3):
    """
    Builds a complete resistive crossbar array circuit.
    
    Args:
        rows: Number of rows (input voltage sources)
        cols: Number of columns (transimpedance amplifiers)  
        row_voltages: List of input voltages for each row (default: [1V, 2V, 3V, ...])
        crosspoint_resistances: 2D array of crosspoint resistances in ohms
                               (default: creates a pattern matrix)
        rf_value: Feedback resistor value for transimpedance amplifiers
        
    Returns:
        tuple: (circuit, components_dict) containing the built circuit and component references
    """
    print(f"🏗️  Building {rows}x{cols} resistive crossbar array...")
    
    # Set default values if not provided
    if row_voltages is None:
        row_voltages = [float(i+1) for i in range(rows)]  # [1V, 2V, 3V, ...]
        
    if crosspoint_resistances is None:
        # Create a pattern matrix with different resistance values
        crosspoint_resistances = np.zeros((rows, cols))
        for i in range(rows):
            for j in range(cols):
                # Create a pattern: diagonal strong connections, off-diagonal weaker
                if i == j:
                    crosspoint_resistances[i, j] = 1e3   # 1kΩ for diagonal elements
                else:
                    crosspoint_resistances[i, j] = 10e3  # 10kΩ for off-diagonal elements
    
    # Ensure we have the right dimensions
    if len(row_voltages) != rows:
        raise ValueError(f"row_voltages must have {rows} elements")
    if crosspoint_resistances.shape != (rows, cols):
        raise ValueError(f"crosspoint_resistances must be {rows}x{cols} array")
    
    print(f"   📡 Row voltages: {row_voltages}")
    print(f"   📡 Using {rf_value/1000:.1f}kΩ feedback resistors")
    
    # Create the main circuit
    circuit = Circuit("ResistiveCrossbarArray")
    
    # Include the ideal op-amp model directly in the main circuit
    circuit.include_model("""
.subckt IDEAL_OPAMP plus minus out
EGAIN out 0 VALUE = {LIMIT(1e6*(V(plus)-V(minus)), -1e12, 1e12)}
.ends IDEAL_OPAMP
""")
    
    # Create row voltage sources
    row_sources = []
    for i in range(rows):
        vs = VoltageSource(voltage=row_voltages[i], name=f"V_ROW{i}")
        row_sources.append(vs)
        circuit.wire(vs.neg, circuit.gnd)  # All voltage sources share common ground
    
    print(f"   📡 Created {len(row_sources)} row voltage sources")
    
    # Create column transimpedance amplifiers directly in main circuit
    col_amplifiers = []
    col_feedback_resistors = []
    for j in range(cols):
        opamp, rf = build_transimpedance_amplifier_in_main_circuit(circuit, rf_value, str(j))
        col_amplifiers.append(opamp)
        col_feedback_resistors.append(rf)
    
    print(f"   🔌 Created {len(col_amplifiers)} column transimpedance amplifiers")
    
    # Create crosspoint resistors and wire the array
    crosspoint_resistors = {}
    
    print("   🔌 Wiring crosspoint resistors...")
    for i in range(rows):
        for j in range(cols):
            # Create crosspoint resistor
            resistance = crosspoint_resistances[i, j]
            r_name = f"R{i}{j}"
            r_cross = Resistor(resistance=resistance, name=r_name)
            crosspoint_resistors[(i, j)] = r_cross
            
            # Wire: Row voltage source → Crosspoint resistor → Column amplifier inverting input
            circuit.wire(row_sources[i].pos, r_cross.n1)        # Row driver to resistor
            circuit.wire(r_cross.n2, col_amplifiers[j].minus)   # Resistor to op-amp inverting input (virtual ground)
            
            if i == 0 and j < 3:  # Print first few connections for debugging
                print(f"      Row {i} → R{r_name}({resistance/1000:.1f}kΩ) → Col {j}")
    
    print(f"   ✅ Crossbar array built with {rows*cols} crosspoint resistors")
    
    # Package component references for easy access
    components = {
        'row_sources': row_sources,
        'col_amplifiers': col_amplifiers,
        'col_feedback_resistors': col_feedback_resistors,
        'crosspoint_resistors': crosspoint_resistors
    }
    
    return circuit, components


def analyze_crossbar_theory(row_voltages, crosspoint_resistances, rf_value):
    """
    Performs theoretical analysis of the crossbar array behavior.
    
    The output voltage at each column is:
    V_out[j] = -Rf * sum_i( V_in[i] / R[i,j] )
    
    This implements matrix-vector multiplication: V_out = -Rf * G * V_in
    where G[i,j] = 1/R[i,j] is the conductance matrix.
    """
    print("\n📐 Theoretical Analysis:")
    
    row_voltages = np.array(row_voltages)
    conductance_matrix = 1.0 / crosspoint_resistances
    
    print(f"   📊 Input vector (row voltages): {row_voltages}")
    print(f"   📊 Conductance matrix G = 1/R:")
    
    for i in range(conductance_matrix.shape[0]):
        row_str = "      ["
        for j in range(conductance_matrix.shape[1]):
            row_str += f"{conductance_matrix[i,j]*1000:.1f}"  # Convert to mS
            if j < conductance_matrix.shape[1] - 1:
                row_str += ", "
        row_str += "] mS"
        print(row_str)
    
    # Calculate theoretical output voltages
    # Each column output: V_out[j] = -Rf * sum_i(V_in[i] * G[i,j])
    theoretical_outputs = []
    
    print(f"   📊 Theoretical column outputs (Rf = {rf_value/1000:.1f}kΩ):")
    for j in range(conductance_matrix.shape[1]):
        # Current into column j: I[j] = sum_i(V_in[i] / R[i,j])
        col_current = np.sum(row_voltages * conductance_matrix[:, j])
        # Output voltage: V_out[j] = -Rf * I[j]
        output_voltage = -rf_value * col_current
        theoretical_outputs.append(output_voltage)
        
        print(f"      Column {j}: I = {col_current*1000:.3f}mA → V_out = {output_voltage:.3f}V")
    
    return np.array(theoretical_outputs)


def simulate_crossbar_array(circuit, components, theoretical_outputs):
    """
    Simulates the crossbar array and compares results with theory.
    """
    print(f"\n🔬 Running SPICE simulation...")
    
    # Show the generated SPICE netlist
    print("\n📝 Generated SPICE netlist:")
    print("=" * 60)
    netlist = circuit.compile_to_spice()
    print(netlist)
    print("=" * 60)
    
    # Check simulation availability
    available, message = check_simulation_requirements()
    if not available:
        print(f"\n⚠️  Simulation not available: {message}")
        print("Install spicelib for actual simulation: pip install spicelib")
        return None
    
    try:
        # Run DC operating point analysis
        print("\n🔬 Running DC operating point analysis...")
        results = circuit.simulate_operating_point(keep_temp_files=False)
        
        print(f"   ✅ Simulation completed!")
        print(f"   📊 Analysis type: {results.analysis_type}")
        print(f"   📊 Nodes: {len(results.nodes)}")
        print(f"   📊 Branches: {len(results.branches)}")
        
        # Extract column output voltages
        print("\n📊 Column Output Results:")
        simulated_outputs = []
        
        col_amplifiers = components['col_amplifiers']
        for j, opamp in enumerate(col_amplifiers):
            # Get the output voltage from the op-amp
            try:
                output_voltage = results.get_node_voltage(opamp.out)
                
                # Handle case where output_voltage might be a numpy array
                if hasattr(output_voltage, 'item'):
                    output_voltage = float(output_voltage.item())
                elif hasattr(output_voltage, '__len__') and len(output_voltage) == 1:
                    output_voltage = float(output_voltage[0])
                else:
                    output_voltage = float(output_voltage)
                
                simulated_outputs.append(output_voltage)
                
                # Compare with theoretical prediction
                theoretical = theoretical_outputs[j]
                error = abs(output_voltage - theoretical)
                error_pct = (error / abs(theoretical)) * 100 if theoretical != 0 else 0
                
                print(f"   Column {j}:")
                print(f"      Simulated: {output_voltage:.3f}V")
                print(f"      Theoretical: {theoretical:.3f}V")
                print(f"      Error: {error:.3f}V ({error_pct:.1f}%)")
                
            except Exception as e:
                print(f"   ❌ Failed to get output for column {j}: {e}")
                simulated_outputs.append(0.0)
        
        # Ensure all outputs are float values before creating array
        simulated_outputs = [float(x) if x is not None else 0.0 for x in simulated_outputs]
        return np.array(simulated_outputs)
        
    except Exception as e:
        print(f"   ❌ Simulation failed: {e}")
        return None


def plot_results(theoretical_outputs, simulated_outputs=None):
    """
    Plot comparison of theoretical vs simulated results.
    """
    if not HAS_MATPLOTLIB:
        print("\n📊 Plotting skipped (matplotlib not available)")
        return
    
    if simulated_outputs is None:
        print("\n📊 Plotting theoretical results only...")
        
        plt.figure(figsize=(10, 6))
        
        cols = range(len(theoretical_outputs))
        plt.bar(cols, theoretical_outputs, alpha=0.7, label='Theoretical', color='blue')
        
        plt.xlabel('Column Index')
        plt.ylabel('Output Voltage (V)')
        plt.title('Resistive Crossbar Array - Column Outputs')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for i, v in enumerate(theoretical_outputs):
            plt.text(i, v + 0.1*max(abs(theoretical_outputs)), f'{v:.3f}V', 
                    ha='center', va='bottom')
        
        plt.tight_layout()
        plt.show()
        
    else:
        print("\n📊 Plotting theoretical vs simulated comparison...")
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        cols = range(len(theoretical_outputs))
        
        # Bar chart comparison
        x = np.arange(len(cols))
        width = 0.35
        
        ax1.bar(x - width/2, theoretical_outputs, width, label='Theoretical', alpha=0.7)
        ax1.bar(x + width/2, simulated_outputs, width, label='Simulated', alpha=0.7)
        
        ax1.set_xlabel('Column Index')
        ax1.set_ylabel('Output Voltage (V)')
        ax1.set_title('Crossbar Array Outputs: Theory vs Simulation')
        ax1.set_xticks(x)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Error plot
        errors = np.abs(simulated_outputs - theoretical_outputs)
        ax2.bar(cols, errors, alpha=0.7, color='red')
        ax2.set_xlabel('Column Index')
        ax2.set_ylabel('Absolute Error (V)')
        ax2.set_title('Simulation Error')
        ax2.grid(True, alpha=0.3)
        
        # Add value labels
        for i, (t, s, e) in enumerate(zip(theoretical_outputs, simulated_outputs, errors)):
            ax1.text(i-width/2, t + 0.05*max(abs(theoretical_outputs)), f'{t:.3f}', 
                    ha='center', va='bottom', fontsize=9)
            ax1.text(i+width/2, s + 0.05*max(abs(theoretical_outputs)), f'{s:.3f}', 
                    ha='center', va='bottom', fontsize=9)
            ax2.text(i, e + 0.05*max(errors), f'{e:.4f}', 
                    ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        plt.show()


def main():
    """
    Main demonstration of the resistive crossbar array.
    """
    print("🔬 Analog Resistive Crossbar Array Simulation")
    print("=" * 60)
    print("This circuit performs analog matrix-vector multiplication")
    print("using resistive crosspoints and transimpedance amplifiers.")
    print()
    
    # Configuration
    rows, cols = 3, 3
    row_voltages = [1.0, 2.0, 1.5]  # Input vector [V]
    rf_value = 10e3  # 10kΩ feedback resistors
    
    # Define crosspoint resistance matrix (weight matrix)
    # This creates a pattern where:
    # - Diagonal elements have strong connections (low resistance)
    # - Off-diagonal elements have weaker connections (high resistance)
    crosspoint_resistances = np.array([
        [1e3,  5e3,  10e3],  # Row 0: Strong connection to Col 0
        [10e3, 1e3,  5e3 ],  # Row 1: Strong connection to Col 1  
        [5e3,  10e3, 1e3 ]   # Row 2: Strong connection to Col 2
    ])
    
    print(f"📋 Configuration:")
    print(f"   Array size: {rows}x{cols}")
    print(f"   Input voltages: {row_voltages} V")
    print(f"   Feedback resistors: {rf_value/1000:.1f} kΩ")
    print()
    
    # Build the circuit
    circuit, components = build_crossbar_array(
        rows=rows, 
        cols=cols, 
        row_voltages=row_voltages, 
        crosspoint_resistances=crosspoint_resistances,
        rf_value=rf_value
    )
    
    # Theoretical analysis
    theoretical_outputs = analyze_crossbar_theory(
        row_voltages, crosspoint_resistances, rf_value
    )
    
    # SPICE simulation
    simulated_outputs = simulate_crossbar_array(
        circuit, components, theoretical_outputs
    )
    
    # Plotting
    plot_results(theoretical_outputs, simulated_outputs)
    
    print("\n✅ Crossbar array demonstration complete!")
    print("\n💡 Key insights:")
    print("   - Each column output is a weighted sum of all row inputs")
    print("   - The weighting is determined by crosspoint conductances (1/R)")
    print("   - Transimpedance amplifiers convert currents to voltages")
    print("   - This implements analog matrix-vector multiplication")
    print("   - Applications: neural networks, analog computing, signal processing")


if __name__ == "__main__":
    main()
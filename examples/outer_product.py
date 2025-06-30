from zest.circuit import Circuit, SubCircuitDef
from zest.components import Component, Terminal, SubCircuit, CurrentSource, ExternalSubCircuit
import numpy as np
import matplotlib.pyplot as plt
import os


def create_comparator_subcircuit_def():
    """Create a proper differential pair comparator subcircuit definition."""
    lif = SubCircuitDef("comparator")

    # Use relative path like in working test
    lif.add_include("examples/models/mosfets.lib")

    # Add external pins for the comparator
    pin_in1 = Terminal()
    pin_in2 = Terminal()
    pin_out = Terminal()
    pin_vdd = Terminal()
    pin_vss = Terminal()
    
    lif.add_pin("IN1", pin_in1)
    lif.add_pin("IN2", pin_in2)
    lif.add_pin("OUT", pin_out)
    lif.add_pin("VDD", pin_vdd)
    lif.add_pin("VSS", pin_vss)
    
    # Create internal nodes
    n1_terminal = Terminal()  # Common source node for differential pair
    n2_terminal = Terminal()  # Drain of M1 (reference side)
    
    # Current source: I1 from N1 to VSS (bias for differential pair)
    i1 = CurrentSource(current=10e-6, name="I1")  # 10µA
    lif.add_component(i1)
    lif.wire(i1.pos, n1_terminal)  # Positive to common source
    lif.wire(i1.neg, pin_vss)      # Negative to VSS
    
    # PROPER DIFFERENTIAL PAIR: Sources connected together
    # M1: Reference side (Drain=N2, Gate=IN1, Source=N1, Bulk=VSS)
    m1 = ExternalSubCircuit("NMOS_SUBCKT", ["D", "G", "S", "B"], name="M1", W="2u", L="0.18u")
    lif.add_component(m1)
    lif.wire(m1.D, n2_terminal)  # Drain to N2 (reference)
    lif.wire(m1.G, pin_in1)      # Gate to IN1
    lif.wire(m1.S, n1_terminal)  # Source to N1 (common source) ← KEY FIX!
    lif.wire(m1.B, pin_vss)      # Bulk to VSS
    
    # M2: Output side (Drain=OUT, Gate=IN2, Source=N1, Bulk=VSS)
    m2 = ExternalSubCircuit("NMOS_SUBCKT", ["D", "G", "S", "B"], name="M2", W="2u", L="0.18u")
    lif.add_component(m2)
    lif.wire(m2.D, pin_out)      # Drain to OUT ← This will switch!
    lif.wire(m2.G, pin_in2)      # Gate to IN2
    lif.wire(m2.S, n1_terminal)  # Source to N1 (common source) ← KEY FIX!
    lif.wire(m2.B, pin_vss)      # Bulk to VSS
    
    # PMOS CURRENT MIRROR LOAD (proper active load)
    # M3: Current mirror reference (Drain=N2, Gate=N2, Source=VDD, Bulk=VDD)
    m3 = ExternalSubCircuit("PMOS_SUBCKT", ["D", "G", "S", "B"], name="M3", W="2u", L="0.18u")
    lif.add_component(m3)
    lif.wire(m3.D, n2_terminal)  # Drain to N2
    lif.wire(m3.G, n2_terminal)  # Gate to N2 (diode connection)
    lif.wire(m3.S, pin_vdd)      # Source to VDD
    lif.wire(m3.B, pin_vdd)      # Bulk to VDD
    
    # M4: Current mirror output (Drain=OUT, Gate=N2, Source=VDD, Bulk=VDD)
    m4 = ExternalSubCircuit("PMOS_SUBCKT", ["D", "G", "S", "B"], name="M4", W="2u", L="0.18u")
    lif.add_component(m4)
    lif.wire(m4.D, pin_out)      # Drain to OUT
    lif.wire(m4.G, n2_terminal)  # Gate to N2 (current mirror)
    lif.wire(m4.S, pin_vdd)      # Source to VDD
    lif.wire(m4.B, pin_vdd)      # Bulk to VDD
    
    return lif


def create_comparator_test_circuit(vin1_voltage=0.9, vin2_voltage=0.8):
    """Create a test circuit for the comparator with specified input voltages."""
    from zest.components import VoltageSource
    
    # Create the test circuit
    test_circuit = Circuit("ComparatorTest")
        
    # Create comparator subcircuit definition
    comparator_def = create_comparator_subcircuit_def()
    
    # Add voltage sources
    vdd = VoltageSource(voltage=1.8, name="VDD")
    vss = VoltageSource(voltage=0.0, name="VSS") 
    vin1 = VoltageSource(voltage=vin1_voltage, name="VIN1")
    vin2 = VoltageSource(voltage=vin2_voltage, name="VIN2")
    
    # Create comparator instance
    comp = SubCircuit(definition=comparator_def, name="COMP1")
    
    # Wire up the test circuit
    test_circuit.wire(vdd.neg, test_circuit.gnd)
    test_circuit.wire(vss.pos, test_circuit.gnd)
    test_circuit.wire(vin1.neg, test_circuit.gnd)
    test_circuit.wire(vin2.neg, test_circuit.gnd)
    
    test_circuit.wire(comp.VDD, vdd.pos)
    test_circuit.wire(comp.VSS, vss.neg)
    test_circuit.wire(comp.IN1, vin1.pos)
    test_circuit.wire(comp.IN2, vin2.pos)
    
    return test_circuit, comp, vin1, vin2

def demo_comparator_dc_sweep_simulation():
    """Use zest's built-in DC sweep to analyze the comparator."""
    print("\n⚡ DC Sweep Simulation (Built-in)")
    print("=" * 50)
    
    # Create circuit with VIN1 as the swept source
    circuit, comp, vin1_src, vin2_src = create_comparator_test_circuit(0.8, 0.8)
    
    # Use zest's DC sweep functionality
    print("Running DC sweep of VIN1 from 0.5V to 1.1V...")
    
    simulated_circuit = circuit.simulate_dc_sweep(
        source_component=vin1_src,
        start=0.5,
        stop=1.1, 
        step=0.001
    )
    
    print("✅ DC sweep simulation completed!")
    
    # Get sweep results
    sweep_var = simulated_circuit.get_sweep_variable()
    vout_sweep = simulated_circuit.get_node_voltage(comp.OUT)
    
    print(f"Sweep variable: {len(sweep_var)} points from {sweep_var[0]:.2f}V to {sweep_var[-1]:.2f}V")
    print(f"Output voltage range: {min(vout_sweep):.3f}V to {max(vout_sweep):.3f}V")
    
    # Find switching point
    mid_voltage = 0.9  # VDD/2 as switching threshold
    crossing_indices = []
    for i in range(len(vout_sweep) - 1):
        if (vout_sweep[i] < mid_voltage < vout_sweep[i+1]) or (vout_sweep[i] > mid_voltage > vout_sweep[i+1]):
            crossing_indices.append(i)
    
    if crossing_indices:
        switch_voltage = sweep_var[crossing_indices[0]]
        print(f"🎯 Switching point found at VIN1 ≈ {switch_voltage:.3f}V")
    
    # Plot DC sweep results
    plt.figure(figsize=(10, 6))
    plt.plot(sweep_var, vout_sweep, 'b-', linewidth=2, label='VOUT')
    plt.axhline(y=mid_voltage, color='r', linestyle='--', alpha=0.7, label='Switching threshold')
    plt.axvline(x=0.8, color='g', linestyle='--', alpha=0.7, label='VIN2 = 0.8V')
    plt.xlabel('VIN1 (V)')
    plt.ylabel('VOUT (V)')
    plt.title('Comparator DC Sweep Analysis')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.xlim(0.5, 1.1)
    plt.ylim(0, 1.8)
    
    plt.savefig('comparator_dc_sweep.png', dpi=150, bbox_inches='tight')
    print(f"📊 DC sweep plot saved as 'comparator_dc_sweep.png'")
    plt.show()

def create_lif_neuron_subcircuit_def():
    """Create a leaky integrate-and-fire neuron subcircuit definition."""
    lif = SubCircuitDef("lif_neuron")
    
    # Use relative path for models
    lif.add_include("examples/models/mosfets.lib")
    
    # External pins for the LIF neuron
    pin_i_input = Terminal()  # Current input
    pin_v_mem = Terminal()    # Membrane voltage output  
    pin_spike = Terminal()    # Spike output from comparator
    pin_vdd = Terminal()      # Power supply
    pin_vss = Terminal()      # Ground
    
    lif.add_pin("I_INPUT", pin_i_input)
    lif.add_pin("V_MEM", pin_v_mem) 
    lif.add_pin("SPIKE", pin_spike)
    lif.add_pin("VDD", pin_vdd)
    lif.add_pin("VSS", pin_vss)
    
    # Internal nodes
    v_threshold = Terminal()  # Reference threshold voltage
    
    # === RC MEMBRANE MODEL ===
    # Membrane resistance (100kΩ for τ=10ms with C=100nF)
    from zest.components import Resistor, Capacitor, VoltageSource
    
    r_mem = Resistor(resistance=100e3, name="R_MEM")  # 100kΩ
    lif.add_component(r_mem)
    lif.wire(r_mem.n1, pin_v_mem)     # One end to membrane voltage
    lif.wire(r_mem.n2, pin_vss)       # Other end to ground (leak)
    
    # Membrane capacitance (100nF for τ=10ms with R=100kΩ)  
    c_mem = Capacitor(capacitance=100e-9, name="C_MEM")  # 100nF
    lif.add_component(c_mem)
    lif.wire(c_mem.pos, pin_v_mem)    # Positive plate to membrane voltage
    lif.wire(c_mem.neg, pin_vss)      # Negative plate to ground
    
    # Current input connection (external current source will connect here)
    # The input current flows into the V_MEM node, charging the capacitor
    # and flowing through the resistor (creating the leaky integration)
    lif.wire(pin_i_input, pin_v_mem)  # Input current flows to membrane
    
    # === THRESHOLD DETECTION ===
    # For now, let's simplify and just connect the spike output directly to the membrane voltage
    # to test the RC charging behavior without the comparator complexity
    lif.wire(pin_spike, pin_v_mem)    # Temporary: spike output = membrane voltage
    
    # TODO: Add comparator back once RC charging is working properly
    
    return lif


def create_lif_test_circuit(input_current=10e-6):
    """Create a test circuit for the LIF neuron with specified input current."""
    from zest.components import VoltageSource, CurrentSource
    
    # Create the test circuit
    test_circuit = Circuit("LIF_Test")
    
    # Add voltage sources
    vdd = VoltageSource(voltage=1.8, name="VDD")
    vss = VoltageSource(voltage=0.0, name="VSS")
    
    # Input current source (10µA default)
    i_input = CurrentSource(current=input_current, name="I_INPUT")
    
    # Create LIF neuron instance
    lif_def = create_lif_neuron_subcircuit_def()
    neuron = SubCircuit(definition=lif_def, name="NEURON1")
    
    # Wire up the test circuit
    test_circuit.wire(vdd.neg, test_circuit.gnd)
    test_circuit.wire(vss.pos, test_circuit.gnd)
    
    # Power connections
    test_circuit.wire(neuron.VDD, vdd.pos)
    test_circuit.wire(neuron.VSS, vss.neg)
    
    # Input current connection (fix direction: current should flow INTO the neuron)
    test_circuit.wire(i_input.neg, neuron.I_INPUT)  # Negative terminal to neuron (current flows out of source into neuron)
    test_circuit.wire(i_input.pos, test_circuit.gnd)  # Positive terminal to ground
    
    return test_circuit, neuron, i_input


def demo_lif_rc_charging():
    """Demonstrate the RC charging behavior of the LIF neuron."""
    print("\n⚡ LIF Neuron RC Charging Demo")
    print("=" * 50)
    
    # Create test circuit with 5µA input current (should reach 0.5V steady-state)
    circuit, neuron, i_input = create_lif_test_circuit(5e-6)
    
    # DEBUG: Print the SPICE netlist to understand the issue
    print("Generated SPICE netlist:")
    print("="*60)
    netlist = circuit.compile_to_spice()
    print(netlist)
    print("="*60)
    
    print("Circuit parameters:")
    print(f"  R_membrane = 100kΩ")
    print(f"  C_membrane = 100nF") 
    print(f"  τ = RC = 10ms")
    print(f"  I_input = 5µA")
    print(f"  V_threshold = 1.0V")
    
    # Calculate expected behavior
    R = 100e3  # 100kΩ
    I = 5e-6   # 5µA
    tau = 10e-3  # 10ms
    V_final = I * R  # Final voltage if no threshold
    
    print(f"\nExpected behavior:")
    print(f"  V_final = I×R = {V_final:.3f}V")
    print(f"  Time to 63% = τ = {tau*1000:.1f}ms")
    
    # Calculate time to threshold (avoid log(0) when V_final = V_threshold)
    if V_final > 1.0:
        t_threshold = -tau * np.log(1 - 1.0/V_final) * 1000
        print(f"  Time to threshold (1.0V) ≈ {t_threshold:.1f}ms")
    elif V_final == 1.0:
        print(f"  Time to threshold (1.0V) ≈ ∞ (asymptotic approach)")
    else:
        print(f"  Threshold (1.0V) never reached (V_final < threshold)")
    
    # Run transient simulation
    print("\nRunning transient simulation (0 to 50ms)...")
    
    simulated_circuit = circuit.simulate_transient(
        step_time=0.1e-3,  # 0.1ms steps
        end_time=50e-3     # 50ms total
    )
    
    print("✅ Transient simulation completed!")
    
    # Debug: Show available nodes
    print("Debug - Available nodes:")
    for node_name in simulated_circuit.nodes.keys():
        print(f"  {node_name}")
    
    print("Debug - Circuit components:")
    for comp, name in simulated_circuit.list_components():
        print(f"  {name}: {comp}")
    
    # Extract results
    time = simulated_circuit.get_time_vector()
    
    try:
        v_mem = simulated_circuit.get_node_voltage(neuron.V_MEM)
        print(f"✅ Got V_MEM voltage data")
    except Exception as e:
        print(f"❌ Error getting V_MEM: {e}")
        # Fallback: try to access membrane voltage via the I_INPUT node (N3)
        try:
            # The RC charging happens at the I_INPUT node (N3 in SPICE)
            v_mem = simulated_circuit._get_node_voltage_value('n3')
            print(f"✅ Got V_MEM via I_INPUT node: n3")
        except Exception as e2:
            print(f"❌ Fallback also failed: {e2}")
            v_mem = None
        
    try:
        v_spike = simulated_circuit.get_node_voltage(neuron.SPIKE)
        print(f"✅ Got SPIKE voltage data")
    except Exception as e:
        print(f"❌ Error getting SPIKE: {e}")
        # Fallback: SPIKE is connected to V_MEM which is connected to I_INPUT (N3)
        try:
            v_spike = simulated_circuit._get_node_voltage_value('n3')
            print(f"✅ Got SPIKE via I_INPUT node: n3")
        except Exception as e2:
            print(f"❌ SPIKE fallback also failed: {e2}")
            v_spike = None
    
    print(f"Simulation results:")
    print(f"  Time points: {len(time) if time is not None else 'N/A'}")
    
    if v_mem is not None:
        print(f"  V_mem range: {min(v_mem):.3f}V to {max(v_mem):.3f}V")
        # Check if threshold was reached
        threshold_reached = np.any(v_mem >= 1.0)
        if threshold_reached:
            crossing_time = time[np.where(v_mem >= 1.0)[0][0]]
            print(f"🎯 Threshold reached at t = {crossing_time*1000:.1f}ms")
        else:
            print("⚠️  Threshold not reached in simulation time")
    else:
        print("  V_mem: Not available")
        
    if v_spike is not None:
        print(f"  V_spike range: {min(v_spike):.3f}V to {max(v_spike):.3f}V")
    else:
        print("  V_spike: Not available")
    
    # Plot results (only if we have data)
    if time is not None and (v_mem is not None or v_spike is not None):
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Membrane voltage
        if v_mem is not None:
            ax1.plot(time*1000, v_mem, 'b-', linewidth=2, label='V_membrane')
            ax1.axhline(y=1.0, color='r', linestyle='--', alpha=0.7, label='Threshold (1.0V)')
            ax1.axhline(y=V_final, color='g', linestyle=':', alpha=0.7, label=f'V_final = {V_final:.2f}V')
        else:
            ax1.text(0.5, 0.5, 'V_membrane data not available', ha='center', va='center', transform=ax1.transAxes)
        ax1.set_ylabel('Membrane Voltage (V)')
        ax1.set_title('LIF Neuron: RC Charging Behavior')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax1.set_xlim(0, 50)
        
        # Spike output  
        if v_spike is not None:
            ax2.plot(time*1000, v_spike, 'r-', linewidth=2, label='Spike Output')
        else:
            ax2.text(0.5, 0.5, 'V_spike data not available', ha='center', va='center', transform=ax2.transAxes)
        ax2.set_xlabel('Time (ms)')
        ax2.set_ylabel('Spike Voltage (V)')
        ax2.set_title('Comparator Output (Spike Detection)')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        ax2.set_xlim(0, 50)
        
        plt.tight_layout()
        plt.savefig('lif_neuron_response.png', dpi=150, bbox_inches='tight')
        print(f"📊 Plot saved as 'lif_neuron_response.png'")
        plt.show()
    else:
        print("⚠️  No plotting data available")


def main():
    # Create the comparator subcircuit definition
    comparator_def = create_comparator_subcircuit_def()
    
    # Test the subcircuit by creating a simple test circuit
    test_circuit = Circuit("ComparatorTest")
    
    # Use relative path like in working test
    test_circuit.add_include("examples/models/mosfets.lib")
    
    # Add voltage sources for testing
    from zest.components import VoltageSource
    
    vdd = VoltageSource(voltage=1.8, name="VDD")
    vss = VoltageSource(voltage=0.0, name="VSS") 
    vin1 = VoltageSource(voltage=0.9, name="VIN1")
    vin2 = VoltageSource(voltage=0.8, name="VIN2")
    
    # Create comparator instance
    comp = SubCircuit(definition=comparator_def, name="COMP1")
    
    # Wire up the test circuit
    test_circuit.wire(vdd.neg, test_circuit.gnd)
    test_circuit.wire(vss.pos, test_circuit.gnd)
    test_circuit.wire(vin1.neg, test_circuit.gnd)
    test_circuit.wire(vin2.neg, test_circuit.gnd)
    
    test_circuit.wire(comp.VDD, vdd.pos)
    test_circuit.wire(comp.VSS, vss.neg)
    test_circuit.wire(comp.IN1, vin1.pos)
    test_circuit.wire(comp.IN2, vin2.pos)
    
    print("Comparator subcircuit created successfully!")
    print("SPICE netlist preview:")
    print(test_circuit.compile_to_spice())
    
    # Run simulation demos
    print("\n" + "="*60)
    print("🚀 RUNNING COMPARATOR SIMULATION DEMOS")
    print("="*60)
    
    # Demo 3: Built-in DC sweep
    demo_comparator_dc_sweep_simulation()
    
    # NEW: Demo LIF neuron RC charging
    print("\n" + "="*60)
    print("🧠 RUNNING LIF NEURON DEMOS")
    print("="*60)
    
    demo_lif_rc_charging()


if __name__ == "__main__":
    main()
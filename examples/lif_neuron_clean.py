import numpy as np
import matplotlib.pyplot as plt

from zest.circuit import Circuit, SubCircuitDef, SubCircuitInst
from zest.components import (
    Resistor, Capacitor, CurrentSource, Terminal, SubCircuit
)


def create_voltage_controlled_switch_with_hysteresis_subcircuit(on_voltage=0.2, hysteresis_voltage=0.1):
    """
    Creates a subcircuit definition for a voltage-controlled switch with hysteresis.
    
    Args:
        on_voltage: Threshold voltage for switch activation
        hysteresis_voltage: Hysteresis voltage for switch behavior
    
    Returns:
        SubCircuitDef: Switch subcircuit with pins N1, N2, NCP, NCM
    """
    switch_def = SubCircuitDef("voltage_controlled_switch")

    # Define the pins
    pin_n1 = Terminal()
    pin_n2 = Terminal()
    pin_ncp = Terminal()
    pin_ncm = Terminal()

    # Add pins to subcircuit
    switch_def.add_pin("N1", pin_n1)
    switch_def.add_pin("N2", pin_n2)
    switch_def.add_pin("NCP", pin_ncp)
    switch_def.add_pin("NCM", pin_ncm)

    # Define and include the switch model
    switch_model = (
        f".model SW1 SW(Ron={1e-9} Roff={1e9} Vt={on_voltage} Vh={hysteresis_voltage})"
    )
    switch_def.include_model(switch_model)

    # Instantiate the switch element inside the subcircuit
    switch_element = f"S1 N1 N2 NCP NCM SW1"
    switch_def.include_model(switch_element)

    return switch_def


def create_rc_with_switch_subcircuit(r=1e6, c=1e-6, switch_on_voltage=0.5, switch_hysteresis=0.4):
    """
    Creates a subcircuit definition for an RC circuit with a voltage-controlled switch.
    This implements the core of a leaky integrate-and-fire neuron.
    
    The circuit consists of:
    - RC membrane (resistor and capacitor)
    - Voltage-controlled switch for reset functionality
    - Switch control is connected to the capacitor voltage (self-triggering)
    
    Args:
        r: Membrane resistance (Ohms)
        c: Membrane capacitance (Farads)
        switch_on_voltage: Voltage threshold for switch activation
        switch_hysteresis: Hysteresis voltage for switch behavior
    
    Returns:
        SubCircuitDef: RC with switch subcircuit with pins IN, OUT, CTRL
    """
    rc_def = SubCircuitDef("rc_with_switch")

    # Create the voltage-controlled switch with hysteresis
    switch_def = create_voltage_controlled_switch_with_hysteresis_subcircuit(
        on_voltage=switch_on_voltage, 
        hysteresis_voltage=switch_hysteresis
    )
    switch = SubCircuitInst(switch_def)
    rc_def.add_component(switch)

    # Create RC membrane components
    r_leak = Resistor(r, "R_leak")
    c_mem = Capacitor(c, "C_mem")

    # Wire the RC membrane
    rc_def.wire(r_leak.n2, rc_def.gnd)           # Resistor to ground
    rc_def.wire(c_mem.pos, r_leak.n1)            # Capacitor positive to resistor
    rc_def.wire(c_mem.neg, rc_def.gnd)           # Capacitor negative to ground
    
    # Wire the switch for reset functionality
    rc_def.wire(c_mem.pos, switch.N1)            # Switch input from membrane
    rc_def.wire(switch.NCM, rc_def.gnd)          # Switch control minus to ground
    rc_def.wire(switch.NCP, c_mem.pos)           # Switch control plus to membrane (self-triggering)

    # Expose pins
    rc_def.add_pin("IN", r_leak.n1)              # Current input to membrane
    rc_def.add_pin("OUT", switch.N2)             # Switch output (spike signal)
    rc_def.add_pin("CTRL", switch.NCP)           # Control signal monitoring

    return rc_def


def test_lif_neuron_circuit(input_current=5e-6, membrane_r=1e6, membrane_c=1e-6, sim_time=8.0):
    """
    Tests the leaky integrate-and-fire neuron circuit.
    
    Args:
        input_current: Input current in Amperes
        membrane_r: Membrane resistance in Ohms
        membrane_c: Membrane capacitance in Farads
        sim_time: Simulation time in seconds
    
    Returns:
        Simulation results object
    """
    # Create the LIF neuron circuit
    rc_def = create_rc_with_switch_subcircuit(r=membrane_r, c=membrane_c)
    rc = SubCircuitInst(rc_def)
    
    circuit = Circuit("LIF Neuron Circuit")
    circuit.add_component(rc)

    # Add input current source
    charging_current = CurrentSource(current=input_current, name="charging_current")
    circuit.add_component(charging_current)
    circuit.wire(charging_current.neg, rc.IN)
    circuit.wire(charging_current.pos, circuit.gnd)

    # Add pull-down resistor for output
    r_pulldown = Resistor(1e3, "R_pulldown")
    circuit.add_component(r_pulldown)
    circuit.wire(rc.OUT, r_pulldown.n1)
    circuit.wire(r_pulldown.n2, circuit.gnd)

    # Print circuit analysis
    tau = membrane_r * membrane_c
    print(f"LIF Neuron Circuit Parameters:")
    print(f"Membrane time constant: {tau:.3f} s")
    print(f"Input current: {input_current*1e6:.1f} μA")
    print(f"Membrane resistance: {membrane_r/1e6:.1f} MΩ")
    print(f"Membrane capacitance: {membrane_c*1e6:.1f} μF")
    print(f"Expected voltage rise: {input_current * membrane_r:.2f} V")

    # Print SPICE netlist for debugging
    print("\nGenerated SPICE Netlist:")
    print("=" * 50)
    print(circuit.compile_to_spice())
    print("=" * 50)

    # Run simulation
    print(f"\nRunning simulation for {sim_time} seconds...")
    results = circuit.simulate_transient(
        step_time=1e-4,
        end_time=sim_time
    )
    
    # Extract and analyze results
    time = results.get_time_vector()
    v_out = results.get_node_voltage(rc.OUT)
    v_membrane = results.get_node_voltage(rc.IN)

    # Count spikes (transitions in output)
    spike_transitions = np.diff(v_out > 0.5).astype(int)
    spike_count = np.sum(spike_transitions == 1)
    spike_rate = spike_count / sim_time

    print(f"\nSimulation Results:")
    print(f"Total spikes: {spike_count}")
    print(f"Average spike rate: {spike_rate:.3f} Hz")
    print(f"Peak membrane voltage: {np.max(v_membrane):.3f} V")
    print(f"Minimum membrane voltage: {np.min(v_membrane):.3f} V")

    # Create plots
    plt.figure(figsize=(12, 8))
    
    plt.subplot(2, 1, 1)
    plt.plot(time, v_membrane, 'g-', linewidth=2, label='Membrane Voltage')
    plt.ylabel('Voltage (V)')
    plt.title('LIF Neuron: Membrane Voltage')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.subplot(3, 1, 2)
    plt.plot(time, v_out, 'b-', linewidth=2, label='Output Voltage (Spikes)')
    plt.ylabel('Voltage (V)')
    plt.title('LIF Neuron: Spike Output')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('lif_neuron_clean.png', dpi=150, bbox_inches='tight')
    print(f"\nPlot saved as lif_neuron_clean.png")

    return results


if __name__ == "__main__":
    # Test the LIF neuron circuit
    test_lif_neuron_circuit(
        input_current=5e-6,    # 5 μA input current
        membrane_r=1e6,        # 1 MΩ membrane resistance
        membrane_c=1e-6,       # 1 μF membrane capacitance
        sim_time=8.0           # 8 second simulation
    ) 
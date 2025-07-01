# lif_streamlit.py

import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

# Your zest imports
from zest.circuit import Circuit, SubCircuitDef, SubCircuitInst
from zest.components import Resistor, Capacitor, CurrentSource, Terminal, SubCircuit

def create_voltage_controlled_switch_with_hysteresis_subcircuit(on_voltage=0.2, hysteresis_voltage=0.1):
    switch_def = SubCircuitDef("voltage_controlled_switch")
    pin_n1 = Terminal()
    pin_n2 = Terminal()
    pin_ncp = Terminal()
    pin_ncm = Terminal()
    switch_def.add_pin("N1", pin_n1)
    switch_def.add_pin("N2", pin_n2)
    switch_def.add_pin("NCP", pin_ncp)
    switch_def.add_pin("NCM", pin_ncm)
    switch_model = (
        f".model SW1 SW(Ron={1e-9} Roff={1e9} Vt={on_voltage} Vh={hysteresis_voltage})"
    )
    switch_def.include_model(switch_model)
    switch_element = f"S1 N1 N2 NCP NCM SW1"
    switch_def.include_model(switch_element)
    return switch_def

def create_rc_with_switch_subcircuit(r=1e6, c=1e-6, switch_on_voltage=0.5, switch_hysteresis=0.4):
    rc_def = SubCircuitDef("rc_with_switch")
    switch_def = create_voltage_controlled_switch_with_hysteresis_subcircuit(
        on_voltage=switch_on_voltage, 
        hysteresis_voltage=switch_hysteresis
    )
    switch = SubCircuitInst(switch_def)
    rc_def.add_component(switch)
    r_leak = Resistor(r, "R_leak")
    c_mem = Capacitor(c, "C_mem")
    rc_def.wire(r_leak.n2, rc_def.gnd)
    rc_def.wire(c_mem.pos, r_leak.n1)
    rc_def.wire(c_mem.neg, rc_def.gnd)
    rc_def.wire(c_mem.pos, switch.N1)
    rc_def.wire(switch.NCM, rc_def.gnd)
    rc_def.wire(switch.NCP, c_mem.pos)
    rc_def.add_pin("IN", r_leak.n1)
    rc_def.add_pin("OUT", switch.N2)
    rc_def.add_pin("CTRL", switch.NCP)
    return rc_def

def run_and_plot_lif(input_current=5e-6, membrane_r=1e6, membrane_c=1e-6, sim_time=8.0):
    rc_def = create_rc_with_switch_subcircuit(r=membrane_r, c=membrane_c)
    rc = SubCircuitInst(rc_def)
    circuit = Circuit("LIF Neuron Circuit")
    circuit.add_component(rc)
    charging_current = CurrentSource(current=input_current, name="charging_current")
    circuit.add_component(charging_current)
    circuit.wire(charging_current.neg, rc.IN)
    circuit.wire(charging_current.pos, circuit.gnd)
    r_pulldown = Resistor(1e3, "R_pulldown")
    circuit.add_component(r_pulldown)
    circuit.wire(rc.OUT, r_pulldown.n1)
    circuit.wire(r_pulldown.n2, circuit.gnd)
    results = circuit.simulate_transient(
        step_time=1e-4,
        end_time=sim_time
    )
    time = results.get_time_vector()
    v_out = results.get_node_voltage(rc.OUT)
    v_membrane = results.get_node_voltage(rc.IN)
    spike_transitions = np.diff(v_out > 0.5).astype(int)
    spike_count = np.sum(spike_transitions == 1)
    spike_rate = spike_count / sim_time

    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    axes[0].plot(time, v_membrane, 'g-', linewidth=2)
    axes[0].set_ylabel('Membrane Voltage (V)')
    axes[0].set_title('LIF Neuron: Membrane Voltage')
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(time, v_out, 'b-', linewidth=2)
    axes[1].set_ylabel('Output Voltage (V)')
    axes[1].set_xlabel('Time (s)')
    axes[1].set_title('LIF Neuron: Spike Output')
    axes[1].grid(True, alpha=0.3)
    plt.tight_layout()

    st.pyplot(fig)
    st.markdown(f"""
    - **Total spikes:** {spike_count}
    - **Average spike rate:** {spike_rate:.3f} Hz
    - **Peak membrane voltage:** {np.max(v_membrane):.3f} V
    - **Minimum membrane voltage:** {np.min(v_membrane):.3f} V
    """)

# --- Streamlit UI ---
st.title("Interactive LIF Neuron Simulator")

input_current = st.slider("Input Current (μA)", min_value=0.1, max_value=100.0, value=5.0, step=0.1) * 1e-6
membrane_r = st.slider("Membrane Resistance (MΩ)", min_value=0.001, max_value=1000.0, value=1.0, step=0.01) * 1e6
membrane_c = st.slider("Membrane Capacitance (μF)", min_value=0.001, max_value=10.0, value=1.0, step=0.001) * 1e-6
sim_time = st.slider("Simulation Time (s)", min_value=1.0, max_value=20.0, value=8.0, step=0.1)

run_and_plot_lif(input_current, membrane_r, membrane_c, sim_time)

# run with `streamlit run lif_interactive.py`
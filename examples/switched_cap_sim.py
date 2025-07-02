import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from zest.circuit import Circuit, SubCircuitDef, SubCircuitInst
from zest.components import Capacitor, PulsedVoltageSource, Terminal, CurrentSource

from lif_neuron_clean import create_voltage_controlled_switch_with_hysteresis_subcircuit


def create_inverter_subcircuit(v_high=1.0, v_low=0.0, v_th=0.5):
    inverter_def = SubCircuitDef("inverter")

    pin_in = Terminal()
    pin_out = Terminal()

    inverter_def.add_pin("IN", pin_in)
    inverter_def.add_pin("OUT", pin_out)

    expression = f"V = {v_high} - (V(IN) > {v_th}) * ({v_high} - {v_low})"
    inverter_def.include_model(f"BVOUT OUT 0 {expression}")

    return inverter_def


def create_switched_cap_subcircuit(c=1e-6, switch_on_voltage=0.5):
    switched_cap_def = SubCircuitDef("switched_cap")

    pin_in = Terminal()
    pin_out = Terminal()
    pin_switch = Terminal()

    switched_cap_def.add_pin("IN", pin_in)
    switched_cap_def.add_pin("OUT", pin_out)
    switched_cap_def.add_pin("SW", pin_switch)

    switch_def = create_voltage_controlled_switch_with_hysteresis_subcircuit(
        on_voltage=switch_on_voltage, hysteresis_voltage=0
    )
    sw1 = SubCircuitInst(switch_def)
    sw2 = SubCircuitInst(switch_def)
    inverter_def = create_inverter_subcircuit(v_high=1.0, v_low=0.0)
    inverter = SubCircuitInst(inverter_def)
    c1 = Capacitor(c)

    switched_cap_def.add_component(sw1)
    switched_cap_def.add_component(sw2)
    switched_cap_def.add_component(c1)

    switched_cap_def.wire(sw1.N1, pin_in)
    switched_cap_def.wire(sw1.N2, c1.pos)
    switched_cap_def.wire(sw2.N1, c1.pos)
    switched_cap_def.wire(c1.neg, switched_cap_def.gnd)
    switched_cap_def.wire(sw2.N2, pin_out)

    switched_cap_def.wire(sw1.NCP, pin_switch)
    switched_cap_def.wire(pin_switch, inverter.IN)
    switched_cap_def.wire(inverter.OUT, sw2.NCP)
    switched_cap_def.wire(sw1.NCM, switched_cap_def.gnd)
    switched_cap_def.wire(sw2.NCM, switched_cap_def.gnd)

    return switched_cap_def


def calculate_moving_average(signal, window_size):
    window = np.ones(window_size) / window_size
    return np.convolve(signal, window, mode='valid')


def simulate_switched_cap(c_value, freq):
    period = 1 / freq
    switched_cap_def = create_switched_cap_subcircuit(c=c_value)
    switched_cap = SubCircuitInst(switched_cap_def)

    circuit = Circuit("switched_cap_test")
    circuit.add_component(switched_cap)

    v_switch = PulsedVoltageSource(
        v1=0.0, v2=1.0,
        td=0.0, tr=1e-9, tf=1e-9,
        pw=period / 2, per=period
    )
    circuit.add_component(v_switch)
    circuit.wire(v_switch.neg, circuit.gnd)
    circuit.wire(v_switch.pos, switched_cap.SW)

    i_source = CurrentSource(1e-6)  # 1 µA
    circuit.add_component(i_source)
    circuit.wire(i_source.pos, switched_cap.IN)
    circuit.wire(i_source.neg, circuit.gnd)
    circuit.wire(switched_cap.OUT, circuit.gnd)

    results = circuit.simulate_transient(end_time=10 * period, step_time=period / 100)

    time = results.get_time_vector()
    v_in = results.get_node_voltage(switched_cap.IN)
    i_in = np.full_like(time, results.get_component_current(i_source))

    window_size = int(1.0 / freq / (period / 100)) * 5
    v_avg = calculate_moving_average(v_in, window_size)
    i_avg = calculate_moving_average(i_in, window_size)
    time_avg = time[window_size - 1:]

    r_eq_inst = v_in / 1e-6
    r_eq_avg = np.divide(v_avg, i_avg, out=np.zeros_like(v_avg), where=i_avg > 1e-12)

    return time, time_avg, v_in, v_avg, i_in, i_avg, r_eq_inst, r_eq_avg


# Streamlit UI
st.title("Switched-Capacitor Resistor Simulator")

c_val = st.slider("Capacitance (µF)", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
freq_val = st.slider("Switching Frequency (Hz)", min_value=10, max_value=5000, value=500, step=10)

c = c_val * 1e-6
f = freq_val

with st.spinner("Running simulation..."):
    t, t_avg, v_in, v_avg, i_in, i_avg, r_eq, r_eq_avg = simulate_switched_cap(c, f)

# Plotting
st.subheader("Voltage, Current, and Resistance over Time")

fig, axs = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

axs[0].plot(t, v_in, 'r-', alpha=0.5, label='Voltage (instant)')
axs[0].plot(t_avg, v_avg, 'k-', label='Voltage (avg)')
axs[0].set_ylabel("Voltage (V)")
axs[0].legend()
axs[0].grid(True, alpha=0.3)

axs[1].plot(t, i_in, 'b-', alpha=0.5, label='Current (instant)')
axs[1].plot(t_avg, i_avg, 'k-', label='Current (avg)')
axs[1].set_ylabel("Current (A)")
axs[1].legend()
axs[1].grid(True, alpha=0.3)

axs[2].plot(t, r_eq / 1e3, 'g-', alpha=0.5, label='Resistance (instant)')
axs[2].plot(t_avg, r_eq_avg / 1e3, 'k-', label='Resistance (avg)')
axs[2].set_ylabel("Resistance (kΩ)")
axs[2].set_xlabel("Time (s)")
axs[2].legend()
axs[2].grid(True, alpha=0.3)

st.pyplot(fig)

# Result summary
r_theory = 1 / (c * f)
st.markdown(f"**Theoretical R_eq:** {r_theory / 1e3:.2f} kΩ")
st.markdown(f"**Measured Average R_eq (last window):** {r_eq_avg[-1] / 1e3:.2f} kΩ")

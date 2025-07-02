from matplotlib import pyplot as plt
import numpy as np
# from examples.lif_neuron_clean import create_voltage_controlled_switch_with_hysteresis_subcircuit
from lif_neuron_clean import create_voltage_controlled_switch_with_hysteresis_subcircuit
from zest.circuit import Circuit, SubCircuitDef, SubCircuitInst
from zest.components import Capacitor, PulsedVoltageSource, Terminal, VoltageSource, Resistor, CurrentSource

def create_inverter_subcircuit(v_high=1.0, v_low=0.0, v_th=0.5):
    inverter_def = SubCircuitDef("inverter")

    pin_in = Terminal()
    pin_out = Terminal()

    inverter_def.add_pin("IN", pin_in)
    inverter_def.add_pin("OUT", pin_out)

    # Use a behavioral voltage source with conditional logic
    # Use a "B" source, which is valid in SPICE:
    expression = f"V = {v_high} - (V(IN) > {v_th}) * ({v_high} - {v_low})"
    inverter_def.include_model(f"BVOUT OUT 0 {expression}")

    return inverter_def

def test_inverter():
    inverter_def = create_inverter_subcircuit(v_high=1.0, v_low=0.0)
    # print(inverter_def.compile_as_subckt())
    inverter = SubCircuitInst(inverter_def)

    circuit = Circuit("inverter_test")
    circuit.add_component(inverter)

    v_in = PulsedVoltageSource(
        v1=0.0,
        v2=1.0,
        td=0.0,
        tr=1e-9,
        tf=1e-9,
        pw=.1,
        per=.2,
    )
    circuit.add_component(v_in)

    circuit.wire(v_in.pos, inverter.IN)
    circuit.wire(v_in.neg, circuit.gnd)

    print(circuit.compile_to_spice())

    results = circuit.simulate_transient(end_time=1, step_time=1e-3)

    time = results.get_time_vector()
    v_out = results.get_node_voltage(inverter.OUT)

    plt.plot(time, results.get_node_voltage(v_in.pos), 'r-', linewidth=2, label='Input Voltage')
    plt.plot(time, v_out, 'b-', linewidth=2, label='Output Voltage')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.show()

# def create_switched_cap_subcircuit(c=1e-6, switch_on_voltage=0.5):
#     switched_cap_def = SubCircuitDef("switched_cap")

#     pin_in = Terminal()
#     pin_out = Terminal()
#     pin_switch = Terminal()
#     # create a distinct node for the inverted clock
#     ctrl_inv = Terminal()                                      # NEW

#     switched_cap_def.add_pin("IN", pin_in)
#     switched_cap_def.add_pin("OUT", pin_out)
#     switched_cap_def.add_pin("SW", pin_switch)

#     # Create voltage-controlled switches
#     switch_def = create_voltage_controlled_switch_with_hysteresis_subcircuit(on_voltage=switch_on_voltage, hysteresis_voltage=0)
#     sw1 = SubCircuitInst(switch_def)  # Input switch
#     sw2 = SubCircuitInst(switch_def)  # Output switch
    
#     inverter_def = create_inverter_subcircuit(v_high=1.0, v_low=0.0)
#     inverter = SubCircuitInst(inverter_def)
#     c1 = Capacitor(c)

#     switched_cap_def.wire(inverter.OUT, ctrl_inv)              # inverter → ctrl_inv

#     # … and use that node to control the second switch
#     switched_cap_def.wire(ctrl_inv, sw2.NCP)                   # ctrl_inv → sw2 control

#     switched_cap_def.add_component(sw1)
#     switched_cap_def.add_component(sw2)
#     switched_cap_def.add_component(inverter)
#     switched_cap_def.add_component(c1)

#     # Phase 1 (SW high): Connect IN to cap+, cap- to ground
#     # Phase 2 (SW low): Connect cap+ to OUT, cap- to ground
    
#     # Top plate connections
#     switched_cap_def.wire(sw1.N1, pin_in)      # Input switch: IN -> cap+
#     switched_cap_def.wire(sw1.N2, c1.pos)     # when SW is high
#     switched_cap_def.wire(sw2.N1, c1.pos)     # Output switch: cap+ -> OUT  
#     switched_cap_def.wire(sw2.N2, pin_out)    # when SW is low (inverted)
    
#     # Bottom plate connections (always to ground for simplicity)
#     switched_cap_def.wire(c1.neg, switched_cap_def.gnd)

#     # Control signals
#     switched_cap_def.wire(sw1.NCP, pin_switch)           # sw1 controlled by SW
#     switched_cap_def.wire(pin_switch, inverter.IN)       # Invert SW
#     switched_cap_def.wire(inverter.OUT, sw2.NCP)         # sw2 controlled by inverted SW
    
#     # Control ground references
#     switched_cap_def.wire(sw1.NCM, switched_cap_def.gnd)
#     switched_cap_def.wire(sw2.NCM, switched_cap_def.gnd)

#     return switched_cap_def

def create_switched_cap_subcircuit(C=1e-6, vt=0.5, vh=50e-3):
    sc = SubCircuitDef("switched_cap")

    pin_in  = Terminal()
    pin_out = Terminal()
    pin_clk = Terminal()

    sc.add_pin("IN",  pin_in)
    sc.add_pin("OUT", pin_out)
    sc.add_pin("SW",  pin_clk)

    # control nodes
    ctrl_p = Terminal()           # inverter output (= φ2 control)

    inv  = SubCircuitInst(create_inverter_subcircuit())
    sw1  = SubCircuitInst(create_voltage_controlled_switch_with_hysteresis_subcircuit(
                            on_voltage=vt, hysteresis_voltage=vh))
    sw2  = SubCircuitInst(create_voltage_controlled_switch_with_hysteresis_subcircuit(
                            on_voltage=vt, hysteresis_voltage=vh))   # same switch model
    cap  = Capacitor(C)

    sc.add_component(inv)
    sc.add_component(sw1)
    sc.add_component(sw2)
    sc.add_component(cap)

    # inverter wiring
    sc.wire(pin_clk, inv.IN)
    sc.wire(inv.OUT, ctrl_p)

    # phase-1 switch (IN ↔ Nf) – on when SW high
    sc.wire(pin_in, sw1.N1)
    sc.wire(sw1.N2, cap.pos)
    sc.wire(sw1.NCP, pin_clk)
    sc.wire(sw1.NCM, sc.gnd)

    # phase-2 switch (Nf ↔ OUT) – on when SW low (ctrl_p high)
    sc.wire(cap.pos,  sw2.N1)
    sc.wire(sw2.N2,   pin_out)
    sc.wire(sw2.NCP,  ctrl_p)
    sc.wire(sw2.NCM,  sc.gnd)

    sc.wire(cap.neg, sc.gnd)
    return sc


def resample_signal(time, signal, num_points=1000):
    """Resample a signal onto a coarser time grid using linear interpolation."""
    import numpy as np
    
    t_min = min(time)
    t_max = max(time)
    common_time = np.linspace(t_min, t_max, num_points)
    resampled_signal = np.interp(common_time, time, signal)
    
    return common_time, resampled_signal

def calculate_moving_average(time, signal, time_window):
    """Calculate moving average of a signal over a specified time window."""
    import numpy as np
    
    avg_signal = np.zeros_like(signal)
    
    for i, t in enumerate(time):
        # Find indices within the time window (trailing window)
        mask = (time >= (t - time_window)) & (time <= t)
        if np.any(mask):
            avg_signal[i] = np.mean(signal[mask])
        else:
            avg_signal[i] = signal[i]  # fallback to original value
    
    return avg_signal

# def test_switched_cap():
#     switched_cap_def = create_switched_cap_subcircuit(C=1e-6)
#     switched_cap = SubCircuitInst(switched_cap_def)

#     circuit = Circuit("switched_cap_test")
#     circuit.add_component(switched_cap)

#     # Clock signal for switching
#     v_switch = PulsedVoltageSource(
#         v1=0.0,
#         v2=1.0,
#         td=0.0,
#         tr=1e-9,
#         tf=1e-9,
#         pw=1e-3,
#         per=2e-3,
#     )
#     circuit.add_component(v_switch)
#     circuit.wire(v_switch.neg, circuit.gnd)
#     circuit.wire(v_switch.pos, switched_cap.SW)

#     # Use voltage source to measure equivalent resistance
#     v_test = VoltageSource(1.0)  # 1V test voltage
    
#     circuit.add_component(v_test)
    
#     # Apply voltage across switched capacitor: v_test+ -> IN, v_test- -> OUT
#     circuit.wire(v_test.pos, switched_cap.IN)
#     circuit.wire(v_test.neg, switched_cap.OUT)

#     print(circuit.compile_to_spice())

#     results = circuit.simulate_transient(end_time=1, step_time=1e-5)

#     time = results.get_time_vector()
#     v_test_applied = 1.0  # Applied test voltage (constant)
    
#     # Debug: Check control signals and internal nodes
#     v_switch_control = results.get_node_voltage(switched_cap.SW)  # Switch control voltage
#     print(f'Switch control voltage range: min={min(v_switch_control):.3f}V, max={max(v_switch_control):.3f}V')
    
#     # Try to access internal capacitor node (this might not work if it's internal)
#     try:
#         # For debugging, let's check a few time points manually
#         t_quarter = len(time) // 4
#         t_half = len(time) // 2 
#         t_three_quarter = 3 * len(time) // 4
#         print(f'Control at 1/4: {v_switch_control[t_quarter]:.3f}V, 1/2: {v_switch_control[t_half]:.3f}V, 3/4: {v_switch_control[t_three_quarter]:.3f}V')
#         print(f'Current at 1/4: {i_test[t_quarter]:.3e}A, 1/2: {i_test[t_half]:.3e}A, 3/4: {i_test[t_three_quarter]:.3e}A')
#     except:
#         print("Could not access detailed switching info")
    
#     i_test_raw = results.get_component_current(v_test)  # Current through voltage source
    
#     # Handle the current data extraction properly
#     if isinstance(i_test_raw, (list, tuple)) and len(i_test_raw) > 0:
#         i_test = i_test_raw
#     elif hasattr(i_test_raw, '__len__') and len(i_test_raw) == len(time):
#         i_test = i_test_raw
#     else:
#         # If it's a scalar, replicate for all time points
#         i_test = [float(i_test_raw)] * len(time)
    
#     print(f'Original data points: {len(time)}')
#     print(f'Current data type: {type(i_test)}, length: {len(i_test) if hasattr(i_test, "__len__") else "scalar"}')
#     print(f'Current range: min={min(i_test):.3e}, max={max(i_test):.3e}, mean={np.mean(i_test):.3e}')

#     # Resample to reduce number of points for faster computation
#     time_resampled, i_test_resampled = resample_signal(time, i_test, num_points=2000)
#     _, v_switch_resampled = resample_signal(time, v_switch_control, num_points=2000)
#     print(f'Resampled data points: {len(time_resampled)}')

#     # Calculate moving averages over 20ms time window (10 switching periods)
#     time_window = 20e-3  # 20ms time window
#     i_avg = calculate_moving_average(time_resampled, i_test_resampled, time_window)
    
#     # Calculate equivalent resistance: R = V / I
#     # Avoid division by zero by adding small epsilon
#     epsilon = 1e-12
#     # Take absolute value to handle sign convention issues
#     i_test_abs = np.abs(i_test_resampled)
#     r_eq = v_test_applied / (i_test_abs + epsilon)  # V / |I| = R_switched_cap
#     r_eq_avg = calculate_moving_average(time_resampled, r_eq, time_window)  # Average of instantaneous resistances
    
#     # Calculate theoretical resistance: R_eq = 1/(f_s * C)
#     switching_period = 2e-3  # 2ms period from PulsedVoltageSource
#     switching_frequency = 1 / switching_period  # 500 Hz
#     capacitance = 1e-6  # 1µF
#     r_theoretical = 1 / (switching_frequency * capacitance)
    
#     print(f'Theoretical equivalent resistance: {r_theoretical/1e3:.2f} kΩ')
#     print(f'Simulated equivalent resistance at t=end: {r_eq[-1]/1e3:.2f} kΩ')
#     print(f'Simulated average equivalent resistance: {r_eq_avg[-1]/1e3:.2f} kΩ')
#     print(f'Error vs theoretical: {abs(r_eq_avg[-1] - r_theoretical)/r_theoretical*100:.1f}%')

#     plt.figure(figsize=(12, 8))
    
#     # Switch control voltage and applied test voltage
#     plt.subplot(311)
#     plt.plot(time_resampled, v_switch_resampled, 'b-', linewidth=2, label='Switch Control')
#     plt.axhline(y=v_test_applied, color='r', linewidth=2, label=f'Applied Test Voltage ({v_test_applied}V)')
#     plt.axhline(y=0.5, color='orange', linestyle='--', alpha=0.7, label='Switch Threshold (0.5V)')
#     plt.ylabel('Voltage (V)')
#     plt.legend()
#     plt.grid(True, alpha=0.3)
    
#     # Current plot
#     plt.subplot(312)
#     plt.plot(time_resampled, i_test_resampled*1e6, 'b-', alpha=0.3, label='Raw Current')
#     plt.plot(time_resampled, i_test_abs*1e6, 'g-', alpha=0.5, label='|Current| (instantaneous)')
#     plt.plot(time_resampled, np.abs(i_avg)*1e6, 'k-', linewidth=2, label='|Current| (average)')
#     plt.ylabel('Current (µA)')
#     plt.legend()
#     plt.grid(True, alpha=0.3)
    
#     # Resistance plot
#     plt.subplot(313)
#     plt.plot(time_resampled, r_eq/1e3, 'g-', alpha=0.5, label='Instantaneous Resistance')
#     plt.plot(time_resampled, r_eq_avg/1e3, 'k-', linewidth=2, label='Average Resistance')
#     plt.axhline(y=r_theoretical/1e3, color='r', linestyle='--', linewidth=2, label=f'Theoretical ({r_theoretical/1e3:.1f} kΩ)')
#     plt.ylabel('Resistance (kΩ)')
#     plt.xlabel('Time (s)')
#     plt.legend()
#     plt.grid(True, alpha=0.3)
    
#     plt.tight_layout()
#     plt.show()

def test_switched_cap():
    """
    Drive the switched-capacitor with a fixed 1 V source referenced to ground
    and tie OUT to ground (high-Z or direct).  The average current drawn from
    the source should be  Iavg = C·f·ΔV  so that  Req = ΔV / Iavg = 1/(C·f).
    """
    # ===== build DUT ========================================================
    switched_cap_def = create_switched_cap_subcircuit(C=1e-6)  # 1 µF
    switched_cap = SubCircuitInst(switched_cap_def)

    circuit = Circuit("switched_cap_test")
    circuit.add_component(switched_cap)

    # ----- clock  φ1/φ2  ----------------------------------------------------
    v_clk = PulsedVoltageSource(
        v1=0.0, v2=1.0,
        td=0, tr=1e-9, tf=1e-9,
        pw=1e-3,  # 1 ms high
        per=2e-3  # 2 ms period → 500 Hz
    )
    circuit.add_component(v_clk)
    circuit.wire(v_clk.neg, circuit.gnd)
    circuit.wire(v_clk.pos, switched_cap.SW)

    # ===== stimulus  (1 V source wrt ground) ================================
    v_in = VoltageSource(1.0)              # +1 V DC
    circuit.add_component(v_in)
    circuit.wire(v_in.pos, switched_cap.IN)
    circuit.wire(v_in.neg, circuit.gnd)    # reference

    # ----- load on OUT ------------------------------------------------------
    # simplest: OUT tied to ground so the cap always dumps charge into gnd
    circuit.wire(switched_cap.OUT, circuit.gnd)
    # If you prefer to watch OUT rise, replace the line above with:
    # r_load = Resistor(1e9)                  # ~open-circuit load
    # circuit.add_component(r_load)
    # circuit.wire(switched_cap.OUT, r_load.pos)
    # circuit.wire(r_load.neg, circuit.gnd)

    print(circuit.compile_to_spice())

    # ===== run transient with finer resolution ================================
    t_stop = 0.2            # 0.2 s  → 100 periods of 2 ms
    dt     = 2e-6           # 2 µs   (≪ τ = 1 µs)
    res = circuit.simulate_transient(end_time=t_stop, step_time=dt)

    t      = res.get_time_vector()
    i_src  = res.get_component_current(v_in)        # A

    # average *integrated* current  (robust even with variable dt)
    import numpy as np
    q_total = np.trapz(i_src, t)                     # ∫ I dt   [Coulomb]
    i_avg   = q_total / (t[-1] - t[0])              # A

    Req_sim = 1.0 / abs(i_avg)                      # Ω

    C  = 1e-6
    fs = 500.0
    Req_theory = 1.0 / (C * fs)                     # 2 kΩ

    print(f"Theoretical  R_eq = {Req_theory/1e3:6.2f} kΩ")
    print(f"Simulated    R_eq = {Req_sim   /1e3:6.2f} kΩ "
        f"({(Req_sim-Req_theory)/Req_theory*100:+.2f} %)")

    # quick plot --------------------------------------------------------------
    import matplotlib.pyplot as plt
    plt.figure(figsize=(7,4))
    plt.plot(t, i_src*1e3)
    plt.xlabel("time  (s)")
    plt.ylabel("source current  (mA)")
    plt.title("Charge-transfer spikes through switched capacitor")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # test_inverter()
    test_switched_cap()

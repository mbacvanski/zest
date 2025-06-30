import numpy as np
import matplotlib.pyplot as plt

from zest.circuit import Circuit, SubCircuitDef
from zest.components import Resistor, VoltageSource, Terminal, SubCircuit, PiecewiseLinearVoltageSource


def create_saturating_opamp_subcircuit(vdd_val=5.0, vss_val=-5.0, gain=1e5):
    """
    Creates a subcircuit definition for an op-amp with output saturation.
    This model has implicit power supplies.
    It has 3 pins: IN+, IN-, OUT.
    """
    opamp_def = SubCircuitDef("saturating_opamp")

    # Define the pins
    pin_inp = Terminal()
    pin_inn = Terminal()
    pin_out = Terminal()

    opamp_def.add_pin("INP", pin_inp)
    opamp_def.add_pin("INN", pin_inn)
    opamp_def.add_pin("OUT", pin_out)

    # Behavioral model for the op-amp using a VCVS with saturation
    # The output is limited to the specified VDD/VSS values.
    vcvs_model = (
        f"E_OPAMP OUT 0 "
        f"VALUE={{LIMIT({gain}*(V(INP) - V(INN)), {vss_val}, {vdd_val})}}"
    )
    opamp_def.include_model(vcvs_model)

    return opamp_def


def demonstrate_schmitt_trigger():
    """
    Builds and simulates an inverting Schmitt trigger using an op-amp
    and plots its hysteresis curve.
    """
    circuit = Circuit("OpAmpSchmittTrigger")

    # Op-amp parameters
    vdd_val = 5.0
    vss_val = -5.0

    # Create the saturating op-amp definition
    opamp_def = create_saturating_opamp_subcircuit(vdd_val=vdd_val, vss_val=vss_val)

    # Components
    opamp = SubCircuit(opamp_def, "U1")
    r1 = Resistor(10e3, "R1")  # Feedback resistor
    r2 = Resistor(10e3, "R2")  # Resistor to ground
    
    # Use a PWL source for a triangular wave input
    time_points = [0, 1e-3, 3e-3, 4e-3]
    voltage_points = [-6, 6, -6, -6]
    time_voltage_pairs = list(zip(time_points, voltage_points))
    vin = PiecewiseLinearVoltageSource(time_voltage_pairs, "Vin")

    # Connect the Schmitt trigger components (inverting configuration)
    # Input signal to the inverting input
    circuit.wire(opamp.INN, vin.pos)
    circuit.wire(vin.neg, circuit.gnd)

    # Positive feedback to the non-inverting input
    circuit.wire(opamp.OUT, r1.n1)
    circuit.wire(r1.n2, opamp.INP)
    circuit.wire(opamp.INP, r2.n1)
    circuit.wire(r2.n2, circuit.gnd)

    # --- Simulation ---
    print("Running transient simulation...")
    tran_results = circuit.simulate_transient(step_time=1e-5, end_time=4e-3)
    
    # --- Plotting ---
    fig, ax = plt.subplots(figsize=(10, 6))

    # For transient analysis, the time vector is retrieved with its own method
    time_t = tran_results.get_time_vector()
    if time_t is None:
        raise ValueError("Time vector not found in simulation results.")
        
    vin_t = tran_results.get_node_voltage(vin.pos)
    vout_t = tran_results.get_node_voltage(opamp.OUT)

    # Split data for plotting rising and falling sweeps
    # The input triangular wave peaks at 1ms and completes its fall at 3ms.
    peak_time = 1e-3
    fall_end_time = 3e-3
    
    rising_indices = np.where(time_t <= peak_time)[0]
    falling_indices = np.where((time_t > peak_time) & (time_t <= fall_end_time))[0]

    # Plot rising and falling sweeps separately
    ax.plot(vin_t[rising_indices], vout_t[rising_indices], "b-", label="Vin Sweeping Up")
    ax.plot(vin_t[falling_indices], vout_t[falling_indices], "r-", label="Vin Sweeping Down")

    # Add arrows to show the direction of the transfer function
    # Arrow for the rising part (Vin increasing)
    idx1_rise = int(len(rising_indices) * 0.45)
    idx2_rise = int(len(rising_indices) * 0.55)
    ax.annotate("",
                xy=(vin_t[rising_indices[idx2_rise]], vout_t[rising_indices[idx2_rise]]), 
                xytext=(vin_t[rising_indices[idx1_rise]], vout_t[rising_indices[idx1_rise]]),
                arrowprops=dict(arrowstyle="->", color="b", lw=2.5))

    # Arrow for the falling part (Vin decreasing)
    idx1_fall = int(len(falling_indices) * 0.45)
    idx2_fall = int(len(falling_indices) * 0.55)
    ax.annotate("",
                xy=(vin_t[falling_indices[idx2_fall]], vout_t[falling_indices[idx2_fall]]), 
                xytext=(vin_t[falling_indices[idx1_fall]], vout_t[falling_indices[idx1_fall]]),
                arrowprops=dict(arrowstyle="->", color="r", lw=2.5))

    ax.set_title("Op-Amp Schmitt Trigger Hysteresis (Transient Analysis)")
    ax.set_xlabel("Input Voltage (V)")
    ax.set_ylabel("Output Voltage (V)")
    ax.grid(True)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.axvline(0, color="black", linewidth=0.5)

    # Theoretical thresholds
    v_sat_pos = vdd_val
    v_sat_neg = vss_val
    beta = r2.resistance / (r1.resistance + r2.resistance)
    vth_high = v_sat_pos * beta
    vth_low = v_sat_neg * beta
    print(f"Theoretical Vth+ = {vth_high:.2f}V")
    print(f"Theoretical Vth- = {vth_low:.2f}V")

    ax.axvline(vth_high, color='green', linestyle=':', label=f'Vth+ (Theory) = {vth_high:.2f}V')
    ax.axvline(vth_low, color='orange', linestyle=':', label=f'Vth- (Theory) = {vth_low:.2f}V')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig("schmitt_trigger_opamp_hysteresis.png")
    print("\nPlot saved to schmitt_trigger_opamp_hysteresis.png")


if __name__ == "__main__":
    demonstrate_schmitt_trigger()

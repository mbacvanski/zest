import numpy as np
import matplotlib.pyplot as plt

from zest.circuit import Circuit, SubCircuitDef
from zest.components import Resistor, VoltageSource, Terminal, SubCircuit


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
    vdd_val = 2.0
    vss_val = 0

    # Create the saturating op-amp definition
    opamp_def = create_saturating_opamp_subcircuit(vdd_val=vdd_val, vss_val=vss_val)

    # Components
    opamp = SubCircuit(opamp_def, "U1")
    r1 = Resistor(10e3, "R1")  # Feedback resistor
    r2 = Resistor(10e3, "R2")  # Resistor to ground
    vin = VoltageSource(0, "Vin")

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
    # Perform a bidirectional DC sweep to show hysteresis
    print("Running DC sweeps...")
    sweep_start = vss_val - 1
    sweep_stop = vdd_val + 1
    rising_sweep = circuit.simulate_dc_sweep(
        source_component=vin, start=sweep_start, stop=sweep_stop, step=0.01
    )
    falling_sweep = circuit.simulate_dc_sweep(
        source_component=vin, start=sweep_stop, stop=sweep_start, step=-0.01
    )
    
    # --- Plotting ---
    fig, ax = plt.subplots(figsize=(10, 6))

    # Extract DC sweep results
    vin_rising = rising_sweep.get_sweep_variable()
    vout_rising = rising_sweep.get_node_voltage(opamp.OUT)
    vin_falling = falling_sweep.get_sweep_variable()
    vout_falling = falling_sweep.get_node_voltage(opamp.OUT)

    # Plot rising and falling sweeps separately
    ax.plot(vin_rising, vout_rising, "b-", label="Vin Sweeping Up")
    ax.plot(vin_falling, vout_falling, "r-", label="Vin Sweeping Down")

    # Add arrows to show the direction of the transfer function
    # Arrow for the rising part (Vin increasing)
    idx1_rise = int(len(vin_rising) * 0.48)
    idx2_rise = int(len(vin_rising) * 0.52)
    ax.annotate("",
                xy=(vin_rising[idx2_rise], vout_rising[idx2_rise]), 
                xytext=(vin_rising[idx1_rise], vout_rising[idx1_rise]),
                arrowprops=dict(arrowstyle="->", color="b", lw=2.5))

    # Arrow for the falling part (Vin decreasing)
    idx1_fall = int(len(vin_falling) * 0.48)
    idx2_fall = int(len(vin_falling) * 0.52)
    ax.annotate("",
                xy=(vin_falling[idx2_fall], vout_falling[idx2_fall]), 
                xytext=(vin_falling[idx1_fall], vout_falling[idx1_fall]),
                arrowprops=dict(arrowstyle="->", color="r", lw=2.5))

    ax.set_title("Op-Amp Schmitt Trigger Hysteresis (DC Sweep)")
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

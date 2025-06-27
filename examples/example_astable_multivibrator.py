#!/usr/bin/env python3
"""
Zest Demo: Astable Multivibrator using Subcircuits & .INCLUDE
This example demonstrates building a classic oscillator from reusable blocks
and managing model file dependencies automatically.
"""
import sys
import os
import numpy as np

# Try to import matplotlib for plotting (optional)
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("📊 Note: matplotlib not available - plots will be skipped")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zest import Circuit, VoltageSource, Resistor, Capacitor, SubCircuit, Component, Terminal
from zest.simulation import check_simulation_requirements

# --- Definition for the reusable RC Block ---
def create_rc_block_definition() -> Circuit:
    """Defines a simple RC block with three pins: input, output, and gnd."""
    rc_circuit = Circuit("RC_BLOCK")
    r = Resistor(resistance=100e3)
    c = Capacitor(capacitance=10e-9)
    rc_circuit.wire(r.n2, c.pos)
    rc_circuit.add_pin("input", r.n1)
    rc_circuit.add_pin("output", c.pos)
    rc_circuit.add_pin("gnd", c.neg)
    return rc_circuit

# --- Definition for the NPN Transistor, which includes a model file ---
class DummyComponent(Component):
    """A dummy component for external subcircuit pin definitions."""
    def to_spice(self, circuit):
        return "* External component - defined in .INCLUDE file"

def create_npn_definition() -> Circuit:
    """Defines the NPN subcircuit and its .INCLUDE dependency."""
    # This assumes the model file exists at 'tests/models/simple_npn.lib'
    # For a real application, this would be a more standard path.
    model_path = os.path.join(os.path.dirname(__file__), '..', 'tests', 'models', 'simple_npn.lib')

    npn_def = Circuit("SIMPLE_NPN")
    npn_def.add_include(os.path.abspath(model_path))
    
    # Use dummy components for external subcircuit pins
    dummy = DummyComponent()
    npn_def.add_pin("C", Terminal(dummy, "c"))
    npn_def.add_pin("B", Terminal(dummy, "b"))
    npn_def.add_pin("E", Terminal(dummy, "e"))
    
    # Mark as external-only (defined in .INCLUDE file)
    npn_def._is_external_only = True
    
    return npn_def

# --- A friendly wrapper class for the NPN subcircuit instance ---
class SimpleNPN(SubCircuit):
    _def = create_npn_definition()
    def __init__(self, name=None):
        super().__init__(definition=self._def, name=name)
        self.collector, self.base, self.emitter = self.C, self.B, self.E

def main():
    print("🚀 Zest Demo: Astable Multivibrator with Subcircuits 🚀")

    rc_block_def = create_rc_block_definition()

    main_circuit = Circuit("AstableMultivibrator")
    vcc, rl1, rl2 = VoltageSource(voltage=5.0), Resistor(4.7e3), Resistor(4.7e3)
    q1, q2 = SimpleNPN("Q1"), SimpleNPN("Q2")
    rc1, rc2 = SubCircuit(rc_block_def, "X_RC1"), SubCircuit(rc_block_def, "X_RC2")

    # Wire the circuit
    main_circuit.wire(vcc.neg, main_circuit.gnd)
    main_circuit.wire(q1.emitter, main_circuit.gnd)
    main_circuit.wire(q2.emitter, main_circuit.gnd)
    main_circuit.wire(vcc.pos, rl1.n1)
    main_circuit.wire(vcc.pos, rl2.n1)
    main_circuit.wire(rl1.n2, q1.collector)
    main_circuit.wire(rl2.n2, q2.collector)
    main_circuit.wire(rc1.gnd, main_circuit.gnd)
    main_circuit.wire(rc2.gnd, main_circuit.gnd)
    main_circuit.wire(q1.collector, rc2.input)
    main_circuit.wire(rc2.output, q2.base)
    main_circuit.wire(q2.collector, rc1.input)
    main_circuit.wire(rc1.output, q1.base)

    main_circuit.set_initial_condition(q1.collector, 5.0)

    print("\n--- Final Compiled SPICE Netlist ---")
    print(main_circuit.compile_to_spice())

    available, message = check_simulation_requirements()
    if not available:
        print(f"\n⚠️  Simulation not available: {message}")
        return

    print("\n--- Running Transient Simulation ---")
    end_time = 10e-3
    results = main_circuit.simulate_transient(step_time=1e-6, end_time=end_time)
    print("✅ Simulation complete!")

    times = results.pyspice_results.time
    v_out1 = results.get_node_voltage(q1.collector)

    crossings = np.where(np.diff(np.sign(v_out1 - 2.5)))[0]
    measured_freq = (len(crossings) / 2) / end_time
    print(f"\nMeasured Frequency: {measured_freq:.0f} Hz")

    if HAS_MATPLOTLIB:
        plt.figure(figsize=(12, 6))
        plt.plot(times * 1000, v_out1, label="V(Q1 Collector)")
        plt.plot(times * 1000, results.get_node_voltage(q2.collector), label="V(Q2 Collector)", linestyle='--')
        plt.title("Astable Multivibrator Output Waveforms")
        plt.xlabel("Time (ms)"), plt.ylabel("Voltage (V)"), plt.grid(True), plt.legend()
        plt.show()

if __name__ == "__main__":
    main() 
"""
Zest: A Pythonic Object-Oriented Wrapper for PySpice

Zest makes circuit building intuitive with auto-naming, auto-registration,
and terminal-based connections for clean, readable circuit descriptions.
"""

from .circuit import Circuit, CircuitRoot, SubCircuitDef, SubCircuitInst, NetlistBlock, NodeMapper
from .components import Component, Terminal, GroundTerminal, VoltageSource, Resistor, Capacitor, Inductor, SubCircuit, gnd
from .simulation import CircuitSimulator, SimulatedCircuit, check_simulation_requirements, SimulatorBackend, SpicelibBackend

__version__ = "0.1.0"
__all__ = [
    # Core circuit classes
    "Circuit", "CircuitRoot", "SubCircuitDef", "SubCircuitInst", "NetlistBlock", "NodeMapper",
    # Component classes
    "Component", "Terminal", "GroundTerminal", "VoltageSource", "Resistor", "Capacitor", "Inductor", "SubCircuit",
    # Ground reference
    "gnd",
    # Simulation classes
    "CircuitSimulator", "SimulatedCircuit", "check_simulation_requirements", "SimulatorBackend", "SpicelibBackend"
] 
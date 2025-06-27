"""
Zest: A Pythonic Object-Oriented Wrapper for PySpice

Zest makes circuit building intuitive with auto-naming, auto-registration,
and terminal-based connections for clean, readable circuit descriptions.
"""

from .circuit import Circuit
from .components import Component, Terminal, VoltageSource, Resistor, Capacitor, Inductor, SubCircuit
from .nodes import Node, gnd
from .simulation import CircuitSimulator, SimulationResults, SimulatedCircuit, check_simulation_requirements

__version__ = "0.1.0"
__all__ = [
    "Circuit", 
    "Component", "Terminal", "VoltageSource", "Resistor", "Capacitor", "Inductor", "SubCircuit",
    "Node", "gnd",
    "CircuitSimulator", "SimulationResults", "SimulatedCircuit", "check_simulation_requirements"
] 
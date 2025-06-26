# Zest 🔧

**A clean, graph-based circuit building library for Python**

Zest is an object-oriented wrapper around PySpice that makes circuit building intuitive through a pure graph-based approach. Components are nodes, wires are edges, and the API enforces clear separation between component creation and circuit topology.

## Features

- **🎯 Pure Graph API**: Components are created independently, wired together explicitly
- **🔌 Type-Safe Terminals**: Connect components using terminal objects (e.g., `r1.n2`, `vs.pos`)
- **⚡ Auto-Registration**: Components automatically join the current circuit
- **📄 SPICE Export**: Generate clean SPICE netlists from your circuit graphs
- **🔬 Simulation Ready**: Integrate with PySpice for analysis (DC, AC, transient)
- **🛡️ Error Prevention**: No string node names to prevent connectivity bugs

## Installation

```bash
pip install -r requirements.txt
```

Requirements:
- `networkx` - Graph data structures
- `matplotlib` - Circuit visualization  
- `pyspice` - SPICE simulation (optional)

## Quick Start

```python
from zest import Circuit, VoltageSource, Resistor, Capacitor

# Create circuit
circuit = Circuit("Voltage Divider")

# Create components independently (no connections specified)
voltage_source = VoltageSource(voltage=12.0)
r1 = Resistor(resistance=1000)  # 1kΩ
r2 = Resistor(resistance=2000)  # 2kΩ

# Wire the components together
circuit.wire(voltage_source.neg, circuit.gnd)     # VS negative to ground
circuit.wire(voltage_source.pos, r1.n1)          # VS positive to R1 input
circuit.wire(r1.n2, r2.n1)                       # R1 output to R2 input
circuit.wire(r2.n2, circuit.gnd)                 # R2 output to ground

# Generate SPICE netlist
print(circuit.compile_to_spice())
```

## Core Concepts

### Graph-Based Architecture

Zest treats circuits as graphs where:
- **Components** are nodes with terminals
- **Wires** are edges connecting terminals
- **Terminals** are the only allowed connection points

This approach eliminates common circuit building errors and makes topology explicit.

### Component Creation

Components are created independently without specifying connections:

```python
# Components created without any wiring
vs = VoltageSource(voltage=5.0)      # Auto-named V1
r1 = Resistor(resistance=1000)       # Auto-named R1  
c1 = Capacitor(capacitance=1e-6)     # Auto-named C1
l1 = Inductor(inductance=1e-3)       # Auto-named L1
```

### Explicit Wiring

The `circuit.wire()` method connects terminals:

```python
circuit = Circuit("My Circuit")

# Only terminal objects and circuit.gnd are allowed
circuit.wire(vs.pos, r1.n1)          # ✅ Valid: terminal to terminal
circuit.wire(r1.n2, circuit.gnd)     # ✅ Valid: terminal to ground
circuit.wire(vs.neg, "node1")        # ❌ Error: no string nodes
```

### Terminal Reference

Each component exposes terminals with intuitive names:

| Component | Primary Terminals | Aliases |
|-----------|------------------|---------|
| `VoltageSource` | `.pos`, `.neg` | `.positive`, `.negative` |
| `Resistor` | `.n1`, `.n2` | `.a`, `.b` |
| `Capacitor` | `.pos`, `.neg` | `.positive`, `.negative` |
| `Inductor` | `.n1`, `.n2` | `.a`, `.b` |

## Examples

### RC Low-Pass Filter

```python
from zest import Circuit, VoltageSource, Resistor, Capacitor

circuit = Circuit("RC Filter")

# Create components
vs = VoltageSource(voltage=5.0)
r1 = Resistor(resistance=1000)      # 1kΩ series resistor
c1 = Capacitor(capacitance=1e-6)    # 1µF filter capacitor

# Wire the circuit
circuit.wire(vs.neg, circuit.gnd)     # VS negative to ground
circuit.wire(vs.pos, r1.n1)           # VS positive to R1 input
circuit.wire(r1.n2, c1.pos)           # R1 output to C1 positive (filter output)
circuit.wire(c1.neg, circuit.gnd)     # C1 negative to ground

# Calculate corner frequency
import math
corner_freq = 1 / (2 * math.pi * r1.resistance * c1.capacitance)
print(f"Corner frequency: {corner_freq:.1f} Hz")

print(circuit.compile_to_spice())
```

### Multi-Stage Filter

```python
circuit = Circuit("Multi-Stage Filter")

# Create components
vin = VoltageSource(voltage=10.0)
r1 = Resistor(resistance=1000)       # First stage
c1 = Capacitor(capacitance=1e-6)
r2 = Resistor(resistance=2000)       # Second stage  
c2 = Capacitor(capacitance=2e-6)
r_load = Resistor(resistance=10000)   # Load

# Wire the multi-stage filter
circuit.wire(vin.neg, circuit.gnd)              # Input source to ground
circuit.wire(vin.pos, r1.n1)                    # Input to first stage
circuit.wire(r1.n2, c1.pos)                     # First RC junction
circuit.wire(c1.neg, circuit.gnd)               # First cap to ground
circuit.wire(r1.n2, r2.n1)                      # Couple to second stage
circuit.wire(r2.n2, c2.pos)                     # Second RC junction
circuit.wire(c2.neg, circuit.gnd)               # Second cap to ground
circuit.wire(r2.n2, r_load.n1)                  # Connect load
circuit.wire(r_load.n2, circuit.gnd)            # Load to ground

print(f"Circuit has {len(circuit.components)} components and {len(circuit.wires)} wires")
```

## Simulation Integration

Zest integrates seamlessly with PySpice for circuit simulation:

```python
from zest.simulation import check_simulation_requirements

# Check if PySpice is available
if check_simulation_requirements():
    # Run DC operating point analysis
    results = circuit.simulate_operating_point()
    print("Node voltages:", results.node_voltages)
    
    # Run DC sweep
    sweep_results = circuit.simulate_dc_sweep("V1", 0, 10, 0.1)
    
    # Run AC analysis
    ac_results = circuit.simulate_ac(start_freq=1, stop_freq=1e6)
    
    # Run transient analysis  
    tran_results = circuit.simulate_transient(step_time=1e-6, end_time=1e-3)
else:
    print("PySpice not available - only SPICE export supported")
```

## API Benefits

### Type Safety
- Terminal objects prevent typos in node names
- IDE auto-completion for all terminal references
- Clear error messages for invalid connections

### Explicit Topology  
- Circuit structure is obvious from wire() calls
- No hidden connections or implicit assumptions
- Easy to reason about signal flow

### Reusable Components
- Components can be created once, used in multiple circuits
- Clean separation between component parameters and connectivity
- Easy to build component libraries

### Graph Visualization
- Natural fit for graph-based visualization tools
- Components as nodes, wires as edges
- Circuit topology is first-class data

## Project Structure

```
zest/
├── zest/                    # Main package
│   ├── __init__.py         # Package exports
│   ├── circuit.py          # Circuit class with wire() method
│   ├── components.py       # Component classes with terminals
│   ├── nodes.py           # Node and ground objects
│   ├── simulation.py      # PySpice integration
│   └── visualization.py   # Circuit plotting
├── tests/
│   ├── test_graph_api.py  # Graph API tests
│   └── test_simulation.py # Simulation tests
├── example_graph_api.py   # Complete examples
├── demo_complete_workflow.py # Simulation demo
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `python -m pytest tests/`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Related Projects

- [PySpice](https://github.com/PySpice-org/PySpice) - Python wrapper for SPICE simulators
- [SciPy](https://scipy.org/) - Scientific computing library
- [NetworkX](https://networkx.org/) - Graph analysis tools

---

**Zest** - Making circuit building a breeze! 🌪️⚡ 
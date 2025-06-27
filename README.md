# Zest ⚡

**A clean, intuitive Python library for building electronic circuits**

Zest makes circuit design simple by treating circuits as graphs: components are nodes, wires are edges, and connections use type-safe terminals instead of error-prone string node names.

## Key Benefits

- **🎯 No String Nodes**: Connect components using terminal objects like `r1.n2` and `vs.pos` 
- **🔌 Auto-Registration**: Components automatically join the current circuit context
- **📐 Pure Graph API**: Clean separation between component creation and circuit topology
- **⚡ PySpice Ready**: Export SPICE netlists and run simulations seamlessly
- **🛡️ Error Prevention**: Type-safe connections prevent common wiring mistakes

## Quick Start

```bash
pip install -r requirements.txt
```

```python
from zest import Circuit, VoltageSource, Resistor

# Create circuit and components
circuit = Circuit("Voltage Divider")
vs = VoltageSource(voltage=12.0)
r1 = Resistor(resistance=1000)  # 1kΩ
r2 = Resistor(resistance=2000)  # 2kΩ

# Wire using terminal objects (not strings!)
circuit.wire(vs.pos, r1.n1)      # Source positive to R1
circuit.wire(r1.n2, r2.n1)       # R1 to R2
circuit.wire(vs.neg, circuit.gnd) # Source negative to ground
circuit.wire(r2.n2, circuit.gnd) # R2 to ground

# Generate SPICE netlist
print(circuit.compile_to_spice())
```

## Examples

### RC Filter
```python
from zest import Circuit, VoltageSource, Resistor, Capacitor

circuit = Circuit("RC Low-Pass Filter")

vs = VoltageSource(voltage=5.0)
r1 = Resistor(resistance=1000)      # 1kΩ
c1 = Capacitor(capacitance=1e-6)    # 1µF

# Wire the RC filter
circuit.wire(vs.pos, r1.n1)        # Input
circuit.wire(r1.n2, c1.pos)        # RC junction (output)
circuit.wire(vs.neg, circuit.gnd)   
circuit.wire(c1.neg, circuit.gnd)

# Calculate corner frequency: 159 Hz
corner_freq = 1 / (2 * 3.14159 * 1000 * 1e-6)
print(f"Corner frequency: {corner_freq:.0f} Hz")
```

### Simulation
```python
# Run SPICE simulation (requires PySpice)
results = circuit.simulate_operating_point()

# Get results using component instances, not strings
r1_data = results.get_component_results(r1)
print(f"R1 voltage: {r1_data['voltage_across']:.2f}V")
print(f"R1 current: {r1_data['current']:.3f}A")
```

### Subcircuits
```python
# Create reusable RC block
rc_block = Circuit("RC_Block")
r = Resistor(resistance=1000)
c = Capacitor(capacitance=1e-6)
rc_block.wire(r.n2, c.pos)

# Expose pins for external connections
rc_block.add_pin("input", r.n1)
rc_block.add_pin("output", r.n2)  
rc_block.add_pin("gnd", c.neg)

# Use as subcircuit
main_circuit = Circuit("Multi-Stage Filter")
stage1 = SubCircuit(definition=rc_block, name="Stage1")
stage2 = SubCircuit(definition=rc_block, name="Stage2")

# Connect stages
main_circuit.wire(stage1.output, stage2.input)
```

## Why Zest?

**Traditional Approach (Error-Prone):**
```python
# String-based node names - easy to make mistakes
circuit.add_resistor("R1", "node1", "node2", 1000)
circuit.add_capacitor("C1", "node2", "gnd", 1e-6)
circuit.connect("node1", "input")  # Typo in node name!
```

**Zest Approach (Type-Safe):**
```python
# Terminal objects prevent typos and enable auto-completion
r1 = Resistor(resistance=1000)
c1 = Capacitor(capacitance=1e-6)
circuit.wire(r1.n2, c1.pos)  # IDE auto-completion helps!
```

## Terminal Reference

| Component | Terminals |
|-----------|-----------|
| `VoltageSource` | `.pos`, `.neg` |
| `Resistor` | `.n1`, `.n2` |
| `Capacitor` | `.pos`, `.neg` |
| `Inductor` | `.n1`, `.n2` |

## Requirements

- Python 3.7+
- `matplotlib` - Visualization
- `pyspice` - SPICE simulation

## More Examples

See the `examples/` directory for complete working examples including:
- Astable multivibrator with subcircuits
- Cascaded filter analysis
- Transient simulations with plotting

---

*Zest: Making circuit design as intuitive as connecting Lego blocks* 🔧 
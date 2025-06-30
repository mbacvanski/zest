# Zest Documentation

Welcome to the official documentation for Zest, a Python library for intuitive electronic circuit simulation. This guide will walk you through the core concepts, usage patterns, and advanced features of Zest. 

## 1. Introduction and Mental Model

Zest allows you to define electronic circuits in Python in an object-oriented way. The core philosophy is to represent circuits as a collection of interconnected components, much like you would think about a real circuit.

The mental model follows these steps:
1.  **Instantiate Components**: Create Python objects for each component in your circuit (e.g., `Resistor`, `VoltageSource`).
2.  **Create a Circuit**: Create a `Circuit` object to act as a container for your components.
3.  **Add Components and Wires**: Add your component instances to the circuit and define the connections between them using the `wire()` method.
4.  **Simulate**: Call one of the `simulate_*` methods on your circuit object (e.g., `simulate_transient()`, `simulate_dc_sweep()`).
5.  **Analyze**: The simulation returns a `SimulatedCircuit` object, which you can query to get voltages, currents, and other results.

## 2. Core Concepts

Zest's architecture is built around a few key classes.

### `Circuit`
The `Circuit` (aliased from `CircuitRoot`) is the top-level container for your entire electronic design. It holds the components, the wires connecting them, and any simulation settings. You will typically start by creating a `Circuit` instance.

```python
from zest import Circuit
circuit = Circuit("My First Circuit")
```

### `Component`
Everything you add to a circuit is a `Component`. This is a base class for all electronic parts. Zest provides several built-in components:
- `Resistor`
- `Capacitor`
- `Inductor`
- `VoltageSource` (for DC)
- `PiecewiseLinearVoltageSource` (for time-varying signals)
- `CurrentSource`
- `SubCircuitInst` (for using reusable circuit blocks)
- `ExternalSubCircuit` (for components defined in external `.lib` files, like MOSFETs)

Each component has `Terminal` objects that represent its connection points (e.g., `resistor.n1`, `voltage_source.pos`).

### `Terminal` and `gnd`
A `Terminal` is a connection point on a `Component`. You connect components by wiring their terminals together. Zest also provides a global `gnd` object, which is a special `GroundTerminal` that represents the circuit's ground reference (0V).

### `SimulatedCircuit`
When you run a simulation, Zest returns a `SimulatedCircuit` object. This object holds all the results of the analysis. You can use it to:
- Get the voltage at any node/terminal.
- Get the current through any component.
- Get the time vector for a transient analysis or the sweep variable for a DC sweep.
- Get a dictionary of results for a specific component. 

## 3. Building Circuits

Let's build a simple voltage divider to see how circuit construction works.

### Step 1: Import necessary classes
You need `Circuit`, `gnd`, and the components you want to use.
```python
from zest import Circuit, gnd
from zest.components import VoltageSource, Resistor
```

### Step 2: Create a Circuit and Components
Instantiate the `Circuit` and all the components you need. It's good practice to give components descriptive names, which will help in debugging and analyzing results.
```python
# Create the main circuit container
circuit = Circuit("Voltage Divider")

# Create the components
v_in = VoltageSource(voltage=5.0, name="Vin")
r1 = Resistor(resistance=1000.0, name="R1")
r2 = Resistor(resistance=2000.0, name="R2")
```

### Step 3: Add Components and Wire Them
Zest automatically adds components to the circuit when you wire one of their terminals. The `circuit.wire()` method connects two terminals.

```python
# The output node is between the two resistors
output_terminal = r1.n2

# Wire the components together
circuit.wire(v_in.pos, r1.n1)
circuit.wire(r1.n2, r2.n1)
circuit.wire(v_in.neg, gnd)
circuit.wire(r2.n2, gnd)
```
**Note**: The order of `wire` calls doesn't matter. Zest builds a graph of connections. Any terminals wired together are considered part of the same electrical node.

### Setting Initial Conditions
For transient analysis, you might need to specify the starting voltage of a node (e.g., a charged capacitor). You can do this with `set_initial_condition()`. This will add a `.IC` directive to the SPICE netlist.

```python
# Set the initial voltage of the capacitor's positive terminal to 1.5V
# circuit.set_initial_condition(c1.pos, 1.5)
```

### Inspecting Components
Some components have helpful methods for verification. For example, you can check the output of a `PiecewiseLinearVoltageSource` at any given time to ensure your waveform is defined correctly.

```python
# From the RC example, where v_in is a PWL source
# that steps to 5V at 1ns.
# print(v_in.get_voltage_at_time(0))     # Output: 0.0
# print(v_in.get_voltage_at_time(2e-9))  # Output: 5.0
```

## 4. Running a Simulation

Once your circuit is defined, you can run various types of SPICE analyses. All simulation methods are called directly on the `Circuit` object.

### DC Operating Point (`.op`)
This analysis calculates the DC behavior of the circuit (all capacitors are treated as open circuits, all inductors as short circuits). It's useful for finding the bias points of a circuit.

```python
results = circuit.simulate_operating_point()
```

### DC Sweep
This analysis varies a DC voltage or current source and calculates the circuit's response. You must specify which source to sweep and the start, stop, and step values.

```python
# Assuming v_in is the VoltageSource component instance from our example
results = circuit.simulate_dc_sweep(
    source_component=v_in,
    start=0,
    stop=10,
    step=0.1,
)
```

### Transient Analysis (`.tran`)
This analysis calculates the circuit's behavior over time. It's used for time-domain signals, like observing a capacitor charging or the output of an oscillator. You must provide the simulation step time and end time.

```python
# Simulate from 0 to 5ms with a 1us time step
results = circuit.simulate_transient(
    step_time=1e-6, # 1us
    end_time=5e-3,  # 5ms
)
```
You can also set initial conditions for transient analysis using `circuit.set_initial_condition(terminal, voltage)`.

### AC Analysis (`.ac`)
This analysis calculates the small-signal frequency response of the circuit. It's used for finding the transfer function of filters, amplifiers, etc. You must specify the frequency range and the number of points per decade.

```python
# AC analysis from 1Hz to 1MHz
results = circuit.simulate_ac(
    start_freq=1,
    stop_freq=1e6,
    points_per_decade=10,
)
```

**Simulation Parameters**: All `simulate_*` methods also accept a `cleanup` parameter:
- `cleanup="silent"` (default): Deletes temporary simulation files.
- `cleanup="verbose"`: Deletes temporary files and prints what is being deleted.
- `cleanup="keep"`: Keeps the temporary `.net`, `.raw`, and `.log` files in the `temp_spice_sim/` directory for debugging.
- `temperature`: You can specify the simulation temperature in Celsius (e.g., `temperature=27`). Defaults to 25°C.

## 5. Analyzing Results

All `simulate_*` methods return a `SimulatedCircuit` object. This object is your gateway to the simulation data.

Let's continue with our voltage divider example. After running the operating point simulation:
```python
# From our example in "Building Circuits"
results = circuit.simulate_operating_point()

# The output node was defined as the connection between R1 and R2
output_terminal = r1.n2
```

### Getting Node Voltages
You can get the voltage at any terminal in the circuit using `results.get_node_voltage()`.

```python
# Get the voltage at the output terminal
output_voltage = results.get_node_voltage(output_terminal)
print(f"Output Voltage: {output_voltage:.2f} V")

# Expected output: Output Voltage: 3.33 V
```
For transient or DC sweep analyses, this method will return a NumPy array of voltages corresponding to the time vector or sweep variable.

### Getting Component Currents
You can get the current flowing through a component using `results.get_component_current()`.

```python
# Get the current through the input voltage source
input_current = results.get_component_current(v_in)
print(f"Input Current: {input_current * 1000:.2f} mA")

# Expected output: Input Current: -1.67 mA
# Note: The current for a voltage source is typically negative,
# as it flows out of the positive terminal.
```

### Getting All Results for a Component
For a more detailed view, you can get all calculated results for a specific component using `results.get_component_results()`. This returns a dictionary containing terminal voltages, currents, power, and other component-specific data.

```python
r2_results = results.get_component_results(r2)
print(r2_results)

# Example output for an operating point simulation:
# {
#     'component': Resistor(R2),
#     'component_name': 'R2',
#     'analysis_type': 'DC Operating Point',
#     'terminal_voltages': {'n1': 3.3333, 'n2': 0.0},
#     'voltage_across': 3.3333,
#     'current': 0.001666,
#     'power': 0.005555
# }
```

### Getting the Time or Sweep Vector
For time-varying or sweep simulations, you need the independent variable's data.
- **Transient**: `results.get_time_vector()` returns the time points as a NumPy array.
- **DC Sweep**: `results.get_sweep_variable()` returns the swept voltage/current values.
- **AC Analysis**: The frequency is part of the raw data accessible via `results.raw_data`.

```python
# Example for a transient simulation
# transient_results = circuit.simulate_transient(...)
# time_points = transient_results.get_time_vector()
# output_waveform = transient_results.get_node_voltage(output_terminal)
#
# import matplotlib.pyplot as plt
# plt.plot(time_points, output_waveform)
# plt.show()
```

### Additional Analysis Helpers
The `SimulatedCircuit` object has several other helpers for scripting and analysis:

- **`get_terminal_current(terminal)`**: A convenience method to get the current flowing into a specific component terminal.
- **`list_components()`**: Returns a list of `(component_instance, compiled_name)` tuples for all components in the circuit, which is useful for inspection.
- **`is_transient()`, `is_dc_sweep()`, `is_ac_analysis()`, `is_operating_point()`**: These boolean methods are helpful for writing generic analysis scripts that need to know the analysis type.
- **`raw_data`**: For advanced users, this attribute provides direct access to the `spicelib.RawRead` object, which contains all traces from the simulation. You can use it to get any trace by its SPICE name (e.g., `results.raw_data.get_trace('v(n1)')`).

## 6. Advanced Topics

### Subcircuits: Creating Reusable Blocks

For complex designs, you'll want to create reusable modules. Zest handles this with a `.SUBCKT`-like system using `SubCircuitDef` and `SubCircuitInst`.

1.  **`SubCircuitDef`**: This is the *definition* of your subcircuit. You create it just like a `Circuit`, adding components and wires. You must also define its external connection points using `add_pin()`.
2.  **`SubCircuitInst`**: This is an *instance* of your subcircuit that you can place in a larger circuit, just like any other component.

**Example: An Op-Amp Voltage Follower**

Let's say you have a simple op-amp model defined as a subcircuit.

```python
from zest.circuit import SubCircuitDef
from zest.components import Resistor, VoltageSource

def create_opamp_model():
    # 1. Define the subcircuit
    opamp_def = SubCircuitDef("SimpleOpAmp")

    # Internal components of the op-amp
    rin = Resistor(1e6, name="Rin")
    # ... more internal components for a real model

    # 2. Define the external pins
    opamp_def.add_pin("plus", rin.n1)
    opamp_def.add_pin("minus", rin.n2)
    # ... other pins like 'out', 'vcc', 'vee'

    # You can include a simple behavioral model
    model_text = "E_opamp out 0 VALUE={1e6 * (V(plus) - V(minus))}"
    opamp_def.include_model(model_text)

    return opamp_def

# 3. Use the subcircuit in your main circuit
opamp_definition = create_opamp_model()
opamp_inst = opamp_definition.create_instance(name="U1")

# Now opamp_inst behaves like a component with terminals:
# opamp_inst.plus, opamp_inst.minus, opamp_inst.out
# circuit.wire(opamp_inst.out, opamp_inst.minus) # Voltage follower
```

### Using External Models and Libraries

Real-world simulations often require manufacturer-provided models (e.g., for MOSFETs, BJTs). Zest supports this through `.INCLUDE` directives and the `ExternalSubCircuit` component.

**Step 1: Include the Library File**
Use `circuit.add_include()` to link to an external `.lib` or `.mod` file. The path should be relative to where the simulation is run.

```python
# This tells NGspice to include the models from this file
circuit.add_include("examples/models/mosfets.lib")
```

**Step 2: Instantiate the Model with `ExternalSubCircuit`**
The `ExternalSubCircuit` component lets you create an instance of a model from an included library. You need to know the model's name (the `.SUBCKT` name) and its pin names.

```python
from zest.components import ExternalSubCircuit

# Create an instance of the 'nmos_model' defined in mosfets.lib
# The pin names must match the order in the .SUBCKT definition
nmos = ExternalSubCircuit(
    subckt_name="nmos_model",
    pin_names=['D', 'G', 'S', 'B'],
    name="M1",
    W=2e-6, L=0.18e-6 # You can pass parameters
)

# Now you can wire it into your circuit
# circuit.wire(nmos.D, v_supply.pos)
# circuit.wire(nmos.S, gnd)
```

## 7. Complete Example: RC Circuit Transient Analysis

Let's put everything together to simulate the charging of a capacitor in a simple RC circuit. We will use a piecewise linear voltage source to create a step input.

```python
import numpy as np
import matplotlib.pyplot as plt
from zest import Circuit, gnd
from zest.components import Resistor, Capacitor, PiecewiseLinearVoltageSource

# 1. Create the circuit and components
circuit = Circuit("RC Circuit")

# Step voltage: 0V for t<0, 5V for t>1ns
v_in = PiecewiseLinearVoltageSource(
    time_voltage_pairs=[(0, 0), (1e-9, 5.0)],
    name="Vin"
)
r1 = Resistor(resistance=1000.0, name="R1") # 1k ohm
c1 = Capacitor(capacitance=1e-6, name="C1") # 1uF

# 2. Wire the components
circuit.wire(v_in.pos, r1.n1)
circuit.wire(r1.n2, c1.pos)
circuit.wire(v_in.neg, gnd)
circuit.wire(c1.neg, gnd)

# Define the output node for probing
output_node = c1.pos

# 3. Run a transient simulation
# Simulate for 5 time constants (5 * R * C = 5 * 1k * 1uF = 5ms)
results = circuit.simulate_transient(
    step_time=1e-5, # 10us
    end_time=5e-3,  # 5ms
)

# 4. Analyze and plot the results
time = results.get_time_vector()
input_voltage = results.get_node_voltage(v_in.pos)
output_voltage = results.get_node_voltage(output_node)

# Theoretical curve
tau = r1.resistance * c1.capacitance
theoretical_v = 5 * (1 - np.exp(-time / tau))

plt.figure(figsize=(10, 6))
plt.plot(time * 1000, input_voltage, label="Input Voltage (Vin)")
plt.plot(time * 1000, output_voltage, label="Capacitor Voltage (Vout)", linestyle='--')
plt.plot(time * 1000, theoretical_v, label="Theoretical Vout", linestyle=':')
plt.title("RC Circuit Transient Response")
plt.xlabel("Time (ms)")
plt.ylabel("Voltage (V)")
plt.grid(True)
plt.legend()
plt.show()

```
This example demonstrates the entire workflow: defining components, building the circuit, running a simulation, and processing the results to verify the circuit's behavior against theory.

Happy simulating!
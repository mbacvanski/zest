# Zest Examples

This directory contains complete working examples demonstrating various features of the Zest circuit library.

## Getting Started

All examples can be run directly from this directory:

```bash
cd examples
python example_final_demo.py
```

## Example Categories

### 🚀 Basic Examples
Perfect for learning Zest fundamentals:

- **`example_final_demo.py`** - Complete demonstration of wire behavior and PySpice integration
- **`example_graph_api.py`** - Pure graph-based circuit building with detailed explanations  
- **`example_simulation.py`** - Circuit simulation and result analysis
- **`example_pure_graph_api.py`** - Minimal example showing clean graph API

### 🔬 Advanced Examples
For users ready to explore more complex features:

- **`example_astable_multivibrator_comprehensive.py`** - Complete oscillator circuit with:
  - Subcircuit definitions and instantiation
  - Transient simulation and waveform analysis
  - Frequency measurement and plotting
  - Model file includes
  
- **`example_cascaded_filter.py`** - Multi-stage filter design showing:
  - Cascaded circuit topologies
  - Frequency response analysis
  
- **`example_subcircuit.py`** - Reusable circuit blocks demonstrating:
  - Subcircuit definition and pins
  - Multiple instantiation
  - Hierarchical design

### 🛠️ Specialized Examples

- **`demo_complete_workflow.py`** - End-to-end circuit design workflow
- **`example_new_component.py`** - Creating custom component types
- **`example_simulated_circuit.py`** - Working with simulation results
- **`debug_simulated_circuit.py`** - Debugging and troubleshooting techniques

## Visual Examples

Several examples generate plots and images (requires matplotlib):

- `astable_multivibrator_demo.png` - Oscillator waveforms
- `cascaded_filter_analysis.png` - Filter frequency response
- `transient_behavior_analysis.png` - Time-domain analysis
- `rc_step_debug.png` - RC circuit debugging

## SPICE Files

Reference SPICE netlists:
- `example_circuit.spice` - Basic circuit netlist
- `voltage_divider.spice` - Simple voltage divider

## Running the Examples

1. **Install requirements** (from project root):
   ```bash
   pip install -r requirements.txt
   ```

2. **Run any example**:
   ```bash
   python examples/example_final_demo.py
   ```

3. **Optional dependencies**:
   - `matplotlib` - For plotting and visualization
   - `pyspice` - For SPICE simulation

## Learning Path

Recommended order for learning:

1. Start with `example_final_demo.py` for a complete overview
2. Study `example_graph_api.py` for API fundamentals  
3. Try `example_simulation.py` for simulation basics
4. Explore `example_subcircuit.py` for modular design
5. Build something complex like the astable multivibrator

## Need Help?

- Check the main README for basic concepts
- Look at the inline comments in each example
- Each example includes detailed docstrings explaining what it demonstrates 
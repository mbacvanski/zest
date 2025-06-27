# Transient Analysis Testing Framework

This document describes the comprehensive transient analysis testing infrastructure for the Zest circuit library.

## Overview

The transient analysis framework provides:

1. **Waveform comparison with interpolation** - Handles different time steps between simulation runs
2. **Golden file validation** - Automatic creation and validation of reference waveforms  
3. **Visual plotting** - Generates and saves publication-quality plots
4. **Comprehensive RC circuit testing** - Multiple test scenarios with different time constants

## Architecture

### Core Components

#### 1. `waveform_test_framework.py`
- **`WaveformTestFramework`** - Main framework class
- **`WaveformTestMixin`** - Mixin for unittest classes
- Handles interpolation, comparison, and plotting

#### 2. `test_transient_analysis.py`
- **`TestTransientAnalysis`** - RC circuit test cases
- **`TestTransientValidation`** - Framework validation tests
- Comprehensive test coverage for different scenarios

### Directory Structure

```
tests/
├── waveform_test_framework.py     # Core framework
├── test_transient_analysis.py     # Test cases
├── golden_waveforms/              # CSV reference files
│   ├── rc_charging_1k_1uF.csv
│   └── rc_time_constants_comparison.csv
├── generated_plots/               # Output plots
│   ├── rc_charging_transient.png
│   └── rc_time_constants_comparison.png
└── golden_files/
    └── rc_transient_circuit.spice # SPICE netlists
```

## Key Features

### 1. Waveform Interpolation

The framework handles the critical problem that SPICE simulations may produce different time grids between runs:

```python
def resample_waveforms(self, time1, values1, time2, values2, num_points=1000):
    """Resample waveforms onto common time grid using linear interpolation."""
    t_min = max(min(time1), min(time2))  # Start from latest start time
    t_max = min(max(time1), max(time2))  # End at earliest end time
    
    common_time = np.linspace(t_min, t_max, num_points)
    resampled1 = np.interp(common_time, time1, values1)
    resampled2 = np.interp(common_time, time2, values2)
    
    return common_time, resampled1, resampled2
```

### 2. Multiple Comparison Metrics

- **MSE (Mean Squared Error)** - Default, good for overall similarity
- **Max Difference** - Catches peak differences
- **Area Difference** - Integral-based comparison

```python
def compare_waveforms(self, values1, values2, tolerance=1e-3, method="mse"):
    if method == "mse":
        metric = np.mean((values1 - values2) ** 2)
    elif method == "max_diff":
        metric = np.max(np.abs(values1 - values2))
    elif method == "area_diff":
        metric = np.trapz(np.abs(values1 - values2))
```

### 3. Automatic Golden File Management

Golden files are automatically created on first run and validated on subsequent runs:

```python
def compare_waveform_against_file(self, golden_file, x_values, values, trace_names):
    golden_path = self.golden_dir / golden_file
    
    if update_golden or not golden_path.exists():
        # Save current data as golden file
        actual_df.to_csv(golden_path, index=False)
        return
    
    # Load and compare against expected data
    expected_df = pd.read_csv(golden_path)
    # ... comparison logic
```

## Test Cases

### 1. RC Charging Circuit
- **Configuration**: 5V step, R=1kΩ, C=1µF (τ=1ms)
- **Analysis**: 5ms simulation (5 time constants)
- **Validation**: Theoretical vs simulated comparison
- **Expected Result**: ~99.3% of final value after 5τ

### 2. Multiple Time Constants
- **τ=1ms**: R=1kΩ, C=1µF
- **τ=2ms**: R=2kΩ, C=1µF  
- **τ=2ms**: R=1kΩ, C=2µF (double capacitance)
- **τ=0.5ms**: R=500Ω, C=1µF

### 3. Framework Validation
- **Interpolation testing** - Verifies resampling accuracy
- **Golden file workflow** - Tests creation, validation, and error detection

## Usage Examples

### Basic Test Case

```python
class TestMyCircuit(WaveformTestMixin, unittest.TestCase):
    def test_rc_response(self):
        # Create circuit
        circuit = Circuit("My RC Circuit")
        # ... add components
        
        # Simulate
        results = circuit.simulate_transient(step_time=1e-5, end_time=5e-3)
        
        # Extract data (implementation-specific)
        times, voltages = extract_results(results)
        
        # Plot and validate
        self.plot_and_save_transient(
            times, [voltages], ('V(output)',),
            title="My RC Response",
            filename="my_rc_response.png"
        )
        
        self.assert_waveform_matches_golden(
            "my_circuit.csv", times, [voltages], ('V(output)',)
        )
```

### Advanced Comparison

```python
# Custom tolerance and comparison method
self.waveform.assert_waveforms_close(
    time1, voltage1, time2, voltage2,
    tolerance=1e-4, method="max_diff", trace_name="V(cap)"
)
```

## Golden File Format

CSV files store time-domain data with columns:

```csv
x,V(capacitor),V(resistor)
0.0,0.0,5.0
5.005e-06,0.0250,4.975
1.001e-05,0.0498,4.950
...
```

- **x**: Time values (seconds)
- **V(name)**: Voltage traces (volts)
- **I(name)**: Current traces (amps) - if needed

## Running Tests

### Individual Test Cases

```bash
# Run RC charging test
python test_transient_analysis.py TestTransientAnalysis.test_rc_charging_transient

# Run framework validation
python test_transient_analysis.py TestTransientValidation.test_waveform_interpolation
```

### Full Test Suite

```bash
python test_transient_analysis.py
```

### Update Golden Files

Set environment variable to regenerate reference data:

```bash
export UPDATE_GOLDEN_WAVEFORMS=1
python test_transient_analysis.py
```

## Output

### Console Output

```
🔬 Transient Analysis Test Suite
==================================================

=== RC Circuit Charging Transient Analysis ===
Circuit created:
- Voltage source: 5.0V
- Resistor: 1000Ω
- Capacitor: 1.0µF
- Time constant τ = RC = 1.0ms

Running transient analysis:
- End time: 5.0ms
- Time step: 5.0µs
- Number of points: 999

✓ Simulation completed successfully
✓ Final capacitor voltage: 4.966V
✓ Expected final voltage: 4.966V

📊 Generating plots...
Plot saved to: /path/to/generated_plots/rc_charging_transient.png
✓ Plot displayed and saved

📋 Validating against golden waveform...
✓ Waveform validation completed
```

### Generated Files

1. **Plots** (`generated_plots/`):
   - High-resolution PNG files (150 DPI)
   - Professional styling with grid and legends
   - Time-domain visualization

2. **Golden Files** (`golden_waveforms/`):
   - CSV format for easy inspection
   - Multiple trace support
   - Precise numerical data

## Integration with Zest

The framework integrates with Zest's simulation capabilities:

```python
# Circuit creation using Zest API
circuit = Circuit("RC Test")
vs = VoltageSource(voltage=5.0)
r1 = Resistor(resistance=1000)
c1 = Capacitor(capacitance=1e-6)

# Wiring using Zest's wire() method
circuit.wire(vs.pos, r1.n1)
circuit.wire(r1.n2, c1.pos)
circuit.wire(c1.neg, circuit.gnd)
circuit.wire(vs.neg, circuit.gnd)

# Simulation using Zest's simulate_transient()
results = circuit.simulate_transient(step_time=5e-6, end_time=5e-3)
```

## Error Handling

The framework provides detailed error messages:

```
AssertionError: Waveforms for V(capacitor) are not close! 
Metric (mse) = 0.001234, Tolerance = 0.001000
```

## Future Enhancements

1. **AC Analysis Support** - Frequency domain testing
2. **Noise Analysis** - Statistical waveform comparison  
3. **Parameter Sweeps** - Multi-dimensional golden files
4. **Parallel Testing** - Multiple circuit configurations
5. **Performance Metrics** - Simulation timing validation

## Best Practices

1. **Use descriptive names** for golden files
2. **Set appropriate tolerances** based on expected accuracy
3. **Include units** in plot labels and documentation
4. **Test edge cases** (very fast/slow time constants)
5. **Validate theoretical expectations** before creating golden files

## Troubleshooting

### Common Issues

1. **Time step variations**: Framework handles automatically via interpolation
2. **Tolerance too strict**: Adjust based on simulation accuracy
3. **Missing packages**: Ensure matplotlib, pandas, numpy are installed
4. **File permissions**: Check write access to test directories

### Debug Mode

For detailed interpolation info:

```python
# Enable debug output in compare_waveforms
common_time, resampled1, resampled2 = self.waveform.resample_waveforms(
    time1, values1, time2, values2, num_points=1000
)
print(f"Interpolation: {len(time1)} -> {len(common_time)} points")
```

This framework provides a robust foundation for validating transient analysis results with the precision and reliability needed for circuit simulation testing. 
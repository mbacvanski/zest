# Golden Test Framework Refactoring

## Overview

Refactored the test suite to consolidate all golden test scaffolding into a centralized framework, eliminating repetitive SPICE validation code and providing a unified approach to golden file testing.

## Changes Made

### 1. Created Golden Test Framework (`golden_test_framework.py`)

**Core Components:**

- `GoldenTestFramework`: Main framework class for golden file operations
- `GoldenTestMixin`: Mixin class to add golden test capabilities to test cases

**Key Features:**

- **Golden file management**: Read, write, and compare against golden files
- **SPICE structure validation**: Common assertions for SPICE netlists
- **Diff reporting**: Clear diff output when golden files don't match
- **Auto-creation**: Creates golden files if they don't exist
- **Format validation**: Ensures SPICE files have proper structure

### 2. Refactored Test Files

**Before**: Repetitive `assertIn` checks scattered across test files:
```python
self.assertIn("V1", spice)
self.assertIn("R1", spice) 
self.assertIn("12", spice)  # Voltage value
self.assertIn("1000", spice)  # R1 resistance
```

**After**: Simple golden file comparison:
```python
# Just compare against golden file - no duplication!
self.assert_circuit_matches_golden(circuit, "voltage_divider.spice")
```

**Files Updated:**
- `test_graph_api.py`: Converted `TestGraphAPIWithGoldenFiles` to use framework
- `test_simulation.py`: Converted `TestSpiceNetlistGeneration` to use framework  
- `test_pyspice_integration.py`: Converted relevant SPICE validation tests

### 3. Golden Files Updated

**Created/Updated Golden Files:**
- `simple_circuit.spice`: Updated to match current SPICE output format
- `voltage_divider.spice`: New golden file for voltage divider circuits
- `rc_filter.spice`: New golden file for RC filter circuits

**Format Standardization:**
```spice
* Circuit: <Circuit Name>

V1 <node1> <node2> DC <voltage>
R1 <node1> <node2> <resistance>
C1 <node1> <node2> <capacitance>

.end
```

## Framework Benefits

### 1. **DRY Principle Applied**
- Eliminated 20+ repetitive `assertIn` statements across test files
- Centralized SPICE validation logic in one place

### 2. **Simple Golden File Comparison**
- `assert_circuit_matches_golden()` for complete validation 
- `assert_spice_has_components()` for basic component checks
- `assert_spice_valid()` for format validation

### 3. **Better Error Messages**
- Clear diff output showing exact differences
- Structured validation with descriptive failure messages

### 4. **Extensibility**
- Easy to add new circuit type validators
- Simple to create new golden files
- Framework can be extended for other validation types

### 5. **Maintenance**
- Golden files can be updated systematically
- Test failures clearly show what changed
- Easy to approve changes to expected output

## Usage Examples

### Basic Golden File Testing
```python
class MyTest(GoldenTestMixin, unittest.TestCase):
    def test_my_circuit(self):
        circuit = create_my_circuit()
        self.assert_circuit_matches_golden(circuit, "my_circuit.spice")
```

### Basic Component Validation
```python
def test_voltage_divider(self):
    spice = circuit.compile_to_spice()
    self.assert_spice_has_components(spice, ["V1", "R1", "R2"])
    self.assert_spice_valid(spice)
```

### Golden File with Environment Flag
```bash
# Update golden files
UPDATE_GOLDEN_FILES=1 python test_my_circuit.py

# Normal testing
python test_my_circuit.py
```

## Testing Results

- All existing tests pass with new framework
- 3 golden files created/updated successfully
- Framework validated across multiple test files
- Clean separation of test logic from validation implementation

## Future Enhancements

- Add support for tolerance-based comparisons
- Extend to other file formats (JSON, XML, etc.)
- Add test execution timing comparisons
- Create visual diff output for complex changes 
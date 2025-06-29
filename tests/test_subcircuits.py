#!/usr/bin/env python3
"""
Test suite for subcircuit functionality in zest.

Tests the SubCircuit component class and circuit compilation with subcircuits.
"""

import unittest
from .golden_test_framework import GoldenTestMixin
import sys
import os

# Add the parent directory to the path for importing zest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from zest import Circuit, Resistor, VoltageSource, SubCircuit, Capacitor


class TestSubcircuits(GoldenTestMixin, unittest.TestCase):
    """Test cases for subcircuit functionality."""
    
    def setUp(self):
        """Set up test cases."""
        super().setUp()
    
    def create_voltage_divider_definition(self):
        """Create a simple voltage divider subcircuit definition."""
        divider_circuit = Circuit("VOLTAGE_DIVIDER")
        r_top = Resistor(resistance=10000)  # 10k
        r_bottom = Resistor(resistance=10000)  # 10k
        
        # Explicitly add components to the circuit
        divider_circuit.add_component(r_top)
        divider_circuit.add_component(r_bottom)
        
        # Wire the resistors together
        divider_circuit.wire(r_top.n2, r_bottom.n1)
        
        # Expose external pins
        divider_circuit.add_pin("vin", r_top.n1)
        divider_circuit.add_pin("vout", r_top.n2)
        divider_circuit.add_pin("gnd", r_bottom.n2)
        
        return divider_circuit
    
    def create_rc_filter_definition(self):
        """Create an RC low-pass filter subcircuit definition."""
        filter_circuit = Circuit("RC_FILTER")
        r1 = Resistor(resistance=1000)  # 1k
        c1 = Capacitor(capacitance=1e-6)  # 1uF
        
        # Explicitly add components to the circuit
        filter_circuit.add_component(r1)
        filter_circuit.add_component(c1)
        
        # Wire R and C in series
        filter_circuit.wire(r1.n2, c1.pos)
        
        # Expose external pins
        filter_circuit.add_pin("input", r1.n1)
        filter_circuit.add_pin("output", r1.n2)
        filter_circuit.add_pin("gnd", c1.neg)
        
        return filter_circuit
    
    def test_simple_subcircuit_instantiation(self):
        """Test Case 1: Simple Subcircuit Instantiation"""
        # Define voltage divider
        divider_def = self.create_voltage_divider_definition()
        
        # Create main circuit
        main_circuit = Circuit("TestMain")
        v_source = VoltageSource(voltage=12.0)
        
        # Instantiate subcircuit
        divider_instance = SubCircuit(definition=divider_def, name="U1")
        
        # Explicitly add components to the main circuit
        main_circuit.add_component(v_source)
        main_circuit.add_component(divider_instance)
        
        # Wire it up
        main_circuit.wire(v_source.pos, divider_instance.vin)
        main_circuit.wire(v_source.neg, divider_instance.gnd)
        
        # Verify the circuit compiles to SPICE
        spice_output = main_circuit.compile_to_spice()
        
        # Check for expected components in output
        self.assertIn(".SUBCKT VOLTAGE_DIVIDER", spice_output)
        self.assertIn(".ENDS VOLTAGE_DIVIDER", spice_output)
        self.assertIn("XU1", spice_output)  # Subcircuit instance
        self.assertIn("V1", spice_output)   # Voltage source
        
        # Use golden file comparison
        self.assert_circuit_matches_golden(main_circuit, "simple_subcircuit.spice")
    
    def test_multiple_instances_same_subcircuit(self):
        """Test Case 2: Multiple Instances of the Same Subcircuit"""
        divider_def = self.create_voltage_divider_definition()
        
        # Create main circuit with two divider instances
        main_circuit = Circuit("MultiInstanceTest")
        v_source = VoltageSource(voltage=15.0)
        
        divider1 = SubCircuit(definition=divider_def, name="U1")
        divider2 = SubCircuit(definition=divider_def, name="U2")
        
        # Explicitly add components to the main circuit
        main_circuit.add_component(v_source)
        main_circuit.add_component(divider1)
        main_circuit.add_component(divider2)
        
        # Wire them in series
        main_circuit.wire(v_source.pos, divider1.vin)
        main_circuit.wire(divider1.vout, divider2.vin)
        main_circuit.wire(v_source.neg, divider1.gnd)
        main_circuit.wire(divider1.gnd, divider2.gnd)
        
        spice_output = main_circuit.compile_to_spice()
        
        # Should have only one .SUBCKT definition but two X lines
        subckt_count = spice_output.count(".SUBCKT VOLTAGE_DIVIDER")
        self.assertEqual(subckt_count, 1, "Should have exactly one .SUBCKT definition")
        
        # Count instance lines specifically (they start with XU1 or XU2 at beginning of line)
        lines = spice_output.split('\n')
        instance_lines = [line for line in lines if line.startswith('XU1 ') or line.startswith('XU2 ')]
        self.assertEqual(len(instance_lines), 2, "Should have two subcircuit instances")
        
        self.assert_circuit_matches_golden(main_circuit, "multiple_instances.spice")
    
    def test_nested_subcircuits_different_types(self):
        """Test Case 3: Multiple different subcircuit types in one circuit"""
        divider_def = self.create_voltage_divider_definition()
        filter_def = self.create_rc_filter_definition()
        
        # Create main circuit
        main_circuit = Circuit("MixedSubcircuits")
        v_source = VoltageSource(voltage=9.0)
        
        # Add instances of both subcircuit types
        bias_divider = SubCircuit(definition=divider_def, name="U1")
        lowpass_filter = SubCircuit(definition=filter_def, name="U2")
        
        # Explicitly add components to the main circuit
        main_circuit.add_component(v_source)
        main_circuit.add_component(bias_divider)
        main_circuit.add_component(lowpass_filter)
        
        # Connect them in cascade
        main_circuit.wire(v_source.pos, bias_divider.vin)
        main_circuit.wire(bias_divider.vout, lowpass_filter.input)
        main_circuit.wire(v_source.neg, bias_divider.gnd)
        main_circuit.wire(bias_divider.gnd, lowpass_filter.gnd)
        
        spice_output = main_circuit.compile_to_spice()
        
        # Should have both subcircuit definitions
        self.assertIn(".SUBCKT VOLTAGE_DIVIDER", spice_output)
        self.assertIn(".SUBCKT RC_FILTER", spice_output)
        self.assertIn("XU1", spice_output)  # Divider instance
        self.assertIn("XU2", spice_output)  # Filter instance
        
        self.assert_circuit_matches_golden(main_circuit, "mixed_subcircuits.spice")
    
    def test_subcircuit_pin_access(self):
        """Test that subcircuit pins are accessible as terminals."""
        divider_def = self.create_voltage_divider_definition()
        divider_instance = SubCircuit(definition=divider_def, name="U1")
        
        # Check that all pins are accessible
        self.assertTrue(hasattr(divider_instance, 'vin'))
        self.assertTrue(hasattr(divider_instance, 'vout'))
        self.assertTrue(hasattr(divider_instance, 'gnd'))
        
        # Check that they are Terminal objects
        from zest.components import Terminal
        self.assertIsInstance(divider_instance.vin, Terminal)
        self.assertIsInstance(divider_instance.vout, Terminal)
        self.assertIsInstance(divider_instance.gnd, Terminal)
    
    def test_error_handling_no_pins(self):
        """Test Case 4: Error Handling - No Pins"""
        # Create a circuit without pins
        bad_circuit = Circuit("NO_PINS")
        Resistor(resistance=1000)  # Add a resistor but no pins
        
        # Should raise ValueError when trying to create SubCircuit
        with self.assertRaises(ValueError) as context:
            SubCircuit(definition=bad_circuit)
        
        self.assertIn("no external pins defined", str(context.exception))
    
    def test_error_handling_invalid_definition(self):
        """Test Case 4: Error Handling - Invalid Definition"""
        # Should raise TypeError if definition is not a Circuit
        with self.assertRaises(TypeError) as context:
            SubCircuit(definition="not a circuit")
        
        self.assertIn("must be a 'Circuit'", str(context.exception))
    
    def test_add_pin_validation(self):
        """Test validation in add_pin method."""
        circuit = Circuit("TestCircuit")
        r1 = Resistor(resistance=1000)
        
        # Explicitly add the component to the circuit
        circuit.add_component(r1)
        
        # Should work with valid terminal
        circuit.add_pin("test", r1.n1)
        self.assertEqual(circuit.pins["test"], r1.n1)
        
        # Should raise TypeError with non-Terminal
        with self.assertRaises(TypeError):
            circuit.add_pin("bad", "not a terminal")
        
        # Create separate circuit and resistor not in our circuit
        other_circuit = Circuit("Other")
        other_resistor = Resistor(resistance=2000)
        other_circuit.add_component(other_resistor)  # Add to other circuit, not our circuit
        
        # Should raise ValueError when terminal's component not in circuit
        with self.assertRaises(ValueError):
            circuit.add_pin("bad", other_resistor.n1)
    
    def test_subcircuit_component_type_prefix(self):
        """Test that SubCircuit has correct component type prefix."""
        divider_def = self.create_voltage_divider_definition()
        divider_instance = SubCircuit(definition=divider_def)
        
        self.assertEqual(divider_instance.get_component_type_prefix(), "X")
    
    def test_subcircuit_get_terminals(self):
        """Test that SubCircuit returns correct terminals list."""
        divider_def = self.create_voltage_divider_definition()
        divider_instance = SubCircuit(definition=divider_def)
        
        terminals = divider_instance.get_terminals()
        self.assertEqual(len(terminals), 3)  # vin, vout, gnd
        
        terminal_names = [name for name, terminal in terminals]
        self.assertIn("vin", terminal_names)
        self.assertIn("vout", terminal_names)
        self.assertIn("gnd", terminal_names)


if __name__ == '__main__':
    unittest.main() 
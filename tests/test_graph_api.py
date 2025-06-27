#!/usr/bin/env python3
"""
Tests for the graph-based API.
"""

import unittest
import os
import sys

# Add the parent directory to the path to import zest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zest import Circuit, VoltageSource, Resistor, Capacitor, Inductor
from golden_test_framework import GoldenTestMixin


class TestGraphAPI(unittest.TestCase):
    """Test the graph-based API functionality."""
    
    def setUp(self):
        """Set up test circuit."""
        self.circuit = Circuit("Test Circuit")
    
    def test_component_creation_without_connections(self):
        """Test that components can be created without specifying connections."""
        vs = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        c1 = Capacitor(capacitance=1e-6)
        l1 = Inductor(inductance=1e-3)
        
        # Components should be auto-registered
        self.assertEqual(len(self.circuit.components), 4)
        self.assertIn(vs, self.circuit.components)
        self.assertIn(r1, self.circuit.components)
        self.assertIn(c1, self.circuit.components)
        self.assertIn(l1, self.circuit.components)
        
        # No wires initially
        self.assertEqual(len(self.circuit.wires), 0)
    
    def test_wire_method_basic(self):
        """Test basic wire() method functionality."""
        vs = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        
        # Wire components
        self.circuit.wire(vs.pos, r1.n1)
        self.circuit.wire(vs.neg, self.circuit.gnd)
        self.circuit.wire(r1.n2, self.circuit.gnd)
        
        # Check wire count
        self.assertEqual(len(self.circuit.wires), 3)
        
        # Check specific wires exist
        self.assertIn((vs.pos, r1.n1), self.circuit.wires)
        self.assertIn((vs.neg, self.circuit.gnd), self.circuit.wires)
        self.assertIn((r1.n2, self.circuit.gnd), self.circuit.wires)
    
    def test_wire_method_multiple_from_same_terminal(self):
        """Test that wire() allows multiple wires FROM same terminal TO different terminals."""
        vs = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        r2 = Resistor(resistance=2000)
        
        # Wire multiple components to the same terminal
        self.circuit.wire(vs.pos, r1.n1)
        self.circuit.wire(vs.pos, r2.n1)  # Multiple wires FROM vs.pos - should be allowed
        self.circuit.wire(r1.n2, self.circuit.gnd)
        self.circuit.wire(r2.n2, self.circuit.gnd)
        
        # Should have all 4 wires
        self.assertEqual(len(self.circuit.wires), 4)
        
        # Check all wires exist
        self.assertIn((vs.pos, r1.n1), self.circuit.wires)
        self.assertIn((vs.pos, r2.n1), self.circuit.wires)
        self.assertIn((r1.n2, self.circuit.gnd), self.circuit.wires)
        self.assertIn((r2.n2, self.circuit.gnd), self.circuit.wires)
    
    def test_wire_method_prevents_duplicate_connections(self):
        """Test that wire() prevents duplicate connections between same endpoints."""
        vs = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        
        # Add the same wire multiple times
        self.circuit.wire(vs.pos, r1.n1)
        self.circuit.wire(vs.pos, r1.n1)  # Duplicate wire - should be ignored
        self.circuit.wire(r1.n1, vs.pos)  # Reverse wire - should also be ignored
        
        # Should only have 1 wire
        self.assertEqual(len(self.circuit.wires), 1)
        self.assertEqual(self.circuit.wires[0], (vs.pos, r1.n1))
    
    def test_wire_method_validation(self):
        """Test that wire() validates input types."""
        vs = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        
        # Valid connections should work
        self.circuit.wire(vs.pos, r1.n1)
        self.circuit.wire(vs.neg, self.circuit.gnd)
        
        # Invalid connections should raise ValueError
        with self.assertRaises(ValueError):
            self.circuit.wire("invalid", r1.n2)
        
        with self.assertRaises(ValueError):
            self.circuit.wire(vs.pos, "invalid")
        
        with self.assertRaises(ValueError):
            self.circuit.wire(vs.pos, 12345)
    
    def test_terminal_properties(self):
        """Test that components expose the correct terminals."""
        vs = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        c1 = Capacitor(capacitance=1e-6)
        l1 = Inductor(inductance=1e-3)
        
        # VoltageSource terminals
        self.assertTrue(hasattr(vs, 'pos'))
        self.assertTrue(hasattr(vs, 'neg'))
        self.assertTrue(hasattr(vs, 'positive'))  # Alias
        self.assertTrue(hasattr(vs, 'negative'))  # Alias
        self.assertEqual(vs.pos, vs.positive)
        self.assertEqual(vs.neg, vs.negative)
        
        # Resistor terminals
        self.assertTrue(hasattr(r1, 'n1'))
        self.assertTrue(hasattr(r1, 'n2'))
        self.assertTrue(hasattr(r1, 'a'))  # Alias
        self.assertTrue(hasattr(r1, 'b'))  # Alias
        self.assertEqual(r1.n1, r1.a)
        self.assertEqual(r1.n2, r1.b)
        
        # Capacitor terminals
        self.assertTrue(hasattr(c1, 'pos'))
        self.assertTrue(hasattr(c1, 'neg'))
        self.assertTrue(hasattr(c1, 'positive'))  # Alias
        self.assertTrue(hasattr(c1, 'negative'))  # Alias
        
        # Inductor terminals
        self.assertTrue(hasattr(l1, 'n1'))
        self.assertTrue(hasattr(l1, 'n2'))
        self.assertTrue(hasattr(l1, 'a'))  # Alias
        self.assertTrue(hasattr(l1, 'b'))  # Alias
    
    def test_spice_generation_with_wiring(self):
        """Test SPICE generation with the graph-based API."""
        vs = VoltageSource(voltage=12.0)
        r1 = Resistor(resistance=1000)
        r2 = Resistor(resistance=2000)
        
        # Build voltage divider
        self.circuit.wire(vs.neg, self.circuit.gnd)
        self.circuit.wire(vs.pos, r1.n1)
        self.circuit.wire(r1.n2, r2.n1)
        self.circuit.wire(r2.n2, self.circuit.gnd)
        
        spice = self.circuit.compile_to_spice()
        
        # Check SPICE content
        self.assertIn("V1", spice)
        self.assertIn("R1", spice)
        self.assertIn("R2", spice)
        self.assertIn("gnd", spice)
        self.assertIn("12", spice)  # Voltage value
        self.assertIn("1000", spice)  # R1 resistance
        self.assertIn("2000", spice)  # R2 resistance
    
    def test_node_name_generation(self):
        """Test SPICE node name generation from terminal connections."""
        vs = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        r2 = Resistor(resistance=2000)
        
        # Connect terminals
        self.circuit.wire(vs.pos, r1.n1)  # Should create shared node
        self.circuit.wire(r1.n2, r2.n1)  # Should create shared node
        
        # Test node name generation
        vs_pos_node = self.circuit.get_spice_node_name(vs.pos)
        r1_n1_node = self.circuit.get_spice_node_name(r1.n1)
        r1_n2_node = self.circuit.get_spice_node_name(r1.n2)
        r2_n1_node = self.circuit.get_spice_node_name(r2.n1)
        
        # Connected terminals should have same node name
        self.assertEqual(vs_pos_node, r1_n1_node)
        self.assertEqual(r1_n2_node, r2_n1_node)
        
        # Different connections should have different node names
        self.assertNotEqual(vs_pos_node, r1_n2_node)
    
    def test_ground_connections(self):
        """Test ground connection handling."""
        vs = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        
        # Connect to ground
        self.circuit.wire(vs.neg, self.circuit.gnd)
        self.circuit.wire(r1.n2, self.circuit.gnd)
        
        # Both should map to 'gnd'
        vs_neg_node = self.circuit.get_spice_node_name(vs.neg)
        r1_n2_node = self.circuit.get_spice_node_name(r1.n2)
        
        self.assertEqual(vs_neg_node, "gnd")
        self.assertEqual(r1_n2_node, "gnd")
    
    def test_complex_connectivity(self):
        """Test complex connectivity patterns."""
        vs = VoltageSource(voltage=10.0)
        r1 = Resistor(resistance=1000)
        r2 = Resistor(resistance=2000)
        c1 = Capacitor(capacitance=1e-6)
        
        # Build complex circuit
        self.circuit.wire(vs.neg, self.circuit.gnd)
        self.circuit.wire(vs.pos, r1.n1)
        self.circuit.wire(r1.n2, r2.n1)
        self.circuit.wire(r1.n2, c1.pos)  # Parallel connection
        self.circuit.wire(r2.n2, self.circuit.gnd)
        self.circuit.wire(c1.neg, self.circuit.gnd)
        
        # Check connectivity
        r1_r2_node = self.circuit.get_spice_node_name(r1.n2)
        r2_c1_node = self.circuit.get_spice_node_name(r2.n1)
        c1_pos_node = self.circuit.get_spice_node_name(c1.pos)
        
        # r1.n2, r2.n1, and c1.pos should all be the same node
        self.assertEqual(r1_r2_node, r2_c1_node)
        self.assertEqual(r1_r2_node, c1_pos_node)
    
    def test_component_auto_naming(self):
        """Test component auto-naming is circuit-local."""
        # Create multiple components of same type
        vs1 = VoltageSource(voltage=5.0)
        vs2 = VoltageSource(voltage=12.0)
        r1 = Resistor(resistance=1000)
        r2 = Resistor(resistance=2000)
        r3 = Resistor(resistance=3000)
        
        # Names are assigned during SPICE compilation
        spice = self.circuit.compile_to_spice()
        
        # Check auto-generated names (circuit-local)
        self.assertEqual(vs1.name, "V1")
        self.assertEqual(vs2.name, "V2")
        self.assertEqual(r1.name, "R1")
        self.assertEqual(r2.name, "R2")
        self.assertEqual(r3.name, "R3")
    
    def test_circuit_local_naming(self):
        """Test that naming is local to each circuit."""
        # Create first circuit
        circuit1 = Circuit("Circuit 1")
        vs1 = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        circuit1.wire(vs1.pos, r1.n1)
        circuit1.wire(vs1.neg, circuit1.gnd)
        circuit1.wire(r1.n2, circuit1.gnd)
        
        # Create second circuit
        circuit2 = Circuit("Circuit 2")
        vs2 = VoltageSource(voltage=12.0)
        r2 = Resistor(resistance=2000)
        circuit2.wire(vs2.pos, r2.n1)
        circuit2.wire(vs2.neg, circuit2.gnd)
        circuit2.wire(r2.n2, circuit2.gnd)
        
        # Compile both circuits
        spice1 = circuit1.compile_to_spice()
        spice2 = circuit2.compile_to_spice()
        
        # Each circuit should have independent naming
        self.assertIn("V1", spice1)
        self.assertIn("R1", spice1)
        self.assertIn("V1", spice2)  # Second circuit also starts from V1, R1
        self.assertIn("R1", spice2)
    
    def test_circuit_representation(self):
        """Test circuit string representation."""
        vs = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        
        self.circuit.wire(vs.pos, r1.n1)
        self.circuit.wire(vs.neg, self.circuit.gnd)
        
        repr_str = str(self.circuit)
        self.assertIn("Test Circuit", repr_str)
        self.assertIn("2 components", repr_str)
        self.assertIn("2 wires", repr_str)


class TestGraphAPIWithGoldenFiles(GoldenTestMixin, unittest.TestCase):
    """Test graph API against golden files."""
    
    def test_voltage_divider_golden(self):
        """Test voltage divider matches expected SPICE output."""
        circuit = Circuit("Voltage Divider")
        
        vs = VoltageSource(voltage=12.0)
        r1 = Resistor(resistance=1000)
        r2 = Resistor(resistance=2000)
        
        circuit.wire(vs.neg, circuit.gnd)
        circuit.wire(vs.pos, r1.n1)
        circuit.wire(r1.n2, r2.n1)
        circuit.wire(r2.n2, circuit.gnd)
        
        # Compare against golden file
        self.assert_circuit_matches_golden(circuit, "voltage_divider.spice")
    
    def test_rc_filter_golden(self):
        """Test RC filter matches expected structure."""
        circuit = Circuit("RC Filter")
        
        vs = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        c1 = Capacitor(capacitance=1e-6)
        
        circuit.wire(vs.neg, circuit.gnd)
        circuit.wire(vs.pos, r1.n1)
        circuit.wire(r1.n2, c1.pos)
        circuit.wire(c1.neg, circuit.gnd)
        
        # Compare against golden file
        self.assert_circuit_matches_golden(circuit, "rc_filter.spice")
    
    def test_simple_circuit_golden(self):
        """Test simple circuit matches existing golden file."""
        circuit = Circuit("Simple Circuit")
        
        vs = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        
        circuit.wire(vs.pos, r1.n1)
        circuit.wire(vs.neg, circuit.gnd)
        circuit.wire(r1.n2, circuit.gnd)
        
        # This should match the existing simple_circuit.spice golden file
        self.assert_circuit_matches_golden(circuit, "simple_circuit.spice")


if __name__ == '__main__':
    unittest.main() 
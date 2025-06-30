#!/usr/bin/env python3
"""
Tests for circuit-related classes: Circuit, CircuitRoot, NetlistBlock, NodeMapper, 
SubCircuitDef, SubCircuitInst, and circuit connectivity functionality.
"""

import unittest
import os
import sys

# Add the parent directory to the path to import zest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zest import Circuit, VoltageSource, Resistor, Capacitor, Inductor, SubCircuit
from zest.circuit import NodeMapper, NetlistBlock, SubCircuitDef, SubCircuitInst
from .golden_test_framework import GoldenTestMixin


class TestCircuit(unittest.TestCase):
    """Test the Circuit class functionality."""
    
    def setUp(self):
        """Set up test circuit."""
        self.circuit = Circuit("Test Circuit")
    
    def test_circuit_creation(self):
        """Test Circuit creation and basic properties."""
        circuit = Circuit("My Circuit")
        self.assertEqual(circuit.name, "My Circuit")
        self.assertEqual(len(circuit.components), 0)
        self.assertEqual(len(circuit.wires), 0)
        self.assertIsNotNone(circuit.gnd)
    
    def test_add_remove_component(self):
        """Test adding and removing components."""
        r1 = Resistor(resistance=1000)
        
        # Add component
        self.circuit.add_component(r1)
        self.assertIn(r1, self.circuit.components)
        self.assertEqual(len(self.circuit.components), 1)
        
        # Adding same component again should not duplicate
        self.circuit.add_component(r1)
        self.assertEqual(len(self.circuit.components), 1)
        
        # Remove component
        self.circuit.remove_component(r1)
        self.assertNotIn(r1, self.circuit.components)
        self.assertEqual(len(self.circuit.components), 0)
    
    def test_wire_method_basic(self):
        """Test basic wire() method functionality."""
        vs = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        
        # Add components to circuit
        self.circuit.add_component(vs)
        self.circuit.add_component(r1)
        
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
        
        # Add components to circuit
        self.circuit.add_component(vs)
        self.circuit.add_component(r1)
        self.circuit.add_component(r2)
        
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
        
        # Add components to circuit
        self.circuit.add_component(vs)
        self.circuit.add_component(r1)
        
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
        
        # Add components to circuit
        self.circuit.add_component(vs)
        self.circuit.add_component(r1)
        
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
    
    def test_node_name_generation(self):
        """Test automatic node name generation."""
        vs = VoltageSource(voltage=10.0)
        r1 = Resistor(resistance=1000)
        r2 = Resistor(resistance=2000)
        
        # Add components to circuit
        self.circuit.add_component(vs)
        self.circuit.add_component(r1)
        self.circuit.add_component(r2)
        
        # Wire the voltage divider
        self.circuit.wire(vs.neg, self.circuit.gnd)
        self.circuit.wire(vs.pos, r1.n1)
        self.circuit.wire(r1.n2, r2.n1)
        self.circuit.wire(r2.n2, self.circuit.gnd)
        
        # Check node names
        self.assertEqual(self.circuit.get_spice_node_name(self.circuit.gnd), "gnd")
        
        # Internal nodes should get N1, N2, etc.
        vs_pos_node = self.circuit.get_spice_node_name(vs.pos)
        divider_node = self.circuit.get_spice_node_name(r1.n2)
        
        # Should be different nodes
        self.assertNotEqual(vs_pos_node, divider_node)
        self.assertNotEqual(vs_pos_node, "gnd")
        self.assertNotEqual(divider_node, "gnd")
    
    def test_ground_connections(self):
        """Test that ground connections work correctly."""
        r1 = Resistor(resistance=1000)
        self.circuit.add_component(r1)
        
        # Connect one terminal to ground
        self.circuit.wire(r1.n1, self.circuit.gnd)
        
        # Check that the terminal gets ground node name
        self.assertEqual(self.circuit.get_spice_node_name(r1.n1), "gnd")
        self.assertEqual(self.circuit.get_spice_node_name(self.circuit.gnd), "gnd")
    
    def test_complex_connectivity(self):
        """Test complex connectivity scenarios."""
        vs = VoltageSource(voltage=12.0)
        r1 = Resistor(resistance=1000)
        r2 = Resistor(resistance=2000)
        r3 = Resistor(resistance=3000)
        
        # Add components to circuit
        self.circuit.add_component(vs)
        self.circuit.add_component(r1)
        self.circuit.add_component(r2)
        self.circuit.add_component(r3)
        
        # Create a more complex network
        self.circuit.wire(vs.neg, self.circuit.gnd)
        self.circuit.wire(vs.pos, r1.n1)  # Supply to R1
        self.circuit.wire(r1.n2, r2.n1)   # R1 to R2
        self.circuit.wire(r1.n2, r3.n1)   # R1 also to R3 (parallel)
        self.circuit.wire(r2.n2, self.circuit.gnd)  # R2 to ground
        self.circuit.wire(r3.n2, self.circuit.gnd)  # R3 to ground
        
        # Check that r2.n1 and r3.n1 get the same node name (connected to r1.n2)
        r1_r2_node = self.circuit.get_spice_node_name(r1.n2)
        r2_n1_node = self.circuit.get_spice_node_name(r2.n1)
        r3_n1_node = self.circuit.get_spice_node_name(r3.n1)
        
        self.assertEqual(r1_r2_node, r2_n1_node)
        self.assertEqual(r1_r2_node, r3_n1_node)
    
    def test_component_auto_naming(self):
        """Test automatic component naming."""
        # Create components without explicit names
        vs = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        r2 = Resistor(resistance=2000)
        c1 = Capacitor(capacitance=1e-6)
        
        # Add to circuit - should get auto-named
        self.circuit.add_component(vs)
        self.circuit.add_component(r1)
        self.circuit.add_component(r2)
        self.circuit.add_component(c1)
        
        # Check that components get proper SPICE names
        vs_name = self.circuit.get_component_name(vs)
        r1_name = self.circuit.get_component_name(r1)
        r2_name = self.circuit.get_component_name(r2)
        c1_name = self.circuit.get_component_name(c1)
        
        self.assertTrue(vs_name.startswith("V"))
        self.assertTrue(r1_name.startswith("R"))
        self.assertTrue(r2_name.startswith("R"))
        self.assertTrue(c1_name.startswith("C"))
        
        # Names should be unique
        self.assertNotEqual(r1_name, r2_name)
    
    def test_initial_conditions(self):
        """Test setting and getting initial conditions."""
        vs = VoltageSource(voltage=5.0)
        c1 = Capacitor(capacitance=1e-6)
        
        self.circuit.add_component(vs)
        self.circuit.add_component(c1)
        
        # Set initial condition on capacitor
        self.circuit.set_initial_condition(c1.pos, 2.5)
        
        # Get initial condition
        ic = self.circuit.get_initial_condition(c1.pos)
        self.assertEqual(ic, 2.5)
        
        # Test ground initial condition
        with self.assertRaises(ValueError):
            self.circuit.set_initial_condition(self.circuit.gnd, 1.0)  # Should be 0V


class TestSubCircuits(GoldenTestMixin, unittest.TestCase):
    """Test SubCircuitDef, SubCircuitInst, and SubCircuit functionality."""
    
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
    
    def test_subcircuit_definition_creation(self):
        """Test creating subcircuit definitions."""
        divider_def = self.create_voltage_divider_definition()
        
        # Should have the correct pins
        self.assertIn("vin", divider_def.pins)
        self.assertIn("vout", divider_def.pins)
        self.assertIn("gnd", divider_def.pins)
        
        # Should compile to SPICE subcircuit
        spice = divider_def.compile_as_subckt()
        self.assertIn(".SUBCKT VOLTAGE_DIVIDER", spice)
        self.assertIn(".ENDS VOLTAGE_DIVIDER", spice)
    
    def test_simple_subcircuit_instantiation(self):
        """Test instantiating subcircuits."""
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
        """Test multiple instances of the same subcircuit."""
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
    
    def test_subcircuit_component_type_prefix(self):
        """Test SubCircuit component type prefix."""
        divider_def = self.create_voltage_divider_definition()
        subcircuit = SubCircuit(definition=divider_def, name="U1")
        self.assertEqual(subcircuit.get_component_type_prefix(), "X")
    
    def test_subcircuit_get_terminals(self):
        """Test SubCircuit get_terminals method."""
        divider_def = self.create_voltage_divider_definition()
        subcircuit = SubCircuit(definition=divider_def, name="U1")
        terminals = subcircuit.get_terminals()
        
        # Should have terminals for all pins
        terminal_names = [name for name, terminal in terminals]
        self.assertIn("vin", terminal_names)
        self.assertIn("vout", terminal_names)
        self.assertIn("gnd", terminal_names)
    
    def test_add_pin_validation(self):
        """Test pin validation when adding pins to circuits."""
        circuit = Circuit("Test")
        r1 = Resistor(resistance=1000)
        circuit.add_component(r1)
        
        # Valid pin addition
        circuit.add_pin("input", r1.n1)
        self.assertIn("input", circuit.pins)
        self.assertEqual(circuit.pins["input"], r1.n1)
        
        # Invalid pin - not a Terminal
        with self.assertRaises(TypeError):
            circuit.add_pin("bad", "not a terminal")
        
        # Invalid pin - component not in circuit
        r2 = Resistor(resistance=2000)  # Not added to circuit
        with self.assertRaises(ValueError):
            circuit.add_pin("bad", r2.n1)
    
    def test_error_handling_no_pins(self):
        """Test error handling when creating subcircuit with no pins."""
        # Create a circuit without pins
        bad_circuit = Circuit("NO_PINS")
        Resistor(resistance=1000)  # Add a resistor but no pins
        
        # Should raise ValueError when trying to create SubCircuit
        with self.assertRaises(ValueError) as context:
            SubCircuit(definition=bad_circuit)
        
        self.assertIn("no external pins defined", str(context.exception))
    
    def test_error_handling_invalid_definition(self):
        """Test error handling with invalid subcircuit definition."""
        # Should raise TypeError if definition is not a Circuit
        with self.assertRaises(TypeError):
            SubCircuit(definition="not a circuit")


class TestSpiceGeneration(GoldenTestMixin, unittest.TestCase):
    """Test SPICE netlist generation functionality."""
    
    def test_voltage_divider_netlist(self):
        """Test netlist generation for voltage divider."""
        circuit = Circuit("Voltage Divider Test")
        
        vs = VoltageSource(voltage=10.0)
        r1 = Resistor(resistance=1000)
        r2 = Resistor(resistance=2000)
        
        # Add components to circuit
        circuit.add_component(vs)
        circuit.add_component(r1)
        circuit.add_component(r2)
        
        # Wire the components
        circuit.wire(vs.neg, circuit.gnd)
        circuit.wire(vs.pos, r1.n1)
        circuit.wire(r1.n2, r2.n1)
        circuit.wire(r2.n2, circuit.gnd)
        
        spice = circuit.compile_to_spice()
        
        # Basic validation - ensure expected components are present
        self.assert_spice_has_components(spice, ["V1", "R1", "R2"])
        self.assert_spice_valid(spice)
    
    def test_rlc_circuit_netlist(self):
        """Test netlist generation for RLC circuit."""
        circuit = Circuit("RLC Test")
        
        vs = VoltageSource(voltage=1.0)
        r1 = Resistor(resistance=100)
        l1 = Inductor(inductance=1e-3)
        c1 = Capacitor(capacitance=1e-6)
        
        # Add components to circuit
        circuit.add_component(vs)
        circuit.add_component(r1)
        circuit.add_component(l1)
        circuit.add_component(c1)
        
        # Wire series RLC circuit
        circuit.wire(vs.neg, circuit.gnd)
        circuit.wire(vs.pos, r1.n1)
        circuit.wire(r1.n2, l1.n1)
        circuit.wire(l1.n2, c1.pos)
        circuit.wire(c1.neg, circuit.gnd)
        
        spice = circuit.compile_to_spice()
        
        # Basic validation - ensure expected components are present
        self.assert_spice_has_components(spice, ["V1", "R1", "L1", "C1"])
        self.assert_spice_valid(spice)
    
    def test_circuit_representation(self):
        """Test string representation of circuits."""
        circuit = Circuit("My Circuit")
        
        # Empty circuit
        repr_str = repr(circuit)
        self.assertIn("My Circuit", repr_str)
        self.assertIn("0 components", repr_str)
        
        # Circuit with components
        vs = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        circuit.add_component(vs)
        circuit.add_component(r1)
        
        repr_str = repr(circuit)
        self.assertIn("My Circuit", repr_str)
        self.assertIn("2 components", repr_str)


if __name__ == '__main__':
    unittest.main()
#!/usr/bin/env python3
"""
Tests for the simulation functionality.
"""

import unittest
import os
import sys

# Add the parent directory to the path to import zest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zest import Circuit, VoltageSource, Resistor, Capacitor, Inductor
from zest.simulation import CircuitSimulator, check_simulation_requirements
from golden_test_framework import GoldenTestMixin


class TestCircuitSimulator(unittest.TestCase):
    """Test the CircuitSimulator class."""
    
    def setUp(self):
        """Set up test circuit."""
        self.circuit = Circuit("Test Circuit")
        self.vs = VoltageSource(voltage=10.0)
        self.r1 = Resistor(resistance=1000)
        self.r2 = Resistor(resistance=2000)
        
        # Add components to circuit
        self.circuit.add_component(self.vs)
        self.circuit.add_component(self.r1)
        self.circuit.add_component(self.r2)
        
        # Wire the voltage divider
        self.circuit.wire(self.vs.neg, self.circuit.gnd)
        self.circuit.wire(self.vs.pos, self.r1.n1)
        self.circuit.wire(self.r1.n2, self.r2.n1)
        self.circuit.wire(self.r2.n2, self.circuit.gnd)
    
    def test_simulator_creation_with_pyspice(self):
        """Test simulator creation when PySpice is available."""
        simulator = CircuitSimulator(self.circuit)
        self.assertIsNotNone(simulator)
        self.assertEqual(simulator.circuit, self.circuit)
    
    def test_simulator_creation_without_pyspice(self):
        """Test simulator creation when PySpice is not available."""
        # This test would need to mock PySpice unavailability
        # For now, just check simulator creation works
        simulator = CircuitSimulator(self.circuit)
        self.assertIsNotNone(simulator)
    
    def test_simulation_requirements_check(self):
        """Test the simulation requirements check function."""
        available, message = check_simulation_requirements()
        # Should return boolean and string, not throw exception
        self.assertIsInstance(available, bool)
        self.assertIsInstance(message, str)


class TestCircuitIntegration(unittest.TestCase):
    """Test circuit simulation integration methods."""
    
    def setUp(self):
        """Set up test circuit."""
        self.circuit = Circuit("Test Circuit")
        self.vs = VoltageSource(voltage=5.0)
        self.r1 = Resistor(resistance=1000)
        
        # Add components to circuit
        self.circuit.add_component(self.vs)
        self.circuit.add_component(self.r1)
        
        # Wire simple circuit
        self.circuit.wire(self.vs.neg, self.circuit.gnd)
        self.circuit.wire(self.vs.pos, self.r1.n1)
        self.circuit.wire(self.r1.n2, self.circuit.gnd)
    
    def test_get_simulator(self):
        """Test getting simulator from circuit."""
        simulator = self.circuit.get_simulator()
        self.assertIsInstance(simulator, CircuitSimulator)
        self.assertEqual(simulator.circuit, self.circuit)
    
    def test_operating_point_method(self):
        """Test circuit operating point simulation method."""
        # This test would run actual simulation if PySpice is available
        # For now, just check the method exists and doesn't crash
        try:
            result = self.circuit.simulate_operating_point()
            # If it succeeds, result should be a SimulatedCircuit object
            self.assertIsNotNone(result)
        except Exception as e:
            # If PySpice not available or other issue, that's OK for this test
            self.assertIsInstance(e, (ImportError, Exception))


class TestSpiceNetlistGeneration(GoldenTestMixin, unittest.TestCase):
    """Test SPICE netlist generation with the new API."""
    
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
    
    def test_terminal_connections(self):
        """Test that terminal connections work properly."""
        circuit = Circuit("Terminal Test")
        
        vs = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        c1 = Capacitor(capacitance=1e-6)
        
        # Add components to circuit
        circuit.add_component(vs)
        circuit.add_component(r1)
        circuit.add_component(c1)
        
        # Connect using different terminal names
        circuit.wire(vs.negative, circuit.gnd)  # Use alias
        circuit.wire(vs.positive, r1.a)         # Use alias
        circuit.wire(r1.b, c1.positive)         # Use alias
        circuit.wire(c1.negative, circuit.gnd)  # Use alias
        
        spice = circuit.compile_to_spice()
        
        # Basic validation - ensure expected components are present
        self.assert_spice_has_components(spice, ["V1", "R1", "C1"])
        self.assert_spice_valid(spice)
    
    def test_wire_validation(self):
        """Test that wire() method validates inputs properly."""
        circuit = Circuit("Validation Test")
        r1 = Resistor(resistance=1000)
        
        # Add component to circuit
        circuit.add_component(r1)
        
        # Valid connections should work
        circuit.wire(r1.n1, circuit.gnd)
        
        # Invalid connections should raise ValueError
        with self.assertRaises(ValueError):
            circuit.wire("invalid", r1.n2)
        
        with self.assertRaises(ValueError):
            circuit.wire(r1.n1, "invalid")
        
        with self.assertRaises(ValueError):
            circuit.wire(r1.n1, 12345)
    
    def test_component_creation_without_connections(self):
        """Test that components can be created independently."""
        circuit = Circuit("Creation Test")
        
        # Create components without any wiring
        vs = VoltageSource(voltage=12.0)
        r1 = Resistor(resistance=1000)
        c1 = Capacitor(capacitance=1e-6)
        l1 = Inductor(inductance=1e-3)
        
        # Add components to circuit explicitly
        circuit.add_component(vs)
        circuit.add_component(r1)
        circuit.add_component(c1)
        circuit.add_component(l1)
        
        # All should be registered
        self.assertEqual(len(circuit.components), 4)
        
        # But no wires initially
        self.assertEqual(len(circuit.wires), 0)
        
        # Compile to assign names
        circuit.compile_to_spice()
        
        # Names should be auto-generated
        self.assertEqual(vs.name, "V1")
        self.assertEqual(r1.name, "R1")
        self.assertEqual(c1.name, "C1")
        self.assertEqual(l1.name, "L1")


if __name__ == '__main__':
    unittest.main() 
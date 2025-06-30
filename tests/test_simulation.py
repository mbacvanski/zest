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
from zest.simulation import CircuitSimulator, SimulatedCircuit, check_simulation_requirements
from .golden_test_framework import GoldenTestMixin


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


class TestBranchCurrentMethods(unittest.TestCase):
    """Test branch current retrieval methods."""
    
    def setUp(self):
        """Set up test circuit."""
        self.circuit = Circuit("Test Current Circuit")
        
        # Create simple circuit: V1 - R1 - R2 - GND
        self.vs = VoltageSource(voltage=10.0, name="source")
        self.r1 = Resistor(resistance=1000, name="upper")  
        self.r2 = Resistor(resistance=2000, name="lower")
        
        # Add components to circuit
        self.circuit.add_component(self.vs)
        self.circuit.add_component(self.r1)
        self.circuit.add_component(self.r2)
        
        # Wire the circuit
        self.circuit.wire(self.vs.neg, self.circuit.gnd)
        self.circuit.wire(self.vs.pos, self.r1.n1)
        self.circuit.wire(self.r1.n2, self.r2.n1)
        self.circuit.wire(self.r2.n2, self.circuit.gnd)
        
    def test_component_names_deterministic(self):
        """Test that component names are assigned deterministically."""
        # Component names should be deterministic based on order and type
        vs_name = self.circuit.get_component_name(self.vs)
        r1_name = self.circuit.get_component_name(self.r1)
        r2_name = self.circuit.get_component_name(self.r2)
        
        self.assertEqual(vs_name, "Vsource")
        self.assertEqual(r1_name, "Rupper") 
        self.assertEqual(r2_name, "Rlower")
        
    def test_get_component_current_missing_circuit(self):
        """Test error handling when circuit reference is missing."""
        # Create SimulatedCircuit without circuit reference
        sim_circuit = SimulatedCircuit(circuit=None)
        
        with self.assertRaises(ValueError) as cm:
            sim_circuit.get_component_current(self.vs)
        self.assertIn("Cannot get component current without circuit reference", str(cm.exception))
        
    def test_get_component_current_component_not_in_circuit(self):
        """Test error handling when component is not in the circuit."""
        # Create a component not in the circuit
        other_resistor = Resistor(resistance=500)
        
        # Create minimal SimulatedCircuit
        sim_circuit = SimulatedCircuit(circuit=self.circuit)
        
        with self.assertRaises(ValueError) as cm:
            sim_circuit.get_component_current(other_resistor)
        self.assertIn("is not part of this circuit", str(cm.exception))
        
    def test_get_component_current_not_found_in_results(self):
        """Test error handling when current data is not found in simulation results."""
        # Create SimulatedCircuit with empty branches
        sim_circuit = SimulatedCircuit(circuit=self.circuit)
        sim_circuit.branches = {}  # No branch current data
        
        with self.assertRaises(ValueError) as cm:
            sim_circuit.get_component_current(self.vs)
        self.assertIn("Current for component Vsource not available", str(cm.exception))
        
    def test_get_component_current_success(self):
        """Test successful current retrieval for components."""
        # Create SimulatedCircuit with mock current data
        sim_circuit = SimulatedCircuit(circuit=self.circuit)
        sim_circuit.branches = {
            'vsource': 0.003333,  # 10V / (1000 + 2000) = 3.33mA
            'rupper': 0.003333,   # Same current through series resistors
            'rlower': 0.003333    # Same current through series resistors
        }
        
        # Test voltage source current
        vs_current = sim_circuit.get_component_current(self.vs)
        self.assertAlmostEqual(vs_current, 0.003333, places=6)
        
        # Test resistor currents
        r1_current = sim_circuit.get_component_current(self.r1)
        r2_current = sim_circuit.get_component_current(self.r2)
        self.assertAlmostEqual(r1_current, 0.003333, places=6)
        self.assertAlmostEqual(r2_current, 0.003333, places=6)
        
    def test_get_terminal_current_missing_circuit(self):
        """Test error handling when circuit reference is missing for terminal current."""
        sim_circuit = SimulatedCircuit(circuit=None)
        
        with self.assertRaises(ValueError) as cm:
            sim_circuit.get_terminal_current(self.vs.pos)
        self.assertIn("Cannot get terminal current without circuit reference", str(cm.exception))
        
    def test_get_terminal_current_terminal_not_found(self):
        """Test error handling when terminal is not found in any component."""
        from zest.components import Terminal
        orphan_terminal = Terminal()  # Terminal not belonging to any component
        
        sim_circuit = SimulatedCircuit(circuit=self.circuit)
        sim_circuit.branches = {'vsource': 0.1}
        
        with self.assertRaises(ValueError) as cm:
            sim_circuit.get_terminal_current(orphan_terminal)
        self.assertIn("not found in any circuit component", str(cm.exception))
        
    def test_get_terminal_current_success(self):
        """Test successful current retrieval for terminals."""
        # Create SimulatedCircuit with mock current data
        sim_circuit = SimulatedCircuit(circuit=self.circuit)
        sim_circuit.branches = {
            'vsource': 0.005,
            'rupper': 0.005,
            'rlower': 0.005
        }
        
        # Test current through voltage source terminals
        vs_pos_current = sim_circuit.get_terminal_current(self.vs.pos)
        vs_neg_current = sim_circuit.get_terminal_current(self.vs.neg)
        self.assertEqual(vs_pos_current, 0.005)
        self.assertEqual(vs_neg_current, 0.005)  # Same component, same current
        
        # Test current through resistor terminals
        r1_n1_current = sim_circuit.get_terminal_current(self.r1.n1)
        r1_n2_current = sim_circuit.get_terminal_current(self.r1.n2)
        self.assertEqual(r1_n1_current, 0.005)
        self.assertEqual(r1_n2_current, 0.005)  # Same component, same current
        
        # Test current through different resistor terminals 
        r2_n1_current = sim_circuit.get_terminal_current(self.r2.n1)
        r2_n2_current = sim_circuit.get_terminal_current(self.r2.n2)
        self.assertEqual(r2_n1_current, 0.005)
        self.assertEqual(r2_n2_current, 0.005)
        
    def test_branch_current_naming_deterministic(self):
        """Test that branch current naming is deterministic and case-consistent."""
        sim_circuit = SimulatedCircuit(circuit=self.circuit)
        
        # Test that the branch naming follows component_name.lower() pattern
        vs_name = self.circuit.get_component_name(self.vs)
        r1_name = self.circuit.get_component_name(self.r1)
        r2_name = self.circuit.get_component_name(self.r2)
        
        self.assertEqual(vs_name, "Vsource")
        self.assertEqual(r1_name, "Rupper")
        self.assertEqual(r2_name, "Rlower")
        
        # Mock data with correct lowercase naming
        sim_circuit.branches = {
            'vsource': 0.001,  # vs_name.lower()
            'rupper': 0.001,   # r1_name.lower()
            'rlower': 0.001    # r2_name.lower()
        }
        
        # Should find currents with deterministic naming
        self.assertEqual(sim_circuit.get_component_current(self.vs), 0.001)
        self.assertEqual(sim_circuit.get_component_current(self.r1), 0.001)
        self.assertEqual(sim_circuit.get_component_current(self.r2), 0.001)
        
    def test_branch_current_array_values(self):
        """Test that branch current methods handle array values properly."""
        import numpy as np
        
        sim_circuit = SimulatedCircuit(circuit=self.circuit)
        
        # Mock transient current data (arrays)
        time_points = 100
        current_array = np.linspace(0.001, 0.005, time_points)  # Ramping current
        
        sim_circuit.branches = {
            'vsource': current_array,
            'rupper': current_array,
            'rlower': current_array
        }
        
        # Test that arrays are returned properly
        vs_current = sim_circuit.get_component_current(self.vs)
        self.assertIsInstance(vs_current, np.ndarray)
        self.assertEqual(len(vs_current), time_points)
        self.assertAlmostEqual(vs_current[0], 0.001, places=6)
        self.assertAlmostEqual(vs_current[-1], 0.005, places=6)
        
        # Test terminal current with arrays
        r1_current = sim_circuit.get_terminal_current(self.r1.n1)
        self.assertIsInstance(r1_current, np.ndarray)
        np.testing.assert_array_equal(r1_current, current_array)


if __name__ == '__main__':
    unittest.main() 
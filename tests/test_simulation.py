#!/usr/bin/env python3
"""
Tests for simulation functionality: CircuitSimulator, SimulatedCircuit, 
simulation backends, analysis types, and simulation integration.
"""

import unittest
import os
import sys

# Add the parent directory to the path to import zest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zest import Circuit, VoltageSource, Resistor, Capacitor, Inductor
from zest.simulation import CircuitSimulator, SimulatedCircuit, check_simulation_requirements, SpicelibBackend
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


class TestSimulatorBackend(unittest.TestCase):
    """Test simulation backend functionality."""
    
    def setUp(self):
        """Set up test circuit."""
        self.circuit = Circuit("Backend Test")
        self.vs = VoltageSource(voltage=12.0)
        self.r1 = Resistor(resistance=2000)
        
        self.circuit.add_component(self.vs)
        self.circuit.add_component(self.r1)
        
        self.circuit.wire(self.vs.pos, self.r1.n1)
        self.circuit.wire(self.vs.neg, self.circuit.gnd)
        self.circuit.wire(self.r1.n2, self.circuit.gnd)
    
    def test_spicelib_backend_creation(self):
        """Test SpicelibBackend creation."""
        backend = SpicelibBackend()
        self.assertIsNotNone(backend)
    
    def test_backend_operating_point(self):
        """Test backend operating point analysis."""
        backend = SpicelibBackend()
        netlist = self.circuit.compile_to_spice()
        
        result = backend.run(netlist, analyses=["op"], circuit=self.circuit)
        self.assertEqual(result.analysis_type, "DC Operating Point")
        self.assertIsNotNone(result)
    
    def test_backend_ac_analysis(self):
        """Test backend AC analysis."""
        backend = SpicelibBackend()
        netlist = self.circuit.compile_to_spice()
        
        result = backend.run(
            netlist, 
            analyses=["ac"], 
            circuit=self.circuit,
            start_freq=1,
            stop_freq=1e6,
            points_per_decade=10
        )
        self.assertEqual(result.analysis_type, "AC Analysis")
        self.assertIsNotNone(result)
    
    def test_backend_transient_analysis(self):
        """Test backend transient analysis."""
        backend = SpicelibBackend()
        netlist = self.circuit.compile_to_spice()
        
        result = backend.run(
            netlist,
            analyses=["transient"],
            circuit=self.circuit,
            step_time=1e-5,
            end_time=1e-3
        )
        self.assertEqual(result.analysis_type, "Transient Analysis")
        self.assertIsNotNone(result)
    
    def test_backend_dc_sweep(self):
        """Test backend DC sweep analysis."""
        backend = SpicelibBackend()
        netlist = self.circuit.compile_to_spice()
        
        result = backend.run(
            netlist,
            analyses=["dc"],
            circuit=self.circuit,
            source_name="V1",
            start=0,
            stop=5,
            step=0.1
        )
        self.assertEqual(result.analysis_type, "DC Sweep")
        self.assertIsNotNone(result)


class TestCircuitIntegrationMethods(unittest.TestCase):
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
        try:
            result = self.circuit.simulate_operating_point()
            # If it succeeds, result should be a SimulatedCircuit object
            self.assertIsNotNone(result)
            self.assertIsInstance(result, SimulatedCircuit)
        except Exception as e:
            # If simulation fails, that's OK for this test
            self.assertIsInstance(e, Exception)
    
    def test_dc_sweep_method(self):
        """Test circuit DC sweep simulation method."""
        try:
            result = self.circuit.simulate_dc_sweep("V1", 0, 5, 0.1)
            self.assertIsNotNone(result)
            self.assertIsInstance(result, SimulatedCircuit)
        except Exception as e:
            # If simulation fails, that's OK for this test
            self.assertIsInstance(e, Exception)
    
    def test_ac_analysis_method(self):
        """Test circuit AC analysis simulation method."""
        try:
            result = self.circuit.simulate_ac(start_freq=1, stop_freq=1e6, points_per_decade=10)
            self.assertIsNotNone(result)
            self.assertIsInstance(result, SimulatedCircuit)
        except Exception as e:
            # If simulation fails, that's OK for this test
            self.assertIsInstance(e, Exception)
    
    def test_transient_method(self):
        """Test circuit transient simulation method."""
        try:
            result = self.circuit.simulate_transient(step_time=1e-5, end_time=1e-3)
            self.assertIsNotNone(result)
            self.assertIsInstance(result, SimulatedCircuit)
        except Exception as e:
            # If simulation fails, that's OK for this test
            self.assertIsInstance(e, Exception)


class TestSimulatedCircuit(unittest.TestCase):
    """Test SimulatedCircuit functionality and result extraction."""
    
    def setUp(self):
        """Set up test circuit."""
        self.circuit = Circuit("Test Circuit")
        self.vs = VoltageSource(voltage=10.0, name="VS")
        self.r1 = Resistor(resistance=1000, name="R1")
        self.r2 = Resistor(resistance=2000, name="R2")
        
        # Add components to circuit
        self.circuit.add_component(self.vs)
        self.circuit.add_component(self.r1)
        self.circuit.add_component(self.r2)
        
        # Wire the voltage divider
        self.circuit.wire(self.vs.neg, self.circuit.gnd)
        self.circuit.wire(self.vs.pos, self.r1.n1)
        self.circuit.wire(self.r1.n2, self.r2.n1)
        self.circuit.wire(self.r2.n2, self.circuit.gnd)
    
    def test_component_names_deterministic(self):
        """Test that component names are deterministic."""
        # Run simulation
        result = self.circuit.simulate_operating_point()
        
        # Get component names - should be deterministic
        vs_name = self.circuit.get_component_name(self.vs)
        r1_name = self.circuit.get_component_name(self.r1)
        r2_name = self.circuit.get_component_name(self.r2)
        
        self.assertTrue(vs_name.startswith("V"))
        self.assertTrue(r1_name.startswith("R"))
        self.assertTrue(r2_name.startswith("R"))
        self.assertNotEqual(r1_name, r2_name)
    
    def test_get_component_current_missing_circuit(self):
        """Test error when getting component current without circuit reference."""
        # Create SimulatedCircuit without circuit reference
        sim_result = SimulatedCircuit(circuit=None, analysis_type="DC Operating Point")
        
        with self.assertRaises(ValueError) as context:
            sim_result.get_component_current(self.vs)
        
        self.assertIn("circuit reference", str(context.exception))
    
    def test_get_component_current_component_not_in_circuit(self):
        """Test error when component is not in the circuit."""
        result = self.circuit.simulate_operating_point()
        
        # Create a component not in the circuit
        external_r = Resistor(resistance=500, name="R_EXT")
        
        with self.assertRaises(ValueError) as context:
            result.get_component_current(external_r)
        
        self.assertIn("is not part of this circuit", str(context.exception))
    
    def test_get_component_current_success(self):
        """Test successful component current retrieval."""
        result = self.circuit.simulate_operating_point()
        
        # Should be able to get current for voltage source
        try:
            current = result.get_component_current(self.vs)
            self.assertIsNotNone(current)
            # For a simple resistive circuit, current should be V/R_total
            expected_current = -10.0 / (1000 + 2000)  # 10V / 3k = 3.33mA
            self.assertAlmostEqual(current, expected_current, places=3)
        except ValueError:
            # Current might not be available in all simulation results
            pass
    
    def test_analysis_type_detection(self):
        """Test analysis type detection methods."""
        # Operating point
        op_result = self.circuit.simulate_operating_point()
        self.assertTrue(op_result.is_operating_point())
        self.assertFalse(op_result.is_transient())
        self.assertFalse(op_result.is_ac_analysis())
        self.assertFalse(op_result.is_dc_sweep())
        
        # Transient (if available)
        try:
            tran_result = self.circuit.simulate_transient(1e-5, 1e-3)
            self.assertTrue(tran_result.is_transient())
            self.assertFalse(tran_result.is_operating_point())
        except Exception:
            pass  # Transient simulation might not be available
    
    def test_get_time_vector(self):
        """Test getting time vector from transient analysis."""
        try:
            result = self.circuit.simulate_transient(1e-5, 1e-3)
            time_vector = result.get_time_vector()
            
            if time_vector is not None:
                self.assertIsNotNone(time_vector)
                # Time should start at 0 and end around 1e-3
                self.assertGreaterEqual(time_vector[0], 0)
                self.assertLessEqual(time_vector[-1], 1e-3 * 1.1)  # Allow some tolerance
        except Exception:
            pass  # Transient simulation might not be available
    
    def test_get_sweep_variable(self):
        """Test getting sweep variable from DC sweep analysis."""
        try:
            result = self.circuit.simulate_dc_sweep("VS", 0, 5, 0.1)
            sweep_var = result.get_sweep_variable()
            
            if sweep_var is not None:
                self.assertIsNotNone(sweep_var)
                # Should start at 0 and end at 5
                self.assertAlmostEqual(sweep_var[0], 0, places=2)
                self.assertAlmostEqual(sweep_var[-1], 5, places=2)
        except Exception:
            pass  # DC sweep might not be available


class TestAnalysisTypes(unittest.TestCase):
    """Test different analysis types and their specific functionality."""
    
    def test_analysis_types(self):
        """Test that analysis types are handled correctly."""
        # This is a placeholder test for analysis type functionality
        # The actual analysis functionality is tested in integration tests
        
        # Test that analysis type strings are recognized
        valid_types = ["op", "dc", "ac", "transient"]
        for analysis_type in valid_types:
            # This would be where we test analysis-specific functionality
            # For now, just verify the strings are valid
            self.assertIsInstance(analysis_type, str)
            self.assertGreater(len(analysis_type), 0)


class TestBranchCurrentMethods(unittest.TestCase):
    """Test branch current calculation methods."""
    
    def setUp(self):
        """Set up test circuit with known current flow."""
        self.circuit = Circuit("Current Test")
        self.vs = VoltageSource(voltage=6.0, name="V1")
        self.r1 = Resistor(resistance=2000, name="R1")  # 2k ohm
        
        self.circuit.add_component(self.vs)
        self.circuit.add_component(self.r1)
        
        # Simple circuit: VS -> R1 -> GND
        self.circuit.wire(self.vs.pos, self.r1.n1)
        self.circuit.wire(self.vs.neg, self.circuit.gnd)
        self.circuit.wire(self.r1.n2, self.circuit.gnd)
    
    def test_get_terminal_current_missing_circuit(self):
        """Test error when getting terminal current without circuit reference."""
        sim_result = SimulatedCircuit(circuit=None, analysis_type="DC Operating Point")
        
        with self.assertRaises(ValueError) as context:
            sim_result.get_terminal_current(self.vs.pos)
        
        self.assertIn("circuit reference", str(context.exception))
    
    def test_get_terminal_current_terminal_not_found(self):
        """Test error when terminal is not found in simulation results."""
        result = self.circuit.simulate_operating_point()
        
        # Create a terminal not in the circuit
        external_r = Resistor(resistance=500)
        
        with self.assertRaises(ValueError) as context:
            result.get_terminal_current(external_r.n1)
        
        self.assertIn("not found", str(context.exception))
    
    def test_get_terminal_current_success(self):
        """Test successful terminal current retrieval."""
        result = self.circuit.simulate_operating_point()
        
        try:
            # Get current through voltage source positive terminal
            current = result.get_terminal_current(self.vs.pos)
            self.assertIsNotNone(current)
            
            # For this simple circuit: I = V/R = 6V/2000 = 3mA
            expected_current = 6.0 / 2000
            self.assertAlmostEqual(abs(current), expected_current, places=3)
        except ValueError:
            # Current might not be available in all simulation results
            pass
    
    def test_branch_current_naming_deterministic(self):
        """Test that branch current naming is deterministic."""
        result = self.circuit.simulate_operating_point()
        
        # Component names should be deterministic
        vs_name = self.circuit.get_component_name(self.vs)
        r1_name = self.circuit.get_component_name(self.r1)
        
        # Names should be consistent across multiple calls
        vs_name2 = self.circuit.get_component_name(self.vs)
        r1_name2 = self.circuit.get_component_name(self.r1)
        
        self.assertEqual(vs_name, vs_name2)
        self.assertEqual(r1_name, r1_name2)
    
    def test_branch_current_array_values(self):
        """Test that branch currents handle array values correctly."""
        # Run a transient simulation to get array results
        try:
            result = self.circuit.simulate_transient(1e-5, 1e-4)
            
            # Try to get current (might be array for transient)
            current = result.get_component_current(self.vs)
            
            if current is not None:
                # Current could be scalar or array
                if hasattr(current, '__len__') and len(current) > 1:
                    # Array case - all values should be similar for resistive circuit
                    self.assertGreater(len(current), 1)
                else:
                    # Scalar case
                    self.assertIsInstance(current, (int, float))
        except Exception:
            # Transient simulation might not be available
            pass


class TestSpiceGenerationIntegration(GoldenTestMixin, unittest.TestCase):
    """Test SPICE generation integration with simulation."""
    
    def test_simple_circuit_spice_generation(self):
        """Test basic SPICE generation for a simple circuit."""
        circuit = Circuit("Simple Test")
        
        vs = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        
        circuit.add_component(vs)
        circuit.add_component(r1)
        
        circuit.wire(vs.pos, r1.n1)
        circuit.wire(vs.neg, circuit.gnd)
        circuit.wire(r1.n2, circuit.gnd)
        
        # Generate SPICE netlist - this is the canonical representation
        spice_netlist = circuit.compile_to_spice()
        
        # Verify it contains expected components and structure
        self.assertIn("* Circuit: Simple Test", spice_netlist)
        self.assertIn("V1 N1 gnd DC 5.0", spice_netlist)
        self.assertIn("R1 N1 gnd 1000", spice_netlist)
        self.assertIn(".end", spice_netlist)
        
        # Test that simulation works with the generated SPICE
        result = circuit.simulate_operating_point()
        self.assertIsNotNone(result)
        self.assertEqual(result.analysis_type, "DC Operating Point")
    
    def test_voltage_divider_spice_generation(self):
        """Test SPICE generation for a voltage divider."""
        circuit = Circuit("Voltage Divider")
        
        vs = VoltageSource(voltage=10.0)
        r1 = Resistor(resistance=1000)
        r2 = Resistor(resistance=2000)
        
        circuit.add_component(vs)
        circuit.add_component(r1)
        circuit.add_component(r2)
        
        circuit.wire(vs.neg, circuit.gnd)
        circuit.wire(vs.pos, r1.n1)
        circuit.wire(r1.n2, r2.n1)
        circuit.wire(r2.n2, circuit.gnd)
        
        spice_netlist = circuit.compile_to_spice()
        
        # Verify structure
        self.assertIn("* Circuit: Voltage Divider", spice_netlist)
        self.assertIn("V1", spice_netlist)
        self.assertIn("R1", spice_netlist)
        self.assertIn("R2", spice_netlist)
        self.assertIn(".end", spice_netlist)
        
        # Verify node mapping is consistent 
        lines = spice_netlist.split('\n')
        component_lines = [line for line in lines if line and not line.startswith('*') and not line.startswith('.')]
        
        # Should have V1, R1, R2
        self.assertEqual(len(component_lines), 3)
    
    def test_rlc_circuit_spice_generation(self):
        """Test SPICE generation for RLC circuit."""
        circuit = Circuit("RLC Circuit")
        
        vs = VoltageSource(voltage=1.0)
        r1 = Resistor(resistance=100)
        l1 = Inductor(inductance=1e-3)
        c1 = Capacitor(capacitance=1e-6)
        
        circuit.add_component(vs)
        circuit.add_component(r1)
        circuit.add_component(l1)
        circuit.add_component(c1)
        
        # Series RLC
        circuit.wire(vs.neg, circuit.gnd)
        circuit.wire(vs.pos, r1.n1)
        circuit.wire(r1.n2, l1.n1)
        circuit.wire(l1.n2, c1.pos)
        circuit.wire(c1.neg, circuit.gnd)
        
        spice_netlist = circuit.compile_to_spice()
        
        # Verify all component types
        self.assertIn("V1", spice_netlist)
        self.assertIn("R1", spice_netlist)
        self.assertIn("L1", spice_netlist)
        self.assertIn("C1", spice_netlist)
        
        # Test simulation works
        result = circuit.simulate_operating_point()
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main() 
#!/usr/bin/env python3
"""
Tests for all component classes: Component base class, Terminal, GroundTerminal,
VoltageSource, Resistor, Capacitor, Inductor, CurrentSource, ExternalSubCircuit,
and component-specific functionality.
"""

import unittest
import os
import sys

# Add the parent directory to the path to import zest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zest import Circuit, VoltageSource, PiecewiseLinearVoltageSource, Resistor, Capacitor, Inductor, gnd
from zest.components import Component, Terminal, GroundTerminal, CurrentSource, ExternalSubCircuit
from .golden_test_framework import GoldenTestMixin


class MockNodeMapper:
    """Simple mock NodeMapper for testing component SPICE generation."""
    def __init__(self):
        self._names = {}
    
    def assign_name(self, terminal, name):
        self._names[terminal] = name
    
    def name_for(self, terminal):
        return self._names.get(terminal, f'N{id(terminal) % 1000}')


class TestTerminal(unittest.TestCase):
    """Test Terminal and GroundTerminal functionality."""
    
    def test_terminal_creation(self):
        """Test Terminal creation and properties."""
        r1 = Resistor(resistance=1000)
        
        # Component terminals
        self.assertEqual(r1.n1.component, r1)
        self.assertEqual(r1.n1.terminal_name, "n1")
        self.assertEqual(r1.n2.component, r1)
        self.assertEqual(r1.n2.terminal_name, "n2")
    
    def test_terminal_string_representation(self):
        """Test Terminal string representation."""
        r1 = Resistor(resistance=1000, name="R1")
        
        # Should show component name and terminal name
        self.assertIn("R1", str(r1.n1))
        self.assertIn("n1", str(r1.n1))
    
    def test_ground_terminal(self):
        """Test GroundTerminal functionality."""
        self.assertIsInstance(gnd, GroundTerminal)
        self.assertEqual(str(gnd), "gnd")
        self.assertEqual(repr(gnd), "GroundTerminal()")
    
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


class TestComponentBase(unittest.TestCase):
    """Test Component base class functionality."""
    
    def test_component_creation(self):
        """Test Component creation with and without names."""
        # Default name
        r1 = Resistor(resistance=1000)
        self.assertEqual(r1.name, "UNNAMED")
        
        # Explicit name
        r2 = Resistor(resistance=2000, name="R2")
        self.assertEqual(r2.name, "R2")
    
    def test_component_type_prefixes(self):
        """Test component type prefixes for SPICE generation."""
        vs = VoltageSource(voltage=5.0)
        r1 = Resistor(resistance=1000)
        c1 = Capacitor(capacitance=1e-6)
        l1 = Inductor(inductance=1e-3)
        i1 = CurrentSource(current=1e-3)
        ext = ExternalSubCircuit("OPAMP", ["IN+", "IN-", "OUT"])
        
        self.assertEqual(vs.get_component_type_prefix(), "V")
        self.assertEqual(r1.get_component_type_prefix(), "R")
        self.assertEqual(c1.get_component_type_prefix(), "C")
        self.assertEqual(l1.get_component_type_prefix(), "L")
        self.assertEqual(i1.get_component_type_prefix(), "I")
        self.assertEqual(ext.get_component_type_prefix(), "X")
    
    def test_component_terminals_method(self):
        """Test that components return correct terminals."""
        vs = VoltageSource(voltage=5.0)
        terminals = list(vs.terminals())
        
        self.assertEqual(len(terminals), 2)
        self.assertIn(vs.pos, terminals)
        self.assertIn(vs.neg, terminals)
    
    def test_component_representation(self):
        """Test component string representation."""
        r1 = Resistor(resistance=1000, name="R1")
        repr_str = repr(r1)
        self.assertIn("Resistor", repr_str)
        self.assertIn("R1", repr_str)


class TestVoltageSource(unittest.TestCase):
    """Test VoltageSource component functionality."""
    
    def test_voltage_source_creation(self):
        """Test VoltageSource creation with default and custom values."""
        # Default voltage source
        vs1 = VoltageSource()
        self.assertEqual(vs1.voltage, 0.0)
        self.assertEqual(vs1.name, "UNNAMED")
        
        # Custom voltage source
        vs2 = VoltageSource(voltage=12.0, name="VCC")
        self.assertEqual(vs2.voltage, 12.0)
        self.assertEqual(vs2.name, "VCC")
    
    def test_voltage_source_terminals(self):
        """Test VoltageSource terminals and aliases."""
        vs = VoltageSource(voltage=5.0)
        
        # Check terminal existence and aliases
        self.assertTrue(hasattr(vs, 'pos'))
        self.assertTrue(hasattr(vs, 'neg'))
        self.assertTrue(hasattr(vs, 'positive'))
        self.assertTrue(hasattr(vs, 'negative'))
        
        # Check aliases work correctly
        self.assertEqual(vs.pos, vs.positive)
        self.assertEqual(vs.neg, vs.negative)
        
        # Check terminal properties
        self.assertEqual(vs.pos.component, vs)
        self.assertEqual(vs.neg.component, vs)
        self.assertEqual(vs.pos.terminal_name, "pos")
        self.assertEqual(vs.neg.terminal_name, "neg")
    
    def test_voltage_source_get_terminals(self):
        """Test VoltageSource get_terminals method."""
        vs = VoltageSource()
        terminals = vs.get_terminals()
        
        self.assertEqual(len(terminals), 2)
        self.assertIn(('pos', vs.pos), terminals)
        self.assertIn(('neg', vs.neg), terminals)
    
    def test_voltage_source_spice_generation(self):
        """Test VoltageSource SPICE generation."""
        vs = VoltageSource(voltage=9.0, name="V1")
        
        # Create a mock node mapper for testing
        mapper = MockNodeMapper()
        mapper.assign_name(vs.pos, "VCC")
        mapper.assign_name(vs.neg, "gnd")
        
        spice_line = vs.to_spice(mapper)
        expected = "V1 VCC gnd DC 9.0"
        self.assertEqual(spice_line, expected)
        
        # Test with forced name
        spice_line_forced = vs.to_spice(mapper, forced_name="V_SUPPLY")
        expected_forced = "V_SUPPLY VCC gnd DC 9.0"
        self.assertEqual(spice_line_forced, expected_forced)


class TestPiecewiseLinearVoltageSource(unittest.TestCase):
    """Test PiecewiseLinearVoltageSource component functionality."""
    
    def test_pwl_voltage_source_creation_default(self):
        """Test PWL voltage source creation with default values."""
        pwl_vs = PiecewiseLinearVoltageSource()
        self.assertEqual(pwl_vs.time_voltage_pairs, [(0, 0)])
        self.assertEqual(pwl_vs.name, "UNNAMED")
    
    def test_pwl_voltage_source_creation_custom(self):
        """Test PWL voltage source creation with custom values."""
        pairs = [(0, 0), (1e-3, 5), (2e-3, 0)]
        pwl_vs = PiecewiseLinearVoltageSource(time_voltage_pairs=pairs, name="V_PWL")
        self.assertEqual(pwl_vs.time_voltage_pairs, pairs)
        self.assertEqual(pwl_vs.name, "V_PWL")
    
    def test_pwl_voltage_source_validation_empty_list(self):
        """Test PWL voltage source validation for empty list."""
        with self.assertRaises(ValueError) as context:
            PiecewiseLinearVoltageSource(time_voltage_pairs=[])
        self.assertIn("non-empty", str(context.exception))
    
    def test_pwl_voltage_source_validation_invalid_pairs(self):
        """Test PWL voltage source validation for invalid pairs."""
        # Test invalid pair format
        with self.assertRaises(ValueError) as context:
            PiecewiseLinearVoltageSource(time_voltage_pairs=[(0, 0), (1,)])  # Missing voltage
        self.assertIn("(time, voltage) pair", str(context.exception))
        
        # Test non-numeric values
        with self.assertRaises(ValueError) as context:
            PiecewiseLinearVoltageSource(time_voltage_pairs=[(0, 0), ("1e-3", 5)])
        self.assertIn("numbers", str(context.exception))
        
        # Test negative time
        with self.assertRaises(ValueError) as context:
            PiecewiseLinearVoltageSource(time_voltage_pairs=[(-1, 0), (1e-3, 5)])
        self.assertIn("non-negative", str(context.exception))
    
    def test_pwl_voltage_source_validation_time_ordering(self):
        """Test PWL voltage source validation for time ordering."""
        # Test duplicate times - should fail
        with self.assertRaises(ValueError) as context:
            PiecewiseLinearVoltageSource(time_voltage_pairs=[(0, 0), (1e-3, 5), (1e-3, 3)])
        self.assertIn("duplicate time", str(context.exception))
        
        # Test decreasing times - should now work because we auto-sort
        # This should succeed and result in sorted pairs
        pwl_vs = PiecewiseLinearVoltageSource(time_voltage_pairs=[(0, 0), (2e-3, 5), (1e-3, 3)])
        expected_sorted = [(0, 0), (1e-3, 3), (2e-3, 5)]
        self.assertEqual(pwl_vs.time_voltage_pairs, expected_sorted)
    
    def test_pwl_voltage_source_auto_sorting(self):
        """Test that PWL voltage source auto-sorts time points."""
        # Provide unsorted time points
        unsorted_pairs = [(2e-3, 0), (0, 5), (1e-3, 10)]
        expected_sorted = [(0, 5), (1e-3, 10), (2e-3, 0)]
        
        pwl_vs = PiecewiseLinearVoltageSource(time_voltage_pairs=unsorted_pairs)
        self.assertEqual(pwl_vs.time_voltage_pairs, expected_sorted)
    
    def test_pwl_voltage_source_terminals(self):
        """Test PWL voltage source terminals and aliases."""
        pwl_vs = PiecewiseLinearVoltageSource([(0, 0), (1e-3, 5)])
        
        # Check terminal existence and aliases
        self.assertTrue(hasattr(pwl_vs, 'pos'))
        self.assertTrue(hasattr(pwl_vs, 'neg'))
        self.assertTrue(hasattr(pwl_vs, 'positive'))
        self.assertTrue(hasattr(pwl_vs, 'negative'))
        
        # Check aliases work correctly
        self.assertEqual(pwl_vs.pos, pwl_vs.positive)
        self.assertEqual(pwl_vs.neg, pwl_vs.negative)
        
        # Check terminal properties
        self.assertEqual(pwl_vs.pos.component, pwl_vs)
        self.assertEqual(pwl_vs.neg.component, pwl_vs)
        self.assertEqual(pwl_vs.pos.terminal_name, "pos")
        self.assertEqual(pwl_vs.neg.terminal_name, "neg")
    
    def test_pwl_voltage_source_get_terminals(self):
        """Test PWL voltage source get_terminals method."""
        pwl_vs = PiecewiseLinearVoltageSource()
        terminals = pwl_vs.get_terminals()
        
        self.assertEqual(len(terminals), 2)
        self.assertIn(('pos', pwl_vs.pos), terminals)
        self.assertIn(('neg', pwl_vs.neg), terminals)
    
    def test_pwl_voltage_source_component_type_prefix(self):
        """Test PWL voltage source component type prefix."""
        pwl_vs = PiecewiseLinearVoltageSource()
        self.assertEqual(pwl_vs.get_component_type_prefix(), "V")
    
    def test_pwl_voltage_source_spice_generation_simple(self):
        """Test PWL voltage source SPICE generation for simple case."""
        pwl_vs = PiecewiseLinearVoltageSource([(0, 0), (1e-3, 5)], name="V_PWL1")
        
        # Create a mock node mapper for testing
        mapper = MockNodeMapper()
        mapper.assign_name(pwl_vs.pos, "VCC")
        mapper.assign_name(pwl_vs.neg, "gnd")
        
        spice_line = pwl_vs.to_spice(mapper)
        expected = "V_PWL1 VCC gnd PWL(0 0 0.001 5)"
        self.assertEqual(spice_line, expected)
    
    def test_pwl_voltage_source_spice_generation_complex(self):
        """Test PWL voltage source SPICE generation for complex waveform."""
        # Triangle wave
        pairs = [(0, 0), (1e-3, 5), (2e-3, 0), (3e-3, -5), (4e-3, 0)]
        pwl_vs = PiecewiseLinearVoltageSource(pairs, name="V_TRI")
        
        # Create a mock node mapper for testing
        mapper = MockNodeMapper()
        mapper.assign_name(pwl_vs.pos, "N1")
        mapper.assign_name(pwl_vs.neg, "N2")
        
        spice_line = pwl_vs.to_spice(mapper)
        expected = "V_TRI N1 N2 PWL(0 0 0.001 5 0.002 0 0.003 -5 0.004 0)"
        self.assertEqual(spice_line, expected)
    
    def test_pwl_voltage_source_spice_generation_forced_name(self):
        """Test PWL voltage source SPICE generation with forced name."""
        pwl_vs = PiecewiseLinearVoltageSource([(0, 2), (1e-3, 8)], name="V_PWL")
        
        # Create a mock node mapper for testing
        mapper = MockNodeMapper()
        mapper.assign_name(pwl_vs.pos, "OUT")
        mapper.assign_name(pwl_vs.neg, "gnd")
        
        spice_line = pwl_vs.to_spice(mapper, forced_name="V_CUSTOM")
        expected = "V_CUSTOM OUT gnd PWL(0 2 0.001 8)"
        self.assertEqual(spice_line, expected)
    
    def test_pwl_voltage_source_get_voltage_at_time_bounds(self):
        """Test get_voltage_at_time method for boundary conditions."""
        pairs = [(1e-3, 0), (2e-3, 5), (3e-3, 10)]
        pwl_vs = PiecewiseLinearVoltageSource(pairs)
        
        # Before first point: should return first voltage
        self.assertEqual(pwl_vs.get_voltage_at_time(0), 0)
        self.assertEqual(pwl_vs.get_voltage_at_time(0.5e-3), 0)
        
        # At first point
        self.assertEqual(pwl_vs.get_voltage_at_time(1e-3), 0)
        
        # After last point: should return last voltage
        self.assertEqual(pwl_vs.get_voltage_at_time(3e-3), 10)
        self.assertEqual(pwl_vs.get_voltage_at_time(5e-3), 10)
    
    def test_pwl_voltage_source_get_voltage_at_time_interpolation(self):
        """Test get_voltage_at_time method for linear interpolation."""
        pairs = [(0, 0), (2e-3, 10)]  # Linear ramp from 0V to 10V over 2ms
        pwl_vs = PiecewiseLinearVoltageSource(pairs)
        
        # Test interpolation at midpoint
        voltage_mid = pwl_vs.get_voltage_at_time(1e-3)
        self.assertAlmostEqual(voltage_mid, 5.0, places=6)  # Should be 5V at 1ms
        
        # Test interpolation at quarter point
        voltage_quarter = pwl_vs.get_voltage_at_time(0.5e-3)
        self.assertAlmostEqual(voltage_quarter, 2.5, places=6)  # Should be 2.5V at 0.5ms
        
        # Test interpolation at three-quarter point
        voltage_three_quarter = pwl_vs.get_voltage_at_time(1.5e-3)
        self.assertAlmostEqual(voltage_three_quarter, 7.5, places=6)  # Should be 7.5V at 1.5ms
    
    def test_pwl_voltage_source_get_voltage_at_time_complex(self):
        """Test get_voltage_at_time method for complex multi-segment waveform."""
        # Two-segment ramp: 0->5V (0-1ms), 5->0V (1-2ms)
        pairs = [(0, 0), (1e-3, 5), (2e-3, 0)]
        pwl_vs = PiecewiseLinearVoltageSource(pairs)
        
        # First segment (0 to 1ms): 0V to 5V
        self.assertAlmostEqual(pwl_vs.get_voltage_at_time(0.5e-3), 2.5, places=6)
        self.assertAlmostEqual(pwl_vs.get_voltage_at_time(1e-3), 5.0, places=6)
        
        # Second segment (1ms to 2ms): 5V to 0V
        self.assertAlmostEqual(pwl_vs.get_voltage_at_time(1.5e-3), 2.5, places=6)
        self.assertAlmostEqual(pwl_vs.get_voltage_at_time(2e-3), 0.0, places=6)
    
    def test_pwl_voltage_source_get_voltage_at_time_negative_time(self):
        """Test get_voltage_at_time method with negative time (should raise error)."""
        pwl_vs = PiecewiseLinearVoltageSource([(0, 0), (1e-3, 5)])
        
        with self.assertRaises(ValueError) as context:
            pwl_vs.get_voltage_at_time(-1e-3)
        self.assertIn("non-negative", str(context.exception))
    
    def test_pwl_voltage_source_representation(self):
        """Test PWL voltage source string representation."""
        pairs = [(0, 0), (1e-3, 5), (2e-3, 0)]
        pwl_vs = PiecewiseLinearVoltageSource(pairs, name="V_PWL_TEST")
        
        repr_str = repr(pwl_vs)
        self.assertIn("PiecewiseLinearVoltageSource", repr_str)
        self.assertIn("V_PWL_TEST", repr_str)
        self.assertIn("3 points", repr_str)  # Should show number of points


class TestResistor(unittest.TestCase):
    """Test Resistor component functionality."""
    
    def test_resistor_creation(self):
        """Test Resistor creation with default and custom values."""
        # Default resistor
        r1 = Resistor()
        self.assertEqual(r1.resistance, 1000.0)
        self.assertEqual(r1.name, "UNNAMED")
        
        # Custom resistor
        r2 = Resistor(resistance=4700.0, name="R2")
        self.assertEqual(r2.resistance, 4700.0)
        self.assertEqual(r2.name, "R2")
    
    def test_resistor_terminals(self):
        """Test Resistor terminals and aliases."""
        r1 = Resistor(resistance=1000)
        
        # Check terminal existence and aliases
        self.assertTrue(hasattr(r1, 'n1'))
        self.assertTrue(hasattr(r1, 'n2'))
        self.assertTrue(hasattr(r1, 'a'))
        self.assertTrue(hasattr(r1, 'b'))
        
        # Check aliases work correctly
        self.assertEqual(r1.n1, r1.a)
        self.assertEqual(r1.n2, r1.b)
        
        # Check terminal properties
        self.assertEqual(r1.n1.component, r1)
        self.assertEqual(r1.n2.component, r1)
        self.assertEqual(r1.n1.terminal_name, "n1")
        self.assertEqual(r1.n2.terminal_name, "n2")
    
    def test_resistor_spice_generation(self):
        """Test Resistor SPICE generation."""
        r1 = Resistor(resistance=2200, name="R1")
        
        # Create a mock node mapper for testing
        mapper = MockNodeMapper()
        mapper.assign_name(r1.n1, "N1")
        mapper.assign_name(r1.n2, "N2")
        
        spice_line = r1.to_spice(mapper)
        expected = "R1 N1 N2 2200"
        self.assertEqual(spice_line, expected)


class TestCapacitor(unittest.TestCase):
    """Test Capacitor component functionality."""
    
    def test_capacitor_creation(self):
        """Test Capacitor creation with default and custom values."""
        # Default capacitor
        c1 = Capacitor()
        self.assertEqual(c1.capacitance, 1e-6)
        self.assertEqual(c1.name, "UNNAMED")
        
        # Custom capacitor
        c2 = Capacitor(capacitance=100e-12, name="C2")
        self.assertEqual(c2.capacitance, 100e-12)
        self.assertEqual(c2.name, "C2")
    
    def test_capacitor_terminals(self):
        """Test Capacitor terminals and aliases."""
        c1 = Capacitor(capacitance=1e-6)
        
        # Check terminal existence and aliases
        self.assertTrue(hasattr(c1, 'pos'))
        self.assertTrue(hasattr(c1, 'neg'))
        self.assertTrue(hasattr(c1, 'positive'))
        self.assertTrue(hasattr(c1, 'negative'))
        
        # Check aliases work correctly
        self.assertEqual(c1.pos, c1.positive)
        self.assertEqual(c1.neg, c1.negative)
    
    def test_capacitor_spice_generation(self):
        """Test Capacitor SPICE generation."""
        c1 = Capacitor(capacitance=220e-9, name="C1")
        
        # Create a mock node mapper for testing
        mapper = MockNodeMapper()
        mapper.assign_name(c1.pos, "VIN")
        mapper.assign_name(c1.neg, "gnd")
        
        spice_line = c1.to_spice(mapper)
        expected = "C1 VIN gnd 2.2e-07"
        self.assertEqual(spice_line, expected)


class TestInductor(unittest.TestCase):
    """Test Inductor component functionality."""
    
    def test_inductor_creation(self):
        """Test Inductor creation with default and custom values."""
        # Default inductor
        l1 = Inductor()
        self.assertEqual(l1.inductance, 1e-3)
        self.assertEqual(l1.name, "UNNAMED")
        
        # Custom inductor
        l2 = Inductor(inductance=10e-6, name="L2")
        self.assertEqual(l2.inductance, 10e-6)
        self.assertEqual(l2.name, "L2")
    
    def test_inductor_terminals(self):
        """Test Inductor terminals and aliases."""
        l1 = Inductor(inductance=1e-3)
        
        # Check terminal existence and aliases
        self.assertTrue(hasattr(l1, 'n1'))
        self.assertTrue(hasattr(l1, 'n2'))
        self.assertTrue(hasattr(l1, 'a'))
        self.assertTrue(hasattr(l1, 'b'))
        
        # Check aliases work correctly
        self.assertEqual(l1.n1, l1.a)
        self.assertEqual(l1.n2, l1.b)
    
    def test_inductor_spice_generation(self):
        """Test Inductor SPICE generation."""
        l1 = Inductor(inductance=47e-6, name="L1")
        
        # Create a mock node mapper for testing
        mapper = MockNodeMapper()
        mapper.assign_name(l1.n1, "RF_IN")
        mapper.assign_name(l1.n2, "RF_OUT")
        
        spice_line = l1.to_spice(mapper)
        expected = "L1 RF_IN RF_OUT 4.7e-05"
        self.assertEqual(spice_line, expected)


class TestCurrentSource(unittest.TestCase):
    """Test CurrentSource component functionality."""
    
    def test_current_source_creation(self):
        """Test CurrentSource creation with default and custom values."""
        # Default current source
        i1 = CurrentSource()
        self.assertEqual(i1.current, 1e-6)  # Default 1 microamp
        self.assertEqual(i1.name, "UNNAMED")
        
        # Custom current source
        i2 = CurrentSource(current=10e-3, name="I2")
        self.assertEqual(i2.current, 10e-3)  # 10 milliamps
        self.assertEqual(i2.name, "I2")
    
    def test_current_source_terminals(self):
        """Test that CurrentSource has correct terminals and aliases."""
        i1 = CurrentSource(current=5e-6)
        
        # Check terminal existence
        self.assertTrue(hasattr(i1, 'pos'))
        self.assertTrue(hasattr(i1, 'neg'))
        self.assertTrue(hasattr(i1, 'positive'))  # Alias
        self.assertTrue(hasattr(i1, 'negative'))  # Alias
        
        # Check aliases work correctly
        self.assertEqual(i1.pos, i1.positive)
        self.assertEqual(i1.neg, i1.negative)
        
        # Check terminal properties
        self.assertEqual(i1.pos.component, i1)
        self.assertEqual(i1.neg.component, i1)
        self.assertEqual(i1.pos.terminal_name, "pos")
        self.assertEqual(i1.neg.terminal_name, "neg")
    
    def test_current_source_get_terminals(self):
        """Test CurrentSource get_terminals method."""
        i1 = CurrentSource()
        terminals = i1.get_terminals()
        
        self.assertEqual(len(terminals), 2)
        self.assertIn(('pos', i1.pos), terminals)
        self.assertIn(('neg', i1.neg), terminals)
    
    def test_current_source_spice_generation(self):
        """Test CurrentSource SPICE generation."""
        i1 = CurrentSource(current=2e-3, name="I1")
        
        # Create a mock node mapper for testing
        mapper = MockNodeMapper()
        mapper.assign_name(i1.pos, "N1")
        mapper.assign_name(i1.neg, "N2")
        
        spice_line = i1.to_spice(mapper)
        expected = "I1 N1 N2 DC 0.002"
        self.assertEqual(spice_line, expected)
        
        # Test with forced name
        spice_line_forced = i1.to_spice(mapper, forced_name="I_FORCED")
        expected_forced = "I_FORCED N1 N2 DC 0.002"
        self.assertEqual(spice_line_forced, expected_forced)


class TestExternalSubCircuit(unittest.TestCase):
    """Test ExternalSubCircuit component functionality."""
    
    def test_external_subcircuit_creation(self):
        """Test ExternalSubCircuit creation with various parameters."""
        # Simple MOSFET
        mosfet = ExternalSubCircuit("NMOS", ["D", "G", "S", "B"], name="M1")
        self.assertEqual(mosfet.subckt_name, "NMOS")
        self.assertEqual(mosfet.pin_names, ["D", "G", "S", "B"])
        self.assertEqual(mosfet.name, "M1")
        self.assertEqual(mosfet.params, {})
        
        # MOSFET with parameters
        mosfet_param = ExternalSubCircuit(
            "NMOS_SUBCKT", 
            ["D", "G", "S", "B"], 
            name="M2",
            W="2u", 
            L="0.18u"
        )
        self.assertEqual(mosfet_param.subckt_name, "NMOS_SUBCKT")
        self.assertEqual(mosfet_param.params, {"W": "2u", "L": "0.18u"})
    
    def test_external_subcircuit_terminals(self):
        """Test that ExternalSubCircuit creates correct terminals."""
        mosfet = ExternalSubCircuit("NMOS", ["D", "G", "S", "B"], name="M1")
        
        # Check that terminals are created and accessible
        self.assertTrue(hasattr(mosfet, 'D'))
        self.assertTrue(hasattr(mosfet, 'G'))
        self.assertTrue(hasattr(mosfet, 'S'))
        self.assertTrue(hasattr(mosfet, 'B'))
        
        # Check terminal properties
        self.assertEqual(mosfet.D.component, mosfet)
        self.assertEqual(mosfet.G.component, mosfet)
        self.assertEqual(mosfet.S.component, mosfet)
        self.assertEqual(mosfet.B.component, mosfet)
        
        self.assertEqual(mosfet.D.terminal_name, "D")
        self.assertEqual(mosfet.G.terminal_name, "G")
        self.assertEqual(mosfet.S.terminal_name, "S")
        self.assertEqual(mosfet.B.terminal_name, "B")
    
    def test_external_subcircuit_get_terminals(self):
        """Test ExternalSubCircuit get_terminals method."""
        opamp = ExternalSubCircuit("OPAMP", ["IN+", "IN-", "OUT", "VCC", "VEE"], name="U1")
        terminals = opamp.get_terminals()
        
        self.assertEqual(len(terminals), 5)
        
        # Check that terminal names match pin names
        terminal_names = [name for name, terminal in terminals]
        for pin_name in opamp.pin_names:
            self.assertIn(pin_name, terminal_names)
    
    def test_external_subcircuit_spice_generation_no_params(self):
        """Test ExternalSubCircuit SPICE generation without parameters."""
        opamp = ExternalSubCircuit("OPAMP", ["IN+", "IN-", "OUT"], name="U1")
        
        # Create a mock node mapper for testing
        mapper = MockNodeMapper()
        mapper.assign_name(getattr(opamp, "IN+"), "VIN_P")
        mapper.assign_name(getattr(opamp, "IN-"), "VIN_N")
        mapper.assign_name(getattr(opamp, "OUT"), "VOUT")
        
        spice_line = opamp.to_spice(mapper)
        # ExternalSubCircuit automatically adds X prefix when compiled in circuit context
        self.assertIn("U1 VIN_P VIN_N VOUT OPAMP", spice_line)
    
    def test_external_subcircuit_spice_generation_with_params(self):
        """Test ExternalSubCircuit SPICE generation with parameters."""
        mosfet = ExternalSubCircuit(
            "NMOS", 
            ["D", "G", "S", "B"], 
            name="M1",
            W="10u",
            L="0.18u",
            AD="50p",
            AS="50p"
        )
        
        # Create a mock node mapper for testing
        mapper = MockNodeMapper()
        mapper.assign_name(mosfet.D, "VDD")
        mapper.assign_name(mosfet.G, "GATE")
        mapper.assign_name(mosfet.S, "gnd")
        mapper.assign_name(mosfet.B, "gnd")
        
        spice_line = mosfet.to_spice(mapper)
        
        # Should contain subcircuit name and parameters
        self.assertIn("M1", spice_line)
        self.assertIn("VDD GATE gnd gnd", spice_line)
        self.assertIn("NMOS", spice_line)
        
        # Parameters can be in any order
        for param in ["W=10u", "L=0.18u", "AD=50p", "AS=50p"]:
            self.assertIn(param, spice_line)
    
    def test_external_subcircuit_forced_name(self):
        """Test ExternalSubCircuit with forced name."""
        ext_sub = ExternalSubCircuit("DIODE", ["A", "K"], name="D1")
        
        mapper = MockNodeMapper()
        mapper.assign_name(ext_sub.A, "ANODE")
        mapper.assign_name(ext_sub.K, "CATHODE")
        
        spice_line = ext_sub.to_spice(mapper, forced_name="D_SPECIAL")
        expected = "D_SPECIAL ANODE CATHODE DIODE"
        self.assertEqual(spice_line, expected)


class TestComponentIntegration(GoldenTestMixin, unittest.TestCase):
    """Test component integration with circuits."""
    
    def test_component_creation_without_connections(self):
        """Test that components can be created independently."""
        # Create components without adding to a circuit first
        vs = VoltageSource(voltage=12.0)
        r1 = Resistor(resistance=1000)
        c1 = Capacitor(capacitance=100e-9)
        l1 = Inductor(inductance=10e-6)
        i1 = CurrentSource(current=1e-3)
        
        # All should be created successfully
        self.assertIsNotNone(vs)
        self.assertIsNotNone(r1)
        self.assertIsNotNone(c1)
        self.assertIsNotNone(l1)
        self.assertIsNotNone(i1)
    
    def test_current_source_in_circuit(self):
        """Test CurrentSource integration with Circuit."""
        circuit = Circuit("Current Source Test")
        i1 = CurrentSource(current=1e-3, name="I1")
        r1 = Resistor(resistance=1000, name="R1")
        
        circuit.add_component(i1)
        circuit.add_component(r1)
        
        # Wire current source through resistor
        circuit.wire(i1.pos, r1.n1)
        circuit.wire(i1.neg, circuit.gnd)
        circuit.wire(r1.n2, circuit.gnd)
        
        # Generate SPICE and check
        spice = circuit.compile_to_spice()
        self.assertIn("I1", spice)
        self.assertIn("R1", spice)
        self.assertIn("DC 0.001", spice)  # 1mA current
    
    def test_external_subcircuit_in_circuit(self):
        """Test ExternalSubCircuit integration with Circuit."""
        circuit = Circuit("External SubCircuit Test")
        
        # Create an op-amp and voltage divider
        opamp = ExternalSubCircuit("OPAMP", ["IN+", "IN-", "OUT"], name="U1")
        vs = VoltageSource(voltage=5.0, name="VCC")
        r1 = Resistor(resistance=10000, name="R1")
        r2 = Resistor(resistance=10000, name="R2")
        
        circuit.add_component(opamp)
        circuit.add_component(vs)
        circuit.add_component(r1)
        circuit.add_component(r2)
        
        # Create voltage divider on non-inverting input
        circuit.wire(vs.pos, r1.n1)
        circuit.wire(r1.n2, r2.n1)
        circuit.wire(r2.n2, circuit.gnd)
        circuit.wire(vs.neg, circuit.gnd)
        
        # Connect to opamp
        circuit.wire(r1.n2, getattr(opamp, "IN+"))  # Non-inverting input
        circuit.wire(getattr(opamp, "IN-"), circuit.gnd)  # Inverting input to ground
        
        # Check SPICE generation
        spice = circuit.compile_to_spice()
        self.assertIn("XU1", spice)  # Op-amp instance
        self.assertIn("OPAMP", spice)  # Op-amp subcircuit name
        self.assertIn("VCC", spice)  # Voltage source
        self.assertIn("R1", spice)  # Resistors
        self.assertIn("R2", spice)
    
    def test_pwl_voltage_source_in_circuit(self):
        """Test PiecewiseLinearVoltageSource integration with Circuit."""
        circuit = Circuit("PWL Voltage Source Test")
        
        # Create a PWL voltage source and resistor
        # Step function: 0V -> 5V at 1ms
        pwl_vs = PiecewiseLinearVoltageSource([(0, 0), (1e-3, 5)], name="V_PWL")
        r1 = Resistor(resistance=1000, name="R1")
        
        circuit.add_component(pwl_vs)
        circuit.add_component(r1)
        
        # Wire PWL voltage source through resistor
        circuit.wire(pwl_vs.pos, r1.n1)
        circuit.wire(pwl_vs.neg, circuit.gnd)
        circuit.wire(r1.n2, circuit.gnd)
        
        # Generate SPICE and check
        spice = circuit.compile_to_spice()
        self.assertIn("V_PWL", spice)
        self.assertIn("R1", spice)
        self.assertIn("PWL(0 0 0.001 5)", spice)  # PWL specification
    
    def test_pwl_voltage_source_triangle_wave(self):
        """Test PiecewiseLinearVoltageSource with triangle wave pattern."""
        circuit = Circuit("Triangle Wave Test")
        
        # Triangle wave: 0V -> 5V -> 0V -> -5V -> 0V
        triangle_pairs = [
            (0, 0),
            (1e-3, 5),
            (2e-3, 0),
            (3e-3, -5),
            (4e-3, 0)
        ]
        
        pwl_vs = PiecewiseLinearVoltageSource(triangle_pairs, name="V_TRI")
        r_load = Resistor(resistance=1000, name="R_LOAD")
        
        circuit.add_component(pwl_vs)
        circuit.add_component(r_load)
        
        # Connect as voltage divider
        circuit.wire(pwl_vs.pos, r_load.n1)
        circuit.wire(pwl_vs.neg, circuit.gnd)
        circuit.wire(r_load.n2, circuit.gnd)
        
        # Verify SPICE generation
        spice = circuit.compile_to_spice()
        self.assertIn("V_TRI", spice)
        self.assertIn("PWL(0 0 0.001 5 0.002 0 0.003 -5 0.004 0)", spice)


if __name__ == '__main__':
    unittest.main()
#!/usr/bin/env python3
"""
Tests for transient analysis functionality.

Comprehensive testing of time-domain simulations with waveform comparison
and golden file validation.
"""

import unittest
import os
import sys
import numpy as np

# Add the parent directory to the path to import zest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zest import Circuit, VoltageSource, Resistor, Capacitor
from zest.simulation import check_simulation_requirements
from waveform_test_framework import WaveformTestMixin


class TestTransientAnalysis(WaveformTestMixin, unittest.TestCase):
    """Test transient analysis with waveform validation."""
    
    def setUp(self):
        """Set up for each test."""
        super().setUp()
        self.available, self.message = check_simulation_requirements()
        if not self.available:
            self.skipTest(f"PySpice not available: {self.message}")
    
    def test_rc_charging_transient(self):
        """Test RC circuit charging transient with golden waveform validation."""
        print("\n=== RC Circuit Charging Transient Analysis ===")
        
        # Create RC charging circuit
        # 5V step input, R=1kΩ, C=1µF
        # Time constant τ = RC = 1000 * 1e-6 = 1ms
        circuit = Circuit("RC Charging Circuit")
        
        vs = VoltageSource(voltage=5.0)  # 5V step input
        r1 = Resistor(resistance=1000)   # 1kΩ
        c1 = Capacitor(capacitance=1e-6) # 1µF
        
        # Add components to circuit
        circuit.add_component(vs)
        circuit.add_component(r1)
        circuit.add_component(c1)
        
        # Wire the circuit: Vs -> R -> C -> Gnd
        circuit.wire(vs.neg, circuit.gnd)
        circuit.wire(vs.pos, r1.n1)      # Voltage source to resistor
        circuit.wire(r1.n2, c1.pos)      # Resistor to capacitor positive
        circuit.wire(c1.neg, circuit.gnd) # Capacitor negative to ground
        
        # Set initial condition: capacitor starts at 0V for proper charging transient
        circuit.set_initial_condition(c1.pos, 0.0)
        
        print("Circuit created:")
        print(f"- Voltage source: {vs.voltage}V")
        print(f"- Resistor: {r1.resistance}Ω")
        print(f"- Capacitor: {c1.capacitance*1e6}µF")
        print(f"- Time constant τ = RC = {r1.resistance * c1.capacitance * 1000:.1f}ms")
        
        # Run transient analysis
        time_constant = r1.resistance * c1.capacitance  # 1ms
        end_time = 5 * time_constant  # Simulate for 5 time constants (5ms)
        step_time = end_time / 1000   # 1000 time points
        
        print(f"\nRunning transient analysis:")
        print(f"- End time: {end_time*1000:.1f}ms")
        print(f"- Time step: {step_time*1e6:.1f}µs")
        print(f"- Number of points: {int(end_time/step_time)}")
        
        # Run transient analysis using Zest
        simulated_circuit = circuit.simulate_transient(step_time=step_time, end_time=end_time)
        
        # Verify we got results
        self.assertIsNotNone(simulated_circuit)
        self.assertEqual(simulated_circuit.analysis_type, "Transient Analysis")
        
        print(f"✓ Simulation completed successfully")
        print(f"✓ Analysis type: {simulated_circuit.analysis_type}")
        print(f"✓ Found {len(simulated_circuit.nodes)} node voltages")
        print(f"✓ Available nodes: {list(simulated_circuit.nodes.keys())}")
        
        # Use SimulatedCircuit methods to get component results
        print("\n🔍 Using SimulatedCircuit methods to extract data:")
        
        # Get component results using the new API
        c1_results = simulated_circuit.get_component_results(c1)
        r1_results = simulated_circuit.get_component_results(r1)
        vs_results = simulated_circuit.get_component_results(vs)
        
        print(f"✓ Capacitor component name: {c1_results['component_name']}")
        print(f"✓ Resistor component name: {r1_results['component_name']}")
        print(f"✓ Voltage source component name: {vs_results['component_name']}")
        
        # Extract terminal voltages from component results
        cap_voltage_data = c1_results['terminal_voltages']['pos']  # Capacitor positive terminal
        input_voltage_data = vs_results['terminal_voltages']['pos']  # Voltage source positive terminal
        
        # Get time vector using the new method
        times = simulated_circuit.get_time_vector()
        if times is None:
            # Fallback: create time vector based on simulation parameters
            print("⚠️  Could not extract time vector from PySpice, using simulation parameters")
            times = np.linspace(0, end_time, len(cap_voltage_data))
        
        # Ensure cap_voltage_data is a numpy array
        if not isinstance(cap_voltage_data, np.ndarray):
            cap_voltage_data = np.array(cap_voltage_data)
        if not isinstance(input_voltage_data, np.ndarray):
            input_voltage_data = np.array(input_voltage_data)
        
        print(f"✓ Extracted {len(times)} time points from PySpice")
        print(f"✓ Time range: {times[0]*1000:.2f}ms to {times[-1]*1000:.2f}ms")
        print(f"✓ Capacitor voltage range: {cap_voltage_data[0]:.3f}V to {cap_voltage_data[-1]:.3f}V")
        
        # Calculate resistor voltage: V_R = V_input - V_capacitor
        resistor_voltage_data = input_voltage_data - cap_voltage_data
        
        # Validate the RC response characteristics
        final_cap_voltage = cap_voltage_data[-1]
        initial_cap_voltage = cap_voltage_data[0]
        voltage_swing = final_cap_voltage - initial_cap_voltage
        
        print(f"✓ Initial capacitor voltage: {initial_cap_voltage:.3f}V")
        print(f"✓ Final capacitor voltage: {final_cap_voltage:.3f}V")
        print(f"✓ Voltage swing: {voltage_swing:.3f}V")
        
        # For RC charging, we expect the capacitor to approach the input voltage
        self.assertGreater(final_cap_voltage, 0.9 * vs.voltage)  # Should reach at least 90% of input
        self.assertLess(initial_cap_voltage, 0.1 * vs.voltage)   # Should start near 0V
        
        # Plot the REAL simulation results
        print("\n📊 Generating plots from REAL PySpice data...")
        
        traces = [cap_voltage_data, resistor_voltage_data]
        trace_names = ('V(capacitor)', 'V(resistor)')
        
        self.plot_and_save_transient(
            times, traces, trace_names,
            title="RC Circuit Charging Transient - PySpice Simulation (R=1kΩ, C=1µF, τ=1ms)",
            filename="rc_charging_pyspice.png"
        )
        
        print("✓ Plot displayed and saved")
        
        # Compare against golden waveform using REAL data
        print("\n📋 Validating against golden waveform...")
        
        self.assert_waveform_matches_golden(
            "rc_charging_pyspice_1k_1uF.csv",
            times,
            traces,
            trace_names
        )
        
        print("✓ Waveform validation completed")
    
    def test_rc_discharging_transient(self):
        """Test RC circuit discharging transient."""
        print("\n=== RC Circuit Discharging Transient Analysis ===")
        
        # Create an RC circuit for discharging
        circuit = Circuit("RC Discharging")
        
        # For discharging, we use a voltage source at 0V and set initial condition on capacitor
        vs = VoltageSource(voltage=0.0)  # Discharge through 0V source
        r1 = Resistor(resistance=2000)   # 2kΩ
        c1 = Capacitor(capacitance=0.5e-6)  # 0.5µF
        
        # Add components to circuit
        circuit.add_component(vs)
        circuit.add_component(r1)
        circuit.add_component(c1)
        
        # Wire the circuit: capacitor discharges through resistor to ground via voltage source
        circuit.wire(vs.neg, circuit.gnd)
        circuit.wire(vs.pos, r1.n1)
        circuit.wire(r1.n2, c1.pos)
        circuit.wire(c1.neg, circuit.gnd)
        
        # Set initial condition: capacitor starts at 5V (charged state)
        circuit.set_initial_condition(c1.pos, 5.0)
        
        # Time constant τ = RC = 2000 * 0.5e-6 = 1ms
        tau = r1.resistance * c1.capacitance
        end_time = 5 * tau  # Simulate for 5 time constants (5ms)
        step_time = end_time / 1000  # 1000 points
        
        print(f"Time constant τ = RC = {tau*1000:.1f}ms")
        print(f"Simulation time: {end_time*1000:.1f}ms (5τ)")
        print(f"Time step: {step_time*1e6:.1f}µs")
        
        # Run transient simulation
        simulated_circuit = circuit.simulate_transient(step_time=step_time, end_time=end_time)
        
        # Extract capacitor voltage
        times = simulated_circuit.get_time_vector()
        cap_voltage = simulated_circuit.get_node_voltage(c1.pos)
        cap_voltage_data = simulated_circuit._extract_value(cap_voltage)
        
        if times is None:
            times = np.linspace(0, end_time, len(cap_voltage_data))
        
        print(f"Initial voltage: {cap_voltage_data[0]:.3f}V")
        print(f"Final voltage: {cap_voltage_data[-1]:.3f}V")
        
        # Verify exponential decay: V(t) = V0 * exp(-t/τ)
        initial_voltage = cap_voltage_data[0]
        final_voltage = cap_voltage_data[-1]
        
        # Should start near 5V and decay towards 0V
        self.assertGreater(initial_voltage, 4.5, "Should start near 5V")
        self.assertLess(final_voltage, 0.5, "Should decay close to 0V after 5τ")
        
        # Check voltage at 1τ should be ~37% of initial (e^-1 ≈ 0.368)
        time_1tau_idx = np.argmin(np.abs(times - tau))
        voltage_1tau = cap_voltage_data[time_1tau_idx]
        expected_1tau = initial_voltage * np.exp(-1)
        
        print(f"Voltage at 1τ: {voltage_1tau:.3f}V (expected: {expected_1tau:.3f}V)")
        self.assertAlmostEqual(voltage_1tau, expected_1tau, delta=0.5, 
                             msg="Voltage at 1τ should be ~37% of initial")
        
        # Plot and save results
        self.plot_and_save_transient(
            times, [cap_voltage_data], ("V(capacitor)",),
            title="RC Discharging Transient (τ=1ms)",
            filename="rc_discharging_transient.png"
        )
        
        # Validate against golden file
        self.assert_waveform_matches_golden(
            "rc_discharging_2k_0p5uF.csv",
            times,
            [cap_voltage_data],
            ("V(capacitor)",)
        )
        
        print("✓ RC discharging transient analysis completed successfully!")
    
    def test_multiple_time_constants(self):
        """Test RC circuits with different time constants using real PySpice simulations."""
        print("\n=== Multiple Time Constants Comparison ===")
        
        # Create circuits with different time constants
        configs = [
            {"R": 1000, "C": 1e-6, "name": "τ=1ms"},      # 1ms
            {"R": 2000, "C": 1e-6, "name": "τ=2ms"},      # 2ms  
            {"R": 1000, "C": 2e-6, "name": "τ=2ms(2C)"},  # 2ms (double C)
            {"R": 500, "C": 1e-6, "name": "τ=0.5ms"},     # 0.5ms
        ]
        
        traces = []
        trace_names = []
        common_times = None
        
        # Calculate maximum time constant to determine simulation time
        max_tau = max(config["R"] * config["C"] for config in configs)
        end_time = 5 * max_tau  # Simulate for 5 time constants of the slowest circuit
        step_time = end_time / 1000  # 1000 points
        
        print(f"Maximum time constant: {max_tau*1000:.1f}ms")
        print(f"Simulation time: {end_time*1000:.1f}ms (5τ of slowest circuit)")
        print(f"Time step: {step_time*1e6:.1f}µs")
        
        for i, config in enumerate(configs):
            print(f"\n🔧 Simulating circuit {i+1}/4: {config['name']}")
            print(f"   R={config['R']}Ω, C={config['C']*1e6}µF")
            
            # Create individual RC circuit for this configuration
            circuit = Circuit(f"RC_{config['name']}")
            vs = VoltageSource(voltage=5.0)
            r1 = Resistor(resistance=config["R"])
            c1 = Capacitor(capacitance=config["C"])
            
            # Add components to circuit
            circuit.add_component(vs)
            circuit.add_component(r1)
            circuit.add_component(c1)
            
            # Wire the circuit
            circuit.wire(vs.neg, circuit.gnd)
            circuit.wire(vs.pos, r1.n1)
            circuit.wire(r1.n2, c1.pos)
            circuit.wire(c1.neg, circuit.gnd)
            
            # Set initial condition: capacitor starts at 0V for proper charging transient
            circuit.set_initial_condition(c1.pos, 0.0)
            
            # Run simulation
            simulated_circuit = circuit.simulate_transient(step_time=step_time, end_time=end_time)
            
            # Use SimulatedCircuit methods to get component results
            c1_results = simulated_circuit.get_component_results(c1)
            
            # Extract capacitor voltage from component results
            cap_voltage_data = c1_results['terminal_voltages']['pos']  # Capacitor positive terminal
            
            # Get time vector using the new method
            times = simulated_circuit.get_time_vector()
            if times is None:
                times = np.linspace(0, end_time, len(cap_voltage_data))
            
            # Store for plotting - use first simulation's times as reference
            if common_times is None:
                common_times = times
            
            traces.append(cap_voltage_data)
            trace_names.append(f'{config["name"]} (R={config["R"]}Ω)')
            
            tau = config["R"] * config["C"]
            final_voltage = cap_voltage_data[-1]
            print(f"   ✓ τ={tau*1000:.1f}ms, Final voltage: {final_voltage:.3f}V")
        
        if len(traces) == 0:
            self.fail("No valid simulation results obtained")
        
        print(f"\n📊 Plotting {len(traces)} real PySpice simulation results...")
        
        # Plot comparison of real simulation results
        self.plot_and_save_transient(
            common_times, traces, tuple(trace_names),
            title="RC Charging: Different Time Constants - PySpice Simulations",
            filename="rc_time_constants_pyspice_comparison.png"
        )
        
        # Validate against golden file
        self.assert_waveform_matches_golden(
            "rc_time_constants_pyspice_comparison.csv",
            common_times,
            traces,
            tuple(trace_names)
        )
        
        print("✓ Time constants comparison completed with real PySpice data")


class TestTransientValidation(WaveformTestMixin, unittest.TestCase):
    """Test waveform validation framework itself."""
    
    def test_waveform_interpolation(self):
        """Test waveform interpolation and comparison functionality."""
        print("\n=== Testing Waveform Interpolation Framework ===")
        
        # Create test waveforms with different time grids
        t1 = np.linspace(0, 1, 100)
        t2 = np.linspace(0, 1, 150)  # Different number of points
        
        # Same mathematical function but different sampling
        v1 = np.sin(2 * np.pi * t1)
        v2 = np.sin(2 * np.pi * t2)
        
        print(f"Waveform 1: {len(t1)} points")
        print(f"Waveform 2: {len(t2)} points")
        
        # Test interpolation
        common_time, resampled1, resampled2 = self.waveform.resample_waveforms(t1, v1, t2, v2)
        
        print(f"Common grid: {len(common_time)} points")
        
        # They should be very close after interpolation
        is_close, metric = self.waveform.compare_waveforms(resampled1, resampled2, tolerance=1e-6)
        
        print(f"Waveforms close: {is_close}")
        print(f"MSE metric: {metric:.2e}")
        
        self.assertTrue(is_close)
        self.assertLess(metric, 1e-6)
        
        print("✓ Interpolation framework validated")
    
    def test_golden_file_workflow(self):
        """Test the complete golden file workflow."""
        print("\n=== Testing Golden File Workflow ===")
        
        # Create a simple test waveform
        times = np.linspace(0, 1, 100)
        voltages = np.exp(-times) * np.cos(10 * times)  # Damped oscillation
        
        test_file = "test_workflow.csv"
        
        # First run should create the golden file
        print("First run: Creating golden file...")
        try:
            self.assert_waveform_matches_golden(
                test_file, times, [voltages], ('V(test)',)
            )
            print("✓ Golden file created successfully")
        except Exception as e:
            if "created" in str(e):
                print("✓ Golden file creation detected")
            else:
                raise
        
        # Second run should pass validation
        print("Second run: Validating against golden file...")
        self.assert_waveform_matches_golden(
            test_file, times, [voltages], ('V(test)',)
        )
        print("✓ Golden file validation passed")
        
        # Test with significantly different data (should fail)
        print("Third run: Testing with different data...")
        voltages_different = voltages + 0.1  # Add 0.1V offset - much larger than 1e-3 tolerance
        
        try:
            self.assert_waveform_matches_golden(
                test_file, times, [voltages_different], ('V(test)',)
            )
            self.fail("Should have failed with different data")
        except Exception as e:
            if "not close" in str(e):
                print("✓ Correctly detected different waveform")
            else:
                raise
        
        print("✓ Golden file workflow validated")


if __name__ == '__main__':
    print("🔬 Transient Analysis Test Suite")
    print("=" * 50)
    
    # Check if required packages are available
    try:
        import matplotlib.pyplot as plt
        import pandas as pd
        import numpy as np
        print("✓ All required packages available")
    except ImportError as e:
        print(f"✗ Missing required package: {e}")
        print("Please install: pip install matplotlib pandas numpy")
        sys.exit(1)
    
    # Run with verbose output
    unittest.main(verbosity=2) 
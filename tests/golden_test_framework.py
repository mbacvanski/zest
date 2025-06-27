#!/usr/bin/env python3
"""
Golden test framework for zest.

Provides utilities for golden file testing, SPICE output validation,
and common test assertions.
"""

import os
import unittest
import difflib
from typing import Optional, List, Dict, Any


class GoldenTestFramework:
    """Framework for golden file testing."""
    
    def __init__(self, test_case: unittest.TestCase):
        """Initialize with reference to test case for assertions."""
        self.test_case = test_case
        self.golden_dir = os.path.join(os.path.dirname(__file__), "golden_files")
    
    def read_golden_file(self, filename: str) -> str:
        """Read a golden file and return its contents."""
        filepath = os.path.join(self.golden_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Golden file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            return f.read().strip()
    
    def write_golden_file(self, filename: str, content: str) -> None:
        """Write content to a golden file (for updating golden files)."""
        filepath = os.path.join(self.golden_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            f.write(content)
    
    def assert_matches_golden(self, actual: str, golden_filename: str, 
                            update_golden: bool = False) -> None:
        """
        Assert that actual output matches golden file.
        
        Args:
            actual: The actual output to compare
            golden_filename: Name of the golden file to compare against
            update_golden: If True, update the golden file with actual content
        """
        if update_golden:
            self.write_golden_file(golden_filename, actual)
            return
        
        try:
            expected = self.read_golden_file(golden_filename)
        except FileNotFoundError:
            # If golden file doesn't exist, create it
            self.write_golden_file(golden_filename, actual)
            self.test_case.fail(f"Golden file {golden_filename} created. Run test again to validate.")
            return
        
        if actual.strip() != expected.strip():
            diff = '\n'.join(difflib.unified_diff(
                expected.splitlines(keepends=True),
                actual.splitlines(keepends=True),
                fromfile=f"golden/{golden_filename}",
                tofile="actual"
            ))
            self.test_case.fail(f"Output doesn't match golden file {golden_filename}:\n{diff}")
    
    def assert_spice_structure(self, spice_output: str, 
                             expected_components: List[str]) -> None:
        """
        Assert SPICE output contains expected components.
        
        Args:
            spice_output: The SPICE netlist to validate
            expected_components: List of component names to check for (e.g., ["V1", "R1", "R2"])
        """
        # Check for components
        for component in expected_components:
            self.test_case.assertIn(component, spice_output, 
                                  f"Expected component {component} not found in SPICE output")
        
        # Check basic SPICE structure
        lines = spice_output.strip().split('\n')
        self.test_case.assertGreater(len(lines), 2, "SPICE output should have multiple lines")
        self.test_case.assertEqual(lines[-1], ".end", "SPICE output should end with '.end'")
    
    def assert_spice_valid_format(self, spice_output: str) -> None:
        """Assert that SPICE output has valid format."""
        lines = spice_output.strip().split('\n')
        
        # Should have at least a title and .end
        self.test_case.assertGreaterEqual(len(lines), 2, "SPICE output too short")
        
        # Should start with title or comment
        first_line = lines[0].strip()
        self.test_case.assertTrue(
            first_line.startswith('.title') or first_line.startswith('*'),
            f"SPICE should start with .title or comment, got: {first_line}"
        )
        
        # Should end with .end
        self.test_case.assertEqual(lines[-1].strip(), ".end", "SPICE should end with '.end'")
        
        # Check for empty lines between components and .end
        has_components = any(line.strip() and not line.startswith('.') and not line.startswith('*') 
                           for line in lines[1:-1])
        if has_components:
            self.test_case.assertTrue(any(line.strip() == '' for line in lines[:-1]),
                                    "SPICE should have blank line before .end")


class GoldenTestMixin:
    """Mixin class to add golden test capabilities to test cases."""
    
    def setUp(self):
        """Set up golden test framework."""
        super().setUp()
        self.golden = GoldenTestFramework(self)
        # Check environment variable for updating golden files
        self.update_golden_files = os.environ.get('UPDATE_GOLDEN_FILES', '').lower() in ('1', 'true', 'yes')
    
    def assert_circuit_matches_golden(self, circuit, golden_filename: str) -> None:
        """Compare circuit SPICE output against golden file."""
        spice_output = circuit.compile_to_spice()
        self.golden.assert_matches_golden(spice_output, golden_filename, self.update_golden_files)
    
    def assert_spice_has_components(self, spice_output: str, expected_components: List[str]) -> None:
        """Simple helper to verify SPICE output contains expected components."""
        self.golden.assert_spice_structure(spice_output, expected_components)
    
    def assert_spice_valid(self, spice_output: str) -> None:
        """Simple helper to verify SPICE output has valid format."""
        self.golden.assert_spice_valid_format(spice_output) 
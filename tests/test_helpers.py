#!/usr/bin/env python3
"""
Test helper components for zest testing.
"""

import sys
import os

# Add the parent directory to the path for importing zest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from zest import Circuit, SubCircuit, Component, Terminal


class DummyComponent(Component):
    """A dummy component for external subcircuit pin definitions."""
    def to_spice(self, mapper, *, forced_name=None):
        return "* External component - defined in .INCLUDE file"

def create_npn_definition() -> Circuit:
    """
    Creates the definition for a simple NPN transistor, which points to an
    external model file.
    """
    npn_definition = Circuit("SIMPLE_NPN")

    # 1. Register the external file dependency.
    # Use absolute path to ensure it works from any working directory
    model_path = os.path.join(os.path.dirname(__file__), "models", "simple_npn.lib")
    npn_definition.add_include(model_path)

    # 2. Define the pins to match the .SUBCKT line in the model file.
    #    Use dummy components that won't be compiled.
    dummy = DummyComponent()
    npn_definition.add_component(dummy)  # Explicitly add dummy component
    npn_definition.add_pin("C", Terminal(dummy, "c"))
    npn_definition.add_pin("B", Terminal(dummy, "b"))
    npn_definition.add_pin("E", Terminal(dummy, "e"))

    # 3. Mark this as an external-only subcircuit.
    npn_definition._is_external_only = True

    return npn_definition


class SimpleNPN(SubCircuit):
    """
    A user-friendly wrapper for the SIMPLE_NPN subcircuit.
    This class provides collector, base, and emitter terminals for easy wiring.
    """
    _npn_definition = None # Class-level cache for the definition

    def __init__(self, name=None):
        # Create the definition only once and cache it.
        if not SimpleNPN._npn_definition:
            SimpleNPN._npn_definition = create_npn_definition()

        super().__init__(definition=SimpleNPN._npn_definition, name=name)

        # Map the pin names from the definition to convenient attributes.
        self.collector = getattr(self, "C", None)
        self.base = getattr(self, "B", None)
        self.emitter = getattr(self, "E", None)


# Legacy SPICE model definition for backwards compatibility
SIMPLE_NPN_MODEL = """
* Simplified NPN BJT model using voltage-controlled current sources
* This is not a physical model. For testing purposes only.
.SUBCKT SIMPLE_NPN C B E
* Simple BJT model using Gummel-Poon parameters
Q1 C B E SIMPLE_NPN_MODEL
.MODEL SIMPLE_NPN_MODEL NPN (IS=1E-15 BF=100 BR=1 RC=10 RE=1 RB=100 CJE=1E-12 CJC=1E-12 TF=1E-9 TR=1E-9)
.ENDS SIMPLE_NPN
""" 
#!/usr/bin/env python3
"""
Neuron-slice “v3” reproduced in Zest
------------------------------------
 * three ideal op-amps  (U29  U30  U32)
 * passive network  R77-R84, R56, C5
 * all nets named exactly as in the schematic
The ideal-op-amp sub-circuit is included inline; replace it with your own
macro-model if you need finite gain / bandwidth.
"""

from zest.components import Resistor, Capacitor, SubCircuit
from zest.circuit import Circuit

# ---------------------------------------------------------------------
# 1) reusable ideal-op-amp definition  (three pins: +  –  out)
# ---------------------------------------------------------------------
def make_ideal_opamp():
    opamp = Circuit("IDEAL_OPAMP")       # .SUBCKT IDEAL_OPAMP + - out
    #
    # Large-gain voltage-controlled voltage source:
    #        out 0  value = 1e6 * ( V(+) – V(-) )
    #
    # Zest doesn’t ship a VCVS, so we just drop raw-SPICE text into the
    # definition and expose the pins.
    opamp.include_model("""
EGAIN out 0 VALUE = {LIMIT(1e6*(V(plus)-V(minus)), -1e12, 1e12)}
""")
    opamp.add_pin("plus",  opamp.gnd)    # placeholders; they are remapped
    opamp.add_pin("minus", opamp.gnd)    # when the instance is wired
    opamp.add_pin("out",   opamp.gnd)
    #
    # Flag this definition as “external only” so Zest will embed the raw
    # text but not try to simulate the empty component list.
    #
    opamp._is_external_only = True
    return opamp

OPAMP_DEF = make_ideal_opamp()           # one definition → three instances

# ---------------------------------------------------------------------
# 2) main circuit
# ---------------------------------------------------------------------
ckt = Circuit("Neuron_v3_slice")

# --- 2.1 active devices ------------------------------------------------
U29 = SubCircuit(OPAMP_DEF, name="U29")      # unity-gain buffer for v3
U30 = SubCircuit(OPAMP_DEF, name="U30")      # “self-term” amp
U32 = SubCircuit(OPAMP_DEF, name="U32")      # “sum” amp

# --- 2.2 passives ------------------------------------------------------
R77 = Resistor(1.0,    name="R77")           #  1  Ω
R78 = Resistor(10e3,   name="R78")           # 10 kΩ
R81 = Resistor(100e3,  name="R81")           # 100 kΩ
R82 = Resistor(10e3,   name="R82")           # 10 kΩ
R83 = Resistor(10e3,   name="R83")           # 10 kΩ
R84 = Resistor(100e3,  name="R84")           # 100 kΩ
R42 = Resistor(1e3,    name="R42")           #  1 kΩ
R56 = Resistor(2e3,    name="R56")           #  2 kΩ   (left arrow node → minus_U30)

C5  = Capacitor(0.0,   name="C5")            # 0 µF placeholder

# ---------------------------------------------------------------------
# 3) Wiring  – each “wire( A , B )” line copies one segment of the LTspice net
#              Pick ONE anchor terminal per node and attach everything else to it
# ---------------------------------------------------------------------

# === Node  v3  (left vertical bus) ====================================
ckt.wire(R78.n1, C5.pos)         # R78 left  , C5 top
ckt.wire(R78.n1, R77.n1)         # R77 left
ckt.wire(R78.n1, U29.plus)       # U29 non-inv
ckt.wire(R78.n1, U29.out)        # unity-gain buffer feedback
ckt.wire(R78.n1, U30.plus)       # U30 non-inv
ckt.wire(R78.n1, R42.n2)         # bottom of R42 (feedback to v3)

# === Node  g3  (top horizontal wire) ==================================
ckt.wire(R77.n2, R83.n1)         # R77 right , R83 left
ckt.wire(R77.n2, R82.n1)         # R82 left

# === Node  self_term_v3  (output of U30) ==============================
ckt.wire(U30.out, R81.n1)

# === Node  sum_term_v3  (right-most vertical bus) =====================
ckt.wire(R78.n2, U32.out)        # R78 right , U32 output

# === U30 feedback / bias network  =====================================
# minus_U30: U30 inverting input, R42 top, R56 right
ckt.wire(U30.minus, R42.n1)
ckt.wire(U30.minus, R56.n2)

# (R56 left goes to an external bias node – hook it up later)
# Example placeholder:  ckt.wire(R56.n1, some_bias_terminal)

# === U32 differential summing network  ================================
# node_minus_U32
ckt.wire(U32.minus, R83.n2)

# node_plus_U32
ckt.wire(U32.plus,  R82.n2)
ckt.wire(U32.plus,  R81.n2)

# feedback resistor R84  (from U32 out → minus input)
ckt.wire(U32.out, R84.n1)
ckt.wire(R84.n2,  U32.minus)

# === Capacitor to ground ==============================================
ckt.wire(C5.neg, ckt.gnd)

# ---------------------------------------------------------------------
# 4) Done – look at the generated netlist
# ---------------------------------------------------------------------
print(ckt.compile_to_spice())

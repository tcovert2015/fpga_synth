"""
Core types used across the synthesis pipeline.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional


class PortDir(Enum):
    """Port direction for module I/O."""
    INPUT = auto()
    OUTPUT = auto()
    INOUT = auto()


class NetType(Enum):
    """Wire vs register semantics."""
    WIRE = auto()
    REG = auto()


class CellOp(Enum):
    """Primitive operations a cell can perform.
    
    These are the atomic operations in the netlist DAG.
    Every node in the graph is one of these.
    """
    # Constants
    CONST = auto()       # Constant value generator
    
    # Bitwise logic (1-bit or vectorized)
    BUF = auto()
    NOT = auto()
    AND = auto()
    OR = auto()
    XOR = auto()
    NAND = auto()
    NOR = auto()
    XNOR = auto()
    
    # Reduction operators
    REDUCE_AND = auto()
    REDUCE_OR = auto()
    REDUCE_XOR = auto()
    
    # Arithmetic
    ADD = auto()
    SUB = auto()
    MUL = auto()
    NEG = auto()         # Unary minus (2's complement)
    
    # Comparison
    EQ = auto()
    NEQ = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    
    # Shift
    SHL = auto()
    SHR = auto()
    SSHR = auto()        # Arithmetic (signed) shift right
    
    # Multiplexer
    MUX = auto()         # 2-to-1 mux: MUX(sel, a, b) = sel ? b : a
    PMUX = auto()        # Priority mux (for case statements)
    
    # Bit manipulation
    CONCAT = auto()      # Concatenation: {a, b}
    SLICE = auto()       # Bit-select: a[hi:lo]
    REPEAT = auto()      # Replication: {N{a}}
    
    # Sequential
    DFF = auto()         # D flip-flop (posedge clk)
    DFFR = auto()        # DFF with sync reset
    DFFRE = auto()       # DFF with sync reset + enable
    DFFS = auto()        # DFF with sync set
    
    # Memory
    MEMRD = auto()       # Memory read port
    MEMWR = auto()       # Memory write port
    
    # Structural
    MODULE_INPUT = auto()   # Primary input to the design
    MODULE_OUTPUT = auto()  # Primary output from the design


@dataclass(frozen=True)
class BitWidth:
    """Represents the width of a signal.
    
    Signals are always [msb:lsb] with msb >= lsb.
    For simple N-bit signals: msb = N-1, lsb = 0.
    """
    msb: int
    lsb: int = 0
    
    @property
    def width(self) -> int:
        return self.msb - self.lsb + 1
    
    @staticmethod
    def from_width(w: int) -> "BitWidth":
        """Create a BitWidth from just a width, e.g., 8 → [7:0]."""
        return BitWidth(msb=w - 1, lsb=0)
    
    def __repr__(self):
        if self.lsb == 0 and self.msb == 0:
            return "BitWidth(1)"
        return f"BitWidth([{self.msb}:{self.lsb}])"


@dataclass
class PortSpec:
    """Specification of a module port."""
    name: str
    direction: PortDir
    width: BitWidth = field(default_factory=lambda: BitWidth(0, 0))
    net_type: NetType = NetType.WIRE
    signed: bool = False


@dataclass
class ParamValue:
    """A resolved parameter value."""
    name: str
    value: int  # For now, only integer parameters

"""
Abstract Syntax Tree nodes for synthesizable Verilog.

The AST is a tree (connected acyclic graph) that directly mirrors
the source code structure. The elaborator will transform this tree
into a netlist DAG.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ============================================================
# Base
# ============================================================

@dataclass
class ASTNode:
    """Base class for all AST nodes."""
    line: int = 0
    col: int = 0
    attributes: dict[str, str] = field(default_factory=dict)  # Verilog attributes (* key = value *)


# ============================================================
# Expressions
# ============================================================

@dataclass
class Expr(ASTNode):
    """Base class for expressions."""
    pass


@dataclass
class NumberLiteral(Expr):
    """Numeric literal: 42, 8'hFF, 4'b1010, etc."""
    raw: str = ""          # Original text
    value: int = 0         # Resolved integer value
    width: int = 32        # Bit width (default 32 for unsized)
    is_signed: bool = False


@dataclass
class Identifier(Expr):
    """A signal or parameter reference: my_signal"""
    name: str = ""


@dataclass
class BitSelect(Expr):
    """Bit or part select: signal[7:0] or signal[3]"""
    target: Expr = None
    msb: Expr = None
    lsb: Optional[Expr] = None  # None for single-bit select


@dataclass
class UnaryOp(Expr):
    """Unary operation: ~a, !a, &a, |a, ^a, -a"""
    op: str = ""           # "~", "!", "&", "|", "^", "-", "+"
    operand: Expr = None


@dataclass
class BinaryOp(Expr):
    """Binary operation: a + b, a & b, a == b, etc."""
    op: str = ""           # "+", "-", "*", "/", "%", "&", "|", "^",
                           # "<<", ">>", ">>>", "==", "!=", "<", "<=", ">", ">=",
                           # "&&", "||"
    left: Expr = None
    right: Expr = None


@dataclass
class TernaryOp(Expr):
    """Ternary/conditional: cond ? true_val : false_val"""
    cond: Expr = None
    true_val: Expr = None
    false_val: Expr = None


@dataclass
class Concat(Expr):
    """Concatenation: {a, b, c}"""
    parts: list[Expr] = field(default_factory=list)


@dataclass
class Repeat(Expr):
    """Replication: {4{a}}"""
    count: Expr = None
    value: Expr = None


@dataclass
class FuncCall(Expr):
    """System/user function call: $clog2(N)"""
    name: str = ""
    args: list[Expr] = field(default_factory=list)


# ============================================================
# Statements
# ============================================================

@dataclass
class Statement(ASTNode):
    """Base class for statements."""
    pass


@dataclass
class BlockingAssign(Statement):
    """Blocking assignment: lhs = rhs;"""
    lhs: Expr = None
    rhs: Expr = None


@dataclass
class NonBlockingAssign(Statement):
    """Non-blocking assignment: lhs <= rhs;"""
    lhs: Expr = None
    rhs: Expr = None


@dataclass
class IfStatement(Statement):
    """if/else: if (cond) ... else ..."""
    cond: Expr = None
    then_body: list[Statement] = field(default_factory=list)
    else_body: list[Statement] = field(default_factory=list)


@dataclass
class CaseStatement(Statement):
    """case/casex/casez"""
    kind: str = "case"     # "case", "casex", "casez"
    expr: Expr = None
    items: list[CaseItem] = field(default_factory=list)
    default: list[Statement] = field(default_factory=list)


@dataclass
class CaseItem(ASTNode):
    """A single arm of a case statement."""
    values: list[Expr] = field(default_factory=list)
    body: list[Statement] = field(default_factory=list)


@dataclass
class ForStatement(Statement):
    """for loop (used in generate blocks)."""
    init: Statement = None
    cond: Expr = None
    update: Statement = None
    body: list[Statement] = field(default_factory=list)


@dataclass
class WhileStatement(Statement):
    """while loop: while (condition) ..."""
    cond: Expr = None
    body: list[Statement] = field(default_factory=list)


@dataclass
class RepeatStatement(Statement):
    """repeat loop: repeat (N) ..."""
    count: Expr = None
    body: list[Statement] = field(default_factory=list)


@dataclass
class ForeverStatement(Statement):
    """forever loop: forever ..."""
    body: list[Statement] = field(default_factory=list)


@dataclass
class DisableStatement(Statement):
    """disable statement: disable block_name;"""
    target: str = ""


@dataclass
class Block(Statement):
    """begin...end block, optionally named."""
    name: str = ""
    stmts: list[Statement] = field(default_factory=list)


# ============================================================
# Declarations
# ============================================================

@dataclass
class Range(ASTNode):
    """Bit range: [msb:lsb]"""
    msb: Expr = None
    lsb: Expr = None


@dataclass
class PortDecl(ASTNode):
    """Port declaration: input [7:0] data, input [7:0] mem [0:255]"""
    direction: str = "input"   # "input", "output", "inout"
    net_type: str = "wire"     # "wire", "reg"
    signed: bool = False
    range: Optional[Range] = None  # Packed dimension (bit width)
    name: str = ""
    array_dims: list[Range] = field(default_factory=list)  # Unpacked dimensions


@dataclass
class NetDecl(ASTNode):
    """Wire/reg declaration: wire [3:0] foo; / reg [7:0] mem [0:255];"""
    net_type: str = "wire"
    signed: bool = False
    range: Optional[Range] = None  # Packed dimension (bit width)
    name: str = ""
    array_dims: list[Range] = field(default_factory=list)  # Unpacked dimensions
    init_value: Optional[Expr] = None


@dataclass
class ParamDecl(ASTNode):
    """Parameter/localparam declaration."""
    kind: str = "parameter"    # "parameter" or "localparam"
    signed: bool = False
    range: Optional[Range] = None
    name: str = ""
    value: Expr = None


@dataclass
class IntegerDecl(ASTNode):
    """integer i;  (used for loop variables)."""
    name: str = ""


# ============================================================
# Module-level constructs
# ============================================================

@dataclass
class ContinuousAssign(ASTNode):
    """assign lhs = rhs;"""
    lhs: Expr = None
    rhs: Expr = None


@dataclass
class SensItem(ASTNode):
    """Sensitivity list item: posedge clk, negedge rst, or plain signal."""
    edge: str = ""         # "posedge", "negedge", or "" for level
    signal: Expr = None


@dataclass
class AlwaysBlock(ASTNode):
    """always @(...) begin ... end"""
    sensitivity: list[SensItem] = field(default_factory=list)
    is_star: bool = False  # always @(*)
    body: list[Statement] = field(default_factory=list)


@dataclass
class InitialBlock(ASTNode):
    """initial begin ... end"""
    body: list[Statement] = field(default_factory=list)


@dataclass
class PortConnection(ASTNode):
    """A port connection in a module instantiation: .port_name(expr)"""
    port_name: str = ""
    expr: Optional[Expr] = None


@dataclass
class ModuleInstance(ASTNode):
    """Module instantiation: mod_name #(.P(V)) inst_name (.port(sig));"""
    module_name: str = ""
    instance_name: str = ""
    params: list[PortConnection] = field(default_factory=list)
    ports: list[PortConnection] = field(default_factory=list)


@dataclass
class GenerateBlock(ASTNode):
    """generate ... endgenerate block."""
    items: list[ASTNode] = field(default_factory=list)


@dataclass
class TaskDecl(ASTNode):
    """Task declaration: task name; ... endtask"""
    name: str = ""
    automatic: bool = False
    inputs: list[PortDecl] = field(default_factory=list)
    outputs: list[PortDecl] = field(default_factory=list)
    inouts: list[PortDecl] = field(default_factory=list)
    body: list[Statement] = field(default_factory=list)


@dataclass
class FunctionDecl(ASTNode):
    """Function declaration: function [range] name; ... endfunction"""
    name: str = ""
    automatic: bool = False
    return_type: Optional[Range] = None  # Return width
    signed: bool = False
    inputs: list[PortDecl] = field(default_factory=list)
    body: list[Statement] = field(default_factory=list)


@dataclass
class TaskCall(Statement):
    """Task call statement: task_name(arg1, arg2);"""
    name: str = ""
    args: list[Expr] = field(default_factory=list)


# ============================================================
# Top-level
# ============================================================

@dataclass
class Module(ASTNode):
    """A Verilog module definition."""
    name: str = ""
    params: list[ParamDecl] = field(default_factory=list)
    ports: list[PortDecl] = field(default_factory=list)
    body: list[ASTNode] = field(default_factory=list)
    # Populated during parsing: all declarations, assigns, always blocks, instances


@dataclass
class SourceFile(ASTNode):
    """A complete Verilog source file (one or more modules)."""
    modules: list[Module] = field(default_factory=list)

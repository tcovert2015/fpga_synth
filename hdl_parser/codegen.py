"""
Verilog Code Generation from AST.

Provides functions to generate Verilog source code from AST nodes.
Useful for pretty-printing, code transformation, and template generation.
"""

from __future__ import annotations
from typing import Optional
from fpga_synth.hdl_parser.ast_nodes import *


class VerilogCodeGenerator:
    """
    Generates Verilog source code from AST nodes.

    Configurable indentation and formatting options.
    """

    def __init__(self, indent_str: str = "    "):
        self.indent_str = indent_str
        self.indent_level = 0
        self.output = []

    def generate(self, node: ASTNode) -> str:
        """Generate Verilog code from an AST node."""
        self.output = []
        self.indent_level = 0
        self._visit(node)
        return "".join(self.output)

    def _indent(self):
        """Add current indentation to output."""
        self.output.append(self.indent_str * self.indent_level)

    def _write(self, text: str):
        """Write text to output."""
        self.output.append(text)

    def _writeln(self, text: str = ""):
        """Write text with newline."""
        if text:
            self.output.append(text)
        self.output.append("\n")

    def _visit(self, node: ASTNode):
        """Dispatch to appropriate generation method."""
        if node is None:
            return

        method_name = f'_gen_{node.__class__.__name__}'
        method = getattr(self, method_name, None)
        if method:
            method(node)
        else:
            raise NotImplementedError(f"Code generation for {node.__class__.__name__} not implemented")

    # ============================================================
    # Top-level
    # ============================================================

    def _gen_SourceFile(self, node: SourceFile):
        """Generate source file with multiple modules."""
        for i, module in enumerate(node.modules):
            if i > 0:
                self._writeln()
            self._visit(module)

    def _gen_Module(self, node: Module):
        """Generate module definition."""
        self._write(f"module {node.name}")

        # Parameters
        if node.params:
            self._writeln(" #(")
            self.indent_level += 1
            for i, param in enumerate(node.params):
                self._indent()
                self._write(f"parameter {param.name}")
                if param.value:
                    self._write(" = ")
                    self._visit(param.value)
                if i < len(node.params) - 1:
                    self._write(",")
                self._writeln()
            self.indent_level -= 1
            self._write(")")

        # Ports
        if node.ports:
            self._writeln(" (")
            self.indent_level += 1
            for i, port in enumerate(node.ports):
                self._indent()
                self._gen_PortDecl(port)
                if i < len(node.ports) - 1:
                    self._write(",")
                self._writeln()
            self.indent_level -= 1
            self._write(")")

        self._writeln(";")

        # Module body
        if node.body:
            self.indent_level += 1
            for item in node.body:
                self._writeln()
                self._indent()
                self._visit(item)
            self.indent_level -= 1

        self._writeln()
        self._writeln("endmodule")

    # ============================================================
    # Declarations
    # ============================================================

    def _gen_PortDecl(self, node: PortDecl):
        """Generate port declaration."""
        self._write(node.direction)
        if node.net_type != "wire":
            self._write(f" {node.net_type}")
        if node.signed:
            self._write(" signed")
        if node.range:
            self._write(" ")
            self._visit(node.range)
        self._write(f" {node.name}")

        # Array dimensions
        for dim in node.array_dims:
            self._write(" ")
            self._visit(dim)

    def _gen_NetDecl(self, node: NetDecl):
        """Generate wire/reg declaration."""
        self._write(node.net_type)
        if node.signed:
            self._write(" signed")
        if node.range:
            self._write(" ")
            self._visit(node.range)
        self._write(f" {node.name}")

        # Array dimensions
        for dim in node.array_dims:
            self._write(" ")
            self._visit(dim)

        if node.init_value:
            self._write(" = ")
            self._visit(node.init_value)

        self._writeln(";")

    def _gen_ParamDecl(self, node: ParamDecl):
        """Generate parameter/localparam declaration."""
        self._write(node.kind)
        if node.signed:
            self._write(" signed")
        if node.range:
            self._write(" ")
            self._visit(node.range)
        self._write(f" {node.name}")
        if node.value:
            self._write(" = ")
            self._visit(node.value)
        self._writeln(";")

    def _gen_IntegerDecl(self, node: IntegerDecl):
        """Generate integer declaration."""
        self._writeln(f"integer {node.name};")

    def _gen_RealDecl(self, node: RealDecl):
        """Generate real/realtime declaration."""
        self._write(node.kind)
        self._write(f" {node.name}")
        if node.init_value:
            self._write(" = ")
            self._visit(node.init_value)
        self._writeln(";")

    def _gen_TimeDecl(self, node: TimeDecl):
        """Generate time declaration."""
        self._write(f"time {node.name}")
        if node.init_value:
            self._write(" = ")
            self._visit(node.init_value)
        self._writeln(";")

    def _gen_EventDecl(self, node: EventDecl):
        """Generate event declaration."""
        self._writeln(f"event {node.name};")

    def _gen_Range(self, node: Range):
        """Generate bit range [msb:lsb]."""
        self._write("[")
        self._visit(node.msb)
        self._write(":")
        self._visit(node.lsb)
        self._write("]")

    # ============================================================
    # Module items
    # ============================================================

    def _gen_ContinuousAssign(self, node: ContinuousAssign):
        """Generate continuous assignment."""
        self._write("assign ")
        self._visit(node.lhs)
        self._write(" = ")
        self._visit(node.rhs)
        self._writeln(";")

    def _gen_AlwaysBlock(self, node: AlwaysBlock):
        """Generate always block."""
        self._write("always @(")
        if node.is_star:
            self._write("*")
        else:
            for i, sens in enumerate(node.sensitivity):
                if i > 0:
                    self._write(" or ")
                self._visit(sens)
        self._writeln(") begin")

        self.indent_level += 1
        for stmt in node.body:
            self._indent()
            self._visit(stmt)
        self.indent_level -= 1

        self._indent()
        self._writeln("end")

    def _gen_InitialBlock(self, node: InitialBlock):
        """Generate initial block."""
        self._writeln("initial begin")

        self.indent_level += 1
        for stmt in node.body:
            self._indent()
            self._visit(stmt)
        self.indent_level -= 1

        self._indent()
        self._writeln("end")

    def _gen_SensItem(self, node: SensItem):
        """Generate sensitivity list item."""
        if node.edge:
            self._write(f"{node.edge} ")
        self._visit(node.signal)

    def _gen_ModuleInstance(self, node: ModuleInstance):
        """Generate module instantiation."""
        self._write(f"{node.module_name} ")

        # Parameter overrides
        if node.params:
            self._write("#(")
            for i, param in enumerate(node.params):
                if i > 0:
                    self._write(", ")
                self._visit(param)
            self._write(") ")

        self._write(f"{node.instance_name} (")

        # Port connections
        for i, port in enumerate(node.ports):
            if i > 0:
                self._write(", ")
            self._visit(port)

        self._writeln(");")

    def _gen_PortConnection(self, node: PortConnection):
        """Generate port connection."""
        self._write(f".{node.port_name}(")
        if node.expr:
            self._visit(node.expr)
        self._write(")")

    def _gen_GenerateBlock(self, node: GenerateBlock):
        """Generate generate block."""
        self._writeln("generate")
        self.indent_level += 1
        for item in node.items:
            self._indent()
            self._visit(item)
        self.indent_level -= 1
        self._indent()
        self._writeln("endgenerate")

    def _gen_SpecifyBlock(self, node: SpecifyBlock):
        """Generate specify block (empty placeholder)."""
        self._writeln("specify")
        self._indent()
        self._writeln("endspecify")

    # ============================================================
    # Statements
    # ============================================================

    def _gen_BlockingAssign(self, node: BlockingAssign):
        """Generate blocking assignment."""
        self._visit(node.lhs)
        self._write(" = ")
        self._visit(node.rhs)
        self._writeln(";")

    def _gen_NonBlockingAssign(self, node: NonBlockingAssign):
        """Generate non-blocking assignment."""
        self._visit(node.lhs)
        self._write(" <= ")
        self._visit(node.rhs)
        self._writeln(";")

    def _gen_IfStatement(self, node: IfStatement):
        """Generate if statement."""
        self._write("if (")
        self._visit(node.cond)
        self._writeln(") begin")

        self.indent_level += 1
        for stmt in node.then_body:
            self._indent()
            self._visit(stmt)
        self.indent_level -= 1

        self._indent()
        if node.else_body:
            self._writeln("end else begin")
            self.indent_level += 1
            for stmt in node.else_body:
                self._indent()
                self._visit(stmt)
            self.indent_level -= 1
            self._indent()
        self._writeln("end")

    def _gen_CaseStatement(self, node: CaseStatement):
        """Generate case statement."""
        self._write(f"{node.kind} (")
        self._visit(node.expr)
        self._writeln(")")

        self.indent_level += 1
        for item in node.items:
            self._visit(item)

        if node.default:
            self._indent()
            self._writeln("default: begin")
            self.indent_level += 1
            for stmt in node.default:
                self._indent()
                self._visit(stmt)
            self.indent_level -= 1
            self._indent()
            self._writeln("end")

        self.indent_level -= 1
        self._indent()
        self._writeln("endcase")

    def _gen_CaseItem(self, node: CaseItem):
        """Generate case item."""
        self._indent()
        for i, val in enumerate(node.values):
            if i > 0:
                self._write(", ")
            self._visit(val)
        self._writeln(": begin")

        self.indent_level += 1
        for stmt in node.body:
            self._indent()
            self._visit(stmt)
        self.indent_level -= 1

        self._indent()
        self._writeln("end")

    def _gen_ForStatement(self, node: ForStatement):
        """Generate for loop."""
        self._write("for (")
        # Init (without semicolon)
        if isinstance(node.init, BlockingAssign):
            self._visit(node.init.lhs)
            self._write(" = ")
            self._visit(node.init.rhs)
        self._write("; ")
        # Condition
        self._visit(node.cond)
        self._write("; ")
        # Update (without semicolon)
        if isinstance(node.update, BlockingAssign):
            self._visit(node.update.lhs)
            self._write(" = ")
            self._visit(node.update.rhs)
        self._writeln(") begin")

        self.indent_level += 1
        for stmt in node.body:
            self._indent()
            self._visit(stmt)
        self.indent_level -= 1

        self._indent()
        self._writeln("end")

    def _gen_SystemTaskCall(self, node: SystemTaskCall):
        """Generate system task call."""
        self._write(node.name)
        if node.args:
            self._write("(")
            for i, arg in enumerate(node.args):
                if i > 0:
                    self._write(", ")
                self._visit(arg)
            self._write(")")
        self._writeln(";")

    def _gen_Block(self, node: Block):
        """Generate begin/end block."""
        if node.name:
            self._writeln(f"begin : {node.name}")
        else:
            self._writeln("begin")

        self.indent_level += 1
        for stmt in node.stmts:
            self._indent()
            self._visit(stmt)
        self.indent_level -= 1

        self._indent()
        self._writeln("end")

    # ============================================================
    # Expressions
    # ============================================================

    def _gen_NumberLiteral(self, node: NumberLiteral):
        """Generate number literal."""
        self._write(node.raw)

    def _gen_StringLiteral(self, node: StringLiteral):
        """Generate string literal."""
        self._write(f'"{node.value}"')

    def _gen_Identifier(self, node: Identifier):
        """Generate identifier."""
        self._write(node.name)

    def _gen_BitSelect(self, node: BitSelect):
        """Generate bit select."""
        self._visit(node.target)
        self._write("[")
        self._visit(node.msb)
        if node.lsb is not None:
            if node.select_type == "plus":
                self._write("+:")
            elif node.select_type == "minus":
                self._write("-:")
            else:
                self._write(":")
            self._visit(node.lsb)
        self._write("]")

    def _gen_UnaryOp(self, node: UnaryOp):
        """Generate unary operation."""
        self._write(node.op)
        self._visit(node.operand)

    def _gen_BinaryOp(self, node: BinaryOp):
        """Generate binary operation."""
        self._write("(")
        self._visit(node.left)
        self._write(f" {node.op} ")
        self._visit(node.right)
        self._write(")")

    def _gen_TernaryOp(self, node: TernaryOp):
        """Generate ternary operation."""
        self._write("(")
        self._visit(node.cond)
        self._write(" ? ")
        self._visit(node.true_val)
        self._write(" : ")
        self._visit(node.false_val)
        self._write(")")

    def _gen_Concat(self, node: Concat):
        """Generate concatenation."""
        self._write("{")
        for i, part in enumerate(node.parts):
            if i > 0:
                self._write(", ")
            self._visit(part)
        self._write("}")

    def _gen_Repeat(self, node: Repeat):
        """Generate replication."""
        self._write("{")
        self._visit(node.count)
        self._write("{")
        self._visit(node.value)
        self._write("}}")

    def _gen_FuncCall(self, node: FuncCall):
        """Generate function call."""
        self._write(f"{node.name}(")
        for i, arg in enumerate(node.args):
            if i > 0:
                self._write(", ")
            self._visit(arg)
        self._write(")")


def generate_verilog(node: ASTNode, indent_str: str = "    ") -> str:
    """
    Generate Verilog code from an AST node.

    Args:
        node: The AST node to generate code from
        indent_str: String to use for indentation (default: 4 spaces)

    Returns:
        Generated Verilog source code
    """
    generator = VerilogCodeGenerator(indent_str=indent_str)
    return generator.generate(node)

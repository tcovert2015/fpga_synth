"""
Elaborator — Converts AST to Netlist IR.

Takes a parsed Verilog AST and elaborates it into a flattened netlist:
- Resolves parameters and localparams
- Expands generate blocks
- Converts expressions to netlist cells
- Handles module hierarchy (for now, single module)

This is the first graph transformation: Tree (AST) → DAG (Netlist).
"""

from __future__ import annotations
from typing import Optional, Dict
from fpga_synth.hdl_parser.ast_nodes import *
from fpga_synth.ir.netlist import Netlist, Cell, Net, Pin
from fpga_synth.ir.types import CellOp, BitWidth, PortDir, NetType


class ElaborationError(Exception):
    """Error during elaboration."""
    pass


class Elaborator:
    """
    Elaborates an AST into a netlist.

    Current scope: Single module, basic combinational logic.
    Future: Module hierarchy, sequential logic, memories.
    """

    def __init__(self):
        self.netlist: Optional[Netlist] = None
        self.net_map: Dict[str, Net] = {}  # signal name → Net
        self.parameters: Dict[str, int] = {}  # parameter name → value

    def elaborate(self, ast: SourceFile) -> Netlist:
        """
        Elaborate an AST into a netlist.

        Args:
            ast: Parsed Verilog source

        Returns:
            Elaborated netlist

        Raises:
            ElaborationError: If elaboration fails
        """
        if len(ast.modules) == 0:
            raise ElaborationError("No modules found in AST")

        # For now, elaborate only the first module
        # TODO: Handle module hierarchy
        module = ast.modules[0]
        return self.elaborate_module(module)

    def elaborate_module(self, module: Module) -> Netlist:
        """Elaborate a single module."""
        self.netlist = Netlist(name=module.name)
        self.net_map = {}
        self.parameters = {}

        # Phase 1: Resolve parameters
        self._resolve_parameters(module)

        # Phase 2: Create primary I/O
        self._elaborate_ports(module)

        # Phase 3: Create nets for declared signals
        self._elaborate_declarations(module)

        # Phase 4: Elaborate module body
        self._elaborate_body(module)

        return self.netlist

    def _resolve_parameters(self, module: Module):
        """Resolve all parameter values."""
        # Module-level parameters
        for param in module.params:
            if param.value:
                self.parameters[param.name] = self._eval_const_expr(param.value)

        # Body parameters (localparam)
        for item in module.body:
            if isinstance(item, ParamDecl) and item.value:
                self.parameters[item.name] = self._eval_const_expr(item.value)

    def _elaborate_ports(self, module: Module):
        """Create MODULE_INPUT and MODULE_OUTPUT cells for ports."""
        for port in module.ports:
            width = self._get_width(port.range)

            if port.direction == "input":
                # Create input cell
                cell = Cell(name=port.name, op=CellOp.MODULE_INPUT)
                out_pin = cell.add_output("Y", width)
                self.netlist.add_cell(cell)
                self.netlist.inputs[port.name] = cell

                # Create net for this input
                net = Net(name=port.name, width=width)
                net.set_driver(out_pin)
                self.netlist.add_net(net)
                self.net_map[port.name] = net

            elif port.direction == "output":
                # Create output cell (will be connected later)
                cell = Cell(name=port.name, op=CellOp.MODULE_OUTPUT)
                in_pin = cell.add_input("A", width)
                self.netlist.add_cell(cell)
                self.netlist.outputs[port.name] = cell

                # Note: Output net is created when the driving logic is elaborated

    def _elaborate_declarations(self, module: Module):
        """Create nets for wire/reg declarations."""
        for item in module.body:
            if isinstance(item, NetDecl):
                width = self._get_width(item.range)

                # Create net if not already created (e.g., by port)
                if item.name not in self.net_map:
                    net = Net(name=item.name, width=width)
                    self.netlist.add_net(net)
                    self.net_map[item.name] = net

    def _elaborate_body(self, module: Module):
        """Elaborate all module body items."""
        for item in module.body:
            if isinstance(item, ContinuousAssign):
                self._elaborate_assign(item)
            # TODO: AlwaysBlock, InitialBlock, ModuleInstance, etc.

    def _elaborate_assign(self, assign: ContinuousAssign):
        """
        Elaborate a continuous assignment.

        Creates cells for the RHS expression and connects to LHS net.
        """
        # Get the LHS net
        if not isinstance(assign.lhs, Identifier):
            raise ElaborationError(f"LHS of assign must be identifier, got {type(assign.lhs).__name__}")

        lhs_name = assign.lhs.name
        if lhs_name not in self.net_map:
            # Create net if it doesn't exist (implicit wire declaration)
            net = Net(name=lhs_name, width=BitWidth(0, 0))
            self.netlist.add_net(net)
            self.net_map[lhs_name] = net

        lhs_net = self.net_map[lhs_name]

        # Elaborate RHS expression to get output net
        rhs_net = self._elaborate_expr(assign.rhs)

        # Connect RHS output to LHS
        # If RHS driver exists, connect it to LHS net
        if rhs_net.driver:
            lhs_net.set_driver(rhs_net.driver)
            # Update driver pin's net to point to LHS net
            rhs_net.driver.net = lhs_net

    def _elaborate_expr(self, expr: Expr) -> Net:
        """
        Elaborate an expression into cells.

        Returns the net containing the expression's output.
        """
        if isinstance(expr, NumberLiteral):
            return self._elaborate_const(expr)

        elif isinstance(expr, Identifier):
            # Reference to existing signal
            if expr.name not in self.net_map:
                raise ElaborationError(f"Undefined signal: {expr.name}")
            return self.net_map[expr.name]

        elif isinstance(expr, BinaryOp):
            return self._elaborate_binary_op(expr)

        elif isinstance(expr, UnaryOp):
            return self._elaborate_unary_op(expr)

        elif isinstance(expr, TernaryOp):
            return self._elaborate_ternary_op(expr)

        elif isinstance(expr, Concat):
            return self._elaborate_concat(expr)

        else:
            raise ElaborationError(f"Unsupported expression type: {type(expr).__name__}")

    def _elaborate_const(self, lit: NumberLiteral) -> Net:
        """Create a CONST cell for a number literal."""
        cell = Cell(name=f"const_{lit.value}", op=CellOp.CONST)
        cell.attributes["value"] = lit.value
        cell.attributes["width"] = lit.width

        width = BitWidth.from_width(lit.width)
        out_pin = cell.add_output("Y", width)

        self.netlist.add_cell(cell)

        # Create output net
        net = Net(name=f"_const_{cell.id}", width=width)
        net.set_driver(out_pin)
        self.netlist.add_net(net)

        return net

    def _elaborate_binary_op(self, expr: BinaryOp) -> Net:
        """Elaborate a binary operation."""
        # Map Verilog operators to CellOp
        op_map = {
            "&": CellOp.AND,
            "|": CellOp.OR,
            "^": CellOp.XOR,
            "+": CellOp.ADD,
            "-": CellOp.SUB,
            "*": CellOp.MUL,
            "==": CellOp.EQ,
            "!=": CellOp.NEQ,
            "<": CellOp.LT,
            "<=": CellOp.LE,
            ">": CellOp.GT,
            ">=": CellOp.GE,
            "<<": CellOp.SHL,
            ">>": CellOp.SHR,
        }

        if expr.op not in op_map:
            raise ElaborationError(f"Unsupported binary operator: {expr.op}")

        cell_op = op_map[expr.op]

        # Elaborate operands
        left_net = self._elaborate_expr(expr.left)
        right_net = self._elaborate_expr(expr.right)

        # Create cell
        cell = Cell(name=f"{cell_op.name.lower()}_{left_net.name}_{right_net.name}", op=cell_op)

        # Determine output width (simplified - needs proper width inference)
        out_width = max(left_net.width.width, right_net.width.width)
        if cell_op in (CellOp.EQ, CellOp.NEQ, CellOp.LT, CellOp.LE, CellOp.GT, CellOp.GE):
            out_width = 1  # Comparison operators return 1 bit

        # Add pins
        a_pin = cell.add_input("A", left_net.width)
        b_pin = cell.add_input("B", right_net.width)
        y_pin = cell.add_output("Y", BitWidth.from_width(out_width))

        # Connect inputs
        left_net.add_sink(a_pin)
        right_net.add_sink(b_pin)

        self.netlist.add_cell(cell)

        # Create output net
        out_net = Net(name=f"_{cell.op.name.lower()}_{cell.id}", width=BitWidth.from_width(out_width))
        out_net.set_driver(y_pin)
        self.netlist.add_net(out_net)

        return out_net

    def _elaborate_unary_op(self, expr: UnaryOp) -> Net:
        """Elaborate a unary operation."""
        op_map = {
            "~": CellOp.NOT,
            "!": CellOp.NOT,  # Logical NOT - same as bitwise for single bit
            "-": CellOp.NEG,
            "&": CellOp.REDUCE_AND,
            "|": CellOp.REDUCE_OR,
            "^": CellOp.REDUCE_XOR,
        }

        if expr.op not in op_map:
            raise ElaborationError(f"Unsupported unary operator: {expr.op}")

        cell_op = op_map[expr.op]

        # Elaborate operand
        operand_net = self._elaborate_expr(expr.operand)

        # Create cell
        cell = Cell(name=f"{cell_op.name.lower()}_{operand_net.name}", op=cell_op)

        # Determine output width
        if cell_op in (CellOp.REDUCE_AND, CellOp.REDUCE_OR, CellOp.REDUCE_XOR):
            out_width = 1
        else:
            out_width = operand_net.width.width

        # Add pins
        a_pin = cell.add_input("A", operand_net.width)
        y_pin = cell.add_output("Y", BitWidth.from_width(out_width))

        # Connect input
        operand_net.add_sink(a_pin)

        self.netlist.add_cell(cell)

        # Create output net
        out_net = Net(name=f"_{cell.op.name.lower()}_{cell.id}", width=BitWidth.from_width(out_width))
        out_net.set_driver(y_pin)
        self.netlist.add_net(out_net)

        return out_net

    def _elaborate_ternary_op(self, expr: TernaryOp) -> Net:
        """Elaborate a ternary (conditional) operation as a MUX."""
        # Elaborate condition and operands
        cond_net = self._elaborate_expr(expr.cond)
        true_net = self._elaborate_expr(expr.true_val)
        false_net = self._elaborate_expr(expr.false_val)

        # Create MUX cell: out = sel ? true : false
        cell = Cell(name=f"mux_{cond_net.name}", op=CellOp.MUX)

        # MUX(sel, false, true) - note the order!
        sel_pin = cell.add_input("S", cond_net.width)
        a_pin = cell.add_input("A", false_net.width)
        b_pin = cell.add_input("B", true_net.width)

        out_width = max(true_net.width.width, false_net.width.width)
        y_pin = cell.add_output("Y", BitWidth.from_width(out_width))

        # Connect
        cond_net.add_sink(sel_pin)
        false_net.add_sink(a_pin)
        true_net.add_sink(b_pin)

        self.netlist.add_cell(cell)

        # Create output net
        out_net = Net(name=f"_mux_{cell.id}", width=BitWidth.from_width(out_width))
        out_net.set_driver(y_pin)
        self.netlist.add_net(out_net)

        return out_net

    def _elaborate_concat(self, expr: Concat) -> Net:
        """Elaborate concatenation {a, b, c}."""
        # Elaborate all parts
        part_nets = [self._elaborate_expr(part) for part in expr.parts]

        # Create CONCAT cell
        cell = Cell(name=f"concat_{len(part_nets)}", op=CellOp.CONCAT)

        # Add input pins for each part
        total_width = 0
        for i, pnet in enumerate(part_nets):
            pin = cell.add_input(f"A{i}", pnet.width)
            pnet.add_sink(pin)
            total_width += pnet.width.width

        # Add output
        y_pin = cell.add_output("Y", BitWidth.from_width(total_width))

        self.netlist.add_cell(cell)

        # Create output net
        out_net = Net(name=f"_concat_{cell.id}", width=BitWidth.from_width(total_width))
        out_net.set_driver(y_pin)
        self.netlist.add_net(out_net)

        return out_net

    def _get_width(self, range_node: Optional[Range]) -> BitWidth:
        """Extract bit width from a Range node."""
        if range_node is None:
            return BitWidth(0, 0)  # Single bit

        msb = self._eval_const_expr(range_node.msb)
        lsb = self._eval_const_expr(range_node.lsb)
        return BitWidth(msb, lsb)

    def _eval_const_expr(self, expr: Expr) -> int:
        """Evaluate a constant expression (for parameters, ranges)."""
        if isinstance(expr, NumberLiteral):
            return expr.value

        elif isinstance(expr, Identifier):
            # Look up parameter
            if expr.name in self.parameters:
                return self.parameters[expr.name]
            raise ElaborationError(f"Undefined parameter: {expr.name}")

        elif isinstance(expr, BinaryOp):
            left = self._eval_const_expr(expr.left)
            right = self._eval_const_expr(expr.right)

            ops = {
                "+": lambda a, b: a + b,
                "-": lambda a, b: a - b,
                "*": lambda a, b: a * b,
                "/": lambda a, b: a // b,
                "%": lambda a, b: a % b,
                "&": lambda a, b: a & b,
                "|": lambda a, b: a | b,
                "^": lambda a, b: a ^ b,
                "<<": lambda a, b: a << b,
                ">>": lambda a, b: a >> b,
            }

            if expr.op in ops:
                return ops[expr.op](left, right)

        raise ElaborationError(f"Cannot evaluate non-constant expression: {type(expr).__name__}")


def elaborate(ast: SourceFile) -> Netlist:
    """
    Convenience function to elaborate an AST.

    Args:
        ast: Parsed Verilog source

    Returns:
        Elaborated netlist
    """
    elaborator = Elaborator()
    return elaborator.elaborate(ast)

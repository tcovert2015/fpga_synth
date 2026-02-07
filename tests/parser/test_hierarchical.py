"""
Tests for hierarchical names (dotted identifiers).

Part of Phase 1.11 of the TODO list.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.ast_nodes import *


def test_hierarchical_signal_reference():
    """Test: hierarchical signal reference in assignment"""
    verilog = """
    module test;
        wire result;
        assign result = top.sub.signal;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    assigns = [item for item in mod.body if isinstance(item, ContinuousAssign)]
    assert len(assigns) == 1

    # RHS should be a hierarchical identifier
    assert isinstance(assigns[0].rhs, Identifier)
    assert assigns[0].rhs.name == "top.sub.signal"
    print("✓ test_hierarchical_signal_reference")


def test_nested_hierarchical_reference():
    """Test: deeply nested hierarchical reference"""
    verilog = """
    module test;
        wire result;
        assign result = top.level1.level2.level3.signal;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    assigns = [item for item in mod.body if isinstance(item, ContinuousAssign)]
    assert isinstance(assigns[0].rhs, Identifier)
    assert assigns[0].rhs.name == "top.level1.level2.level3.signal"
    print("✓ test_nested_hierarchical_reference")


def test_hierarchical_in_expression():
    """Test: hierarchical reference in expression"""
    verilog = """
    module test;
        wire [7:0] result;
        assign result = module1.data + module2.data;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    assigns = [item for item in mod.body if isinstance(item, ContinuousAssign)]
    assert isinstance(assigns[0].rhs, BinaryOp)

    # Left and right operands should be hierarchical identifiers
    assert isinstance(assigns[0].rhs.left, Identifier)
    assert assigns[0].rhs.left.name == "module1.data"
    assert isinstance(assigns[0].rhs.right, Identifier)
    assert assigns[0].rhs.right.name == "module2.data"
    print("✓ test_hierarchical_in_expression")


def test_hierarchical_with_bit_select():
    """Test: hierarchical reference with bit select"""
    verilog = """
    module test;
        wire bit_val;
        assign bit_val = top.sub.bus[5];
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    assigns = [item for item in mod.body if isinstance(item, ContinuousAssign)]

    # RHS should be a bit select
    assert isinstance(assigns[0].rhs, BitSelect)
    # Target should be hierarchical identifier
    assert isinstance(assigns[0].rhs.target, Identifier)
    assert assigns[0].rhs.target.name == "top.sub.bus"
    print("✓ test_hierarchical_with_bit_select")


def test_hierarchical_with_part_select():
    """Test: hierarchical reference with part select"""
    verilog = """
    module test;
        wire [3:0] nibble;
        assign nibble = top.submod.data[7:4];
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    assigns = [item for item in mod.body if isinstance(item, ContinuousAssign)]

    # RHS should be a bit select (part select)
    assert isinstance(assigns[0].rhs, BitSelect)
    # Target should be hierarchical identifier
    assert isinstance(assigns[0].rhs.target, Identifier)
    assert assigns[0].rhs.target.name == "top.submod.data"
    print("✓ test_hierarchical_with_part_select")


def test_hierarchical_parameter_access():
    """Test: hierarchical parameter access"""
    verilog = """
    module test;
        wire [top.submod.WIDTH-1:0] data;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    wires = [item for item in mod.body if isinstance(item, NetDecl)]
    assert len(wires) == 1

    # MSB should be an expression with hierarchical identifier
    msb = wires[0].range.msb
    assert isinstance(msb, BinaryOp)
    assert msb.op == "-"
    # Left side should be hierarchical identifier
    assert isinstance(msb.left, Identifier)
    assert msb.left.name == "top.submod.WIDTH"
    print("✓ test_hierarchical_parameter_access")


def test_hierarchical_in_always_block():
    """Test: hierarchical reference in always block"""
    verilog = """
    module test;
        reg [7:0] local_data;
        always @(posedge clk) begin
            local_data <= other_module.output_data;
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    always_blocks = [item for item in mod.body if isinstance(item, AlwaysBlock)]
    assert len(always_blocks) == 1

    # Find the assignment
    assert len(always_blocks[0].body) > 0
    assign_stmt = always_blocks[0].body[0]
    assert isinstance(assign_stmt, NonBlockingAssign)

    # RHS should be hierarchical identifier
    assert isinstance(assign_stmt.rhs, Identifier)
    assert assign_stmt.rhs.name == "other_module.output_data"
    print("✓ test_hierarchical_in_always_block")


def test_mixed_local_and_hierarchical():
    """Test: mix of local and hierarchical references"""
    verilog = """
    module test;
        wire a;
        wire b;
        assign a = local_signal;
        assign b = top.submod.remote_signal;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    assigns = [item for item in mod.body if isinstance(item, ContinuousAssign)]
    assert len(assigns) == 2

    # First assignment uses local reference
    assert isinstance(assigns[0].rhs, Identifier)
    assert assigns[0].rhs.name == "local_signal"

    # Second assignment uses hierarchical reference
    assert isinstance(assigns[1].rhs, Identifier)
    assert assigns[1].rhs.name == "top.submod.remote_signal"
    print("✓ test_mixed_local_and_hierarchical")


def run_all():
    """Run all hierarchical name tests"""
    tests = [
        test_hierarchical_signal_reference,
        test_nested_hierarchical_reference,
        test_hierarchical_in_expression,
        test_hierarchical_with_bit_select,
        test_hierarchical_with_part_select,
        test_hierarchical_parameter_access,
        test_hierarchical_in_always_block,
        test_mixed_local_and_hierarchical,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
            import traceback
            traceback.print_exc()

    print(f"\n{'='*50}")
    print(f"Hierarchical Name Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running hierarchical name tests...\n")
    run_all()

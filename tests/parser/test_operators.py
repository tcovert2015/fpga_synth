"""
Tests for operators and expressions.

Part of Phase 1.10 of the TODO list.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.ast_nodes import *


def test_indexed_part_select_ascending():
    """Test: indexed part-select with +: (ascending)"""
    verilog = """
    module test;
        wire [31:0] data;
        wire [7:0] byte_val;
        assign byte_val = data[8 +: 8];
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    assigns = [item for item in mod.body if isinstance(item, ContinuousAssign)]
    assert len(assigns) == 1

    # RHS should be a bit select with plus type
    assert isinstance(assigns[0].rhs, BitSelect)
    assert assigns[0].rhs.select_type == "plus"

    # Target should be 'data'
    assert isinstance(assigns[0].rhs.target, Identifier)
    assert assigns[0].rhs.target.name == "data"

    # msb is base (8), lsb is width (8)
    assert isinstance(assigns[0].rhs.msb, NumberLiteral)
    assert assigns[0].rhs.msb.value == 8
    assert isinstance(assigns[0].rhs.lsb, NumberLiteral)
    assert assigns[0].rhs.lsb.value == 8

    print("✓ test_indexed_part_select_ascending")


def test_indexed_part_select_descending():
    """Test: indexed part-select with -: (descending)"""
    verilog = """
    module test;
        wire [31:0] data;
        wire [7:0] byte_val;
        assign byte_val = data[15 -: 8];
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    assigns = [item for item in mod.body if isinstance(item, ContinuousAssign)]
    assert len(assigns) == 1

    # RHS should be a bit select with minus type
    assert isinstance(assigns[0].rhs, BitSelect)
    assert assigns[0].rhs.select_type == "minus"

    # msb is base (15), lsb is width (8)
    assert assigns[0].rhs.msb.value == 15
    assert assigns[0].rhs.lsb.value == 8

    print("✓ test_indexed_part_select_descending")


def test_indexed_part_select_with_expression():
    """Test: indexed part-select with expression for base"""
    verilog = """
    module test;
        wire [31:0] data;
        wire [3:0] idx;
        wire [7:0] byte_val;
        assign byte_val = data[idx*8 +: 8];
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    assigns = [item for item in mod.body if isinstance(item, ContinuousAssign)]
    # Should be the third assignment (after wire declarations)
    assign = None
    for item in assigns:
        if isinstance(item.rhs, BitSelect):
            assign = item
            break

    assert assign is not None
    assert isinstance(assign.rhs, BitSelect)
    assert assign.rhs.select_type == "plus"

    # Base should be a binary operation (idx*8)
    assert isinstance(assign.rhs.msb, BinaryOp)
    assert assign.rhs.msb.op == "*"

    print("✓ test_indexed_part_select_with_expression")


def test_normal_part_select_still_works():
    """Test: normal part-select [msb:lsb] still works"""
    verilog = """
    module test;
        wire [31:0] data;
        wire [7:0] byte_val;
        assign byte_val = data[15:8];
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    assigns = [item for item in mod.body if isinstance(item, ContinuousAssign)]
    assert len(assigns) == 1

    # RHS should be a bit select with normal type
    assert isinstance(assigns[0].rhs, BitSelect)
    assert assigns[0].rhs.select_type == "normal"

    # msb is 15, lsb is 8
    assert assigns[0].rhs.msb.value == 15
    assert assigns[0].rhs.lsb.value == 8

    print("✓ test_normal_part_select_still_works")


def test_single_bit_select_still_works():
    """Test: single bit select [idx] still works"""
    verilog = """
    module test;
        wire [7:0] data;
        wire bit_val;
        assign bit_val = data[3];
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    assigns = [item for item in mod.body if isinstance(item, ContinuousAssign)]
    assert len(assigns) == 1

    # RHS should be a bit select with normal type and no lsb
    assert isinstance(assigns[0].rhs, BitSelect)
    assert assigns[0].rhs.select_type == "normal"
    assert assigns[0].rhs.lsb is None
    assert assigns[0].rhs.msb.value == 3

    print("✓ test_single_bit_select_still_works")


def test_unary_reduction_operators():
    """Test: unary reduction operators (&, |, ^, etc.)"""
    verilog = """
    module test;
        wire [7:0] data;
        wire and_reduce;
        wire or_reduce;
        wire xor_reduce;
        assign and_reduce = &data;
        assign or_reduce = |data;
        assign xor_reduce = ^data;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    assigns = [item for item in mod.body if isinstance(item, ContinuousAssign)]
    assert len(assigns) == 3

    # All should be unary operations
    assert isinstance(assigns[0].rhs, UnaryOp)
    assert assigns[0].rhs.op == "&"

    assert isinstance(assigns[1].rhs, UnaryOp)
    assert assigns[1].rhs.op == "|"

    assert isinstance(assigns[2].rhs, UnaryOp)
    assert assigns[2].rhs.op == "^"

    print("✓ test_unary_reduction_operators")


def test_signed_operations():
    """Test: signed keyword in declarations"""
    verilog = """
    module test;
        wire signed [7:0] signed_data;
        reg signed [15:0] signed_reg;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    wires = [item for item in mod.body if isinstance(item, NetDecl) and item.net_type == "wire"]
    regs = [item for item in mod.body if isinstance(item, NetDecl) and item.net_type == "reg"]

    assert len(wires) == 1
    assert wires[0].signed == True

    assert len(regs) == 1
    assert regs[0].signed == True

    print("✓ test_signed_operations")


def run_all():
    """Run all operator tests"""
    tests = [
        test_indexed_part_select_ascending,
        test_indexed_part_select_descending,
        test_indexed_part_select_with_expression,
        test_normal_part_select_still_works,
        test_single_bit_select_still_works,
        test_unary_reduction_operators,
        test_signed_operations,
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
    print(f"Operator Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running operator tests...\n")
    run_all()

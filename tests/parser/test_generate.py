"""
Tests for generate blocks (if-else, case, named blocks).

Part of Phase 1.4 of the TODO list.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.ast_nodes import *


def test_generate_if():
    """Test: generate if conditional"""
    verilog = """
    module test #(parameter USE_FEATURE = 1);
        generate
            if (USE_FEATURE) begin
                wire feature_wire;
            end
        endgenerate
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    gen_blocks = [item for item in mod.body if isinstance(item, GenerateBlock)]
    assert len(gen_blocks) == 1

    gb = gen_blocks[0]
    assert len(gb.items) > 0
    # First item should be an if statement
    assert isinstance(gb.items[0], IfStatement)
    print("✓ test_generate_if")


def test_generate_if_else():
    """Test: generate if-else"""
    verilog = """
    module test #(parameter WIDTH = 8);
        generate
            if (WIDTH == 8) begin
                wire [7:0] data;
            end else begin
                wire [15:0] data;
            end
        endgenerate
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    gen_blocks = [item for item in mod.body if isinstance(item, GenerateBlock)]
    gb = gen_blocks[0]

    if_stmt = gb.items[0]
    assert isinstance(if_stmt, IfStatement)
    assert len(if_stmt.then_body) > 0
    assert len(if_stmt.else_body) > 0
    print("✓ test_generate_if_else")


def test_generate_case():
    """Test: generate case statement"""
    verilog = """
    module test #(parameter MODE = 0);
        generate
            case (MODE)
                0: begin
                    wire mode0_wire;
                end
                1: begin
                    wire mode1_wire;
                end
                default: begin
                    wire default_wire;
                end
            endcase
        endgenerate
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    gen_blocks = [item for item in mod.body if isinstance(item, GenerateBlock)]
    gb = gen_blocks[0]

    case_stmt = gb.items[0]
    assert isinstance(case_stmt, CaseStatement)
    assert len(case_stmt.items) == 2
    assert len(case_stmt.default) > 0
    print("✓ test_generate_case")


def test_named_generate_block():
    """Test: generate block with name"""
    verilog = """
    module test;
        generate
            begin : gen_block_name
                wire internal_signal;
            end
        endgenerate
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    gen_blocks = [item for item in mod.body if isinstance(item, GenerateBlock)]
    gb = gen_blocks[0]

    # Should have a named block
    assert len(gb.items) > 0
    block = gb.items[0]
    assert isinstance(block, Block)
    assert block.name == "gen_block_name"
    print("✓ test_named_generate_block")


def test_generate_for_loop():
    """Test: generate for loop"""
    verilog = """
    module test;
        genvar i;
        generate
            for (i = 0; i < 4; i = i + 1) begin : gen_loop
                wire [7:0] data;
            end
        endgenerate
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    gen_blocks = [item for item in mod.body if isinstance(item, GenerateBlock)]
    gb = gen_blocks[0]

    # Should have a for statement
    for_found = False
    for item in gb.items:
        if isinstance(item, ForStatement):
            for_found = True
            break

    assert for_found
    print("✓ test_generate_for_loop")


def test_nested_generate():
    """Test: nested generate constructs"""
    verilog = """
    module test #(parameter N = 4, parameter M = 2);
        genvar i;
        genvar j;
        generate
            for (i = 0; i < N; i = i + 1) begin : outer
                if (M > 1) begin : inner
                    wire [M-1:0] signal;
                end
            end
        endgenerate
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    gen_blocks = [item for item in mod.body if isinstance(item, GenerateBlock)]
    assert len(gen_blocks) == 1

    gb = gen_blocks[0]
    # Has for loop
    for_stmt = None
    for item in gb.items:
        if isinstance(item, ForStatement):
            for_stmt = item
            break

    assert for_stmt is not None
    # For loop body should contain a named block with if statement
    assert len(for_stmt.body) > 0

    # The body should have a Block (from "begin : outer")
    block = for_stmt.body[0]
    assert isinstance(block, Block)
    assert block.name == "outer"

    # Inside the block should be an if statement
    if_found = False
    for stmt in block.stmts:
        if isinstance(stmt, IfStatement):
            if_found = True
            break

    assert if_found
    print("✓ test_nested_generate")


def test_multiple_genvars():
    """Test: multiple genvar declarations"""
    verilog = """
    module test;
        genvar i;
        genvar j;
        genvar k;
        generate
            for (i = 0; i < 2; i = i + 1) begin
                wire sig;
            end
        endgenerate
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    # Should parse without errors
    gen_blocks = [item for item in mod.body if isinstance(item, GenerateBlock)]
    assert len(gen_blocks) == 1
    print("✓ test_multiple_genvars")


def test_generate_with_module_instances():
    """Test: generate block with module instances"""
    verilog = """
    module test;
        genvar i;
        generate
            for (i = 0; i < 4; i = i + 1) begin : gen_inst
                register reg_inst (
                    .clk(clk),
                    .data(data[i])
                );
            end
        endgenerate
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    gen_blocks = [item for item in mod.body if isinstance(item, GenerateBlock)]
    gb = gen_blocks[0]

    # Should have a for statement
    for_stmt = None
    for item in gb.items:
        if isinstance(item, ForStatement):
            for_stmt = item
            break

    assert for_stmt is not None
    # Body should contain module instance
    assert len(for_stmt.body) > 0
    print("✓ test_generate_with_module_instances")


def run_all():
    """Run all generate tests"""
    tests = [
        test_generate_if,
        test_generate_if_else,
        test_generate_case,
        test_named_generate_block,
        test_generate_for_loop,
        test_nested_generate,
        test_multiple_genvars,
        test_generate_with_module_instances,
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
    print(f"Generate Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running generate block tests...\n")
    run_all()

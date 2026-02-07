"""
Tests for procedural blocks: initial, loops (while, repeat, forever), disable.

Part of Phase 1.2 of the TODO list.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.ast_nodes import *


def test_initial_block():
    """Test: initial begin ... end"""
    verilog = """
    module test;
        reg clk;
        reg data;
        initial begin
            clk = 0;
            data = 1;
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    initial_blocks = [item for item in mod.body if isinstance(item, InitialBlock)]
    assert len(initial_blocks) == 1

    ib = initial_blocks[0]
    assert len(ib.body) >= 1
    print("✓ test_initial_block")


def test_while_loop():
    """Test: while (condition) ..."""
    verilog = """
    module test;
        integer i;
        initial begin
            i = 0;
            while (i < 10) begin
                i = i + 1;
            end
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    initial_blocks = [item for item in mod.body if isinstance(item, InitialBlock)]
    ib = initial_blocks[0]

    # Find while statement in body
    while_found = False
    for stmt in ib.body:
        if isinstance(stmt, WhileStatement):
            while_found = True
            assert stmt.cond is not None
            assert len(stmt.body) > 0
            break

    assert while_found
    print("✓ test_while_loop")


def test_repeat_loop():
    """Test: repeat (N) ..."""
    verilog = """
    module test;
        reg data;
        initial begin
            repeat (10) begin
                data = 1;
            end
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    initial_blocks = [item for item in mod.body if isinstance(item, InitialBlock)]
    ib = initial_blocks[0]

    # Find repeat statement
    repeat_found = False
    for stmt in ib.body:
        if isinstance(stmt, RepeatStatement):
            repeat_found = True
            assert stmt.count is not None
            assert len(stmt.body) > 0
            break

    assert repeat_found
    print("✓ test_repeat_loop")


def test_forever_loop():
    """Test: forever ..."""
    verilog = """
    module test;
        reg clk;
        initial begin
            forever begin
                clk = ~clk;
            end
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    initial_blocks = [item for item in mod.body if isinstance(item, InitialBlock)]
    ib = initial_blocks[0]

    # Find forever statement
    forever_found = False
    for stmt in ib.body:
        if isinstance(stmt, ForeverStatement):
            forever_found = True
            assert len(stmt.body) > 0
            break

    assert forever_found
    print("✓ test_forever_loop")


def test_disable_statement():
    """Test: disable block_name;"""
    verilog = """
    module test;
        initial begin : main_block
            begin : inner_block
                disable inner_block;
            end
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    initial_blocks = [item for item in mod.body if isinstance(item, InitialBlock)]
    ib = initial_blocks[0]

    # Find disable statement (it's nested in a block)
    def find_disable(stmts):
        for stmt in stmts:
            if isinstance(stmt, DisableStatement):
                return stmt
            elif isinstance(stmt, Block):
                result = find_disable(stmt.stmts)
                if result:
                    return result
        return None

    disable_stmt = find_disable(ib.body)
    assert disable_stmt is not None
    assert disable_stmt.target == "inner_block"
    print("✓ test_disable_statement")


def test_nested_loops():
    """Test nested loops"""
    verilog = """
    module test;
        integer i;
        integer j;
        initial begin
            for (i = 0; i < 10; i = i + 1) begin
                while (j < 5) begin
                    j = j + 1;
                end
            end
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    initial_blocks = [item for item in mod.body if isinstance(item, InitialBlock)]
    ib = initial_blocks[0]

    # Find for loop
    for_found = False
    for stmt in ib.body:
        if isinstance(stmt, ForStatement):
            for_found = True
            # Check for while inside for
            while_found = False
            for inner in stmt.body:
                if isinstance(inner, WhileStatement):
                    while_found = True
                    break
            assert while_found
            break

    assert for_found
    print("✓ test_nested_loops")


def test_multiple_initial_blocks():
    """Test multiple initial blocks in one module"""
    verilog = """
    module test;
        reg a;
        reg b;
        initial a = 0;
        initial b = 1;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    initial_blocks = [item for item in mod.body if isinstance(item, InitialBlock)]
    assert len(initial_blocks) == 2
    print("✓ test_multiple_initial_blocks")


def test_initial_with_always():
    """Test initial and always blocks together"""
    verilog = """
    module test;
        reg clk;
        reg enable;
        initial clk = 0;
        always @(*) enable = clk;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    initial_blocks = [item for item in mod.body if isinstance(item, InitialBlock)]
    always_blocks = [item for item in mod.body if isinstance(item, AlwaysBlock)]

    assert len(initial_blocks) == 1
    assert len(always_blocks) == 1
    print("✓ test_initial_with_always")


def run_all():
    """Run all procedural block tests"""
    tests = [
        test_initial_block,
        test_while_loop,
        test_repeat_loop,
        test_forever_loop,
        test_disable_statement,
        test_nested_loops,
        test_multiple_initial_blocks,
        test_initial_with_always,
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
    print(f"Procedural Block Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running procedural block tests...\n")
    run_all()

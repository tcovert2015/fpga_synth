"""
Tests for miscellaneous features: specify blocks, system tasks, compiler directives.

Phases 1.6, 1.7, 1.8 of the TODO list.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.ast_nodes import *


# ============================================================
# Phase 1.6: Specify Blocks
# ============================================================

def test_specify_block_basic():
    """Test: basic specify block (parsed but timing ignored)"""
    verilog = """
    module test;
        specify
            (a => b) = 10;
            (c => d) = (5:6:7);
        endspecify
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    # Should parse without errors
    # Specify block is in body but timing is ignored
    specify_blocks = [item for item in mod.body if isinstance(item, SpecifyBlock)]
    assert len(specify_blocks) == 1

    print("✓ test_specify_block_basic")


def test_module_with_specify_and_logic():
    """Test: module with both specify block and logic"""
    verilog = """
    module test(input a, output b);
        wire w;
        assign b = a & w;

        specify
            (a => b) = 10;
        endspecify
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    # Should have both assigns and specify block
    assigns = [item for item in mod.body if isinstance(item, ContinuousAssign)]
    specify_blocks = [item for item in mod.body if isinstance(item, SpecifyBlock)]

    assert len(assigns) >= 1
    assert len(specify_blocks) == 1

    print("✓ test_module_with_specify_and_logic")


# ============================================================
# Phase 1.7: System Tasks
# ============================================================

def test_system_task_display():
    """Test: $display system task"""
    verilog = """
    module test;
        initial begin
            $display("Hello, World!");
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    initial_blocks = [item for item in mod.body if isinstance(item, InitialBlock)]
    assert len(initial_blocks) == 1

    # Find $display call
    display_found = False
    for stmt in initial_blocks[0].body:
        if isinstance(stmt, SystemTaskCall) and stmt.name == "$display":
            display_found = True
            assert len(stmt.args) == 1  # One string argument
            break

    assert display_found
    print("✓ test_system_task_display")


def test_system_task_finish():
    """Test: $finish system task"""
    verilog = """
    module test;
        initial begin
            $finish;
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    initial_blocks = [item for item in mod.body if isinstance(item, InitialBlock)]

    # Find $finish call
    finish_found = False
    for stmt in initial_blocks[0].body:
        if isinstance(stmt, SystemTaskCall) and stmt.name == "$finish":
            finish_found = True
            assert len(stmt.args) == 0  # No arguments
            break

    assert finish_found
    print("✓ test_system_task_finish")


def test_system_task_with_args():
    """Test: system task with multiple arguments"""
    verilog = """
    module test;
        reg [7:0] data;
        initial begin
            $monitor("data = %h", data);
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    initial_blocks = [item for item in mod.body if isinstance(item, InitialBlock)]

    # Find $monitor call
    monitor_found = False
    for stmt in initial_blocks[0].body:
        if isinstance(stmt, SystemTaskCall) and stmt.name == "$monitor":
            monitor_found = True
            assert len(stmt.args) == 2  # Format string and data
            break

    assert monitor_found
    print("✓ test_system_task_with_args")


def test_multiple_system_tasks():
    """Test: multiple system tasks in sequence"""
    verilog = """
    module test;
        initial begin
            $display("Starting");
            $write("In progress");
            $finish;
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    initial_blocks = [item for item in mod.body if isinstance(item, InitialBlock)]

    # Count system task calls
    system_tasks = [stmt for stmt in initial_blocks[0].body if isinstance(stmt, SystemTaskCall)]
    assert len(system_tasks) == 3

    assert system_tasks[0].name == "$display"
    assert system_tasks[1].name == "$write"
    assert system_tasks[2].name == "$finish"

    print("✓ test_multiple_system_tasks")


# ============================================================
# Phase 1.8: Compiler Directives
# ============================================================

def test_compiler_directive_define():
    """Test: `define directive (skipped in lexer)"""
    verilog = """
    `define WIDTH 8
    module test;
        wire [7:0] data;
    endmodule
    """
    # Should parse without errors - directive is skipped
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    assert mod.name == "test"

    print("✓ test_compiler_directive_define")


def test_compiler_directive_ifdef():
    """Test: `ifdef directive (skipped in lexer)"""
    verilog = """
    module test;
        `ifdef DEBUG
        wire debug_enable;
        `endif
        wire normal_signal;
    endmodule
    """
    # Should parse without errors - directives are skipped
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    # Both wires should be present (ifdef not processed, just skipped)
    wires = [item for item in mod.body if isinstance(item, NetDecl)]
    assert len(wires) >= 1

    print("✓ test_compiler_directive_ifdef")


def test_compiler_directive_timescale():
    """Test: `timescale directive (skipped in lexer)"""
    verilog = """
    `timescale 1ns/1ps
    module test;
        wire w;
    endmodule
    """
    # Should parse without errors
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    assert mod.name == "test"

    print("✓ test_compiler_directive_timescale")


def test_compiler_directive_include():
    """Test: `include directive (skipped in lexer)"""
    verilog = """
    `include "defs.v"
    module test;
        wire w;
    endmodule
    """
    # Should parse without errors - include is skipped
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    assert mod.name == "test"

    print("✓ test_compiler_directive_include")


def run_all():
    """Run all miscellaneous feature tests"""
    tests = [
        # Phase 1.6: Specify blocks
        test_specify_block_basic,
        test_module_with_specify_and_logic,

        # Phase 1.7: System tasks
        test_system_task_display,
        test_system_task_finish,
        test_system_task_with_args,
        test_multiple_system_tasks,

        # Phase 1.8: Compiler directives
        test_compiler_directive_define,
        test_compiler_directive_ifdef,
        test_compiler_directive_timescale,
        test_compiler_directive_include,
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
    print(f"Miscellaneous Feature Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running miscellaneous feature tests...\n")
    run_all()

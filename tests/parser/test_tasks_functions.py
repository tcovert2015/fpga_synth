"""
Tests for task and function declarations.

Part of Phase 1.3 of the TODO list.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.ast_nodes import *


def test_simple_task():
    """Test: task my_task; ... endtask"""
    verilog = """
    module test;
        task my_task;
            input a;
            reg temp;
            begin
                temp = a;
            end
        endtask
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    tasks = [item for item in mod.body if isinstance(item, TaskDecl)]
    assert len(tasks) == 1

    task = tasks[0]
    assert task.name == "my_task"
    assert len(task.inputs) == 1
    assert task.inputs[0].name == "a"
    print("✓ test_simple_task")


def test_task_with_multiple_ports():
    """Test task with inputs, outputs, and inouts"""
    verilog = """
    module test;
        task complex_task;
            input [7:0] data_in;
            output [7:0] data_out;
            inout control;
            begin
                data_out = data_in;
            end
        endtask
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    tasks = [item for item in mod.body if isinstance(item, TaskDecl)]
    task = tasks[0]

    assert task.name == "complex_task"
    assert len(task.inputs) == 1
    assert len(task.outputs) == 1
    assert len(task.inouts) == 1
    assert task.inputs[0].name == "data_in"
    assert task.outputs[0].name == "data_out"
    assert task.inouts[0].name == "control"
    print("✓ test_task_with_multiple_ports")


def test_automatic_task():
    """Test: task automatic my_task; ... endtask"""
    verilog = """
    module test;
        task automatic recursive_task;
            input [7:0] n;
            begin
                if (n > 0)
                    recursive_task(n - 1);
            end
        endtask
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    tasks = [item for item in mod.body if isinstance(item, TaskDecl)]
    task = tasks[0]

    assert task.name == "recursive_task"
    assert task.automatic == True
    print("✓ test_automatic_task")


def test_simple_function():
    """Test: function my_func; ... endfunction"""
    verilog = """
    module test;
        function [7:0] add_one;
            input [7:0] val;
            begin
                add_one = val + 1;
            end
        endfunction
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    functions = [item for item in mod.body if isinstance(item, FunctionDecl)]
    assert len(functions) == 1

    func = functions[0]
    assert func.name == "add_one"
    assert func.return_type is not None  # Has [7:0] return type
    assert len(func.inputs) == 1
    assert func.inputs[0].name == "val"
    print("✓ test_simple_function")


def test_signed_function():
    """Test: function signed [15:0] my_func; ... endfunction"""
    verilog = """
    module test;
        function signed [15:0] multiply;
            input signed [7:0] a;
            input signed [7:0] b;
            begin
                multiply = a * b;
            end
        endfunction
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    functions = [item for item in mod.body if isinstance(item, FunctionDecl)]
    func = functions[0]

    assert func.name == "multiply"
    assert func.signed == True
    assert func.return_type is not None
    assert len(func.inputs) == 2
    print("✓ test_signed_function")


def test_automatic_function():
    """Test: function automatic ..."""
    verilog = """
    module test;
        function automatic [31:0] factorial;
            input [31:0] n;
            begin
                if (n < 2)
                    factorial = 1;
                else
                    factorial = n * factorial(n - 1);
            end
        endfunction
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    functions = [item for item in mod.body if isinstance(item, FunctionDecl)]
    func = functions[0]

    assert func.name == "factorial"
    assert func.automatic == True
    print("✓ test_automatic_function")


def test_task_call():
    """Test task call as a statement"""
    verilog = """
    module test;
        task my_task;
            input a;
            reg temp;
            temp = a;
        endtask

        initial begin
            my_task(1);
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    # Find initial block
    initial_blocks = [item for item in mod.body if isinstance(item, InitialBlock)]
    ib = initial_blocks[0]

    # Find task call in initial block
    task_call_found = False
    for stmt in ib.body:
        if isinstance(stmt, TaskCall):
            task_call_found = True
            assert stmt.name == "my_task"
            assert len(stmt.args) == 1
            break

    assert task_call_found
    print("✓ test_task_call")


def test_function_call_in_expression():
    """Test function call in expression"""
    verilog = """
    module test;
        function [7:0] double;
            input [7:0] x;
            double = x * 2;
        endfunction

        reg [7:0] result;
        initial begin
            result = double(5);
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    # Find initial block
    initial_blocks = [item for item in mod.body if isinstance(item, InitialBlock)]
    ib = initial_blocks[0]

    # Find assignment with function call
    for stmt in ib.body:
        if isinstance(stmt, BlockingAssign):
            # RHS should be a function call
            assert isinstance(stmt.rhs, FuncCall)
            assert stmt.rhs.name == "double"
            assert len(stmt.rhs.args) == 1
            print("✓ test_function_call_in_expression")
            return

    assert False, "Function call not found"


def test_module_with_tasks_and_functions():
    """Test module with both tasks and functions"""
    verilog = """
    module calculator;
        function [15:0] add;
            input [7:0] a;
            input [7:0] b;
            add = a + b;
        endfunction

        task display_result;
            input [15:0] val;
            reg temp;
            temp = val;
        endtask

        reg [15:0] result;
        initial begin
            result = add(10, 20);
            display_result(result);
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    functions = [item for item in mod.body if isinstance(item, FunctionDecl)]
    tasks = [item for item in mod.body if isinstance(item, TaskDecl)]

    assert len(functions) == 1
    assert len(tasks) == 1
    assert functions[0].name == "add"
    assert tasks[0].name == "display_result"
    print("✓ test_module_with_tasks_and_functions")


def run_all():
    """Run all task and function tests"""
    tests = [
        test_simple_task,
        test_task_with_multiple_ports,
        test_automatic_task,
        test_simple_function,
        test_signed_function,
        test_automatic_function,
        test_task_call,
        test_function_call_in_expression,
        test_module_with_tasks_and_functions,
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
    print(f"Task/Function Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running task and function tests...\n")
    run_all()

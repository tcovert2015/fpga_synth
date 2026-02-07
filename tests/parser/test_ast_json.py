"""
Tests for Phase 4.2: AST JSON Serialization.
"""

import sys
import os
import json
import tempfile
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.ast_nodes import *
from fpga_synth.hdl_parser.ast_json import (
    ast_to_dict, ast_to_json, dict_to_ast, json_to_ast,
    ast_to_json_file, ast_from_json_file, ast_to_compact_json
)


def test_simple_module_to_json():
    """Test: Convert simple module to JSON"""
    verilog = """
    module test;
        wire a;
    endmodule
    """
    ast = parse_verilog(verilog)

    # Convert to JSON
    json_str = ast_to_json(ast)

    # Should be valid JSON
    data = json.loads(json_str)
    assert data["_type"] == "SourceFile"
    assert len(data["modules"]) == 1
    assert data["modules"][0]["_type"] == "Module"
    assert data["modules"][0]["name"] == "test"

    print("✓ test_simple_module_to_json")


def test_round_trip_conversion():
    """Test: Convert to JSON and back"""
    verilog = """
    module test;
        wire a;
        assign a = 1;
    endmodule
    """
    ast = parse_verilog(verilog)

    # Convert to JSON and back
    json_str = ast_to_json(ast)
    ast2 = json_to_ast(json_str)

    # Verify structure is preserved
    assert isinstance(ast2, SourceFile)
    assert len(ast2.modules) == 1
    assert ast2.modules[0].name == "test"

    # Check wire declaration
    wire_decls = [item for item in ast2.modules[0].body if isinstance(item, NetDecl)]
    assert len(wire_decls) == 1
    assert wire_decls[0].name == "a"

    # Check assign statement
    assigns = [item for item in ast2.modules[0].body if isinstance(item, ContinuousAssign)]
    assert len(assigns) == 1

    print("✓ test_round_trip_conversion")


def test_complex_ast_to_json():
    """Test: Convert complex AST with expressions"""
    verilog = """
    module test;
        wire [7:0] a;
        wire [7:0] b;
        wire [7:0] c;
        assign c = (a + b) & 8'hFF;
    endmodule
    """
    ast = parse_verilog(verilog)

    json_str = ast_to_json(ast)
    data = json.loads(json_str)

    # Verify module structure
    mod = data["modules"][0]
    assert mod["name"] == "test"

    # Should have continuous assignment with binary operations
    assigns = [item for item in mod["body"] if item["_type"] == "ContinuousAssign"]
    assert len(assigns) == 1

    # Check that expression structure is preserved
    assert "rhs" in assigns[0]
    assert "_type" in assigns[0]["rhs"]

    print("✓ test_complex_ast_to_json")


def test_always_block_to_json():
    """Test: Convert always block to JSON"""
    verilog = """
    module test;
        reg [7:0] count;
        always @(posedge clk) begin
            count <= count + 1;
        end
    endmodule
    """
    ast = parse_verilog(verilog)

    json_str = ast_to_json(ast)
    ast2 = json_to_ast(json_str)

    # Verify always block is preserved
    always_blocks = [item for item in ast2.modules[0].body if isinstance(item, AlwaysBlock)]
    assert len(always_blocks) == 1
    assert len(always_blocks[0].sensitivity) == 1
    assert always_blocks[0].sensitivity[0].edge == "posedge"

    print("✓ test_always_block_to_json")


def test_file_write_and_read():
    """Test: Write to file and read back"""
    verilog = """
    module test;
        wire a;
    endmodule
    """
    ast = parse_verilog(verilog)

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name

    try:
        ast_to_json_file(ast, temp_file)

        # Read back
        ast2 = ast_from_json_file(temp_file)

        # Verify
        assert isinstance(ast2, SourceFile)
        assert len(ast2.modules) == 1
        assert ast2.modules[0].name == "test"

        print("✓ test_file_write_and_read")
    finally:
        os.unlink(temp_file)


def test_module_with_parameters():
    """Test: Module with parameters"""
    verilog = """
    module test #(
        parameter WIDTH = 8
    ) (
        input wire [WIDTH-1:0] data
    );
        localparam DEPTH = 16;
    endmodule
    """
    ast = parse_verilog(verilog)

    json_str = ast_to_json(ast)
    ast2 = json_to_ast(json_str)

    # Verify parameters in mod.body (localparam)
    params_in_body = [item for item in ast2.modules[0].body if isinstance(item, ParamDecl)]
    assert len(params_in_body) >= 1

    # Verify ports
    assert len(ast2.modules[0].ports) >= 1

    print("✓ test_module_with_parameters")


def test_nested_expressions():
    """Test: Nested expressions preserved"""
    verilog = """
    module test;
        wire result;
        assign result = a ? (b + c) : (d - e);
    endmodule
    """
    ast = parse_verilog(verilog)

    json_str = ast_to_json(ast)
    ast2 = json_to_ast(json_str)

    # Verify ternary expression is preserved
    assigns = [item for item in ast2.modules[0].body if isinstance(item, ContinuousAssign)]
    assert len(assigns) == 1
    assert isinstance(assigns[0].rhs, TernaryOp)

    print("✓ test_nested_expressions")


def test_compact_json():
    """Test: Compact JSON format"""
    verilog = """
    module test;
        wire a;
    endmodule
    """
    ast = parse_verilog(verilog)

    # Regular JSON
    json_str = ast_to_json(ast, indent=2)

    # Compact JSON (should be similar length or smaller for simple structures)
    compact_str = ast_to_compact_json(ast, indent=2)

    # Both should be valid JSON
    data1 = json.loads(json_str)
    data2 = json.loads(compact_str)

    # Should have same structure
    assert data1["_type"] == data2["_type"]

    print("✓ test_compact_json")


def test_integration_uart_to_json():
    """Test: Convert UART design to JSON"""
    uart_path = os.path.join(os.path.dirname(__file__), "..", "integration", "uart_tx.v")

    if not os.path.exists(uart_path):
        print("✓ test_integration_uart_to_json (skipped - file not found)")
        return

    with open(uart_path, "r") as f:
        verilog = f.read()

    ast = parse_verilog(verilog)

    # Convert to JSON
    json_str = ast_to_json(ast)

    # Should be valid JSON
    data = json.loads(json_str)
    assert data["_type"] == "SourceFile"
    assert len(data["modules"]) == 1
    assert data["modules"][0]["name"] == "uart_tx"

    # Round trip
    ast2 = json_to_ast(json_str)
    assert isinstance(ast2, SourceFile)
    assert ast2.modules[0].name == "uart_tx"

    # Verify parameters are preserved
    params = [item for item in ast2.modules[0].body if isinstance(item, ParamDecl)]
    assert len(params) >= 3

    print(f"✓ test_integration_uart_to_json ({len(json_str)} chars)")


def run_all():
    """Run all JSON serialization tests"""
    tests = [
        test_simple_module_to_json,
        test_round_trip_conversion,
        test_complex_ast_to_json,
        test_always_block_to_json,
        test_file_write_and_read,
        test_module_with_parameters,
        test_nested_expressions,
        test_compact_json,
        test_integration_uart_to_json,
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
    print(f"AST JSON Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running AST JSON serialization tests...\n")
    run_all()

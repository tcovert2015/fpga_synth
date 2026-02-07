"""
Tests for Phase 4.3: Verilog Code Generation from AST.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.codegen import generate_verilog


def test_simple_module():
    """Test: Generate code for simple module"""
    verilog = """module test;
endmodule"""

    ast = parse_verilog(verilog)
    generated = generate_verilog(ast)

    assert "module test" in generated
    assert "endmodule" in generated
    print("✓ test_simple_module")


def test_wire_declaration():
    """Test: Generate wire declarations"""
    verilog = """module test;
    wire a;
    wire [7:0] b;
endmodule"""

    ast = parse_verilog(verilog)
    generated = generate_verilog(ast)

    assert "wire a" in generated
    assert "wire [7:0] b" in generated
    print("✓ test_wire_declaration")


def test_continuous_assign():
    """Test: Generate continuous assignment"""
    verilog = """module test;
    wire a;
    wire b;
    assign b = a;
endmodule"""

    ast = parse_verilog(verilog)
    generated = generate_verilog(ast)

    assert "assign b = a" in generated
    print("✓ test_continuous_assign")


def test_always_block():
    """Test: Generate always block"""
    verilog = """module test;
    reg [7:0] count;
    always @(posedge clk) begin
        count <= count + 1;
    end
endmodule"""

    ast = parse_verilog(verilog)
    generated = generate_verilog(ast)

    assert "always @(posedge clk)" in generated
    assert "begin" in generated
    assert "count <= " in generated
    assert "end" in generated
    print("✓ test_always_block")


def test_if_statement():
    """Test: Generate if statement"""
    verilog = """module test;
    always @(*) begin
        if (en)
            data = 1;
    end
endmodule"""

    ast = parse_verilog(verilog)
    generated = generate_verilog(ast)

    assert "if (en)" in generated
    assert "data = " in generated
    print("✓ test_if_statement")


def test_case_statement():
    """Test: Generate case statement"""
    verilog = """module test;
    always @(*) begin
        case (sel)
            0: out = a;
            1: out = b;
            default: out = 0;
        endcase
    end
endmodule"""

    ast = parse_verilog(verilog)
    generated = generate_verilog(ast)

    assert "case (sel)" in generated
    assert "0:" in generated or "0 :" in generated
    assert "default:" in generated
    assert "endcase" in generated
    print("✓ test_case_statement")


def test_module_with_ports():
    """Test: Generate module with ports"""
    verilog = """module test(
    input wire clk,
    input wire rst,
    output reg [7:0] data
);
endmodule"""

    ast = parse_verilog(verilog)
    generated = generate_verilog(ast)

    assert "module test" in generated
    assert "input" in generated
    assert "output" in generated
    assert "clk" in generated
    assert "data" in generated
    print("✓ test_module_with_ports")


def test_module_with_parameters():
    """Test: Generate module with parameters"""
    verilog = """module test #(
    parameter WIDTH = 8
) (
    input wire [WIDTH-1:0] data
);
    localparam DEPTH = 16;
endmodule"""

    ast = parse_verilog(verilog)
    generated = generate_verilog(ast)

    assert "parameter WIDTH" in generated
    assert "localparam DEPTH" in generated
    print("✓ test_module_with_parameters")


def test_expressions():
    """Test: Generate various expressions"""
    verilog = """module test;
    wire result;
    assign result = (a + b) & c;
endmodule"""

    ast = parse_verilog(verilog)
    generated = generate_verilog(ast)

    # Should have parentheses and operators
    assert "+" in generated or "a + b" in generated
    assert "&" in generated
    print("✓ test_expressions")


def test_round_trip_simple():
    """Test: Parse → Generate → Parse round trip"""
    original = """module test;
    wire a;
    assign a = 1;
endmodule"""

    # First parse
    ast1 = parse_verilog(original)

    # Generate
    generated = generate_verilog(ast1)

    # Parse again
    ast2 = parse_verilog(generated)

    # Verify structure is preserved
    assert len(ast2.modules) == 1
    assert ast2.modules[0].name == "test"

    print("✓ test_round_trip_simple")


def test_round_trip_counter():
    """Test: Round trip with counter design"""
    original = """module counter(
    input wire clk,
    input wire rst_n,
    input wire en,
    output reg [7:0] count
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= 0;
        else if (en)
            count <= count + 1;
    end
endmodule"""

    # Parse → Generate → Parse
    ast1 = parse_verilog(original)
    generated = generate_verilog(ast1)
    ast2 = parse_verilog(generated)

    # Verify
    assert len(ast2.modules) == 1
    assert ast2.modules[0].name == "counter"
    assert len(ast2.modules[0].ports) == 4

    print("✓ test_round_trip_counter")


def test_system_task():
    """Test: Generate system task"""
    verilog = """module test;
    initial begin
        $display("Hello");
    end
endmodule"""

    ast = parse_verilog(verilog)
    generated = generate_verilog(ast)

    assert "$display" in generated
    print("✓ test_system_task")


def run_all():
    """Run all code generation tests"""
    tests = [
        test_simple_module,
        test_wire_declaration,
        test_continuous_assign,
        test_always_block,
        test_if_statement,
        test_case_statement,
        test_module_with_ports,
        test_module_with_parameters,
        test_expressions,
        test_round_trip_simple,
        test_round_trip_counter,
        test_system_task,
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
    print(f"Code Generation Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running code generation tests...\n")
    run_all()

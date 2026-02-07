"""
Tests for Verilog attributes (* key = value *).

Part of Phase 1.5 of the TODO list.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.ast_nodes import *


def test_attribute_on_module():
    """Test: attribute on module declaration"""
    verilog = """
    (* top_module *)
    module test;
        wire w;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    assert "top_module" in mod.attributes
    print("✓ test_attribute_on_module")


def test_attribute_on_wire():
    """Test: attribute on wire declaration"""
    verilog = """
    module test;
        (* keep = "true" *)
        wire important_signal;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    wires = [item for item in mod.body if isinstance(item, NetDecl)]
    assert len(wires) == 1
    assert "keep" in wires[0].attributes
    assert wires[0].attributes["keep"] == "true"
    print("✓ test_attribute_on_wire")


def test_multiple_attributes():
    """Test: multiple attributes in one declaration"""
    verilog = """
    module test;
        (* keep = "true", maxfan = 100 *)
        wire data;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    wires = [item for item in mod.body if isinstance(item, NetDecl)]
    wire = wires[0]

    assert "keep" in wire.attributes
    assert "maxfan" in wire.attributes
    assert wire.attributes["keep"] == "true"
    assert wire.attributes["maxfan"] == "100"
    print("✓ test_multiple_attributes")


def test_attribute_on_instance():
    """Test: attribute on module instance"""
    verilog = """
    module test;
        (* dont_touch *)
        my_module inst (
            .clk(clk),
            .data(data)
        );
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    instances = [item for item in mod.body if isinstance(item, ModuleInstance)]
    assert len(instances) == 1
    assert "dont_touch" in instances[0].attributes
    print("✓ test_attribute_on_instance")


def test_attribute_on_always_block():
    """Test: attribute on always block"""
    verilog = """
    module test;
        (* full_case *)
        always @(posedge clk) begin
            q <= d;
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    always_blocks = [item for item in mod.body if isinstance(item, AlwaysBlock)]
    assert len(always_blocks) == 1
    assert "full_case" in always_blocks[0].attributes
    print("✓ test_attribute_on_always_block")


def test_attribute_with_number():
    """Test: attribute with numeric value"""
    verilog = """
    module test;
        (* priority = 5 *)
        wire [7:0] data;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    wires = [item for item in mod.body if isinstance(item, NetDecl)]
    wire = wires[0]

    assert "priority" in wire.attributes
    assert wire.attributes["priority"] == "5"
    print("✓ test_attribute_with_number")


def test_attribute_on_parameter():
    """Test: attribute on parameter"""
    verilog = """
    module test;
        (* synthesis, keep *)
        parameter WIDTH = 8;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    params = [item for item in mod.body if isinstance(item, ParamDecl)]
    assert len(params) == 1
    assert "synthesis" in params[0].attributes
    assert "keep" in params[0].attributes
    print("✓ test_attribute_on_parameter")


def test_attribute_without_value():
    """Test: attribute key without explicit value"""
    verilog = """
    module test;
        (* fsm_encoding *)
        reg [1:0] state;
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    regs = [item for item in mod.body if isinstance(item, NetDecl)]
    reg = regs[0]

    assert "fsm_encoding" in reg.attributes
    assert reg.attributes["fsm_encoding"] == ""
    print("✓ test_attribute_without_value")


def run_all():
    """Run all attribute tests"""
    tests = [
        test_attribute_on_module,
        test_attribute_on_wire,
        test_multiple_attributes,
        test_attribute_on_instance,
        test_attribute_on_always_block,
        test_attribute_with_number,
        test_attribute_on_parameter,
        test_attribute_without_value,
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
    print(f"Attribute Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running attribute tests...\n")
    run_all()

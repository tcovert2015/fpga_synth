"""
Tests for array declarations (unpacked and multi-dimensional arrays).

Part of Phase 1.1 of the TODO list.
"""

import sys
import os
# Add project root (go up from tests/parser/ to fpga_synth parent)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.ast_nodes import *


def test_simple_unpacked_array():
    """Test: reg [7:0] mem [0:255];"""
    verilog = """
    module test;
        reg [7:0] mem [0:255];
    endmodule
    """
    ast = parse_verilog(verilog)
    assert len(ast.modules) == 1

    mod = ast.modules[0]
    net_decls = [item for item in mod.body if isinstance(item, NetDecl)]
    assert len(net_decls) == 1

    decl = net_decls[0]
    assert decl.name == "mem"
    assert decl.net_type == "reg"
    assert decl.range is not None  # [7:0]
    assert len(decl.array_dims) == 1  # [0:255]
    print("✓ test_simple_unpacked_array")


def test_unpacked_array_wire():
    """Test: wire [3:0] data [0:15];"""
    verilog = """
    module test;
        wire [3:0] data [0:15];
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    net_decls = [item for item in mod.body if isinstance(item, NetDecl)]

    decl = net_decls[0]
    assert decl.name == "data"
    assert decl.net_type == "wire"
    assert len(decl.array_dims) == 1
    print("✓ test_unpacked_array_wire")


def test_multidimensional_array():
    """Test: reg [7:0] mem [0:15][0:31];"""
    verilog = """
    module test;
        reg [7:0] mem [0:15][0:31];
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    net_decls = [item for item in mod.body if isinstance(item, NetDecl)]

    decl = net_decls[0]
    assert decl.name == "mem"
    assert decl.net_type == "reg"
    assert decl.range is not None  # [7:0]
    assert len(decl.array_dims) == 2  # [0:15][0:31]
    print("✓ test_multidimensional_array")


def test_array_port_declaration():
    """Test: input [7:0] data [0:3];"""
    verilog = """
    module test(
        input [7:0] data [0:3]
    );
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    assert len(mod.ports) == 1
    port = mod.ports[0]
    assert port.name == "data"
    assert port.direction == "input"
    assert port.range is not None  # [7:0]
    assert len(port.array_dims) == 1  # [0:3]
    print("✓ test_array_port_declaration")


def test_multidimensional_port():
    """Test: output reg [15:0] result [0:7][0:7];"""
    verilog = """
    module test(
        output reg [15:0] result [0:7][0:7]
    );
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    port = mod.ports[0]
    assert port.name == "result"
    assert port.direction == "output"
    assert port.net_type == "reg"
    assert port.range is not None  # [15:0]
    assert len(port.array_dims) == 2  # [0:7][0:7]
    print("✓ test_multidimensional_port")


def test_array_without_packed_dimension():
    """Test: reg mem [0:255]; (no bit width, scalar array)"""
    verilog = """
    module test;
        reg mem [0:255];
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    net_decls = [item for item in mod.body if isinstance(item, NetDecl)]

    decl = net_decls[0]
    assert decl.name == "mem"
    assert decl.range is None  # No packed dimension
    assert len(decl.array_dims) == 1  # [0:255]
    print("✓ test_array_without_packed_dimension")


def test_signed_array():
    """Test: reg signed [7:0] data [0:15];"""
    verilog = """
    module test;
        reg signed [7:0] data [0:15];
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]
    net_decls = [item for item in mod.body if isinstance(item, NetDecl)]

    decl = net_decls[0]
    assert decl.name == "data"
    assert decl.signed == True
    assert len(decl.array_dims) == 1
    print("✓ test_signed_array")


def test_complex_array_module():
    """Test module with multiple array declarations"""
    verilog = """
    module memory_bank #(
        parameter WIDTH = 32,
        parameter DEPTH = 1024
    )(
        input clk,
        input [7:0] addr [0:3],
        output reg [WIDTH-1:0] data [0:3]
    );
        reg [WIDTH-1:0] mem [0:DEPTH-1];
        wire [3:0] control [0:15][0:7];
    endmodule
    """
    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    assert mod.name == "memory_bank"
    assert len(mod.params) == 2
    assert len(mod.ports) == 3

    # Check array port
    addr_port = mod.ports[1]
    assert addr_port.name == "addr"
    assert len(addr_port.array_dims) == 1

    data_port = mod.ports[2]
    assert data_port.name == "data"
    assert len(data_port.array_dims) == 1

    # Check internal arrays
    net_decls = [item for item in mod.body if isinstance(item, NetDecl)]
    assert len(net_decls) == 2

    mem_decl = net_decls[0]
    assert mem_decl.name == "mem"
    assert len(mem_decl.array_dims) == 1

    control_decl = net_decls[1]
    assert control_decl.name == "control"
    assert len(control_decl.array_dims) == 2

    print("✓ test_complex_array_module")


def run_all():
    """Run all array tests"""
    tests = [
        test_simple_unpacked_array,
        test_unpacked_array_wire,
        test_multidimensional_array,
        test_array_port_declaration,
        test_multidimensional_port,
        test_array_without_packed_dimension,
        test_signed_array,
        test_complex_array_module,
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
    print(f"Array Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running array declaration tests...\n")
    run_all()

"""
Tests for sequential logic elaboration (flip-flops, registers).
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.elaborator import elaborate
from fpga_synth.ir.types import CellOp


def test_simple_dff():
    """Test: Simple D flip-flop"""
    verilog = """
    module test(
        input wire clk,
        input wire d,
        output reg q
    );
        always @(posedge clk) begin
            q <= d;
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should have a DFF cell
    dff_cells = [cell for cell in netlist.cells.values() if cell.op in (CellOp.DFF, CellOp.DFFR)]
    assert len(dff_cells) >= 1

    dff = dff_cells[0]
    assert "CLK" in dff.inputs
    assert "D" in dff.inputs
    assert "Q" in dff.outputs

    print("✓ test_simple_dff")


def test_dff_with_reset():
    """Test: DFF with asynchronous reset"""
    verilog = """
    module test(
        input wire clk,
        input wire rst_n,
        input wire d,
        output reg q
    );
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n)
                q <= 0;
            else
                q <= d;
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should have a DFFR cell (DFF with reset)
    dffr_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.DFFR]
    assert len(dffr_cells) >= 1

    dffr = dffr_cells[0]
    assert "CLK" in dffr.inputs
    assert "D" in dffr.inputs
    assert "RST" in dffr.inputs
    assert "Q" in dffr.outputs

    print("✓ test_dff_with_reset")


def test_counter():
    """Test: Simple counter"""
    verilog = """
    module counter(
        input wire clk,
        input wire rst_n,
        output reg [3:0] count
    );
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n)
                count <= 0;
            else
                count <= count + 1;
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should have DFF and ADD cells
    dff_cells = [cell for cell in netlist.cells.values()
                 if cell.op in (CellOp.DFF, CellOp.DFFR)]
    add_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.ADD]

    assert len(dff_cells) >= 1
    assert len(add_cells) >= 1

    print("✓ test_counter")


def test_register_file():
    """Test: Simple register"""
    verilog = """
    module register(
        input wire clk,
        input wire en,
        input wire [7:0] d,
        output reg [7:0] q
    );
        always @(posedge clk) begin
            if (en)
                q <= d;
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should have DFF cells
    dff_cells = [cell for cell in netlist.cells.values()
                 if cell.op in (CellOp.DFF, CellOp.DFFR, CellOp.DFFRE)]
    assert len(dff_cells) >= 1

    print("✓ test_register_file")


def test_combinational_always():
    """Test: Combinational always block"""
    verilog = """
    module test;
        reg a;
        reg b;
        reg c;
        always @(*) begin
            c = a & b;
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should have AND cell, not DFF
    and_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.AND]
    dff_cells = [cell for cell in netlist.cells.values()
                 if cell.op in (CellOp.DFF, CellOp.DFFR)]

    assert len(and_cells) >= 1
    assert len(dff_cells) == 0  # No flip-flops in combinational block

    print("✓ test_combinational_always")


def test_sequential_vs_combinational():
    """Test: Module with both sequential and combinational logic"""
    verilog = """
    module test(
        input wire clk,
        input wire a,
        output reg b,
        output wire c
    );
        // Sequential
        always @(posedge clk) begin
            b <= a;
        end

        // Combinational
        assign c = a & b;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should have both DFF and AND cells
    dff_cells = [cell for cell in netlist.cells.values()
                 if cell.op in (CellOp.DFF, CellOp.DFFR)]
    and_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.AND]

    assert len(dff_cells) >= 1
    assert len(and_cells) >= 1

    print("✓ test_sequential_vs_combinational")


def test_shift_register():
    """Test: Simple shift register"""
    verilog = """
    module shift_reg(
        input wire clk,
        input wire si,
        output reg [3:0] data
    );
        always @(posedge clk) begin
            data <= {data[2:0], si};
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should have DFF cells
    dff_cells = [cell for cell in netlist.cells.values()
                 if cell.op in (CellOp.DFF, CellOp.DFFR)]
    assert len(dff_cells) >= 1

    print("✓ test_shift_register")


def run_all():
    """Run all sequential logic tests"""
    tests = [
        test_simple_dff,
        test_dff_with_reset,
        test_counter,
        test_register_file,
        test_combinational_always,
        test_sequential_vs_combinational,
        test_shift_register,
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
    print(f"Sequential Logic Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running sequential logic tests...\n")
    run_all()

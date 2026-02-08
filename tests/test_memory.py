"""
Tests for memory inference (RAM/ROM).
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.elaborator import elaborate
from fpga_synth.ir.types import CellOp


def test_memory_declaration():
    """Test: Memory array declaration"""
    verilog = """
    module test;
        reg [7:0] mem [0:255];
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should detect memory (no cells created yet, just tracked)
    # Memory access creates cells
    print("✓ test_memory_declaration")


def test_memory_read():
    """Test: Simple memory read"""
    verilog = """
    module test(
        input [7:0] addr,
        output [7:0] data
    );
        reg [7:0] mem [0:255];
        assign data = mem[addr];
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should have MEMRD cell
    memrd_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.MEMRD]
    assert len(memrd_cells) >= 1

    memrd = memrd_cells[0]
    assert "ADDR" in memrd.inputs
    assert "DATA" in memrd.outputs
    assert memrd.attributes["memory"] == "mem"
    assert memrd.attributes["depth"] == 256

    print("✓ test_memory_read")


def test_memory_write():
    """Test: Simple memory write"""
    verilog = """
    module test(
        input clk,
        input [7:0] addr,
        input [7:0] data
    );
        reg [7:0] mem [0:255];

        always @(posedge clk) begin
            mem[addr] <= data;
        end
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should have MEMWR cell
    memwr_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.MEMWR]
    assert len(memwr_cells) >= 1

    memwr = memwr_cells[0]
    assert "CLK" in memwr.inputs
    assert "ADDR" in memwr.inputs
    assert "DATA" in memwr.inputs
    assert "EN" in memwr.inputs  # Write enable
    assert memwr.attributes["memory"] == "mem"

    print("✓ test_memory_write")


def test_memory_read_write():
    """Test: Memory with both read and write"""
    verilog = """
    module test(
        input clk,
        input we,
        input [7:0] addr,
        input [7:0] din,
        output [7:0] dout
    );
        reg [7:0] mem [0:255];

        always @(posedge clk) begin
            if (we)
                mem[addr] <= din;
        end

        assign dout = mem[addr];
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should have both MEMRD and MEMWR cells
    memrd_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.MEMRD]
    memwr_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.MEMWR]

    assert len(memrd_cells) >= 1
    assert len(memwr_cells) >= 1

    print("✓ test_memory_read_write")


def test_dual_port_memory():
    """Test: Dual-port memory (separate read/write addresses)"""
    verilog = """
    module dual_port_ram(
        input clk,
        input we,
        input [7:0] waddr,
        input [7:0] raddr,
        input [7:0] din,
        output [7:0] dout
    );
        reg [7:0] mem [0:255];

        always @(posedge clk) begin
            if (we)
                mem[waddr] <= din;
        end

        assign dout = mem[raddr];
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    memrd_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.MEMRD]
    memwr_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.MEMWR]

    assert len(memrd_cells) >= 1
    assert len(memwr_cells) >= 1

    print("✓ test_dual_port_memory")


def test_parameterized_memory():
    """Test: Memory with parameterized depth"""
    verilog = """
    module parameterized_mem #(
        parameter DEPTH = 256,
        parameter WIDTH = 8
    ) (
        input clk,
        input [7:0] addr,
        input [WIDTH-1:0] din,
        output [WIDTH-1:0] dout
    );
        reg [WIDTH-1:0] mem [0:DEPTH-1];

        always @(posedge clk) begin
            mem[addr] <= din;
        end

        assign dout = mem[addr];
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should elaborate with parameter values
    memwr_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.MEMWR]
    assert len(memwr_cells) >= 1

    # Check depth is resolved
    memwr = memwr_cells[0]
    assert memwr.attributes["depth"] == 256

    print("✓ test_parameterized_memory")


def test_rom():
    """Test: Read-only memory (ROM)"""
    verilog = """
    module rom(
        input [3:0] addr,
        output [7:0] data
    );
        reg [7:0] mem [0:15];

        assign data = mem[addr];
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should have MEMRD cell only (no writes)
    memrd_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.MEMRD]
    memwr_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.MEMWR]

    assert len(memrd_cells) >= 1
    assert len(memwr_cells) == 0  # No writes, so it's ROM

    print("✓ test_rom")


def test_fifo_buffer():
    """Test: Simple FIFO buffer with memory"""
    verilog = """
    module fifo #(
        parameter DEPTH = 16,
        parameter WIDTH = 8
    ) (
        input clk,
        input rst_n,
        input wr_en,
        input rd_en,
        input [WIDTH-1:0] din,
        output [WIDTH-1:0] dout
    );
        reg [WIDTH-1:0] mem [0:DEPTH-1];
        reg [3:0] wr_ptr;
        reg [3:0] rd_ptr;

        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                wr_ptr <= 0;
                rd_ptr <= 0;
            end else begin
                if (wr_en)
                    mem[wr_ptr] <= din;
                if (wr_en)
                    wr_ptr <= wr_ptr + 1;
                if (rd_en)
                    rd_ptr <= rd_ptr + 1;
            end
        end

        assign dout = mem[rd_ptr];
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should have memory cells, DFF cells for pointers, and ADD cells
    memrd_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.MEMRD]
    memwr_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.MEMWR]
    dff_cells = [cell for cell in netlist.cells.values()
                 if cell.op in (CellOp.DFF, CellOp.DFFR)]
    add_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.ADD]

    assert len(memrd_cells) >= 1  # Read port
    assert len(memwr_cells) >= 1  # Write port
    assert len(dff_cells) >= 1    # Pointers
    assert len(add_cells) >= 1    # Pointer increment

    print("✓ test_fifo_buffer")


def run_all():
    """Run all memory tests"""
    tests = [
        test_memory_declaration,
        test_memory_read,
        test_memory_write,
        test_memory_read_write,
        test_dual_port_memory,
        test_parameterized_memory,
        test_rom,
        test_fifo_buffer,
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
    print(f"Memory Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running memory inference tests...\n")
    run_all()

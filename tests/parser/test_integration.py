"""
Integration tests with real-world Verilog designs.

Phase 3.4: Real-world designs testing.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.ast_nodes import *


def test_uart_tx_module():
    """Test: Parse a realistic UART transmitter module"""
    # Read UART design
    uart_path = os.path.join(os.path.dirname(__file__), "..", "integration", "uart_tx.v")
    with open(uart_path, "r") as f:
        verilog = f.read()

    # Parse the design
    ast = parse_verilog(verilog)

    # Validate module structure
    assert len(ast.modules) == 1
    mod = ast.modules[0]
    assert mod.name == "uart_tx"

    # Check parameters
    # Note: Parameters with #() are stored in mod.params, while parameter declarations
    # in the body are stored as ParamDecl in mod.body
    params = [item for item in mod.body if isinstance(item, ParamDecl)]
    assert len(mod.params) + len(params) >= 2
    param_names = [p.name for p in mod.params]
    assert "CLK_FREQ" in param_names
    assert "BAUD_RATE" in param_names

    # Check ports
    port_names = [p.name for p in mod.ports]
    assert "clk" in port_names
    assert "rst_n" in port_names
    assert "tx_data" in port_names
    assert "tx_valid" in port_names
    assert "tx_ready" in port_names
    assert "tx" in port_names

    # Check for localparam declarations
    localparams = [item for item in mod.body if isinstance(item, ParamDecl) and item.kind == "localparam"]
    assert len(localparams) >= 3  # CYCLES_PER_BIT, COUNTER_WIDTH, state values

    # Check for always blocks
    always_blocks = [item for item in mod.body if isinstance(item, AlwaysBlock)]
    assert len(always_blocks) == 2  # Baud generator and main FSM

    # Check for continuous assignments
    assigns = [item for item in mod.body if isinstance(item, ContinuousAssign)]
    assert len(assigns) >= 1  # baud_tick

    print("✓ test_uart_tx_module")


def test_simple_fifo():
    """Test: Parse a simple FIFO buffer"""
    verilog = """
    module fifo #(
        parameter DATA_WIDTH = 8,
        parameter DEPTH = 16
    ) (
        input wire clk,
        input wire rst_n,

        // Write interface
        input wire [DATA_WIDTH-1:0] wr_data,
        input wire wr_en,
        output wire full,

        // Read interface
        output reg [DATA_WIDTH-1:0] rd_data,
        input wire rd_en,
        output wire empty
    );

        localparam ADDR_WIDTH = $clog2(DEPTH);

        // Memory array
        reg [DATA_WIDTH-1:0] mem [0:DEPTH-1];

        // Pointers
        reg [ADDR_WIDTH:0] wr_ptr;
        reg [ADDR_WIDTH:0] rd_ptr;

        // Status flags
        assign full = (wr_ptr[ADDR_WIDTH] != rd_ptr[ADDR_WIDTH]) &&
                     (wr_ptr[ADDR_WIDTH-1:0] == rd_ptr[ADDR_WIDTH-1:0]);
        assign empty = (wr_ptr == rd_ptr);

        // Write logic
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                wr_ptr <= 0;
            end else if (wr_en && !full) begin
                mem[wr_ptr[ADDR_WIDTH-1:0]] <= wr_data;
                wr_ptr <= wr_ptr + 1;
            end
        end

        // Read logic
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                rd_ptr <= 0;
                rd_data <= 0;
            end else if (rd_en && !empty) begin
                rd_data <= mem[rd_ptr[ADDR_WIDTH-1:0]];
                rd_ptr <= rd_ptr + 1;
            end
        end

    endmodule
    """

    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    assert mod.name == "fifo"
    # Check parameters (either in mod.params for #() or in body for internal declarations)
    params = [item for item in mod.body if isinstance(item, ParamDecl)]
    assert len(mod.params) + len(params) >= 2

    # Check for memory array
    memory_arrays = [item for item in mod.body
                    if isinstance(item, NetDecl) and len(item.array_dims) > 0]
    assert len(memory_arrays) >= 1

    # Check always blocks (write and read logic)
    always_blocks = [item for item in mod.body if isinstance(item, AlwaysBlock)]
    assert len(always_blocks) == 2

    print("✓ test_simple_fifo")


def test_counter_with_load():
    """Test: Parse a counter with parallel load"""
    verilog = """
    module counter #(
        parameter WIDTH = 8
    ) (
        input wire clk,
        input wire rst_n,
        input wire en,
        input wire load,
        input wire [WIDTH-1:0] load_value,
        output reg [WIDTH-1:0] count
    );

        always @(posedge clk or negedge rst_n) begin
            if (!rst_n)
                count <= 0;
            else if (load)
                count <= load_value;
            else if (en)
                count <= count + 1;
        end

    endmodule
    """

    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    assert mod.name == "counter"
    assert len(mod.params) == 1

    always_blocks = [item for item in mod.body if isinstance(item, AlwaysBlock)]
    assert len(always_blocks) == 1

    # Check if statement structure
    always_body = always_blocks[0].body[0]
    assert isinstance(always_body, IfStatement)

    print("✓ test_counter_with_load")


def test_mux_parametric():
    """Test: Parse a parametric multiplexer"""
    verilog = """
    module mux #(
        parameter WIDTH = 8,
        parameter INPUTS = 4
    ) (
        input wire [WIDTH-1:0] data_in [0:INPUTS-1],
        input wire [$clog2(INPUTS)-1:0] sel,
        output reg [WIDTH-1:0] data_out
    );

        integer i;

        always @(*) begin
            data_out = 0;
            for (i = 0; i < INPUTS; i = i + 1) begin
                if (sel == i) begin
                    data_out = data_in[i];
                end
            end
        end

    endmodule
    """

    ast = parse_verilog(verilog)
    mod = ast.modules[0]

    assert mod.name == "mux"

    # Check integer declaration
    integers = [item for item in mod.body if isinstance(item, IntegerDecl)]
    assert len(integers) >= 1

    # Check for loop in always block
    always_blocks = [item for item in mod.body if isinstance(item, AlwaysBlock)]
    assert len(always_blocks) == 1

    print("✓ test_mux_parametric")


def run_all():
    """Run all integration tests"""
    tests = [
        test_uart_tx_module,
        test_simple_fifo,
        test_counter_with_load,
        test_mux_parametric,
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
    print(f"Integration Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running integration tests with real-world designs...\n")
    run_all()

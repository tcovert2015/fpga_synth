/**
 * Shift Register with Parallel Load
 *
 * Demonstrates:
 * - Sequential logic
 * - Parallel load capability
 * - Shift operations
 */

module shift_register #(
    parameter WIDTH = 8
) (
    input wire clk,
    input wire rst_n,
    input wire load,
    input wire shift_en,
    input wire serial_in,
    input wire [WIDTH-1:0] parallel_in,
    output wire [WIDTH-1:0] parallel_out,
    output wire serial_out
);

    reg [WIDTH-1:0] data;

    assign parallel_out = data;
    assign serial_out = data[WIDTH-1];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            data <= 0;
        else if (load)
            data <= parallel_in;
        else if (shift_en)
            data <= {data[WIDTH-2:0], serial_in};
    end

endmodule

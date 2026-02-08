/**
 * Gray Code Counter
 *
 * Demonstrates:
 * - Binary to Gray conversion
 * - XOR reduction
 * - Ternary operator
 */

module gray_counter #(
    parameter WIDTH = 4
) (
    input wire clk,
    input wire rst_n,
    input wire en,
    output wire [WIDTH-1:0] gray_out
);

    reg [WIDTH-1:0] binary_count;

    // Binary counter
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            binary_count <= 0;
        else if (en)
            binary_count <= binary_count + 1;
    end

    // Binary to Gray conversion
    assign gray_out = binary_count ^ (binary_count >> 1);

endmodule

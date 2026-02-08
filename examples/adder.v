/**
 * 8-bit Adder
 *
 * Demonstrates:
 * - Parametric width
 * - Arithmetic operations
 * - Vector signals
 */

module adder #(
    parameter WIDTH = 8
) (
    input wire [WIDTH-1:0] a,
    input wire [WIDTH-1:0] b,
    input wire cin,
    output wire [WIDTH-1:0] sum,
    output wire cout
);

    assign {cout, sum} = a + b + cin;

endmodule

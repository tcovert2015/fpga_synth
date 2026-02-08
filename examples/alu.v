/**
 * Simple ALU (Arithmetic Logic Unit)
 *
 * Demonstrates:
 * - Case statements
 * - Multiple operations
 * - Localparam
 * - Complex expressions
 */

module alu #(
    parameter WIDTH = 8
) (
    input wire [WIDTH-1:0] a,
    input wire [WIDTH-1:0] b,
    input wire [2:0] op,
    output reg [WIDTH-1:0] result,
    output reg zero
);

    // Operation codes
    localparam OP_ADD  = 3'b000;
    localparam OP_SUB  = 3'b001;
    localparam OP_AND  = 3'b010;
    localparam OP_OR   = 3'b011;
    localparam OP_XOR  = 3'b100;
    localparam OP_SLL  = 3'b101;
    localparam OP_SRL  = 3'b110;

    always @(*) begin
        case (op)
            OP_ADD:  result = a + b;
            OP_SUB:  result = a - b;
            OP_AND:  result = a & b;
            OP_OR:   result = a | b;
            OP_XOR:  result = a ^ b;
            OP_SLL:  result = a << b[2:0];
            OP_SRL:  result = a >> b[2:0];
            default: result = 0;
        endcase

        zero = (result == 0);
    end

endmodule

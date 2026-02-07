// Simple ALU demonstrating combinational logic
// Demonstrates: case statements, continuous assignments, concatenation

module simple_alu #(
    parameter WIDTH = 8
)(
    input [WIDTH-1:0] a,
    input [WIDTH-1:0] b,
    input [2:0] op,
    output reg [WIDTH-1:0] result,
    output zero
);

    // Combinational logic
    always @(*) begin
        case (op)
            3'd0: result = a + b;      // ADD
            3'd1: result = a - b;      // SUB
            3'd2: result = a & b;      // AND
            3'd3: result = a | b;      // OR
            3'd4: result = a ^ b;      // XOR
            3'd5: result = ~a;         // NOT
            3'd6: result = a << 1;     // Shift left
            3'd7: result = a >> 1;     // Shift right
            default: result = 8'h00;
        endcase
    end

    // Zero flag
    assign zero = (result == 8'h00) ? 1'b1 : 1'b0;

endmodule

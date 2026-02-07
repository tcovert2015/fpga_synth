"""
Token types for the synthesizable Verilog subset.
"""

from enum import Enum, auto
from dataclasses import dataclass


class TokenType(Enum):
    # Literals
    NUMBER = auto()         # 32, 8'hFF, 4'b1010, 3'd7
    STRING = auto()         # "hello"
    IDENT = auto()          # my_signal
    
    # Keywords
    MODULE = auto()
    ENDMODULE = auto()
    INPUT = auto()
    OUTPUT = auto()
    INOUT = auto()
    WIRE = auto()
    REG = auto()
    PARAMETER = auto()
    LOCALPARAM = auto()
    ASSIGN = auto()
    ALWAYS = auto()
    BEGIN = auto()
    END = auto()
    IF = auto()
    ELSE = auto()
    CASE = auto()
    CASEX = auto()
    CASEZ = auto()
    ENDCASE = auto()
    DEFAULT = auto()
    FOR = auto()
    GENERATE = auto()
    ENDGENERATE = auto()
    GENVAR = auto()
    POSEDGE = auto()
    NEGEDGE = auto()
    SIGNED = auto()
    INTEGER = auto()
    
    # Operators
    PLUS = auto()           # +
    MINUS = auto()          # -
    STAR = auto()           # *
    SLASH = auto()          # /
    PERCENT = auto()        # %
    AMP = auto()            # &
    PIPE = auto()           # |
    CARET = auto()          # ^
    TILDE = auto()          # ~
    BANG = auto()            # !
    LSHIFT = auto()         # <<
    RSHIFT = auto()         # >>
    ARSHIFT = auto()        # >>>
    
    LAND = auto()           # &&
    LOR = auto()            # ||
    
    EQ = auto()             # ==
    NEQ = auto()            # !=
    LT = auto()             # <
    LE = auto()             # <=
    GT = auto()             # >
    GE = auto()             # >=
    
    QUESTION = auto()       # ?
    COLON = auto()          # :
    AT = auto()             # @
    HASH = auto()           # #
    
    # Delimiters
    LPAREN = auto()         # (
    RPAREN = auto()         # )
    LBRACKET = auto()       # [
    RBRACKET = auto()       # ]
    LBRACE = auto()         # {
    RBRACE = auto()         # }
    SEMICOLON = auto()      # ;
    COMMA = auto()          # ,
    DOT = auto()            # .
    ASSIGN_OP = auto()      # = (blocking assignment)
    
    # Special
    ATAT = auto()           # @@  (not real Verilog, placeholder)
    STARPAREN = auto()      # (*  for attributes (ignored for now)
    
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    col: int
    
    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, L{self.line}:{self.col})"


# Keyword lookup table
KEYWORDS: dict[str, TokenType] = {
    "module": TokenType.MODULE,
    "endmodule": TokenType.ENDMODULE,
    "input": TokenType.INPUT,
    "output": TokenType.OUTPUT,
    "inout": TokenType.INOUT,
    "wire": TokenType.WIRE,
    "reg": TokenType.REG,
    "parameter": TokenType.PARAMETER,
    "localparam": TokenType.LOCALPARAM,
    "assign": TokenType.ASSIGN,
    "always": TokenType.ALWAYS,
    "begin": TokenType.BEGIN,
    "end": TokenType.END,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "case": TokenType.CASE,
    "casex": TokenType.CASEX,
    "casez": TokenType.CASEZ,
    "endcase": TokenType.ENDCASE,
    "default": TokenType.DEFAULT,
    "for": TokenType.FOR,
    "generate": TokenType.GENERATE,
    "endgenerate": TokenType.ENDGENERATE,
    "genvar": TokenType.GENVAR,
    "posedge": TokenType.POSEDGE,
    "negedge": TokenType.NEGEDGE,
    "signed": TokenType.SIGNED,
    "integer": TokenType.INTEGER,
}

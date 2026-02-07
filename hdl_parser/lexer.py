"""
Hand-written lexer for synthesizable Verilog.

Handles:
  - Verilog number formats: plain decimal, sized (8'hFF, 4'b1010, 3'd7)
  - Single and multi-character operators
  - // and /* */ comments
  - `define, `include, `ifdef (stripped as preprocessing — not yet expanded)
"""

from fpga_synth.hdl_parser.tokens import Token, TokenType, KEYWORDS


class LexerError(Exception):
    def __init__(self, msg: str, line: int, col: int):
        super().__init__(f"Lexer error at L{line}:{col}: {msg}")
        self.line = line
        self.col = col


class Lexer:
    def __init__(self, source: str, filename: str = "<input>"):
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: list[Token] = []
        self.in_attribute = False  # Track if we're inside an attribute
    
    def _peek(self, offset=0) -> str:
        p = self.pos + offset
        if p < len(self.source):
            return self.source[p]
        return "\0"
    
    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch
    
    def _at_end(self) -> bool:
        return self.pos >= len(self.source)
    
    def _skip_whitespace_and_comments(self):
        while not self._at_end():
            ch = self._peek()
            
            # Whitespace
            if ch in " \t\r\n":
                self._advance()
                continue
            
            # Line comment
            if ch == "/" and self._peek(1) == "/":
                while not self._at_end() and self._peek() != "\n":
                    self._advance()
                continue
            
            # Block comment
            if ch == "/" and self._peek(1) == "*":
                self._advance()  # /
                self._advance()  # *
                while not self._at_end():
                    if self._peek() == "*" and self._peek(1) == "/":
                        self._advance()  # *
                        self._advance()  # /
                        break
                    self._advance()
                continue
            
            # Compiler directives (skip the line)
            if ch == "`":
                while not self._at_end() and self._peek() != "\n":
                    self._advance()
                continue
            
            break
    
    def _read_number(self) -> Token:
        """Read a Verilog number literal.

        Formats: 123, 8'hFF, 4'b1010, 3'd7, 'h1A, 'b1, 1.5, 2.5e10, 1.0e-3
        """
        start_line, start_col = self.line, self.col
        num_str = ""

        # Read the size prefix or plain number
        while not self._at_end() and (self._peek().isdigit() or self._peek() == "_"):
            num_str += self._advance()

        # Check for sized literal: <size>'<base><digits>
        if not self._at_end() and self._peek() == "'":
            num_str += self._advance()  # consume '
            if not self._at_end() and self._peek().lower() in "bhdo":
                num_str += self._advance()  # consume base char
                # Read hex/bin/oct/dec digits
                while not self._at_end() and (
                    self._peek() in "0123456789abcdefABCDEFxXzZ_"
                ):
                    num_str += self._advance()
            return Token(TokenType.NUMBER, num_str, start_line, start_col)

        # Check for real number: decimal point
        if not self._at_end() and self._peek() == ".":
            num_str += self._advance()  # consume .
            # Read fractional part
            while not self._at_end() and (self._peek().isdigit() or self._peek() == "_"):
                num_str += self._advance()

        # Check for scientific notation: e or E
        if not self._at_end() and self._peek().lower() == "e":
            num_str += self._advance()  # consume e/E
            # Optional +/- sign
            if not self._at_end() and self._peek() in "+-":
                num_str += self._advance()
            # Read exponent
            while not self._at_end() and (self._peek().isdigit() or self._peek() == "_"):
                num_str += self._advance()

        return Token(TokenType.NUMBER, num_str, start_line, start_col)
    
    def _read_ident_or_keyword(self) -> Token:
        start_line, start_col = self.line, self.col
        ident = ""
        while not self._at_end() and (self._peek().isalnum() or self._peek() in "_$"):
            ident += self._advance()
        
        tt = KEYWORDS.get(ident, TokenType.IDENT)
        return Token(tt, ident, start_line, start_col)
    
    def _make_token(self, tt: TokenType, value: str) -> Token:
        return Token(tt, value, self.line, self.col)
    
    def tokenize(self) -> list[Token]:
        """Tokenize the entire source. Returns list of tokens ending with EOF."""
        self.tokens = []
        
        while True:
            self._skip_whitespace_and_comments()
            if self._at_end():
                break
            
            ch = self._peek()
            start_line, start_col = self.line, self.col
            
            # Numbers (also handle unsized literals like 'h1A)
            if ch.isdigit():
                self.tokens.append(self._read_number())
                continue
            
            if ch == "'" and self._peek(1).lower() in "bhdo":
                self.tokens.append(self._read_number())
                continue
            
            # Identifiers and keywords
            if ch.isalpha() or ch == "_" or ch == "$":
                self.tokens.append(self._read_ident_or_keyword())
                continue
            
            # String literals
            if ch == '"':
                self._advance()  # opening "
                s = ""
                while not self._at_end() and self._peek() != '"':
                    if self._peek() == "\\":
                        self._advance()
                        s += self._advance()
                    else:
                        s += self._advance()
                if not self._at_end():
                    self._advance()  # closing "
                self.tokens.append(Token(TokenType.STRING, s, start_line, start_col))
                continue
            
            # Multi-character operators
            ch2 = ch + self._peek(1) if self.pos + 1 < len(self.source) else ch
            ch3 = ch2 + self._peek(2) if self.pos + 2 < len(self.source) else ch2

            # Attribute begin: (* but NOT (*)
            # @(*) is sensitivity list, not an attribute
            ch3_check = ""
            if self.pos + 2 < len(self.source):
                ch3_check = ch2 + self.source[self.pos + 2]

            if ch2 == "(*" and ch3_check != "(*)":
                self._advance(); self._advance()
                self.tokens.append(Token(TokenType.ATTR_BEGIN, "(*", start_line, start_col))
                self.in_attribute = True
                continue

            # Attribute end: *) - only if we're inside an attribute
            if ch2 == "*)" and self.in_attribute:
                self._advance(); self._advance()
                self.tokens.append(Token(TokenType.ATTR_END, "*)", start_line, start_col))
                self.in_attribute = False
                continue

            if ch3 == ">>>":
                self._advance(); self._advance(); self._advance()
                self.tokens.append(Token(TokenType.ARSHIFT, ">>>", start_line, start_col))
                continue

            TWO_CHAR = {
                "<<": TokenType.LSHIFT,
                ">>": TokenType.RSHIFT,
                "==": TokenType.EQ,
                "!=": TokenType.NEQ,
                "<=": TokenType.LE,
                ">=": TokenType.GE,
                "&&": TokenType.LAND,
                "||": TokenType.LOR,
                "->": TokenType.ARROW,
                "+:": TokenType.PLUSCOLON,
                "-:": TokenType.MINUSCOLON,
            }

            if ch2 in TWO_CHAR:
                self._advance(); self._advance()
                self.tokens.append(Token(TWO_CHAR[ch2], ch2, start_line, start_col))
                continue
            
            # Single character operators/delimiters
            ONE_CHAR = {
                "+": TokenType.PLUS,
                "-": TokenType.MINUS,
                "*": TokenType.STAR,
                "/": TokenType.SLASH,
                "%": TokenType.PERCENT,
                "&": TokenType.AMP,
                "|": TokenType.PIPE,
                "^": TokenType.CARET,
                "~": TokenType.TILDE,
                "!": TokenType.BANG,
                "<": TokenType.LT,
                ">": TokenType.GT,
                "?": TokenType.QUESTION,
                ":": TokenType.COLON,
                "@": TokenType.AT,
                "#": TokenType.HASH,
                "(": TokenType.LPAREN,
                ")": TokenType.RPAREN,
                "[": TokenType.LBRACKET,
                "]": TokenType.RBRACKET,
                "{": TokenType.LBRACE,
                "}": TokenType.RBRACE,
                ";": TokenType.SEMICOLON,
                ",": TokenType.COMMA,
                ".": TokenType.DOT,
                "=": TokenType.ASSIGN_OP,
            }
            
            if ch in ONE_CHAR:
                self._advance()
                self.tokens.append(Token(ONE_CHAR[ch], ch, start_line, start_col))
                continue
            
            raise LexerError(f"Unexpected character: {ch!r}", self.line, self.col)
        
        self.tokens.append(Token(TokenType.EOF, "", self.line, self.col))
        return self.tokens


def lex(source: str, filename: str = "<input>") -> list[Token]:
    """Convenience function: lex source code into tokens."""
    return Lexer(source, filename).tokenize()

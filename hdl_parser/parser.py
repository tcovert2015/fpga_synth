"""
Recursive-descent parser for a synthesizable Verilog subset.

Supported constructs:
  - Module declarations with parameters and ports
  - wire / reg / integer declarations
  - parameter / localparam
  - assign (continuous assignment)
  - always @(posedge clk), always @(*)
  - if/else, case/casex/casez
  - begin/end blocks
  - Module instantiation with named ports
  - generate / for-generate
  - Expressions: arithmetic, bitwise, logical, comparison, shift,
    ternary, concatenation, replication, bit-select, part-select
  
  Number literal parsing resolves sized (8'hFF) and unsized (42) formats.
"""

from __future__ import annotations
from typing import Optional

from fpga_synth.hdl_parser.tokens import Token, TokenType
from fpga_synth.hdl_parser.lexer import lex
from fpga_synth.hdl_parser.ast_nodes import *


class ParseError(Exception):
    def __init__(self, msg: str, token: Token):
        super().__init__(f"Parse error at L{token.line}:{token.col}: {msg} (got {token.type.name} = {token.value!r})")
        self.token = token


class Parser:
    """Recursive-descent parser producing an AST."""
    
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
    
    # ---- Token navigation ----
    
    def _cur(self) -> Token:
        return self.tokens[self.pos]
    
    def _peek(self, offset=0) -> Token:
        p = self.pos + offset
        if p < len(self.tokens):
            return self.tokens[p]
        return self.tokens[-1]  # EOF
    
    def _at(self, *types: TokenType) -> bool:
        return self._cur().type in types
    
    def _eat(self, tt: TokenType) -> Token:
        tok = self._cur()
        if tok.type != tt:
            raise ParseError(f"Expected {tt.name}", tok)
        self.pos += 1
        return tok
    
    def _eat_if(self, tt: TokenType) -> Optional[Token]:
        if self._cur().type == tt:
            return self._eat(tt)
        return None
    
    def _expect_semi(self):
        self._eat(TokenType.SEMICOLON)
    
    # ---- Number literal resolution ----
    
    @staticmethod
    def resolve_number(raw: str) -> tuple[int, int, bool]:
        """Parse a Verilog number literal. Returns (value, width, signed)."""
        raw = raw.replace("_", "")
        
        if "'" in raw:
            parts = raw.split("'", 1)
            size_str = parts[0]
            rest = parts[1]
            
            signed = False
            if rest and rest[0].lower() == 's':
                signed = True
                rest = rest[1:]
            
            if not rest:
                return (0, 32, False)
            
            base_char = rest[0].lower()
            digits = rest[1:] if len(rest) > 1 else "0"
            digits = digits.replace("x", "0").replace("X", "0")
            digits = digits.replace("z", "0").replace("Z", "0")
            
            base_map = {"b": 2, "o": 8, "d": 10, "h": 16}
            base = base_map.get(base_char, 10)
            
            width = int(size_str) if size_str else 32
            value = int(digits, base) if digits else 0
            return (value, width, signed)
        else:
            return (int(raw), 32, False)

    # ---- Attributes ----

    def _parse_attributes(self) -> dict[str, str]:
        """Parse Verilog attributes: (* key1 = value1, key2 = value2 *)"""
        attrs = {}
        if not self._at(TokenType.ATTR_BEGIN):
            return attrs

        self._eat(TokenType.ATTR_BEGIN)

        while not self._at(TokenType.ATTR_END):
            # Parse key = value
            key = self._eat(TokenType.IDENT).value

            value = ""
            if self._eat_if(TokenType.ASSIGN_OP):
                # Value can be identifier, number, or string
                if self._at(TokenType.IDENT):
                    value = self._eat(TokenType.IDENT).value
                elif self._at(TokenType.NUMBER):
                    value = self._eat(TokenType.NUMBER).value
                elif self._at(TokenType.STRING):
                    value = self._eat(TokenType.STRING).value
                else:
                    value = self._eat(TokenType.IDENT).value  # Try to eat something

            attrs[key] = value

            # Comma separates multiple attributes
            if not self._eat_if(TokenType.COMMA):
                break

        self._eat(TokenType.ATTR_END)
        return attrs

    # ---- Top-level ----
    
    def parse(self) -> SourceFile:
        """Parse a complete Verilog source file."""
        sf = SourceFile()
        while not self._at(TokenType.EOF):
            sf.modules.append(self._parse_module())
        return sf
    
    # ---- Module ----
    
    def _parse_module(self) -> Module:
        # Parse attributes if present
        attrs = self._parse_attributes()

        tok = self._eat(TokenType.MODULE)
        mod = Module(line=tok.line, col=tok.col, attributes=attrs)
        mod.name = self._eat(TokenType.IDENT).value
        
        # Optional parameter list: #(parameter ...)
        if self._eat_if(TokenType.HASH):
            self._eat(TokenType.LPAREN)
            while not self._at(TokenType.RPAREN):
                mod.params.append(self._parse_param_decl())
                self._eat_if(TokenType.COMMA)
            self._eat(TokenType.RPAREN)
        
        # Port list
        if self._eat_if(TokenType.LPAREN):
            if not self._at(TokenType.RPAREN):
                self._parse_port_list(mod)
            self._eat(TokenType.RPAREN)
        
        self._expect_semi()
        
        # Module body
        while not self._at(TokenType.ENDMODULE):
            item = self._parse_module_item(mod)
            if item is not None:
                mod.body.append(item)
        
        self._eat(TokenType.ENDMODULE)
        return mod
    
    def _parse_port_list(self, mod: Module):
        """Parse ANSI-style port declarations in the module header."""
        while True:
            port = self._parse_port_decl()
            mod.ports.append(port)
            if not self._eat_if(TokenType.COMMA):
                break
    
    def _parse_port_decl(self) -> PortDecl:
        """Parse a single port declaration: input [signed] [7:0] name"""
        tok = self._cur()
        pd = PortDecl(line=tok.line, col=tok.col)
        
        # Direction
        if self._at(TokenType.INPUT):
            pd.direction = "input"
            self._eat(TokenType.INPUT)
        elif self._at(TokenType.OUTPUT):
            pd.direction = "output"
            self._eat(TokenType.OUTPUT)
        elif self._at(TokenType.INOUT):
            pd.direction = "inout"
            self._eat(TokenType.INOUT)
        
        # Optional: wire / reg
        if self._at(TokenType.WIRE):
            pd.net_type = "wire"
            self._eat(TokenType.WIRE)
        elif self._at(TokenType.REG):
            pd.net_type = "reg"
            self._eat(TokenType.REG)
        
        # Optional: signed
        if self._at(TokenType.SIGNED):
            pd.signed = True
            self._eat(TokenType.SIGNED)
        
        # Optional: range
        if self._at(TokenType.LBRACKET):
            pd.range = self._parse_range()

        pd.name = self._eat(TokenType.IDENT).value

        # Optional array dimensions (unpacked arrays)
        while self._at(TokenType.LBRACKET):
            pd.array_dims.append(self._parse_range())

        return pd
    
    def _parse_range(self) -> Range:
        """Parse [msb:lsb]"""
        self._eat(TokenType.LBRACKET)
        msb = self._parse_expr()
        self._eat(TokenType.COLON)
        lsb = self._parse_expr()
        self._eat(TokenType.RBRACKET)
        return Range(msb=msb, lsb=lsb)
    
    # ---- Module body items ----
    
    def _parse_module_item(self, mod: Optional[Module]) -> Optional[ASTNode]:
        tok = self._cur()

        # Parse attributes if present
        attrs = self._parse_attributes()

        # Wire / reg declaration
        if self._at(TokenType.WIRE, TokenType.REG):
            decl = self._parse_net_decl()
            decl.attributes = attrs
            if mod:
                mod.body.append(decl)
                return None  # Already appended
            return decl

        # Integer declaration
        if self._at(TokenType.INTEGER):
            self._eat(TokenType.INTEGER)
            name = self._eat(TokenType.IDENT).value
            self._expect_semi()
            decl = IntegerDecl(name=name, line=tok.line, col=tok.col, attributes=attrs)
            if mod:
                mod.body.append(decl)
                return None
            return decl

        # Parameter / localparam in body
        if self._at(TokenType.PARAMETER, TokenType.LOCALPARAM):
            pd = self._parse_param_decl()
            pd.attributes = attrs
            self._expect_semi()
            if mod:
                mod.body.append(pd)
                mod.params.append(pd)
                return None
            return pd

        # Continuous assign
        if self._at(TokenType.ASSIGN):
            item = self._parse_continuous_assign()
            item.attributes = attrs
            return item

        # Always block
        if self._at(TokenType.ALWAYS):
            item = self._parse_always()
            item.attributes = attrs
            return item

        # Initial block
        if self._at(TokenType.INITIAL):
            item = self._parse_initial()
            item.attributes = attrs
            return item

        # Task declaration
        if self._at(TokenType.TASK):
            item = self._parse_task()
            item.attributes = attrs
            return item

        # Function declaration
        if self._at(TokenType.FUNCTION):
            item = self._parse_function()
            item.attributes = attrs
            return item

        # Generate block
        if self._at(TokenType.GENERATE):
            item = self._parse_generate()
            item.attributes = attrs
            return item

        # Genvar
        if self._at(TokenType.GENVAR):
            self._eat(TokenType.GENVAR)
            name = self._eat(TokenType.IDENT).value
            self._expect_semi()
            decl = IntegerDecl(name=name, line=tok.line, col=tok.col, attributes=attrs)
            if mod:
                mod.body.append(decl)
                return None
            return decl

        # Module instantiation: identifier identifier (...)
        if self._at(TokenType.IDENT):
            # Look ahead to distinguish net declaration from instantiation
            # Instantiation: modname [#(...)] instname (...)
            if (self._peek(1).type == TokenType.IDENT or
                self._peek(1).type == TokenType.HASH):
                item = self._parse_module_instance()
                item.attributes = attrs
                return item

        raise ParseError(f"Unexpected token in module body", tok)
    
    def _parse_net_decl(self) -> NetDecl:
        tok = self._cur()
        nd = NetDecl(line=tok.line, col=tok.col)
        
        if self._at(TokenType.WIRE):
            nd.net_type = "wire"
            self._eat(TokenType.WIRE)
        elif self._at(TokenType.REG):
            nd.net_type = "reg"
            self._eat(TokenType.REG)
        
        if self._at(TokenType.SIGNED):
            nd.signed = True
            self._eat(TokenType.SIGNED)
        
        if self._at(TokenType.LBRACKET):
            nd.range = self._parse_range()
        
        nd.name = self._eat(TokenType.IDENT).value

        # Optional array dimensions (unpacked arrays)
        while self._at(TokenType.LBRACKET):
            nd.array_dims.append(self._parse_range())

        # Optional initial value
        if self._eat_if(TokenType.ASSIGN_OP):
            nd.init_value = self._parse_expr()

        self._expect_semi()
        return nd
    
    def _parse_param_decl(self) -> ParamDecl:
        tok = self._cur()
        pd = ParamDecl(line=tok.line, col=tok.col)
        
        if self._at(TokenType.PARAMETER):
            pd.kind = "parameter"
            self._eat(TokenType.PARAMETER)
        elif self._at(TokenType.LOCALPARAM):
            pd.kind = "localparam"
            self._eat(TokenType.LOCALPARAM)
        
        if self._at(TokenType.SIGNED):
            pd.signed = True
            self._eat(TokenType.SIGNED)
        
        if self._at(TokenType.LBRACKET):
            pd.range = self._parse_range()
        
        # Check for optional INTEGER keyword
        if self._at(TokenType.INTEGER):
            self._eat(TokenType.INTEGER)
        
        pd.name = self._eat(TokenType.IDENT).value
        self._eat(TokenType.ASSIGN_OP)
        pd.value = self._parse_expr()
        
        return pd
    
    def _parse_continuous_assign(self) -> ContinuousAssign:
        tok = self._eat(TokenType.ASSIGN)
        ca = ContinuousAssign(line=tok.line, col=tok.col)
        ca.lhs = self._parse_expr()
        self._eat(TokenType.ASSIGN_OP)
        ca.rhs = self._parse_expr()
        self._expect_semi()
        return ca
    
    # ---- Always blocks ----
    
    def _parse_always(self) -> AlwaysBlock:
        tok = self._eat(TokenType.ALWAYS)
        ab = AlwaysBlock(line=tok.line, col=tok.col)
        
        self._eat(TokenType.AT)
        self._eat(TokenType.LPAREN)
        
        # Check for @(*)
        if self._at(TokenType.STAR):
            self._eat(TokenType.STAR)
            ab.is_star = True
        else:
            # Parse sensitivity list
            while True:
                si = SensItem()
                if self._at(TokenType.POSEDGE):
                    si.edge = "posedge"
                    self._eat(TokenType.POSEDGE)
                elif self._at(TokenType.NEGEDGE):
                    si.edge = "negedge"
                    self._eat(TokenType.NEGEDGE)
                si.signal = self._parse_expr()
                ab.sensitivity.append(si)
                
                if not self._at(TokenType.COMMA) and not self._at(TokenType.IDENT, TokenType.POSEDGE, TokenType.NEGEDGE):
                    break
                self._eat_if(TokenType.COMMA)
                # Also allow "or" keyword between sensitivity items
                if self._at(TokenType.IDENT) and self._cur().value == "or":
                    self._eat(TokenType.IDENT)
        
        self._eat(TokenType.RPAREN)
        
        # Body: single statement or begin...end block
        ab.body = self._parse_statement_or_block()
        return ab

    def _parse_initial(self) -> InitialBlock:
        tok = self._eat(TokenType.INITIAL)
        ib = InitialBlock(line=tok.line, col=tok.col)
        ib.body = self._parse_statement_or_block()
        return ib

    def _parse_statement_or_block(self) -> list[Statement]:
        """Parse either begin...end or a single statement."""
        if self._at(TokenType.BEGIN):
            return self._parse_begin_end()
        else:
            stmt = self._parse_statement()
            return [stmt] if stmt else []
    
    def _parse_begin_end(self) -> list[Statement]:
        self._eat(TokenType.BEGIN)
        # Optional block name: begin : name
        if self._eat_if(TokenType.COLON):
            self._eat(TokenType.IDENT)  # block name (ignored for now)
        
        stmts = []
        while not self._at(TokenType.END):
            stmt = self._parse_statement()
            if stmt:
                stmts.append(stmt)
        self._eat(TokenType.END)
        return stmts
    
    def _parse_statement(self) -> Optional[Statement]:
        tok = self._cur()
        
        if self._at(TokenType.IF):
            return self._parse_if()
        
        if self._at(TokenType.CASE, TokenType.CASEX, TokenType.CASEZ):
            return self._parse_case()
        
        if self._at(TokenType.FOR):
            return self._parse_for()

        if self._at(TokenType.WHILE):
            return self._parse_while()

        if self._at(TokenType.REPEAT):
            return self._parse_repeat()

        if self._at(TokenType.FOREVER):
            return self._parse_forever()

        if self._at(TokenType.DISABLE):
            return self._parse_disable()

        if self._at(TokenType.BEGIN):
            stmts = self._parse_begin_end()
            return Block(stmts=stmts, line=tok.line, col=tok.col)
        
        # Task call or assignment
        if self._at(TokenType.IDENT, TokenType.LBRACE):
            # Look ahead to distinguish task call from assignment
            # Task call: identifier(args);
            # Assignment: identifier = expr;
            if self._at(TokenType.IDENT) and self._peek(1).type == TokenType.LPAREN:
                # Could be task call
                name = self._eat(TokenType.IDENT).value
                self._eat(TokenType.LPAREN)
                args = []
                while not self._at(TokenType.RPAREN):
                    args.append(self._parse_expr())
                    if not self._eat_if(TokenType.COMMA):
                        break
                self._eat(TokenType.RPAREN)
                self._expect_semi()
                return TaskCall(name=name, args=args, line=tok.line, col=tok.col)

            # Otherwise parse as assignment
            lhs = self._parse_expr()

            if self._at(TokenType.ASSIGN_OP):
                self._eat(TokenType.ASSIGN_OP)
                rhs = self._parse_expr()
                self._expect_semi()
                return BlockingAssign(lhs=lhs, rhs=rhs, line=tok.line, col=tok.col)
            elif self._at(TokenType.LE):
                self._eat(TokenType.LE)
                rhs = self._parse_expr()
                self._expect_semi()
                return NonBlockingAssign(lhs=lhs, rhs=rhs, line=tok.line, col=tok.col)
        
        # Integer / reg declaration inside always (for loop vars etc.)
        if self._at(TokenType.INTEGER):
            self._eat(TokenType.INTEGER)
            name = self._eat(TokenType.IDENT).value
            self._expect_semi()
            return None  # Treat as declaration, not a statement
        
        raise ParseError("Expected statement", tok)
    
    def _parse_if(self) -> IfStatement:
        tok = self._eat(TokenType.IF)
        self._eat(TokenType.LPAREN)
        cond = self._parse_expr()
        self._eat(TokenType.RPAREN)
        
        then_body = self._parse_statement_or_block()
        else_body = []
        
        if self._eat_if(TokenType.ELSE):
            else_body = self._parse_statement_or_block()
        
        return IfStatement(cond=cond, then_body=then_body, else_body=else_body,
                           line=tok.line, col=tok.col)
    
    def _parse_case(self) -> CaseStatement:
        tok = self._cur()
        kind = tok.value
        self._eat(tok.type)  # case / casex / casez
        
        self._eat(TokenType.LPAREN)
        expr = self._parse_expr()
        self._eat(TokenType.RPAREN)
        
        cs = CaseStatement(kind=kind, expr=expr, line=tok.line, col=tok.col)
        
        while not self._at(TokenType.ENDCASE):
            if self._at(TokenType.DEFAULT):
                self._eat(TokenType.DEFAULT)
                self._eat(TokenType.COLON)
                cs.default = self._parse_statement_or_block()
            else:
                ci = CaseItem(line=self._cur().line, col=self._cur().col)
                # Parse comma-separated values
                while True:
                    ci.values.append(self._parse_expr())
                    if not self._eat_if(TokenType.COMMA):
                        break
                self._eat(TokenType.COLON)
                ci.body = self._parse_statement_or_block()
                cs.items.append(ci)
        
        self._eat(TokenType.ENDCASE)
        return cs
    
    def _parse_for(self) -> ForStatement:
        tok = self._eat(TokenType.FOR)
        self._eat(TokenType.LPAREN)
        
        # Init
        init_lhs = self._parse_expr()
        self._eat(TokenType.ASSIGN_OP)
        init_rhs = self._parse_expr()
        init = BlockingAssign(lhs=init_lhs, rhs=init_rhs)
        self._expect_semi()
        
        # Condition
        cond = self._parse_expr()
        self._expect_semi()
        
        # Update
        upd_lhs = self._parse_expr()
        self._eat(TokenType.ASSIGN_OP)
        upd_rhs = self._parse_expr()
        update = BlockingAssign(lhs=upd_lhs, rhs=upd_rhs)
        
        self._eat(TokenType.RPAREN)
        
        body = self._parse_statement_or_block()
        return ForStatement(init=init, cond=cond, update=update, body=body,
                           line=tok.line, col=tok.col)

    def _parse_while(self) -> WhileStatement:
        tok = self._eat(TokenType.WHILE)
        self._eat(TokenType.LPAREN)
        cond = self._parse_expr()
        self._eat(TokenType.RPAREN)
        body = self._parse_statement_or_block()
        return WhileStatement(cond=cond, body=body, line=tok.line, col=tok.col)

    def _parse_repeat(self) -> RepeatStatement:
        tok = self._eat(TokenType.REPEAT)
        self._eat(TokenType.LPAREN)
        count = self._parse_expr()
        self._eat(TokenType.RPAREN)
        body = self._parse_statement_or_block()
        return RepeatStatement(count=count, body=body, line=tok.line, col=tok.col)

    def _parse_forever(self) -> ForeverStatement:
        tok = self._eat(TokenType.FOREVER)
        body = self._parse_statement_or_block()
        return ForeverStatement(body=body, line=tok.line, col=tok.col)

    def _parse_disable(self) -> DisableStatement:
        tok = self._eat(TokenType.DISABLE)
        target = self._eat(TokenType.IDENT).value
        self._expect_semi()
        return DisableStatement(target=target, line=tok.line, col=tok.col)

    def _parse_task(self) -> TaskDecl:
        tok = self._eat(TokenType.TASK)
        td = TaskDecl(line=tok.line, col=tok.col)

        # Optional: automatic
        if self._at(TokenType.AUTOMATIC):
            td.automatic = True
            self._eat(TokenType.AUTOMATIC)

        td.name = self._eat(TokenType.IDENT).value
        self._expect_semi()

        # Task body: declarations and statements
        while not self._at(TokenType.ENDTASK):
            if self._at(TokenType.INPUT):
                self._eat(TokenType.INPUT)
                # Parse input declaration(s)
                port = self._parse_task_port("input")
                td.inputs.append(port)
                self._expect_semi()
            elif self._at(TokenType.OUTPUT):
                self._eat(TokenType.OUTPUT)
                port = self._parse_task_port("output")
                td.outputs.append(port)
                self._expect_semi()
            elif self._at(TokenType.INOUT):
                self._eat(TokenType.INOUT)
                port = self._parse_task_port("inout")
                td.inouts.append(port)
                self._expect_semi()
            elif self._at(TokenType.REG, TokenType.INTEGER, TokenType.WIRE):
                # Local variable declaration - skip for now
                self._parse_net_decl()
            else:
                # Statement
                stmt = self._parse_statement()
                if stmt:
                    td.body.append(stmt)

        self._eat(TokenType.ENDTASK)
        return td

    def _parse_task_port(self, direction: str) -> PortDecl:
        """Parse a task/function port declaration."""
        tok = self._cur()
        pd = PortDecl(line=tok.line, col=tok.col)
        pd.direction = direction

        # Optional: reg
        if self._at(TokenType.REG):
            pd.net_type = "reg"
            self._eat(TokenType.REG)

        # Optional: signed
        if self._at(TokenType.SIGNED):
            pd.signed = True
            self._eat(TokenType.SIGNED)

        # Optional: range
        if self._at(TokenType.LBRACKET):
            pd.range = self._parse_range()

        pd.name = self._eat(TokenType.IDENT).value
        return pd

    def _parse_function(self) -> FunctionDecl:
        tok = self._eat(TokenType.FUNCTION)
        fd = FunctionDecl(line=tok.line, col=tok.col)

        # Optional: automatic
        if self._at(TokenType.AUTOMATIC):
            fd.automatic = True
            self._eat(TokenType.AUTOMATIC)

        # Optional: signed
        if self._at(TokenType.SIGNED):
            fd.signed = True
            self._eat(TokenType.SIGNED)

        # Optional: return range
        if self._at(TokenType.LBRACKET):
            fd.return_type = self._parse_range()

        fd.name = self._eat(TokenType.IDENT).value
        self._expect_semi()

        # Function body: input declarations and statements
        while not self._at(TokenType.ENDFUNCTION):
            if self._at(TokenType.INPUT):
                self._eat(TokenType.INPUT)
                port = self._parse_task_port("input")
                fd.inputs.append(port)
                self._expect_semi()
            elif self._at(TokenType.REG, TokenType.INTEGER):
                # Local variable declaration
                self._parse_net_decl()
            else:
                # Statement
                stmt = self._parse_statement()
                if stmt:
                    fd.body.append(stmt)

        self._eat(TokenType.ENDFUNCTION)
        return fd

    def _parse_generate_item_or_block(self) -> list[ASTNode]:
        """Parse either begin...end with module items or a single module item in generate context."""
        if self._at(TokenType.BEGIN):
            tok = self._eat(TokenType.BEGIN)
            # Optional block name: begin : name
            name = ""
            if self._eat_if(TokenType.COLON):
                name = self._eat(TokenType.IDENT).value

            items = []
            while not self._at(TokenType.END):
                if self._at(TokenType.FOR):
                    items.append(self._parse_generate_for())
                elif self._at(TokenType.IF):
                    items.append(self._parse_generate_if())
                elif self._at(TokenType.CASE, TokenType.CASEX, TokenType.CASEZ):
                    items.append(self._parse_generate_case())
                else:
                    item = self._parse_module_item(None)
                    if item:
                        items.append(item)
            self._eat(TokenType.END)

            # Wrap in a Block if it has a name
            if name:
                return [Block(name=name, stmts=items, line=tok.line, col=tok.col)]
            else:
                return items
        else:
            # Single module item
            item = self._parse_module_item(None)
            return [item] if item else []

    def _parse_generate_if(self) -> IfStatement:
        """Parse if statement in generate context (body contains module items)."""
        tok = self._eat(TokenType.IF)
        self._eat(TokenType.LPAREN)
        cond = self._parse_expr()
        self._eat(TokenType.RPAREN)

        then_body = self._parse_generate_item_or_block()
        else_body = []

        if self._eat_if(TokenType.ELSE):
            else_body = self._parse_generate_item_or_block()

        return IfStatement(cond=cond, then_body=then_body, else_body=else_body,
                          line=tok.line, col=tok.col)

    def _parse_generate_for(self) -> ForStatement:
        """Parse for loop in generate context (body contains module items)."""
        tok = self._eat(TokenType.FOR)
        self._eat(TokenType.LPAREN)

        # Init
        init_lhs = self._parse_expr()
        self._eat(TokenType.ASSIGN_OP)
        init_rhs = self._parse_expr()
        init = BlockingAssign(lhs=init_lhs, rhs=init_rhs)
        self._expect_semi()

        # Condition
        cond = self._parse_expr()
        self._expect_semi()

        # Update
        upd_lhs = self._parse_expr()
        self._eat(TokenType.ASSIGN_OP)
        upd_rhs = self._parse_expr()
        update = BlockingAssign(lhs=upd_lhs, rhs=upd_rhs)

        self._eat(TokenType.RPAREN)

        body = self._parse_generate_item_or_block()
        return ForStatement(init=init, cond=cond, update=update, body=body,
                           line=tok.line, col=tok.col)

    def _parse_generate_case(self) -> CaseStatement:
        """Parse case statement in generate context (body contains module items)."""
        tok = self._cur()
        kind = tok.value
        self._eat(tok.type)  # case / casex / casez

        self._eat(TokenType.LPAREN)
        expr = self._parse_expr()
        self._eat(TokenType.RPAREN)

        cs = CaseStatement(kind=kind, expr=expr, line=tok.line, col=tok.col)

        while not self._at(TokenType.ENDCASE):
            if self._at(TokenType.DEFAULT):
                self._eat(TokenType.DEFAULT)
                self._eat(TokenType.COLON)
                cs.default = self._parse_generate_item_or_block()
            else:
                ci = CaseItem(line=self._cur().line, col=self._cur().col)
                # Parse comma-separated values
                while True:
                    ci.values.append(self._parse_expr())
                    if not self._eat_if(TokenType.COMMA):
                        break
                self._eat(TokenType.COLON)
                ci.body = self._parse_generate_item_or_block()
                cs.items.append(ci)

        self._eat(TokenType.ENDCASE)
        return cs

    def _parse_generate(self) -> GenerateBlock:
        tok = self._eat(TokenType.GENERATE)
        gb = GenerateBlock(line=tok.line, col=tok.col)

        while not self._at(TokenType.ENDGENERATE):
            if self._at(TokenType.FOR):
                gb.items.append(self._parse_generate_for())
            elif self._at(TokenType.IF):
                gb.items.append(self._parse_generate_if())
            elif self._at(TokenType.CASE, TokenType.CASEX, TokenType.CASEZ):
                gb.items.append(self._parse_generate_case())
            elif self._at(TokenType.BEGIN):
                # Named generate block: begin : name ... end
                tok = self._eat(TokenType.BEGIN)
                name = ""
                if self._eat_if(TokenType.COLON):
                    name = self._eat(TokenType.IDENT).value
                items = []
                while not self._at(TokenType.END):
                    if self._at(TokenType.FOR):
                        items.append(self._parse_generate_for())
                    elif self._at(TokenType.IF):
                        items.append(self._parse_generate_if())
                    elif self._at(TokenType.CASE, TokenType.CASEX, TokenType.CASEZ):
                        items.append(self._parse_generate_case())
                    else:
                        # Module instance or other item
                        item = self._parse_module_item(None)
                        if item:
                            items.append(item)
                self._eat(TokenType.END)
                gb.items.append(Block(name=name, stmts=items, line=tok.line, col=tok.col))
            elif self._at(TokenType.GENVAR):
                self._eat(TokenType.GENVAR)
                self._eat(TokenType.IDENT)
                self._expect_semi()
            else:
                # Try parsing as module instance or other module item
                item = self._parse_module_item(None)
                if item:
                    gb.items.append(item)

        self._eat(TokenType.ENDGENERATE)
        return gb
    
    # ---- Module instantiation ----
    
    def _parse_module_instance(self) -> ModuleInstance:
        tok = self._cur()
        mi = ModuleInstance(line=tok.line, col=tok.col)
        mi.module_name = self._eat(TokenType.IDENT).value
        
        # Optional parameter overrides: #(.P(V), ...)
        if self._eat_if(TokenType.HASH):
            self._eat(TokenType.LPAREN)
            while not self._at(TokenType.RPAREN):
                pc = PortConnection()
                if self._at(TokenType.DOT):
                    self._eat(TokenType.DOT)
                    pc.port_name = self._eat(TokenType.IDENT).value
                    self._eat(TokenType.LPAREN)
                    pc.expr = self._parse_expr()
                    self._eat(TokenType.RPAREN)
                else:
                    pc.expr = self._parse_expr()
                mi.params.append(pc)
                self._eat_if(TokenType.COMMA)
            self._eat(TokenType.RPAREN)
        
        mi.instance_name = self._eat(TokenType.IDENT).value
        
        # Port connections: (.port(signal), ...)
        self._eat(TokenType.LPAREN)
        while not self._at(TokenType.RPAREN):
            pc = PortConnection()
            if self._at(TokenType.DOT):
                self._eat(TokenType.DOT)
                pc.port_name = self._eat(TokenType.IDENT).value
                self._eat(TokenType.LPAREN)
                if not self._at(TokenType.RPAREN):
                    pc.expr = self._parse_expr()
                self._eat(TokenType.RPAREN)
            else:
                pc.expr = self._parse_expr()
            mi.ports.append(pc)
            self._eat_if(TokenType.COMMA)
        self._eat(TokenType.RPAREN)
        
        self._expect_semi()
        return mi
    
    # ---- Expression parsing (precedence climbing) ----
    
    def _parse_expr(self) -> Expr:
        return self._parse_ternary()
    
    def _parse_ternary(self) -> Expr:
        expr = self._parse_lor()
        if self._eat_if(TokenType.QUESTION):
            true_val = self._parse_expr()
            self._eat(TokenType.COLON)
            false_val = self._parse_ternary()
            return TernaryOp(cond=expr, true_val=true_val, false_val=false_val,
                            line=expr.line, col=expr.col)
        return expr
    
    def _parse_lor(self) -> Expr:
        left = self._parse_land()
        while self._at(TokenType.LOR):
            op = self._eat(TokenType.LOR).value
            right = self._parse_land()
            left = BinaryOp(op=op, left=left, right=right, line=left.line, col=left.col)
        return left
    
    def _parse_land(self) -> Expr:
        left = self._parse_bitor()
        while self._at(TokenType.LAND):
            op = self._eat(TokenType.LAND).value
            right = self._parse_bitor()
            left = BinaryOp(op=op, left=left, right=right, line=left.line, col=left.col)
        return left
    
    def _parse_bitor(self) -> Expr:
        left = self._parse_bitxor()
        while self._at(TokenType.PIPE):
            op = self._eat(TokenType.PIPE).value
            right = self._parse_bitxor()
            left = BinaryOp(op=op, left=left, right=right, line=left.line, col=left.col)
        return left
    
    def _parse_bitxor(self) -> Expr:
        left = self._parse_bitand()
        while self._at(TokenType.CARET):
            op = self._eat(TokenType.CARET).value
            right = self._parse_bitand()
            left = BinaryOp(op=op, left=left, right=right, line=left.line, col=left.col)
        return left
    
    def _parse_bitand(self) -> Expr:
        left = self._parse_equality()
        while self._at(TokenType.AMP):
            op = self._eat(TokenType.AMP).value
            right = self._parse_equality()
            left = BinaryOp(op=op, left=left, right=right, line=left.line, col=left.col)
        return left
    
    def _parse_equality(self) -> Expr:
        left = self._parse_comparison()
        while self._at(TokenType.EQ, TokenType.NEQ):
            op = self._eat(self._cur().type).value
            right = self._parse_comparison()
            left = BinaryOp(op=op, left=left, right=right, line=left.line, col=left.col)
        return left
    
    def _parse_comparison(self) -> Expr:
        left = self._parse_shift()
        while self._at(TokenType.LT, TokenType.GT, TokenType.GE):
            op = self._eat(self._cur().type).value
            right = self._parse_shift()
            left = BinaryOp(op=op, left=left, right=right, line=left.line, col=left.col)
        # LE is tricky: in statements it's non-blocking assign, in expressions it's <=
        # Here in expression context, we already parsed it as comparison in parent
        return left
    
    def _parse_shift(self) -> Expr:
        left = self._parse_additive()
        while self._at(TokenType.LSHIFT, TokenType.RSHIFT, TokenType.ARSHIFT):
            op = self._eat(self._cur().type).value
            right = self._parse_additive()
            left = BinaryOp(op=op, left=left, right=right, line=left.line, col=left.col)
        return left
    
    def _parse_additive(self) -> Expr:
        left = self._parse_multiplicative()
        while self._at(TokenType.PLUS, TokenType.MINUS):
            op = self._eat(self._cur().type).value
            right = self._parse_multiplicative()
            left = BinaryOp(op=op, left=left, right=right, line=left.line, col=left.col)
        return left
    
    def _parse_multiplicative(self) -> Expr:
        left = self._parse_unary()
        while self._at(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self._eat(self._cur().type).value
            right = self._parse_unary()
            left = BinaryOp(op=op, left=left, right=right, line=left.line, col=left.col)
        return left
    
    def _parse_unary(self) -> Expr:
        tok = self._cur()
        
        if self._at(TokenType.TILDE, TokenType.BANG, TokenType.MINUS, TokenType.PLUS):
            op = self._eat(self._cur().type).value
            operand = self._parse_unary()
            return UnaryOp(op=op, operand=operand, line=tok.line, col=tok.col)
        
        # Reduction operators: &x, |x, ^x (check if followed by expression, not assignment)
        if self._at(TokenType.AMP, TokenType.PIPE, TokenType.CARET):
            # Peek ahead — if this is the start of an expression and the next token
            # is a primary, it's a reduction operator
            if self._peek(1).type in (TokenType.IDENT, TokenType.NUMBER, TokenType.LPAREN, 
                                       TokenType.LBRACE, TokenType.TILDE, TokenType.BANG):
                op = self._eat(self._cur().type).value
                operand = self._parse_unary()
                return UnaryOp(op=op, operand=operand, line=tok.line, col=tok.col)
        
        return self._parse_postfix()
    
    def _parse_postfix(self) -> Expr:
        expr = self._parse_primary()
        
        # Bit select / part select: expr[idx] or expr[msb:lsb]
        while self._at(TokenType.LBRACKET):
            self._eat(TokenType.LBRACKET)
            msb = self._parse_expr()
            lsb = None
            if self._eat_if(TokenType.COLON):
                lsb = self._parse_expr()
            self._eat(TokenType.RBRACKET)
            expr = BitSelect(target=expr, msb=msb, lsb=lsb,
                            line=expr.line, col=expr.col)
        
        return expr
    
    def _parse_primary(self) -> Expr:
        tok = self._cur()
        
        # Number literal
        if self._at(TokenType.NUMBER):
            raw = self._eat(TokenType.NUMBER).value
            value, width, signed = self.resolve_number(raw)
            return NumberLiteral(raw=raw, value=value, width=width,
                               is_signed=signed, line=tok.line, col=tok.col)
        
        # Identifier (possibly a function call)
        if self._at(TokenType.IDENT):
            name = self._eat(TokenType.IDENT).value
            
            # System function call: $clog2(...)
            if name.startswith("$") or (self._at(TokenType.LPAREN) and 
                                         not self._peek(-2 if self.pos >= 2 else 0).type == TokenType.DOT):
                # Only treat as function call if immediately followed by (
                if self._at(TokenType.LPAREN):
                    self._eat(TokenType.LPAREN)
                    args = []
                    while not self._at(TokenType.RPAREN):
                        args.append(self._parse_expr())
                        self._eat_if(TokenType.COMMA)
                    self._eat(TokenType.RPAREN)
                    return FuncCall(name=name, args=args, line=tok.line, col=tok.col)
            
            return Identifier(name=name, line=tok.line, col=tok.col)
        
        # Parenthesized expression
        if self._at(TokenType.LPAREN):
            self._eat(TokenType.LPAREN)
            expr = self._parse_expr()
            self._eat(TokenType.RPAREN)
            return expr
        
        # Concatenation or replication: {a, b} or {4{a}}
        if self._at(TokenType.LBRACE):
            return self._parse_concat_or_repeat()
        
        raise ParseError("Expected expression", tok)
    
    def _parse_concat_or_repeat(self) -> Expr:
        tok = self._eat(TokenType.LBRACE)
        
        first = self._parse_expr()
        
        # Replication: {count{expr}}
        if self._at(TokenType.LBRACE):
            self._eat(TokenType.LBRACE)
            value = self._parse_expr()
            self._eat(TokenType.RBRACE)
            self._eat(TokenType.RBRACE)
            return Repeat(count=first, value=value, line=tok.line, col=tok.col)
        
        # Concatenation: {a, b, c, ...}
        parts = [first]
        while self._eat_if(TokenType.COMMA):
            parts.append(self._parse_expr())
        self._eat(TokenType.RBRACE)
        
        if len(parts) == 1:
            return parts[0]  # {a} is just a
        return Concat(parts=parts, line=tok.line, col=tok.col)


# ============================================================
# Public API
# ============================================================

def parse_verilog(source: str, filename: str = "<input>") -> SourceFile:
    """Parse Verilog source code into an AST."""
    tokens = lex(source, filename)
    parser = Parser(tokens)
    return parser.parse()

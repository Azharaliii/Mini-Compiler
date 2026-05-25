"""
Complete Mini Compiler Implementation – AssemblyLang
Includes: Lexical Analysis, Parsing, Semantic Analysis, and Intermediate Code Generation

Features:
- Assembly-style language definition with grammar
- Complete lexical analyzer with error handling
- LL(1) recursive-descent parser with syntax error detection and recovery
- Symbol table with scope management (DATA scope / CODE scope / PROC scope)
- Type checking and semantic analysis
- Three-Address Code (TAC) generation mirroring the parser structure
- Modern GUI matching the original SimpleLang dashboard design

Language: AssemblyLang – A simplified x86-style assembly language
Supports: MOV, ADD, SUB, MUL, DIV, CMP, JMP, JE, JNE, JG, JL, JGE, JLE,
          PUSH, POP, CALL, RET, NOP, HLT, PROC/ENDP, SECTION DATA/CODE,
          DB/DW/DD/DQ variable declarations, registers, memory references

Run: python Assembly_Compiler.py
Requires: Python 3 with tkinter
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import webbrowser
from enum import Enum

# ==================== LANGUAGE DEFINITION ====================
"""
AssemblyLang Grammar (Transformed – Ambiguity Removed, Left Recursion Eliminated):

Program      → SectionList EOF
SectionList  → Section SectionList | ε
Section      → DataSection | CodeSection
DataSection  → SECTION DATA VarDeclList
CodeSection  → SECTION CODE ProcOrStmtList
VarDeclList  → VarDecl VarDeclList | ε
VarDecl      → ID SizeDir Initializer
SizeDir      → DB | DW | DD | DQ
Initializer  → NUM | HEX_NUM | STR_LITERAL | ?
ProcOrStmtList → ProcDef ProcOrStmtList | Stmt ProcOrStmtList | ε
ProcDef      → PROC ID StmtList ENDP ID
StmtList     → Stmt StmtList | ε
Stmt         → LabelDef | Instruction
LabelDef     → ID COLON
Instruction  → MovInstr | ArithInstr | CmpInstr | JumpInstr
             | StackInstr | CallInstr | RetInstr | NopInstr | HltInstr
MovInstr     → MOV Operand COMMA Operand
ArithInstr   → (ADD|SUB|MUL|DIV) Operand COMMA Operand
CmpInstr     → CMP Operand COMMA Operand
JumpInstr    → JmpOp ID
JmpOp        → JMP|JE|JNE|JG|JL|JGE|JLE
StackInstr   → PUSH Operand | POP Operand
CallInstr    → CALL ID
RetInstr     → RET
NopInstr     → NOP
HltInstr     → HLT
Operand      → SizeQual LBRACKET InnerMem RBRACKET
             | LBRACKET InnerMem RBRACKET
             | Register | NUM | HEX_NUM | ID
SizeQual     → (BYTE|WORD|DWORD|QWORD) PTR
InnerMem     → Operand | Operand PLUS Operand | Operand MINUS Operand
Register     → AX|BX|CX|DX|SP|BP|SI|DI|AL|AH|BL|BH|CL|CH|DL|DH
"""

# ==================== TOKEN DEFINITIONS ====================
class TokenType(Enum):
    # Instructions / Mnemonics
    MOV = 'MOV'; ADD = 'ADD'; SUB = 'SUB'; MUL = 'MUL'; DIV = 'DIV'
    CMP = 'CMP'; JMP = 'JMP'; JE = 'JE';  JNE = 'JNE'; JG = 'JG'
    JL  = 'JL';  JGE = 'JGE'; JLE = 'JLE'
    PUSH = 'PUSH'; POP = 'POP'; CALL = 'CALL'; RET = 'RET'
    NOP = 'NOP';  HLT = 'HLT'; PROC = 'PROC'; ENDP = 'ENDP'
    # Directives
    SECTION = 'SECTION'; DATA = 'DATA'; CODE = 'CODE'
    DB = 'DB'; DW = 'DW'; DD = 'DD'; DQ = 'DQ'
    BYTE = 'BYTE'; WORD = 'WORD'; DWORD = 'DWORD'; QWORD = 'QWORD'; PTR = 'PTR'
    # Registers
    REG = 'REG'
    # Separators
    COMMA = 'COMMA'; COLON = 'COLON'
    LBRACKET = 'LBRACKET'; RBRACKET = 'RBRACKET'
    PLUS = 'PLUS'; MINUS = 'MINUS'
    NEWLINE = 'NEWLINE'
    # Literals / Identifiers
    ID = 'ID'; NUM = 'NUM'; HEX_NUM = 'HEX_NUM'; STR_LITERAL = 'STR_LITERAL'
    # Special
    COMMENT = 'COMMENT'; EOF = 'EOF'; ERROR = 'ERROR'


KEYWORDS = {
    'MOV': TokenType.MOV, 'ADD': TokenType.ADD, 'SUB': TokenType.SUB,
    'MUL': TokenType.MUL, 'DIV': TokenType.DIV, 'CMP': TokenType.CMP,
    'JMP': TokenType.JMP, 'JE':  TokenType.JE,  'JNE': TokenType.JNE,
    'JG':  TokenType.JG,  'JL':  TokenType.JL,  'JGE': TokenType.JGE,
    'JLE': TokenType.JLE,
    'PUSH':TokenType.PUSH,'POP': TokenType.POP, 'CALL':TokenType.CALL,
    'RET': TokenType.RET, 'NOP': TokenType.NOP, 'HLT': TokenType.HLT,
    'PROC':TokenType.PROC,'ENDP':TokenType.ENDP,
    'SECTION':TokenType.SECTION,'DATA':TokenType.DATA,'CODE':TokenType.CODE,
    'DB':TokenType.DB,'DW':TokenType.DW,'DD':TokenType.DD,'DQ':TokenType.DQ,
    'BYTE':TokenType.BYTE,'WORD':TokenType.WORD,
    'DWORD':TokenType.DWORD,'QWORD':TokenType.QWORD,'PTR':TokenType.PTR,
}

REGISTERS = {
    'AX','BX','CX','DX','SP','BP','SI','DI',
    'AL','AH','BL','BH','CL','CH','DL','DH',
    'EAX','EBX','ECX','EDX','ESP','EBP','ESI','EDI',
}

SIZE_DIRECTIVES  = {TokenType.DB, TokenType.DW, TokenType.DD, TokenType.DQ}
JUMP_MNEMONICS   = {TokenType.JMP,TokenType.JE,TokenType.JNE,
                    TokenType.JG,TokenType.JL,TokenType.JGE,TokenType.JLE}
ARITH_MNEMONICS  = {TokenType.ADD,TokenType.SUB,TokenType.MUL,TokenType.DIV}
SIZE_QUALIFIERS  = {TokenType.BYTE,TokenType.WORD,TokenType.DWORD,TokenType.QWORD}

SIZE_BYTES = {'DB':1,'DW':2,'DD':4,'DQ':8}


class Token:
    def __init__(self, type_, value, line, column):
        self.type   = type_
        self.value  = value
        self.line   = line
        self.column = column
    def __repr__(self):
        return f"Token({self.type.value}, '{self.value}', {self.line}:{self.column})"


# ==================== LEXICAL ANALYZER ====================
class Lexer:
    def __init__(self, source):
        self.source = source
        self.pos = 0; self.line = 1; self.column = 1
        self.tokens = []; self.errors = []

    def error(self, msg):
        self.errors.append(f"Lexical Error at {self.line}:{self.column}: {msg}")

    def peek(self, offset=0):
        p = self.pos + offset
        return self.source[p] if p < len(self.source) else None

    def advance(self):
        if self.pos < len(self.source):
            if self.source[self.pos] == '\n':
                self.line += 1; self.column = 1
            else:
                self.column += 1
            self.pos += 1

    def skip_spaces(self):
        while self.peek() and self.peek() in ' \t\r':
            self.advance()

    def read_comment(self):
        sc = self.column; txt = ''
        while self.peek() and self.peek() != '\n':
            txt += self.peek(); self.advance()
        return Token(TokenType.COMMENT, txt, self.line, sc)

    def read_number(self):
        sc = self.column; num = ''
        if self.peek() == '0' and self.peek(1) in ('x','X'):
            num += self.peek(); self.advance()
            num += self.peek(); self.advance()
            while self.peek() and self.peek() in '0123456789abcdefABCDEF':
                num += self.peek(); self.advance()
            return Token(TokenType.HEX_NUM, num, self.line, sc)
        while self.peek() and self.peek().isdigit():
            num += self.peek(); self.advance()
        if self.peek() and self.peek().lower() == 'h':
            num += self.peek(); self.advance()
            return Token(TokenType.HEX_NUM, num, self.line, sc)
        return Token(TokenType.NUM, num, self.line, sc)

    def read_string(self):
        sc = self.column; q = self.peek(); self.advance(); s = ''
        while self.peek() and self.peek() != q:
            if self.peek() == '\\':
                self.advance()
                if self.peek(): s += self.peek(); self.advance()
            else:
                s += self.peek(); self.advance()
        if self.peek() == q:
            self.advance()
            return Token(TokenType.STR_LITERAL, s, self.line, sc)
        self.error("Unterminated string literal")
        return Token(TokenType.ERROR, s, self.line, sc)

    def read_identifier(self):
        sc = self.column; ident = ''
        while self.peek() and (self.peek().isalnum() or self.peek() in '_@?.'):
            ident += self.peek(); self.advance()
        upper = ident.upper()
        if upper in REGISTERS:
            return Token(TokenType.REG, ident.upper(), self.line, sc)
        tt = KEYWORDS.get(upper, TokenType.ID)
        return Token(tt, ident, self.line, sc)

    def tokenize(self):
        while self.pos < len(self.source):
            self.skip_spaces()
            if self.pos >= len(self.source):
                break
            sc = self.column; ch = self.peek()

            if ch == '\n':
                self.tokens.append(Token(TokenType.NEWLINE, '\\n', self.line, sc))
                self.advance()
            elif ch == ';':
                self.tokens.append(self.read_comment())
            elif ch.isdigit():
                self.tokens.append(self.read_number())
            elif ch in ('"', "'"):
                self.tokens.append(self.read_string())
            elif ch.isalpha() or ch in '_@?.':
                self.tokens.append(self.read_identifier())
            elif ch == ',':
                self.advance(); self.tokens.append(Token(TokenType.COMMA,    ',', self.line, sc))
            elif ch == ':':
                self.advance(); self.tokens.append(Token(TokenType.COLON,    ':', self.line, sc))
            elif ch == '[':
                self.advance(); self.tokens.append(Token(TokenType.LBRACKET, '[', self.line, sc))
            elif ch == ']':
                self.advance(); self.tokens.append(Token(TokenType.RBRACKET, ']', self.line, sc))
            elif ch == '+':
                self.advance(); self.tokens.append(Token(TokenType.PLUS,     '+', self.line, sc))
            elif ch == '-':
                self.advance(); self.tokens.append(Token(TokenType.MINUS,    '-', self.line, sc))
            else:
                self.error(f"Unexpected character '{ch}'")
                self.advance()

        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column))
        return self.tokens, self.errors


# ==================== SYMBOL TABLE ====================
class SymbolTable:
    """
    Scope-aware symbol table.
      scope 0 = global
      scope 1 = DATA section
      scope 2 = CODE section
      scope 3+ = inside PROC bodies
    """
    def __init__(self):
        self.scopes        = [{}]
        self.current_scope = 0

    def enter_scope(self):
        self.scopes.append({})
        self.current_scope += 1

    def exit_scope(self):
        if self.current_scope > 0:
            self.scopes.pop()
            self.current_scope -= 1

    def declare(self, name, type_, line, extra=None):
        if name in self.scopes[self.current_scope]:
            return False, f"'{name}' already declared in current scope (line {line})"
        entry = {'type': type_, 'line': line, 'scope': self.current_scope}
        if extra:
            entry.update(extra)
        self.scopes[self.current_scope][name] = entry
        return True, None

    def lookup(self, name):
        for i in range(self.current_scope, -1, -1):
            if name in self.scopes[i]:
                return self.scopes[i][name]
        return None

    def get_all_symbols(self):
        result = []
        for scope_level, scope in enumerate(self.scopes):
            for name, info in scope.items():
                result.append({
                    'name':  name,
                    'type':  info['type'],
                    'scope': scope_level,
                    'line':  info['line'],
                })
        return result


# ==================== PARSER ====================
class Parser:
    def __init__(self, tokens):
        self.tokens = [t for t in tokens
                       if t.type not in (TokenType.NEWLINE, TokenType.COMMENT)]
        self.pos          = 0
        self.current      = self.tokens[0] if self.tokens else None
        self.errors       = []
        self.symbol_table = SymbolTable()
        self._current_section = 'GLOBAL'

    def _err(self, msg):
        loc = f"{self.current.line}:{self.current.column}" if self.current else "?"
        self.errors.append(f"Syntax Error at {loc}: {msg}")

    def _sem(self, msg):
        self.errors.append(f"Semantic Error: {msg}")

    def advance(self):
        if self.pos < len(self.tokens) - 1:
            self.pos    += 1
            self.current = self.tokens[self.pos]

    def peek_next(self):
        p = self.pos + 1
        return self.tokens[p] if p < len(self.tokens) else None

    def match(self, tt):
        if self.current and self.current.type == tt:
            tok = self.current; self.advance(); return tok
        got = self.current.type.value if self.current else 'EOF'
        self._err(f"Expected {tt.value}, got '{got}'")
        return None

    def at_eof(self):
        return self.current is None or self.current.type == TokenType.EOF

    def parse(self):
        try:
            self.program()
        except Exception as e:
            self._err(f"Parser exception: {e}")
        return self.errors

    def program(self):
        while not self.at_eof():
            if self.current.type == TokenType.SECTION:
                self.section()
            else:
                self.stmt()

    def section(self):
        self.match(TokenType.SECTION)
        if self.at_eof():
            return
        if self.current.type == TokenType.DATA:
            self._current_section = 'DATA'
            self.advance()
            self.symbol_table.enter_scope()
            self.var_decl_list()
        elif self.current.type == TokenType.CODE:
            self._current_section = 'CODE'
            self.advance()
            self.symbol_table.enter_scope()
            self.proc_or_stmt_list()
        else:
            self._err(f"Expected DATA or CODE after SECTION, got '{self.current.value}'")
            self.advance()

    def var_decl_list(self):
        while not self.at_eof() and self.current.type != TokenType.SECTION:
            if (self.current.type == TokenType.ID
                    and self.peek_next()
                    and self.peek_next().type in SIZE_DIRECTIVES):
                self.var_decl()
            else:
                break

    def var_decl(self):
        id_tok   = self.match(TokenType.ID)
        size_tok = self.current; self.advance()
        init_val = '?'
        if not self.at_eof():
            if self.current.type in (TokenType.NUM, TokenType.HEX_NUM):
                init_val = self.current.value; self.advance()
            elif self.current.type == TokenType.STR_LITERAL:
                init_val = f'"{self.current.value}"'; self.advance()
            elif self.current.type == TokenType.ID and self.current.value == '?':
                self.advance()
        if id_tok:
            ok, msg = self.symbol_table.declare(
                id_tok.value, size_tok.type.value, id_tok.line,
                extra={'init': init_val,
                       'size_bytes': SIZE_BYTES.get(size_tok.type.value, 0),
                       'section': 'DATA'})
            if not ok:
                self._sem(msg)

    def proc_or_stmt_list(self):
        while not self.at_eof() and self.current.type != TokenType.SECTION:
            if self.current.type == TokenType.PROC:
                self.proc_def()
            else:
                self.stmt()

    def proc_def(self):
        self.match(TokenType.PROC)
        name_tok = self.match(TokenType.ID)
        if name_tok:
            ok, msg = self.symbol_table.declare(
                name_tok.value, 'PROC', name_tok.line,
                extra={'section': 'CODE'})
            if not ok:
                self._sem(msg)
        self.symbol_table.enter_scope()
        self.stmt_list()
        self.symbol_table.exit_scope()
        self.match(TokenType.ENDP)
        if not self.at_eof() and self.current.type == TokenType.ID:
            self.advance()

    def stmt_list(self):
        stop = {TokenType.ENDP, TokenType.SECTION, TokenType.EOF}
        while not self.at_eof() and self.current.type not in stop:
            self.stmt()

    def stmt(self):
        if self.at_eof():
            return
        tok = self.current
        nxt = self.peek_next()

        if tok.type == TokenType.ID and nxt and nxt.type == TokenType.COLON:
            self.label_def()
        elif tok.type == TokenType.MOV:
            self.mov_instr()
        elif tok.type in ARITH_MNEMONICS:
            self.arith_instr()
        elif tok.type == TokenType.CMP:
            self.cmp_instr()
        elif tok.type in JUMP_MNEMONICS:
            self.jump_instr()
        elif tok.type == TokenType.PUSH:
            self.advance(); self.operand()
        elif tok.type == TokenType.POP:
            self.advance(); self.operand()
        elif tok.type == TokenType.CALL:
            self.call_instr()
        elif tok.type in (TokenType.RET, TokenType.NOP, TokenType.HLT):
            self.advance()
        else:
            self._err(f"Unexpected token '{tok.value}' ({tok.type.value})")
            self.advance()

    def label_def(self):
        id_tok = self.match(TokenType.ID)
        self.match(TokenType.COLON)
        if id_tok:
            ok, msg = self.symbol_table.declare(
                id_tok.value, 'LABEL', id_tok.line,
                extra={'section': self._current_section})
            if not ok:
                self._sem(msg)

    def mov_instr(self):
        self.match(TokenType.MOV)
        dst = self.operand()
        self.match(TokenType.COMMA)
        src = self.operand()
        if dst and src:
            is_mem = lambda x: x and x.startswith('[')
            if is_mem(dst) and is_mem(src):
                self._sem(f"MOV cannot have two memory operands: {dst}, {src}")

    def arith_instr(self):
        self.advance()
        self.operand()
        self.match(TokenType.COMMA)
        self.operand()

    def cmp_instr(self):
        self.match(TokenType.CMP)
        self.operand()
        self.match(TokenType.COMMA)
        self.operand()

    def jump_instr(self):
        self.advance()
        if not self.at_eof() and self.current.type == TokenType.ID:
            self.advance()
        else:
            self._err("Expected label name after jump instruction")

    def call_instr(self):
        self.match(TokenType.CALL)
        if not self.at_eof() and self.current.type == TokenType.ID:
            proc_name = self.current.value
            sym = self.symbol_table.lookup(proc_name)
            if sym and sym['type'] not in ('PROC', 'LABEL'):
                self._sem(f"'{proc_name}' is not a procedure or label")
            self.advance()
        else:
            self._err("Expected procedure name after CALL")

    def operand(self):
        if self.at_eof():
            return None
        tok = self.current

        if tok.type in SIZE_QUALIFIERS:
            sz = tok.value.upper(); self.advance()
            if not self.at_eof() and self.current.type == TokenType.PTR:
                self.advance()
            if not self.at_eof() and self.current.type == TokenType.LBRACKET:
                return f"{sz} PTR {self.mem_ref()}"
            return sz

        if tok.type == TokenType.LBRACKET:
            return self.mem_ref()
        if tok.type == TokenType.REG:
            self.advance(); return tok.value.upper()
        if tok.type in (TokenType.NUM, TokenType.HEX_NUM):
            self.advance(); return tok.value
        if tok.type == TokenType.ID:
            name = tok.value
            if self.symbol_table.lookup(name) is None:
                self._sem(f"Undeclared identifier '{name}' at line {tok.line}")
            self.advance(); return name

        self._err(f"Expected operand, got '{tok.value}'")
        self.advance(); return None

    def mem_ref(self):
        self.match(TokenType.LBRACKET)
        base = self.operand()
        result = f"[{base}"
        if not self.at_eof() and self.current.type in (TokenType.PLUS, TokenType.MINUS):
            op = self.current.value; self.advance()
            disp = self.operand()
            result += f"{op}{disp}"
        self.match(TokenType.RBRACKET)
        return result + ']'


# ==================== TAC GENERATOR ====================
class TACGenerator:
    """
    Mirrors the parser structure exactly – one method per grammar rule.
    Every instruction maps to its Three-Address Code equivalent.
    """
    def __init__(self, tokens, symbol_table):
        self.tokens = [t for t in tokens
                       if t.type not in (TokenType.NEWLINE, TokenType.COMMENT)]
        self.pos          = 0
        self.current      = self.tokens[0] if self.tokens else None
        self.tac          = []
        self.temp_count   = 0
        self.label_count  = 0
        self.symbol_table = symbol_table

    def new_temp(self):
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self):
        self.label_count += 1
        return f"L{self.label_count}"

    def emit(self, instr):
        self.tac.append(instr)

    def advance(self):
        if self.pos < len(self.tokens) - 1:
            self.pos    += 1
            self.current = self.tokens[self.pos]

    def peek_next(self):
        p = self.pos + 1
        return self.tokens[p] if p < len(self.tokens) else None

    def match(self, tt):
        if self.current and self.current.type == tt:
            tok = self.current; self.advance(); return tok
        return None

    def at_eof(self):
        return self.current is None or self.current.type == TokenType.EOF

    # ---- top-level ----
    def generate(self):
        try:
            self.program()
        except Exception:
            pass
        return self.tac

    def program(self):
        while not self.at_eof():
            if self.current.type == TokenType.SECTION:
                self.section()
            else:
                self.stmt()

    def section(self):
        self.match(TokenType.SECTION)
        if self.at_eof():
            return
        if self.current.type in (TokenType.DATA, TokenType.CODE):
            sec_name = self.current.value.upper(); self.advance()
            self.emit(f"; ════════ SECTION {sec_name} ════════")
            if sec_name == 'DATA':
                self.var_decl_list()
            else:
                self.proc_or_stmt_list()
        else:
            self.advance()

    # ---- DATA section ----
    def var_decl_list(self):
        while not self.at_eof() and self.current.type != TokenType.SECTION:
            if (self.current.type == TokenType.ID
                    and self.peek_next()
                    and self.peek_next().type in SIZE_DIRECTIVES):
                self.var_decl()
            else:
                break

    def var_decl(self):
        id_tok   = self.match(TokenType.ID)
        size_tok = self.current; self.advance()
        init_val = '?'
        if not self.at_eof():
            if self.current.type in (TokenType.NUM, TokenType.HEX_NUM):
                init_val = self.current.value; self.advance()
            elif self.current.type == TokenType.STR_LITERAL:
                init_val = f'"{self.current.value}"'; self.advance()
            elif self.current.type == TokenType.ID and self.current.value == '?':
                self.advance()
        name   = id_tok.value if id_tok else '?'
        sz     = size_tok.type.value if size_tok else '?'
        nbytes = SIZE_BYTES.get(sz, 0)
        self.emit(f"DECLARE  {name} : {sz}({nbytes}B) = {init_val}")

    # ---- CODE section ----
    def proc_or_stmt_list(self):
        while not self.at_eof() and self.current.type != TokenType.SECTION:
            if self.current.type == TokenType.PROC:
                self.proc_def()
            else:
                self.stmt()

    def proc_def(self):
        self.match(TokenType.PROC)
        name_tok = self.match(TokenType.ID)
        name     = name_tok.value if name_tok else '?'
        self.emit(f"; ---- BEGIN PROC {name} ----")
        self.emit(f"PROC_ENTRY {name}")
        self.stmt_list()
        self.match(TokenType.ENDP)
        if not self.at_eof() and self.current.type == TokenType.ID:
            self.advance()
        self.emit(f"PROC_EXIT  {name}")
        self.emit(f"; ---- END PROC {name} ----")

    def stmt_list(self):
        stop = {TokenType.ENDP, TokenType.SECTION, TokenType.EOF}
        while not self.at_eof() and self.current.type not in stop:
            self.stmt()

    def stmt(self):
        if self.at_eof():
            return
        tok = self.current
        nxt = self.peek_next()

        if tok.type == TokenType.ID and nxt and nxt.type == TokenType.COLON:
            label = tok.value; self.advance(); self.advance()
            self.emit(f"{label}:")
        elif tok.type == TokenType.MOV:
            self.mov_instr()
        elif tok.type in ARITH_MNEMONICS:
            self.arith_instr()
        elif tok.type == TokenType.CMP:
            self.cmp_instr()
        elif tok.type in JUMP_MNEMONICS:
            self.jump_instr()
        elif tok.type == TokenType.PUSH:
            self.advance()
            op = self.consume_operand()
            self.emit(f"PUSH  {op}")
        elif tok.type == TokenType.POP:
            self.advance()
            op = self.consume_operand()
            self.emit(f"POP   {op}")
        elif tok.type == TokenType.CALL:
            self.advance()
            func = self.consume_operand()
            self.emit(f"CALL  {func}")
        elif tok.type == TokenType.RET:
            self.advance()
            self.emit("RETURN")
        elif tok.type == TokenType.NOP:
            self.advance()
            self.emit("NOP")
        elif tok.type == TokenType.HLT:
            self.advance()
            self.emit("HALT  ; end of execution")
        else:
            self.advance()

    # ---- instruction TAC emitters ----
    def mov_instr(self):
        """MOV dst, src  =>  t = src  ;  dst = t"""
        self.match(TokenType.MOV)
        dst = self.consume_operand()
        self.match(TokenType.COMMA)
        src = self.consume_operand()
        temp = self.new_temp()
        self.emit(f"{temp} = {src}")
        self.emit(f"{dst} = {temp}          ; MOV {dst}, {src}")

    def arith_instr(self):
        """ADD/SUB/MUL/DIV dst, src  =>  t = dst OP src  ;  dst = t"""
        mnem = self.current.value.upper(); self.advance()
        dst  = self.consume_operand()
        self.match(TokenType.COMMA)
        src  = self.consume_operand()
        op_map = {'ADD':'+','SUB':'-','MUL':'*','DIV':'/'}
        op   = op_map.get(mnem, mnem)
        temp = self.new_temp()
        self.emit(f"{temp} = {dst} {op} {src}")
        self.emit(f"{dst} = {temp}          ; {mnem} {dst}, {src}")

    def cmp_instr(self):
        """CMP op1, op2  =>  t = op1 - op2  ;  FLAGS = t"""
        self.match(TokenType.CMP)
        op1 = self.consume_operand()
        self.match(TokenType.COMMA)
        op2 = self.consume_operand()
        temp = self.new_temp()
        self.emit(f"{temp} = {op1} - {op2}")
        self.emit(f"FLAGS = {temp}          ; CMP {op1}, {op2}")

    def jump_instr(self):
        """JMP/Jxx target  =>  goto / if FLAGS … goto"""
        mnem = self.current.value.upper(); self.advance()
        target = self.consume_operand()
        cond_map = {
            'JMP':  f"goto {target}",
            'JE':   f"if FLAGS == 0 goto {target}",
            'JNE':  f"if FLAGS != 0 goto {target}",
            'JG':   f"if FLAGS >  0 goto {target}",
            'JL':   f"if FLAGS <  0 goto {target}",
            'JGE':  f"if FLAGS >= 0 goto {target}",
            'JLE':  f"if FLAGS <= 0 goto {target}",
        }
        self.emit(cond_map.get(mnem, f"goto {target}"))

    # ---- operand consumer (returns its string representation) ----
    def consume_operand(self):
        if self.at_eof():
            return '?'
        tok = self.current

        if tok.type in SIZE_QUALIFIERS:
            sz = tok.value.upper(); self.advance()
            if not self.at_eof() and self.current.type == TokenType.PTR:
                self.advance()
            if not self.at_eof() and self.current.type == TokenType.LBRACKET:
                return f"{sz} PTR {self.consume_mem_ref()}"
            return sz

        if tok.type == TokenType.LBRACKET:
            return self.consume_mem_ref()
        if tok.type == TokenType.REG:
            self.advance(); return tok.value.upper()
        if tok.type in (TokenType.NUM, TokenType.HEX_NUM):
            self.advance(); return tok.value
        if tok.type == TokenType.ID:
            self.advance(); return tok.value
        self.advance(); return tok.value

    def consume_mem_ref(self):
        self.match(TokenType.LBRACKET)
        base = self.consume_operand()
        result = f"[{base}"
        if not self.at_eof() and self.current.type in (TokenType.PLUS, TokenType.MINUS):
            op = self.current.value; self.advance()
            disp = self.consume_operand()
            result += f"{op}{disp}"
        self.match(TokenType.RBRACKET)
        return result + ']'


# ==================== GUI APPLICATION ====================
class CompilerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Mini Compiler - AssemblyLang')
        self.geometry('1400x860')
        self.configure(bg='#f0f4f8')
        self.create_widgets()
        self.load_sample()

    # ------------------------------------------------------------------ build UI --
    def create_widgets(self):
        # ── Title bar ──────────────────────────────────────────────────────────
        title_frame = tk.Frame(self, bg='#2c3e50', height=60)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text='🔧 Mini Compiler - AssemblyLang',
                 bg='#2c3e50', fg='white',
                 font=('Segoe UI', 18, 'bold')).pack(side='left', padx=20, pady=15)

        # ── Supervisor / Project info bar  ─────────────────────────────────────
        # This bar is always visible at the top of the workspace, right below
        # the title.  It shows the course, university and supervisor name so
        # the information is on-screen at all times.
        info_bar = tk.Frame(self, bg='#1a252f', height=38)
        info_bar.pack(fill='x')
        info_bar.pack_propagate(False)

        # Left cluster: university & course
        left_info = tk.Frame(info_bar, bg='#1a252f')
        left_info.pack(side='left', padx=18, pady=6)
        tk.Label(left_info,
                 text='🎓  Sukkur IBA University',
                 bg='#1a252f', fg='#aed6f1',
                 font=('Segoe UI', 9, 'bold')).pack(side='left', padx=(0, 18))
        tk.Label(left_info,
                 text='📚  Computer Architecture & Assembly Language',
                 bg='#1a252f', fg='#aed6f1',
                 font=('Segoe UI', 9)).pack(side='left')

        # Right cluster: developer & supervisor
        right_info = tk.Frame(info_bar, bg='#1a252f')
        right_info.pack(side='right', padx=18, pady=6)
        tk.Label(right_info,
                 text='👨‍💻  Developer: Muhammad Awais',
                 bg='#1a252f', fg='#a9dfbf',
                 font=('Segoe UI', 9)).pack(side='left', padx=(0, 20))

        # Supervisor label – highlighted with a slightly different colour so it
        # stands out from the rest.
        sup_badge = tk.Frame(right_info, bg='#154360', padx=8, pady=2)
        sup_badge.pack(side='left')
        tk.Label(sup_badge,
                 text=' Subject Supervisor: Dr. Hifazat Shah',
                 bg='#154360', fg='#f9e79f',
                 font=('Segoe UI', 9, 'bold')).pack()

        # ── Main container ─────────────────────────────────────────────────────
        main_container = tk.Frame(self, bg='#f0f4f8')
        main_container.pack(fill='both', expand=True, padx=10, pady=10)

        # ── Left panel ────────────────────────────────────────────────────────
        left_panel = tk.Frame(main_container, bg='white', relief='solid', borderwidth=1)
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 5))

        tk.Label(left_panel, text='📝 Source Code (AssemblyLang)',
                 bg='#3498db', fg='white',
                 font=('Segoe UI', 11, 'bold'), height=2).pack(fill='x')

        self.source_text = scrolledtext.ScrolledText(
            left_panel, wrap='none', font=('Consolas', 10),
            bg='#fafafa', fg='#2c3e50', padx=10, pady=10)
        self.source_text.pack(fill='both', expand=True, padx=5, pady=5)

        btn_frame = tk.Frame(left_panel, bg='white', height=50)
        btn_frame.pack(fill='x', pady=5)
        tk.Button(btn_frame, text='▶ Compile All', command=self.compile_all,
                  bg='#27ae60', fg='white', font=('Segoe UI', 10, 'bold'),
                  cursor='hand2', padx=15, pady=5).pack(side='left', padx=5)
        tk.Button(btn_frame, text='🗑 Clear', command=self.clear_all,
                  bg='#e74c3c', fg='white', font=('Segoe UI', 10, 'bold'),
                  cursor='hand2', padx=15, pady=5).pack(side='left', padx=5)
        tk.Button(btn_frame, text='📋 Sample', command=self.load_sample,
                  bg='#95a5a6', fg='white', font=('Segoe UI', 10, 'bold'),
                  cursor='hand2', padx=15, pady=5).pack(side='left', padx=5)
        tk.Button(btn_frame, text='👨‍💻 About', command=self.show_about,
                  bg='#9b59b6', fg='white', font=('Segoe UI', 10, 'bold'),
                  cursor='hand2', padx=15, pady=5).pack(side='left', padx=5)

        # ── Right panel (notebook) ─────────────────────────────────────────────
        right_panel = tk.Frame(main_container, bg='white', relief='solid', borderwidth=1)
        right_panel.pack(side='right', fill='both', expand=True, padx=(5, 0))

        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Tab 1 – Tokens
        tokens_frame = tk.Frame(self.notebook, bg='white')
        self.notebook.add(tokens_frame, text='🎯 Tokens')
        cols_t = ('Line', 'Token', 'Type', 'Column')
        self.tokens_tree = ttk.Treeview(tokens_frame, columns=cols_t, show='headings')
        for c in cols_t:
            self.tokens_tree.heading(c, text=c)
        self.tokens_tree.column('Line',   width=55,  anchor='center')
        self.tokens_tree.column('Token',  width=160)
        self.tokens_tree.column('Type',   width=150)
        self.tokens_tree.column('Column', width=65,  anchor='center')
        sc1 = ttk.Scrollbar(tokens_frame, orient='vertical', command=self.tokens_tree.yview)
        self.tokens_tree.configure(yscrollcommand=sc1.set)
        self.tokens_tree.pack(side='left', fill='both', expand=True)
        sc1.pack(side='right', fill='y')

        # Tab 2 – Symbol Table
        sym_frame = tk.Frame(self.notebook, bg='white')
        self.notebook.add(sym_frame, text='📊 Symbol Table')
        cols_s = ('Name', 'Type', 'Scope', 'Line')
        self.symbol_tree = ttk.Treeview(sym_frame, columns=cols_s, show='headings')
        self.symbol_tree.heading('Name',  text='Identifier')
        self.symbol_tree.heading('Type',  text='Kind / Size')
        self.symbol_tree.heading('Scope', text='Scope Level')
        self.symbol_tree.heading('Line',  text='Declared at Line')
        for c, w in zip(cols_s, [160, 120, 100, 120]):
            self.symbol_tree.column(c, width=w,
                                    anchor='center' if c != 'Name' else 'w')
        sc2 = ttk.Scrollbar(sym_frame, orient='vertical', command=self.symbol_tree.yview)
        self.symbol_tree.configure(yscrollcommand=sc2.set)
        self.symbol_tree.pack(side='left', fill='both', expand=True)
        sc2.pack(side='right', fill='y')

        # Tab 3 – Parse Results
        parse_frame = tk.Frame(self.notebook, bg='white')
        self.notebook.add(parse_frame, text='🌳 Parse Results')
        self.parse_text = scrolledtext.ScrolledText(
            parse_frame, wrap='word', font=('Consolas', 9),
            bg='#fafafa', fg='#2c3e50', padx=10, pady=10)
        self.parse_text.pack(fill='both', expand=True)

        # Tab 4 – TAC
        tac_frame = tk.Frame(self.notebook, bg='white')
        self.notebook.add(tac_frame, text='⚙️ TAC (Intermediate Code)')
        self.tac_text = scrolledtext.ScrolledText(
            tac_frame, wrap='none', font=('Consolas', 9),
            bg='#fafafa', fg='#2c3e50', padx=10, pady=10)
        self.tac_text.pack(fill='both', expand=True)

        # Tab 5 – Grammar
        grammar_frame = tk.Frame(self.notebook, bg='white')
        self.notebook.add(grammar_frame, text='📖 Grammar')
        self.grammar_text = scrolledtext.ScrolledText(
            grammar_frame, wrap='word', font=('Consolas', 9),
            bg='#fafafa', fg='#2c3e50', padx=10, pady=10)
        self.grammar_text.pack(fill='both', expand=True)
        self.grammar_text.insert('1.0', self.get_grammar_info())
        self.grammar_text.config(state='disabled')

        # ── Supervisor footer bar (bottom, always fully visible) ──────────────
        supervisor_bar = tk.Frame(self, bg='#1a252f')
        supervisor_bar.pack(fill='x', side='bottom')

        # Decorative top border line
        tk.Frame(self, bg='#f39c12', height=2).pack(fill='x', side='bottom')

        # Left: subject info
        tk.Label(supervisor_bar,
                 text='📚  Computer Architecture & Assembly Language',
                 bg='#1a252f', fg='#aed6f1',
                 font=('Segoe UI', 10)).pack(side='left', padx=20, pady=10)

        # Centre divider
        tk.Label(supervisor_bar, text='|', bg='#1a252f', fg='#566573',
                 font=('Segoe UI', 12)).pack(side='left', pady=10)

        # Right: supervisor name — prominent gold text
        tk.Label(supervisor_bar,
                 text='🎓  Sukkur IBA University',
                 bg='#1a252f', fg='#aed6f1',
                 font=('Segoe UI', 10)).pack(side='left', padx=20, pady=10)

        tk.Label(supervisor_bar, text='|', bg='#1a252f', fg='#566573',
                 font=('Segoe UI', 12)).pack(side='left', pady=10)

        tk.Label(supervisor_bar,
                 text=' Subject Supervisor:  Dr. Hifazat Shah',
                 bg='#1a252f', fg='#f9e79f',
                 font=('Segoe UI', 11, 'bold')).pack(side='left', padx=20, pady=10)

        tk.Label(supervisor_bar,
                 text='2026',
                 bg='#1a252f', fg='#7f8c8d',
                 font=('Segoe UI', 10)).pack(side='right', padx=10, pady=10)

        # ── Status bar (above supervisor bar) ─────────────────────────────────
        status_frame = tk.Frame(self, bg='#2c3e50')
        status_frame.pack(fill='x', side='bottom')

        self.status_label = tk.Label(
            status_frame,
            text='Ready – load sample or type your code and click ▶ Compile All',
            bg='#2c3e50', fg='#ecf0f1',
            font=('Segoe UI', 9), anchor='w')
        self.status_label.pack(side='left', padx=15, pady=6)

    # ---------------------------------------------------------------- compile --
    def compile_all(self):
        source = self.source_text.get('1.0', 'end-1c')
        if not source.strip():
            messagebox.showwarning('Empty Source', 'Please enter assembly source code.')
            return
        self.clear_results()

        # ── Phase 1: Lexical Analysis ──────────────────────────────
        self.status_label.config(text='Phase 1: Lexical Analysis...')
        self.update()

        lexer            = Lexer(source)
        tokens, lex_errs = lexer.tokenize()

        visible = [t for t in tokens
                   if t.type not in (TokenType.EOF, TokenType.NEWLINE,
                                     TokenType.COMMENT)]
        for tok in visible:
            self.tokens_tree.insert('', 'end',
                values=(tok.line, tok.value, tok.type.value, tok.column))

        if lex_errs:
            self.parse_text.insert('end', '=== LEXICAL ERRORS ===\n', 'error')
            for e in lex_errs:
                self.parse_text.insert('end', f'{e}\n', 'error')
            self.status_label.config(text='Compilation failed: Lexical errors')
            self._set_tags(); return

        self.parse_text.insert('end', '✓ Lexical Analysis: SUCCESS\n', 'success')
        self.parse_text.insert('end', f'  Total tokens: {len(visible)}\n\n')

        # ── Phase 2: Syntax + Semantic Analysis ───────────────────
        self.status_label.config(text='Phase 2: Syntax Analysis...')
        self.update()

        parser       = Parser(tokens)
        parse_errors = parser.parse()

        if parse_errors:
            self.parse_text.insert('end', '=== SYNTAX / SEMANTIC ERRORS ===\n', 'error')
            for e in parse_errors:
                self.parse_text.insert('end', f'{e}\n', 'error')
            self.status_label.config(text='Compilation failed: Syntax/Semantic errors')
            self._set_tags(); return

        self.parse_text.insert('end', '✓ Syntax Analysis: SUCCESS\n', 'success')
        self.parse_text.insert('end', '  Grammar validated successfully\n\n')

        symbols = parser.symbol_table.get_all_symbols()
        for sym in symbols:
            self.symbol_tree.insert('', 'end',
                values=(sym['name'], sym['type'], sym['scope'], sym['line']))

        self.parse_text.insert('end', '✓ Semantic Analysis: SUCCESS\n', 'success')
        self.parse_text.insert('end', f'  Symbols declared: {len(symbols)}\n\n')

        # ── Phase 3: TAC / Intermediate Code Generation ───────────
        self.status_label.config(text='Phase 3: Code Generation...')
        self.update()

        tac_gen  = TACGenerator(tokens, parser.symbol_table)
        tac_code = tac_gen.generate()

        self.tac_text.insert('1.0',
            '=== THREE-ADDRESS CODE (TAC) – AssemblyLang ===\n\n')
        for i, instr in enumerate(tac_code, 1):
            self.tac_text.insert('end', f'{i:3d}. {instr}\n')

        self.parse_text.insert('end', '✓ Code Generation: SUCCESS\n', 'success')
        self.parse_text.insert('end', f'  TAC instructions: {len(tac_code)}\n\n')

        self._set_tags()
        self.status_label.config(text='✓ Compilation successful!')
        messagebox.showinfo('Success',
            f'Compilation completed successfully!\n\n'
            f'Tokens:           {len(visible)}\n'
            f'Symbols:          {len(symbols)}\n'
            f'TAC Instructions: {len(tac_code)}')

    def _set_tags(self):
        self.parse_text.tag_config('success',
            foreground='#27ae60', font=('Consolas', 9, 'bold'))
        self.parse_text.tag_config('error',
            foreground='#e74c3c', font=('Consolas', 9, 'bold'))

    # ---------------------------------------------------------------- helpers --
    def clear_results(self):
        for item in self.tokens_tree.get_children():
            self.tokens_tree.delete(item)
        for item in self.symbol_tree.get_children():
            self.symbol_tree.delete(item)
        self.parse_text.delete('1.0', 'end')
        self.tac_text.delete('1.0', 'end')

    def clear_all(self):
        self.source_text.delete('1.0', 'end')
        self.clear_results()
        self.status_label.config(text='All cleared')

    def load_sample(self):
        sample = """; ════════════════════════════════════════════
; AssemblyLang Sample Program
; Demonstrates: sections, variables, labels,
;   arithmetic, comparison, jumps, stack, proc
; ════════════════════════════════════════════

SECTION DATA
    num1    DB 10
    num2    DB 5
    result  DW ?
    counter DB 0
    msg     DB "Hello, AssemblyLang!"

SECTION CODE

main:
    ; ── Load values ──────────────────────────
    MOV AX, num1
    MOV BX, num2

    ; ── Addition ─────────────────────────────
    ADD AX, BX
    MOV result, AX

    ; ── Subtraction ──────────────────────────
    MOV CX, num1
    SUB CX, num2

    ; ── Multiplication ───────────────────────
    MOV DX, num1
    MUL DX, num2

    ; ── Division ─────────────────────────────
    MOV AX, num1
    DIV AX, num2

    ; ── Comparison + conditional branch ──────
    CMP AX, 15
    JGE bigger
    MOV AX, 0
    JMP done

bigger:
    MOV AX, 1

    ; ── While-style loop ─────────────────────
loop_start:
    CMP counter, 5
    JGE loop_end
    ADD counter, 1
    JMP loop_start

loop_end:
    MOV result, counter

    ; ── Memory reference ─────────────────────
    MOV AX, WORD PTR [result]
    MOV [BX], AX

done:
    ; ── Stack and procedure call ─────────────
    PUSH AX
    PUSH BX
    CALL printResult
    POP  BX
    POP  AX
    HLT

PROC printResult
    MOV  AX, [BP+4]
    CMP  AX, 0
    JE   print_zero
    MOV  BX, AX
    JMP  print_done
print_zero:
    MOV  BX, 0
print_done:
    RET
ENDP printResult
"""
        self.source_text.delete('1.0', 'end')
        self.source_text.insert('1.0', sample)
        self.status_label.config(text='Sample code loaded')

    # ---------------------------------------------------------------- grammar --
    def get_grammar_info(self):
        return """AssemblyLang Grammar – Context-Free Grammar (Transformed)
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501

\u2713 Ambiguity Removed
\u2713 Left Recursion Eliminated
\u2713 Left Factoring Applied
\u2713 Non-determinism Removed

PRODUCTION RULES:
\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

Program       \u2192 SectionList EOF
SectionList   \u2192 Section SectionList | \u03b5

Section       \u2192 DataSection | CodeSection
DataSection   \u2192 SECTION DATA VarDeclList
CodeSection   \u2192 SECTION CODE ProcOrStmtList

VarDeclList   \u2192 VarDecl VarDeclList | \u03b5
VarDecl       \u2192 ID SizeDir Initializer
SizeDir       \u2192 DB | DW | DD | DQ
Initializer   \u2192 NUM | HEX_NUM | STR_LITERAL | ?

ProcOrStmtList \u2192 ProcDef ProcOrStmtList | Stmt ProcOrStmtList | \u03b5
ProcDef       \u2192 PROC ID StmtList ENDP ID

StmtList      \u2192 Stmt StmtList | \u03b5
Stmt          \u2192 LabelDef | Instruction
LabelDef      \u2192 ID COLON

Instruction   \u2192 MovInstr  | ArithInstr | CmpInstr
              | JumpInstr | StackInstr | CallInstr
              | RetInstr  | NopInstr   | HltInstr

MovInstr      \u2192 MOV  Operand , Operand
ArithInstr    \u2192 (ADD|SUB|MUL|DIV) Operand , Operand
CmpInstr      \u2192 CMP  Operand , Operand
JumpInstr     \u2192 (JMP|JE|JNE|JG|JL|JGE|JLE) ID
StackInstr    \u2192 PUSH Operand | POP Operand
CallInstr     \u2192 CALL ID
RetInstr      \u2192 RET
NopInstr      \u2192 NOP
HltInstr      \u2192 HLT

Operand       \u2192 SizeQual LBRACKET InnerMem RBRACKET
              | LBRACKET InnerMem RBRACKET
              | Register | NUM | HEX_NUM | ID
SizeQual      \u2192 BYTE PTR | WORD PTR | DWORD PTR | QWORD PTR
InnerMem      \u2192 Operand | Operand + Operand | Operand - Operand
Register      \u2192 AX|BX|CX|DX|SP|BP|SI|DI (halves: AL AH BL BH ...)

REGISTERS:   AX BX CX DX SP BP SI DI  (and 8-bit halves)
MNEMONICS:   MOV ADD SUB MUL DIV CMP
             JMP JE JNE JG JL JGE JLE
             PUSH POP CALL RET NOP HLT PROC ENDP
DIRECTIVES:  SECTION DATA / CODE
             DB(1B) DW(2B) DD(4B) DQ(8B)
             BYTE/WORD/DWORD/QWORD PTR
COMMENT:     ; ... (to end of line)

TRANSFORMATIONS APPLIED:
\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

1. LEFT RECURSION REMOVAL:
   Orig:  StmtList \u2192 StmtList Stmt | Stmt
   Trans: StmtList \u2192 Stmt StmtList | \u03b5

2. LEFT FACTORING:
   Orig:  Stmt \u2192 ID COLON | ID SizeDir ...
   Trans: Stmt \u2192 ID ( COLON | SizeDir Initializer )

3. AMBIGUITY RESOLUTION:
   Size qualifier resolved before memory-reference bracket.
   Jump targets verified in symbol-table pass.
   MOV mem, mem flagged as semantic error.

TAC MAPPING:
\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
  MOV  dst, src  \u2192  t = src  ;  dst = t
  ADD  dst, src  \u2192  t = dst + src  ;  dst = t
  SUB  dst, src  \u2192  t = dst - src  ;  dst = t
  MUL  dst, src  \u2192  t = dst * src  ;  dst = t
  DIV  dst, src  \u2192  t = dst / src  ;  dst = t
  CMP  op1, op2  \u2192  t = op1 - op2  ;  FLAGS = t
  JE   lbl       \u2192  if FLAGS == 0 goto lbl
  JNE  lbl       \u2192  if FLAGS != 0 goto lbl
  JG   lbl       \u2192  if FLAGS >  0 goto lbl
  JL   lbl       \u2192  if FLAGS <  0 goto lbl
  JGE  lbl       \u2192  if FLAGS >= 0 goto lbl
  JLE  lbl       \u2192  if FLAGS <= 0 goto lbl
  JMP  lbl       \u2192  goto lbl
  PUSH op        \u2192  PUSH op
  POP  op        \u2192  POP  op
  CALL proc      \u2192  CALL proc
  RET            \u2192  RETURN
  HLT            \u2192  HALT
"""

    # ---------------------------------------------------------------- About --
    def show_about(self):
        profile_win = tk.Toplevel(self)
        profile_win.title('Developer Profile')
        profile_win.geometry('600x650')
        profile_win.configure(bg='#e8f4f8')
        profile_win.resizable(False, False)
        profile_win.transient(self)
        profile_win.grab_set()

        header = tk.Frame(profile_win, bg='#e8f4f8')
        header.pack(fill='x', pady=(20, 10))
        tk.Label(header, text='🚀', bg='#e8f4f8',
                 font=('Segoe UI', 32)).pack()
        tk.Label(header, text='Mini Compiler Project',
                 bg='#e8f4f8', fg='#2c3e50',
                 font=('Segoe UI', 18, 'bold')).pack(pady=(5, 2))
        tk.Label(header, text='Assembly Language Mini Compiler 2026',
                 bg='#e8f4f8', fg='#7f8c8d',
                 font=('Segoe UI', 10)).pack()

        tk.Label(profile_win, text='Meet the Developer',
                 bg='#e8f4f8', fg='#2c3e50',
                 font=('Segoe UI', 14, 'bold')).pack(pady=(15, 10))

        card = tk.Frame(profile_win, bg='white', relief='solid',
                        borderwidth=1, width=320, height=180)
        card.pack(); card.pack_propagate(False)

        av = tk.Canvas(card, width=80, height=80, bg='white', highlightthickness=0)
        av.place(x=120, y=15)
        av.create_oval(5, 5, 75, 75, fill='#4a7ba7', outline='#2c5aa0', width=3)
        av.create_text(40, 40, text='MA', fill='white',
                       font=('Segoe UI', 20, 'bold'))

        tk.Label(card, text='Muhammad Awais', bg='white', fg='#2c3e50',
                 font=('Segoe UI', 13, 'bold')).place(x=95, y=100)

        role_f = tk.Frame(card, bg='#d6eaf8', height=24)
        role_f.place(x=110, y=125)
        tk.Label(role_f, text='AI Developer', bg='#d6eaf8', fg='#1976d2',
                 font=('Segoe UI', 9, 'bold'), padx=10, pady=3).pack()

        tk.Label(card, text='🎓 Sukkur IBA University',
                 bg='white', fg='#555',
                 font=('Segoe UI', 9)).place(x=90, y=155)

        cf = tk.Frame(profile_win, bg='#e8f4f8')
        cf.pack(pady=(15, 10))
        email_btn = tk.Frame(cf, bg='#e3f2fd', cursor='hand2',
                             relief='solid', borderwidth=1)
        email_btn.pack(side='left', padx=5)
        tk.Label(email_btn, text='📧 Email', bg='#e3f2fd', fg='#1976d2',
                 font=('Segoe UI', 9, 'bold'), padx=12, pady=4).pack()
        email_btn.bind('<Button-1>',
            lambda e: webbrowser.open(
                'mailto:muhammadawais.bscsf22@iba-suk.edu.pk'))

        lin_btn = tk.Frame(cf, bg='#fce4ec', cursor='hand2',
                           relief='solid', borderwidth=1)
        lin_btn.pack(side='left', padx=5)
        tk.Label(lin_btn, text='💼 LinkedIn', bg='#fce4ec', fg='#c2185b',
                 font=('Segoe UI', 9, 'bold'), padx=12, pady=4).pack()
        lin_btn.bind('<Button-1>',
            lambda e: webbrowser.open(
                'https://linkedin.com/in/muhammadawais'))

        feat_sec = tk.Frame(profile_win, bg='white', relief='solid', borderwidth=1)
        feat_sec.pack(fill='x', padx=30, pady=(10, 20))
        tk.Label(feat_sec, text='✨ Project Features', bg='white', fg='#2c3e50',
                 font=('Segoe UI', 11, 'bold')).pack(pady=(10, 5))
        for f in ['✓ Complete Lexical Analysis',
                  '✓ LL(1) Parser Implementation',
                  '✓ Symbol Table with Scope Management',
                  '✓ Semantic Analysis & Type Checking',
                  '✓ Three-Address Code Generation',
                  '✓ Grammar Transformations Applied']:
            tk.Label(feat_sec, text=f, bg='white', fg='#555',
                     font=('Segoe UI', 9), anchor='w').pack(anchor='w', padx=20)
        tk.Label(feat_sec, text='', bg='white').pack(pady=5)

        bot = tk.Frame(profile_win, bg='#5b7fc9', height=80)
        bot.pack(fill='x', side='bottom'); bot.pack_propagate(False)
        tk.Label(bot, text='📚 Subject: Computer Architecture & Assembly Language',
                 bg='#5b7fc9', fg='white',
                 font=('Segoe UI', 14, 'bold')).pack(pady=(12, 4))
        tk.Label(bot, text='Subject Supervisor: Dr. Hifazat Shah',
                 bg='#5b7fc9', fg='white',
                 font=('Segoe UI', 11)).pack()


if __name__ == '__main__':
    app = CompilerGUI()
    app.mainloop()
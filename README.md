# 🔧 Mini Compiler — AssemblyLang

A complete mini compiler for an x86-style assembly language, built in Python with a modern Tkinter GUI. Developed as a course project for **Computer Architecture & Assembly Language** at **Sukkur IBA University**.

---

## 📸 Features

- **Lexical Analysis** — Tokenizes AssemblyLang source into classified tokens with line/column tracking
- **LL(1) Recursive-Descent Parser** — Full syntax validation with error detection and recovery
- **Symbol Table** — Scope-aware table managing DATA, CODE, and PROC scopes
- **Semantic Analysis** — Type checking, undeclared identifier detection, duplicate declaration errors
- **Three-Address Code (TAC) Generation** — Intermediate code output mirroring the parser structure
- **Modern GUI Dashboard** — Tabbed interface showing Tokens, Symbol Table, Parse Results, TAC, and Grammar

---

## 🚀 Getting Started

### Prerequisites

- Python 3.x
- `tkinter` (included with standard Python installations)

### Run

```bash
python Assembly_Compiler.py
```

---

## 🗣️ Language: AssemblyLang

A simplified x86-style assembly language supporting:

| Category | Keywords |
|---|---|
| Instructions | `MOV`, `ADD`, `SUB`, `MUL`, `DIV`, `CMP` |
| Jumps | `JMP`, `JE`, `JNE`, `JG`, `JL`, `JGE`, `JLE` |
| Stack | `PUSH`, `POP` |
| Control | `CALL`, `RET`, `NOP`, `HLT` |
| Procedures | `PROC`, `ENDP` |
| Sections | `SECTION DATA`, `SECTION CODE` |
| Data sizes | `DB` (1B), `DW` (2B), `DD` (4B), `DQ` (8B) |
| Size quals | `BYTE PTR`, `WORD PTR`, `DWORD PTR`, `QWORD PTR` |
| Registers | `AX BX CX DX SP BP SI DI` + 8-bit halves |

---

## 📐 Grammar (Summary)

```
Program       → SectionList EOF
SectionList   → Section SectionList | ε
Section       → SECTION DATA VarDeclList | SECTION CODE ProcOrStmtList
VarDecl       → ID (DB|DW|DD|DQ) Initializer
ProcDef       → PROC ID StmtList ENDP ID
Stmt          → LabelDef | Instruction
Instruction   → MovInstr | ArithInstr | CmpInstr | JumpInstr
              | StackInstr | CallInstr | RetInstr | NopInstr | HltInstr
Operand       → Register | NUM | HEX_NUM | ID | [InnerMem] | SizeQual [InnerMem]
```

**Transformations applied:** left recursion removal, left factoring, ambiguity resolution.

---

## ⚙️ TAC Mapping

```
MOV  dst, src  →  t = src  ;  dst = t
ADD  dst, src  →  t = dst + src  ;  dst = t
CMP  op1, op2  →  t = op1 - op2  ;  FLAGS = t
JE   label     →  if FLAGS == 0 goto label
JMP  label     →  goto label
CALL proc      →  CALL proc
RET            →  RETURN
HLT            →  HALT
```

---

## 🖥️ GUI Tabs

| Tab | Description |
|---|---|
| 🎯 Tokens | All lexed tokens with type, line, and column |
| 📊 Symbol Table | Declared identifiers with kind, scope level, and line |
| 🌳 Parse Results | Phase-by-phase compilation status and errors |
| ⚙️ TAC | Generated three-address intermediate code |
| 📖 Grammar | Full grammar reference with transformation notes |

---

## 📁 Project Structure

```
Assembly_Compiler.py   # Single-file implementation
README.md
```

---

## 🧱 Architecture

```
Source Code
    │
    ▼
Lexer          →  Token stream
    │
    ▼
Parser         →  Syntax tree (implicit) + Symbol Table
    │
    ▼
Semantic Pass  →  Type & scope checking
    │
    ▼
TACGenerator   →  Three-Address Code
    │
    ▼
GUI Display    →  Tabbed results dashboard
```

---

## 👨‍💻 Developer

**Muhammad Awais**  
BS Computer Science — Sukkur IBA University  
📧 muhammadawais.bscsf22@iba-suk.edu.pk
📧 Azharali.bscsaif24@iba-suk.edu.pk

---

## 🎓 Academic Info

| | |
|---|---|
| University | Sukkur IBA University |
| Subject | Computer Architecture & Assembly Language |
| Supervisor | Dr. Hifazat Shah |
| Year | 2026 |

---

## 📄 License

This project is submitted as an academic assignment. Feel free to use it for learning purposes.

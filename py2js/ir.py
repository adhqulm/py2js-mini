# flake8: noqa

from dataclasses import dataclass, field
from typing import List, Optional

# ===== Modules =====
@dataclass
class Module:
    body: List["Stmt"]

# ===== Base nodes =====
class Stmt: ...
class Expr: ...

# ===== Statements =====
@dataclass
class Assign(Stmt):
    name: str
    value: "Expr"

@dataclass
class AssignAttr(Stmt):
    obj: "Expr"
    attr: str
    value: "Expr"

@dataclass
class UnpackAssign(Stmt):
    targets: List[Optional[str]]  # names; None for starred capture slot
    starred_index: Optional[int]  # index of starred element in targets, or None
    value: "Expr"
    starred_name: Optional[str]

@dataclass
class ImportFrom(Stmt):
    module: str
    names: List[str]  # only simple names

@dataclass
class ExprStmt(Stmt):
    expr: "Expr"

@dataclass
class If(Stmt):
    test: "Expr"
    body: List[Stmt]
    orelse: List[Stmt]

@dataclass
class For(Stmt):
    target: str
    iter: "Expr"
    body: List[Stmt]
    orelse: List[Stmt]

@dataclass
class While(Stmt):
    test: "Expr"
    body: List[Stmt]
    orelse: List[Stmt]

class Break(Stmt): ...
class Continue(Stmt): ...
class Pass(Stmt): ...

@dataclass
class Function(Stmt):
    name: str
    params: List[str]                 # named positional params
    body: List[Stmt]
    defaults: List[Optional["Expr"]]  # align with params
    vararg: Optional[str] = None      # *args name
    kwarg: Optional[str] = None       # **kwargs name

@dataclass
class ClassDef(Stmt):
    name: str
    bases: List[str]                  # single name base supported
    methods: List["Function"]

@dataclass
class WithItem:
    context_expr: "Expr"
    optional_vars: Optional[str]  # simple name or None

@dataclass
class With(Stmt):
    items: List[WithItem]
    body: List[Stmt]

@dataclass
class Return(Stmt):
    value: Optional["Expr"]

@dataclass
class Raise(Stmt):
    exc_type: str
    message: Optional["Expr"]

@dataclass
class ExceptHandler:
    type_name: Optional[str]
    varname: Optional[str]
    body: List["Stmt"]

@dataclass
class Try(Stmt):
    body: List[Stmt]
    handlers: List[ExceptHandler]
    orelse: List[Stmt]
    finalbody: List[Stmt]

# ===== Expressions =====
@dataclass
class Name(Expr):
    id: str

@dataclass
class Const(Expr):
    value: object

@dataclass
class Undef(Expr):
    pass

@dataclass
class BinOp(Expr):
    left: Expr
    op: str
    right: Expr

@dataclass
class BoolOp(Expr):
    op: str
    values: List[Expr]

@dataclass
class UnaryNot(Expr):
    value: Expr

@dataclass
class Compare(Expr):
    left: Expr
    op: str
    right: Expr

@dataclass
class CompareChain(Expr):
    left: Expr
    ops: List[str]
    comparators: List[Expr]

@dataclass
class Call(Expr):
    func: str
    args: List[Expr] = field(default_factory=list)

@dataclass
class Starred(Expr):
    value: Expr  # for *args at call sites

@dataclass
class KwargPairs(Expr):
    pairs: List[tuple[str, Expr]]  # list of (key, value)

@dataclass
class KwargExp(Expr):
    value: Expr  # for **mapping expansion at call sites

@dataclass
class ListLit(Expr):
    elts: List[Expr]

@dataclass
class TupleLit(Expr):
    elts: List[Expr]

@dataclass
class DictLit(Expr):
    keys: List[Expr]
    values: List[Expr]

@dataclass
class Subscript(Expr):
    value: Expr
    index: Expr

@dataclass
class Slice(Expr):
    value: Expr
    start: Optional[Expr]
    stop: Optional[Expr]
    step: Optional[Expr]

@dataclass
class Attribute(Expr):
    value: Expr
    attr: str

@dataclass
class MethodCall(Expr):
    obj: Expr
    method: str
    args: List[Expr]

@dataclass
class New(Expr):
    class_name: str
    args: List[Expr]

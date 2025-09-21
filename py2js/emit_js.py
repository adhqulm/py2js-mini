# flake8: noqa
# mypy: ignore-errors

from typing import List
from .ir import (
    Module, Stmt, Expr,
    Assign, AssignAttr, UnpackAssign, ImportFrom, ExprStmt, If, For, While, Break, Continue, Pass,
    Function, ClassDef, With, WithItem, Return, Raise, Try, ExceptHandler,
    Name, Const, Undef, BinOp, BoolOp, UnaryNot, Call, Starred, KwargPairs, KwargExp,
    Compare, CompareChain, ListLit, TupleLit, DictLit, Subscript, Slice,
    Attribute, MethodCall, New
)

_MATH_EXPORTS = {
    "floor": "py_math_floor",
    "ceil":  "py_math_ceil",
    "sqrt":  "py_math_sqrt",
    "pow":   "py_math_pow",
    "abs":   "py_math_abs",
}

class Emitter:
    def __init__(self):
        self.lines: List[str] = []
        self.indent = 0
        self._tmp_counter = 0
        self._scopes: List[set[str]] = [set()]
        self._break_flag_stack: List[str] = []
        self._self_stack: List[str] = []
        self._base_stack: List[str] = []  # for super()

    def _tmp(self, prefix: str) -> str:
        self._tmp_counter += 1
        return f"__py_{prefix}_{self._tmp_counter}"

    def writeln(self, s: str = "") -> None:
        self.lines.append("  " * self.indent + s)

    def _is_declared(self, name: str) -> bool:
        for scope in reversed(self._scopes):
            if name in scope:
                return True
        return False

    def _declare(self, name: str) -> None:
        self._scopes[-1].add(name)

    def emit_module(self, mod: Module) -> str:
        for s in mod.body:
            self.emit_stmt(s)
        return "\n".join(self.lines)

    # -----------------------------
    # Statements
    # -----------------------------
    def emit_stmt(self, s: Stmt) -> None:
        if isinstance(s, ImportFrom):
            # minimal import shim
            if s.module == "math":
                for name in s.names:
                    target = _MATH_EXPORTS.get(name)
                    if not target:
                        self.writeln(f"// from math import {name} (unsupported)")
                        continue
                    if not self._is_declared(name):
                        self._declare(name)
                        self.writeln(f"let {name} = {target};")
            else:
                self.writeln(f"// import from {s.module} (no-op)")
            return

        if isinstance(s, Assign):
            target = s.name
            expr = self.emit_expr(s.value)
            if self._is_declared(target):
                self.writeln(f"{target} = {expr};")
            else:
                self._declare(target)
                self.writeln(f"let {target} = {expr};")
            return

        if isinstance(s, AssignAttr):
            obj = self.emit_expr(s.obj)
            val = self.emit_expr(s.value)
            self.writeln(f"{obj}.{s.attr} = {val};")
            return

        if isinstance(s, UnpackAssign):
            arr = self._tmp("unpack")
            self.writeln(f"const {arr} = py_to_array({self.emit_expr(s.value)});")
            n = len(s.targets)
            if s.starred_index is None:
                for i, name in enumerate(s.targets):
                    if not self._is_declared(name):
                        self._declare(name)
                        self.writeln(f"let {name} = {arr}[{i}];")
                    else:
                        self.writeln(f"{name} = {arr}[{i}];")
            else:
                star = s.starred_index
                before = star
                after = n - star - 1
                for i in range(before):
                    name = s.targets[i]
                    if not self._is_declared(name):
                        self._declare(name)
                        self.writeln(f"let {name} = {arr}[{i}];")
                    else:
                        self.writeln(f"{name} = {arr}[{i}];")
                rest_tmp = self._tmp("rest")
                self.writeln(f"const {rest_tmp} = {arr}.slice({before}, {arr}.length - {after});")
                star_var = s.starred_name or "rest"
                if not self._is_declared(star_var):
                    self._declare(star_var)
                    self.writeln(f"let {star_var} = {rest_tmp};")
                else:
                    self.writeln(f"{star_var} = {rest_tmp};")
                for j in range(after):
                    idx_src = f"{arr}.length - {after} + {j}"
                    name = s.targets[star + 1 + j]
                    if not self._is_declared(name):
                        self._declare(name)
                        self.writeln(f"let {name} = {arr}[{idx_src}];")
                    else:
                        self.writeln(f"{name} = {arr}[{idx_src}];")
            return

        if isinstance(s, ExprStmt):
            self.writeln(self.emit_expr(s.expr) + ";")
            return

        if isinstance(s, If):
            test_js = self.emit_expr(s.test)
            self.writeln(f"if (py_truth({test_js})) {{")
            self.indent += 1
            for b in s.body:
                self.emit_stmt(b)
            self.indent -= 1
            self.writeln("}")
            if s.orelse:
                self.writeln("else {")
                self.indent += 1
                for o in s.orelse:
                    self.emit_stmt(o)
                self.indent -= 1
                self.writeln("}")
            return

        if isinstance(s, For):
            if not self._is_declared(s.target):
                self._declare(s.target)
                self.writeln(f"let {s.target};")
            use_range = isinstance(s.iter, Call) and s.iter.func == "range"
            iter_src = (
                f"py_range({', '.join(self.emit_expr(a) for a in s.iter.args)})"
                if use_range else
                f"py_iter({self.emit_expr(s.iter)})"
            )
            if s.orelse:
                brk_flag = self._tmp("broke")
                self.writeln("{")
                self.indent += 1
                self.writeln(f"let {brk_flag} = false;")
                self._break_flag_stack.append(brk_flag)
                self.writeln(f"for (const __it of {iter_src}) {{")
                self.indent += 1
                self.writeln(f"{s.target} = __it;")
                for b in s.body:
                    self.emit_stmt(b)
                self.indent -= 1
                self.writeln("}")
                self._break_flag_stack.pop()
                self.writeln(f"if (!{brk_flag}) {{")
                self.indent += 1
                for b in s.orelse:
                    self.emit_stmt(b)
                self.indent -= 1
                self.writeln("}")
                self.indent -= 1
                self.writeln("}")
            else:
                self.writeln(f"for (const __it of {iter_src}) {{")
                self.indent += 1
                self.writeln(f"{s.target} = __it;")
                for b in s.body:
                    self.emit_stmt(b)
                self.indent -= 1
                self.writeln("}")
            return

        if isinstance(s, While):
            if s.orelse:
                brk_flag = self._tmp("broke")
                self.writeln("{")
                self.indent += 1
                self.writeln(f"let {brk_flag} = false;")
                self._break_flag_stack.append(brk_flag)
                self.writeln(f"while (py_truth({self.emit_expr(s.test)})) {{")
                self.indent += 1
                for b in s.body:
                    self.emit_stmt(b)
                self.indent -= 1
                self.writeln("}")
                self._break_flag_stack.pop()
                self.writeln(f"if (!{brk_flag}) {{")
                self.indent += 1
                for b in s.orelse:
                    self.emit_stmt(b)
                self.indent -= 1
                self.writeln("}")
                self.indent -= 1
                self.writeln("}")
            else:
                self.writeln(f"while (py_truth({self.emit_expr(s.test)})) {{")
                self.indent += 1
                for b in s.body:
                    self.emit_stmt(b)
                self.indent -= 1
                self.writeln("}")
            return

        if isinstance(s, Break):
            if self._break_flag_stack:
                self.writeln(f"{self._break_flag_stack[-1]} = true;")
            self.writeln("break;")
            return

        if isinstance(s, Continue):
            self.writeln("continue;")
            return

        if isinstance(s, Pass):
            self.writeln(";")
            return

        if isinstance(s, Function):
            # functions accept hidden trailing __kwargs__ (may be undefined)
            params = s.params + ([s.vararg] if s.vararg else [])
            params_js = ", ".join(params + ["__kwargs__"])
            self.writeln(f"function {s.name}({params_js}) {{")
            self._scopes.append(set())
            self.indent += 1
            base_params_count = len(s.params)
            # defaults
            for idx, (p, d) in enumerate(zip(s.params, s.defaults)):
                if d is not None:
                    expr_js = self.emit_expr(d)
                    self.writeln(f"if (arguments.length <= {idx} || {p} === undefined) {p} = {expr_js};")
            # *args to tuple (exclude hidden __kwargs__)
            if s.vararg:
                self.writeln(
                    f"{s.vararg} = py_tuple_from_array("
                    f"Array.prototype.slice.call(arguments, {base_params_count}, "
                    f"Math.max({base_params_count}, arguments.length - 1)));"
                )
            # **kwargs binding
            if s.kwarg:
                self.writeln(f"let {s.kwarg} = (__kwargs__ === undefined || __kwargs__ === null) ? {{}} : __kwargs__;")
            for b in s.body:
                self.emit_stmt(b)
            self.indent -= 1
            self.writeln("}")
            self._scopes.pop()
            return

        if isinstance(s, ClassDef):
            base = s.bases[0] if s.bases else None
            if base:
                self.writeln(f"class {s.name} extends {base} " + "{")
            else:
                self.writeln(f"class {s.name} " + "{")
            self.indent += 1
            self._base_stack.append(base)

            init = next((m for m in s.methods if m.name == "__init__"), None)
            if init:
                params = ", ".join(init.params[1:] + ([init.vararg] if init.vararg else []) + ["__kwargs__"])
                self.writeln(f"constructor({params}) " + "{")
                self.indent += 1
                self._self_stack.append(init.params[0])
                self._scopes.append(set())
                base_params_count = len(init.params) - 1
                for idx, d in enumerate(init.defaults[1:]):
                    if d is not None:
                        p = init.params[1 + idx]
                        expr_js = self.emit_expr(d)
                        self.writeln(f"if (arguments.length <= {idx} || {p} === undefined) {p} = {expr_js};")
                if init.vararg:
                    self.writeln(
                        f"{init.vararg} = py_tuple_from_array("
                        f"Array.prototype.slice.call(arguments, {base_params_count}, "
                        f"Math.max({base_params_count}, arguments.length - 1)));"
                    )
                self.writeln(f"let __kwargs__ctor = __kwargs__;")
                for b in init.body:
                    self.emit_stmt(b)
                self._scopes.pop()
                self._self_stack.pop()
                self.indent -= 1
                self.writeln("}")
            else:
                self.writeln("constructor() {}")

            for m in s.methods:
                if m.name == "__init__":
                    continue
                params = ", ".join(m.params[1:] + ([m.vararg] if m.vararg else []) + ["__kwargs__"])
                self.writeln(f"{m.name}({params}) " + "{")
                self.indent += 1
                self._self_stack.append(m.params[0])
                self._scopes.append(set())
                base_params_count = len(m.params) - 1
                for idx, d in enumerate(m.defaults[1:]):
                    if d is not None:
                        p = m.params[1 + idx]
                        expr_js = self.emit_expr(d)
                        self.writeln(f"if (arguments.length <= {idx} || {p} === undefined) {p} = {expr_js};")
                if m.vararg:
                    self.writeln(
                        f"{m.vararg} = py_tuple_from_array("
                        f"Array.prototype.slice.call(arguments, {base_params_count}, "
                        f"Math.max({base_params_count}, arguments.length - 1)));"
                    )
                self.writeln(f"let __kwargs__meth = __kwargs__;")
                for b in m.body:
                    self.emit_stmt(b)
                self._scopes.pop()
                self._self_stack.pop()
                self.indent -= 1
                self.writeln("}")
            self._base_stack.pop()
            self.indent -= 1
            self.writeln("}")
            return

        if isinstance(s, With):
            exits = []
            for it in s.items:
                mgr = self._tmp("mgr")
                val = self._tmp("val")
                self.writeln(f"const {mgr} = {self.emit_expr(it.context_expr)};")
                self.writeln(f"const {val} = py_with_enter({mgr});")
                exits.append(mgr)
                if it.optional_vars:
                    if not self._is_declared(it.optional_vars):
                        self._declare(it.optional_vars)
                        self.writeln(f"let {it.optional_vars} = {val};")
                    else:
                        self.writeln(f"{it.optional_vars} = {val};")
            self.writeln("try {")
            self.indent += 1
            for b in s.body:
                self.emit_stmt(b)
            self.indent -= 1
            self.writeln("} finally {")
            self.indent += 1
            for mgr in reversed(exits):
                self.writeln(f"py_with_exit({mgr});")
            self.indent -= 1
            self.writeln("}")
            return

        if isinstance(s, Return):
            if s.value is None:
                self.writeln("return;")
            else:
                self.writeln(f"return {self.emit_expr(s.value)};")
            return

        if isinstance(s, Raise):
            if s.message is None:
                self.writeln(f"py_raise({repr(s.exc_type)});")
            else:
                self.writeln(f"py_raise({repr(s.exc_type)}, {self.emit_expr(s.message)});")
            return

        if isinstance(s, Try):
            # Inline synthetic blocks (used by lowering for unpack-to-attrs) to avoid block scoping issues.
            if not s.handlers and not s.orelse and not s.finalbody:
                for b in s.body:
                    self.emit_stmt(b)
                return

            ok = self._tmp("try_ok")
            caught = self._tmp("caught")
            err = self._tmp("err")
            self.writeln("{")
            self.indent += 1
            self.writeln(f"let {ok} = false;")
            self.writeln("try {")
            self.indent += 1
            for b in s.body:
                self.emit_stmt(b)
            self.writeln(f"{ok} = true;")
            self.indent -= 1
            self.writeln(f"}} catch ({caught}) {{")
            self.indent += 1
            self.writeln(f"const {err} = py_wrap_error({caught});")
            if s.handlers:
                for i, h in enumerate(s.handlers):
                    cond = "true" if (h.type_name is None) else f"py_exc_match({err}, {repr(h.type_name)})"
                    self.writeln(("if " if i == 0 else "else if ") + f"({cond}) " + "{")
                    self.indent += 1
                    if h.varname:
                        self.writeln(f"let {h.varname} = {err};")
                    for b in h.body:
                        self.emit_stmt(b)
                    self.indent -= 1
                    self.writeln("}")
                self.writeln("else { throw " + err + "; }")
            else:
                self.writeln("throw " + err + ";")
            self.indent -= 1
            self.writeln("} finally {")
            self.indent += 1
            for b in s.finalbody:
                self.emit_stmt(b)
            self.indent -= 1
            self.writeln("}")
            if s.orelse:
                self.writeln(f"if ({ok}) " + "{")
                self.indent += 1
                for b in s.orelse:
                    self.emit_stmt(b)
                self.indent -= 1
                self.writeln("}")
            self.indent -= 1
            self.writeln("}")
            return

        raise NotImplementedError(f"Stmt not handled: {type(s).__name__}")

    # -----------------------------
    # Expressions
    # -----------------------------
    def emit_expr(self, e: Expr) -> str:
        if isinstance(e, Name):
            if self._self_stack and e.id == self._self_stack[-1]:
                return "this"
            return e.id

        if isinstance(e, Const):
            v = e.value
            if v is True:  return "true"
            if v is False: return "false"
            if v is None:  return "null"
            if isinstance(v, str): return repr(v)
            return repr(v)

        if isinstance(e, Undef):
            return "undefined"

        if isinstance(e, BinOp):
            if e.op == "//":
                return f"py_floor_div({self.emit_expr(e.left)}, {self.emit_expr(e.right)})"
            if e.op == "+":
                return f"py_add({self.emit_expr(e.left)}, {self.emit_expr(e.right)})"
            if e.op == "*":
                return f"py_mul({self.emit_expr(e.left)}, {self.emit_expr(e.right)})"
            return f"({self.emit_expr(e.left)} {e.op} {self.emit_expr(e.right)})"

        if isinstance(e, BoolOp):
            lines = []
            t = self._tmp("bool")
            lines.append(f"const {t} = {self.emit_expr(e.values[0])};")
            if e.op == "and":
                prev = t
                for v in e.values[1:]:
                    lines.append(f"if (!py_truth({prev})) return {prev};")
                    cur = self._tmp("bool")
                    lines.append(f"const {cur} = {self.emit_expr(v)};")
                    prev = cur
                lines.append(f"return {prev};")
            else:
                prev = t
                for v in e.values[1:]:
                    lines.append(f"if (py_truth({prev})) return {prev};")
                    cur = self._tmp("bool")
                    lines.append(f"const {cur} = {self.emit_expr(v)};")
                    prev = cur
                lines.append(f"return {prev};")
            return f"(function(){{\n" + "\n".join(lines) + "\n})()"


        if isinstance(e, UnaryNot):
            return f"(!py_truth({self.emit_expr(e.value)}))"

        if isinstance(e, CompareChain):
            lines = []
            t_prev = self._tmp("cmp")
            lines.append(f"const {t_prev} = {self.emit_expr(e.left)};")
            for op, comp in zip(e.ops, e.comparators):
                t_cur = self._tmp("cmp")
                lines.append(f"const {t_cur} = {self.emit_expr(comp)};")
                if op == "in":
                    cond = f"py_in({t_prev}, {t_cur})"
                elif op == "not in":
                    cond = f"!py_in({t_prev}, {t_cur})"
                elif op == "==":
                    cond = f"py_eq({t_prev}, {t_cur})"
                elif op == "!=":
                    cond = f"!py_eq({t_prev}, {t_cur})"
                else:
                    cond = f"({t_prev} {op} {t_cur})"
                lines.append(f"if (!{cond}) return false;")
                t_prev = t_cur
            lines.append("return true;")
            return f"(function(){{\n" + "\n".join(lines) + "\n})()"


        if isinstance(e, Compare):
            if e.op == "in":
                return f"py_in({self.emit_expr(e.left)}, {self.emit_expr(e.right)})"
            if e.op == "not in":
                return f"!py_in({self.emit_expr(e.left)}, {self.emit_expr(e.right)})"
            if e.op == "==":
                return f"py_eq({self.emit_expr(e.left)}, {self.emit_expr(e.right)})"
            if e.op == "!=":
                return f"!py_eq({self.emit_expr(e.left)}, {self.emit_expr(e.right)})"
            return f"({self.emit_expr(e.left)} {e.op} {self.emit_expr(e.right)})"

        if isinstance(e, ListLit):
            return "[" + ", ".join(self.emit_expr(x) for x in e.elts) + "]"

        if isinstance(e, TupleLit):
            return f"py_tuple({', '.join(self.emit_expr(x) for x in e.elts)})"

        if isinstance(e, DictLit):
            pairs = []
            for k, v in zip(e.keys, e.values):
                pairs.append(f"{self.emit_expr(k)}: {self.emit_expr(v)}")
            return "({" + ", ".join(pairs) + "})"

        if isinstance(e, Subscript):
            return f"py_getitem({self.emit_expr(e.value)}, {self.emit_expr(e.index)})"

        if isinstance(e, Slice):
            a0 = self.emit_expr(e.start) if e.start else "null"
            a1 = self.emit_expr(e.stop) if e.stop else "null"
            a2 = self.emit_expr(e.step) if e.step else "null"
            return f"py_slice({self.emit_expr(e.value)}, {a0}, {a1}, {a2})"

        if isinstance(e, Attribute):
            return f"{self.emit_expr(e.value)}.{e.attr}"

        if isinstance(e, MethodCall):
            # super() handling
            if isinstance(e.obj, Call) and e.obj.func == "super":
                base = self._base_stack[-1] if self._base_stack else None
                segs = []
                for a in e.args:
                    if isinstance(a, Starred):
                        segs.append(f"...py_to_array({self.emit_expr(a.value)})")
                    elif isinstance(a, Undef):
                        segs.append("undefined")
                    else:
                        segs.append(self.emit_expr(a))
                if e.method == "__init__":
                    return f"super({', '.join(segs)})"
                else:
                    if not base:
                        raise RuntimeError("super() call but no base class")
                    return f"py_super(this, {base}).{e.method}({', '.join(segs)})"

            segs = []
            for a in e.args:
                if isinstance(a, Starred):
                    segs.append(f"...py_to_array({self.emit_expr(a.value)})")
                elif isinstance(a, Undef):
                    segs.append("undefined")
                else:
                    segs.append(self.emit_expr(a))
            return f"{self.emit_expr(e.obj)}.{e.method}({', '.join(segs)})"

        if isinstance(e, New):
            segs = []
            for a in e.args:
                if isinstance(a, Starred):
                    segs.append(f"...py_to_array({self.emit_expr(a.value)})")
                elif isinstance(a, Undef):
                    segs.append("undefined")
                else:
                    segs.append(self.emit_expr(a))
            return f"new {e.class_name}({', '.join(segs)})"

        if isinstance(e, Call):
            if e.func == "print":
                args_js = ", ".join(self.emit_expr(a) for a in e.args)
                return f"py_print({args_js})"
            if e.func == "__len__":
                return f"py_len({self.emit_expr(e.args[0])})"
            if e.func == "__str__":
                return f"py_str({self.emit_expr(e.args[0])})"
            # string/list helpers
            if e.func == "__str_upper__":      return f"py_str_upper({self.emit_expr(e.args[0])})"
            if e.func == "__str_lower__":      return f"py_str_lower({self.emit_expr(e.args[0])})"
            if e.func == "__str_split__":
                base = self.emit_expr(e.args[0])
                sep  = (self.emit_expr(e.args[1]) if len(e.args) > 1 else "null")
                return f"py_str_split({base}, {sep})"
            if e.func == "__str_join__":       return f"py_str_join({self.emit_expr(e.args[0])}, {self.emit_expr(e.args[1])})"
            if e.func == "__str_startswith__": return f"py_str_startswith({self.emit_expr(e.args[0])}, {self.emit_expr(e.args[1])})"
            if e.func == "__str_endswith__":   return f"py_str_endswith({self.emit_expr(e.args[0])}, {self.emit_expr(e.args[1])})"
            if e.func == "__str_replace__":    return f"py_str_replace({self.emit_expr(e.args[0])}, {self.emit_expr(e.args[1])}, {self.emit_expr(e.args[2])})"
            if e.func == "__str_find__":       return f"py_str_find({self.emit_expr(e.args[0])}, {self.emit_expr(e.args[1])})"
            if e.func == "__list_append__":    return f"py_list_append({self.emit_expr(e.args[0])}, {self.emit_expr(e.args[1])})"
            if e.func == "__list_pop__":       return f"py_list_pop({self.emit_expr(e.args[0])})"

            # generic call with * and ** handling
            parts_js = []
            kwargs_obj = self._tmp("kwargs")
            have_kwargs = False
            for a in e.args:
                if isinstance(a, Starred):
                    parts_js.append(f"...py_to_array({self.emit_expr(a.value)})")
                elif isinstance(a, KwargPairs):
                    if not have_kwargs:
                        have_kwargs = True
                        self.writeln(f"const {kwargs_obj} = {{}};")
                    for k, v in a.pairs:
                        self.writeln(f"{kwargs_obj}[{repr(k)}] = {self.emit_expr(v)};")
                elif isinstance(a, KwargExp):
                    if not have_kwargs:
                        have_kwargs = True
                        self.writeln(f"const {kwargs_obj} = {{}};")
                    self.writeln(f"py_kwargs_merge({kwargs_obj}, {self.emit_expr(a.value)});")
                else:
                    parts_js.append(self.emit_expr(a))
            call_args_str = ", ".join(parts_js + ([kwargs_obj] if have_kwargs else ["undefined"]))
            return f"{e.func}({call_args_str})"

        raise NotImplementedError(f"Expr not handled: {type(e).__name__}")

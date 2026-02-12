import ast
from typing import List, Optional, Dict, Tuple
from .ir import (
    Module, Stmt, Expr,
    Assign, AssignAttr, UnpackAssign, ImportFrom, ExprStmt, If, For, While, Break, Continue, Pass,
    Block, Function, ClassDef, With, WithItem, Return, Raise, Try, ExceptHandler,
    Name, Const, Undef, BinOp, BoolOp, UnaryNot, Call, Starred, KwargPairs, KwargExp,
    Compare, CompareChain, ListLit, TupleLit, DictLit, Subscript, Slice,
    Attribute, MethodCall, New,
)

SUPPORTED_BINOPS = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.FloorDiv: "//",
    ast.Mod: "%",
}

SUPPORTED_CMPOPS = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.In: "in",
    ast.NotIn: "not in",
    ast.Is: "is",
    ast.IsNot: "is not",
}

_BUILTIN_METHODS = {
    "upper": "__str_upper__", "lower": "__str_lower__", "split": "__str_split__",
    "join": "__str_join__", "startswith": "__str_startswith__", "endswith": "__str_endswith__",
    "replace": "__str_replace__", "find": "__str_find__",
    "append": "__list_append__", "pop": "__list_pop__",
}

_SINGLE_ARG_BUILTINS = {
    "len": "__len__",
    "str": "__str__",
    "sorted": "__sorted__",
    "sum": "__sum__",
}

_VARIADIC_BUILTINS = {"min": "__min__", "max": "__max__", "zip": "__zip__"}

class _LowerCtx:
    def __init__(self, func_params: Dict[str, List[str]], class_names: set[str]):
        self.func_params = func_params
        self.class_names = class_names


def _lower_func_args(
    ctx: _LowerCtx, args: ast.arguments
) -> Tuple[List[str], List[Optional[Expr]], Optional[str], Optional[str]]:
    params = [a.arg for a in args.args]
    num_params = len(params)
    num_defaults = len(args.defaults)
    defaults: List[Optional[Expr]] = [None] * (num_params - num_defaults) + [
        _lower_expr(ctx, d) for d in args.defaults
    ]
    vararg = args.vararg.arg if args.vararg else None
    kwarg = args.kwarg.arg if args.kwarg else None
    return params, defaults, vararg, kwarg


def _lower_args(ctx: _LowerCtx, args: list[ast.expr]) -> List[Expr]:
    result: List[Expr] = []
    for a in args:
        if isinstance(a, ast.Starred):
            result.append(Starred(_lower_expr(ctx, a.value)))
        else:
            result.append(_lower_expr(ctx, a))
    return result


def lower(py_src: str) -> Module:
    tree = ast.parse(py_src)

    func_params: Dict[str, List[str]] = {}
    class_names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            func_params[node.name] = [a.arg for a in node.args.args]
        if isinstance(node, ast.ClassDef):
            class_names.add(node.name)

    ctx = _LowerCtx(func_params=func_params, class_names=class_names)
    return Module(body=[_lower_stmt(ctx, s) for s in tree.body])

def _lower_stmt(ctx: _LowerCtx, node: ast.stmt) -> Stmt:
    if isinstance(node, ast.ImportFrom):
        if node.module is None:
            raise NotImplementedError("Relative imports not supported")
        names = []
        for alias in node.names:
            if alias.asname:
                raise NotImplementedError("No aliases yet")
            names.append(alias.name)
        return ImportFrom(module=node.module, names=names)

    if isinstance(node, ast.Assign):
        if len(node.targets) != 1:
            raise NotImplementedError("Only single-target assignment supported")
        tgt = node.targets[0]

        if isinstance(tgt, ast.Name):
            return Assign(name=tgt.id, value=_lower_expr(ctx, node.value))

        if isinstance(tgt, ast.Attribute):
            return AssignAttr(obj=_lower_expr(ctx, tgt.value), attr=tgt.attr, value=_lower_expr(ctx, node.value))

        if isinstance(tgt, (ast.Tuple, ast.List)):
            elts = tgt.elts
            has_star = any(isinstance(e, ast.Starred) for e in elts)

            if has_star:
                targets: List[str] = []
                starred_index: Optional[int] = None
                starred_name: Optional[str] = None
                for i, el in enumerate(elts):
                    if isinstance(el, ast.Starred):
                        if starred_index is not None:
                            raise NotImplementedError("Only one starred target")
                        if not isinstance(el.value, ast.Name):
                            raise NotImplementedError("* target must be a simple name")
                        starred_index = i
                        starred_name = el.value.id
                        targets.append(starred_name)
                    elif isinstance(el, ast.Name):
                        targets.append(el.id)
                    else:
                        raise NotImplementedError("Only names supported in unpack with *")
                return UnpackAssign(
                    targets=targets,
                    starred_index=starred_index,
                    starred_name=starred_name,
                    value=_lower_expr(ctx, node.value),
                )

            rhs = _lower_expr(ctx, node.value)
            tmp_name = "__py_unpack_tmp"
            stmts: List[Stmt] = []
            stmts.append(Assign(name=tmp_name, value=rhs))
            for i, el in enumerate(elts):
                idx_expr = Subscript(value=Name(id=tmp_name), index=Const(i))
                if isinstance(el, ast.Name):
                    stmts.append(Assign(name=el.id, value=idx_expr))
                elif isinstance(el, ast.Attribute):
                    stmts.append(AssignAttr(obj=_lower_expr(ctx, el.value), attr=el.attr, value=idx_expr))
                else:
                    raise NotImplementedError("Only names/attributes in unpack")
            return Block(body=stmts)

        raise NotImplementedError("Unsupported assignment target")

    if isinstance(node, ast.AugAssign):
        op = SUPPORTED_BINOPS.get(type(node.op))
        if not op:
            raise NotImplementedError(f"Unsupported augmented operator: {type(node.op).__name__}")
        tgt = node.target
        if isinstance(tgt, ast.Name):
            return Assign(
                name=tgt.id,
                value=BinOp(left=Name(id=tgt.id), op=op, right=_lower_expr(ctx, node.value)),
            )
        if isinstance(tgt, ast.Attribute):
            obj = _lower_expr(ctx, tgt.value)
            return AssignAttr(
                obj=obj,
                attr=tgt.attr,
                value=BinOp(left=Attribute(value=obj, attr=tgt.attr), op=op, right=_lower_expr(ctx, node.value)),
            )
        raise NotImplementedError("Unsupported augmented assignment target")

    if isinstance(node, ast.Expr):
        return ExprStmt(expr=_lower_expr(ctx, node.value))

    if isinstance(node, ast.If):
        return If(
            test=_lower_expr(ctx, node.test),
            body=[_lower_stmt(ctx, s) for s in node.body],
            orelse=[_lower_stmt(ctx, s) for s in node.orelse],
        )

    if isinstance(node, ast.For):
        if not isinstance(node.target, ast.Name):
            raise NotImplementedError("For-loop target must be a simple name")
        it = _lower_expr(ctx, node.iter)
        return For(
            target=node.target.id,
            iter=it,
            body=[_lower_stmt(ctx, s) for s in node.body],
            orelse=[_lower_stmt(ctx, s) for s in node.orelse],
        )

    if isinstance(node, ast.While):
        return While(
            test=_lower_expr(ctx, node.test),
            body=[_lower_stmt(ctx, s) for s in node.body],
            orelse=[_lower_stmt(ctx, s) for s in node.orelse],
        )

    if isinstance(node, ast.Break): return Break()
    if isinstance(node, ast.Continue): return Continue()
    if isinstance(node, ast.Pass): return Pass()

    if isinstance(node, ast.FunctionDef):
        params, defaults, vararg, kwarg = _lower_func_args(ctx, node.args)
        return Function(
            name=node.name,
            params=params,
            body=[_lower_stmt(ctx, s) for s in node.body],
            defaults=defaults,
            vararg=vararg,
            kwarg=kwarg,
        )

    if isinstance(node, ast.ClassDef):
        methods: List[Function] = []
        for b in node.body:
            if isinstance(b, ast.FunctionDef):
                params, defaults, vararg, kwarg = _lower_func_args(ctx, b.args)
                methods.append(Function(
                    name=b.name,
                    params=params,
                    body=[_lower_stmt(ctx, s) for s in b.body],
                    defaults=defaults,
                    vararg=vararg,
                    kwarg=kwarg,
                ))
            else:
                raise NotImplementedError("Only methods supported inside class")
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            else:
                raise NotImplementedError("Only simple base names supported")
        return ClassDef(name=node.name, bases=bases, methods=methods)

    if isinstance(node, ast.With):
        items: List[WithItem] = []
        for it in node.items:
            if it.optional_vars is not None and not isinstance(it.optional_vars, ast.Name):
                raise NotImplementedError("with only supports 'as name'")
            items.append(WithItem(context_expr=_lower_expr(ctx, it.context_expr),
                                  optional_vars=(it.optional_vars.id if it.optional_vars else None)))
        return With(items=items, body=[_lower_stmt(ctx, s) for s in node.body])

    if isinstance(node, ast.Return):
        return Return(value=_lower_expr(ctx, node.value) if node.value else None)

    if isinstance(node, ast.Raise):
        if node.exc is None:
            raise NotImplementedError("raise without exception not supported in v1")
        if isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
            etype = node.exc.func.id
            msg = _lower_expr(ctx, node.exc.args[0]) if node.exc.args else None
            return Raise(exc_type=etype, message=msg)
        if isinstance(node.exc, ast.Name):
            return Raise(exc_type=node.exc.id, message=None)
        raise NotImplementedError("Only simple 'raise Name(...)' supported in v1")

    if isinstance(node, ast.Try):
        handlers = []
        for h in node.handlers:
            if h.type is None:
                handlers.append(ExceptHandler(type_name=None, varname=h.name, body=[_lower_stmt(ctx, s) for s in h.body]))
            elif isinstance(h.type, ast.Name):
                handlers.append(ExceptHandler(type_name=h.type.id, varname=h.name, body=[_lower_stmt(ctx, s) for s in h.body]))
            else:
                raise NotImplementedError("Only simple 'except Name' supported in v1")
        return Try(
            body=[_lower_stmt(ctx, s) for s in node.body],
            handlers=handlers,
            orelse=[_lower_stmt(ctx, s) for s in node.orelse],
            finalbody=[_lower_stmt(ctx, s) for s in node.finalbody],
        )

    raise NotImplementedError(f"Unsupported statement: {type(node).__name__}")

def _lower_expr(ctx: _LowerCtx, node: ast.expr) -> Expr:
    if isinstance(node, ast.Name):
        return Name(id=node.id)

    if isinstance(node, ast.Constant):
        return Const(value=node.value)

    if isinstance(node, ast.Tuple):
        return TupleLit(elts=[_lower_expr(ctx, e) for e in node.elts])

    if isinstance(node, ast.List):
        return ListLit(elts=[_lower_expr(ctx, e) for e in node.elts])

    if isinstance(node, ast.Dict):
        return DictLit(keys=[_lower_expr(ctx, k) for k in node.keys], values=[_lower_expr(ctx, v) for v in node.values])

    if isinstance(node, ast.BinOp):
        op = SUPPORTED_BINOPS.get(type(node.op))
        if not op:
            raise NotImplementedError(f"Unsupported binary operator: {type(node.op).__name__}")
        return BinOp(left=_lower_expr(ctx, node.left), op=op, right=_lower_expr(ctx, node.right))

    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            return BoolOp(op="and", values=[_lower_expr(ctx, v) for v in node.values])
        if isinstance(node.op, ast.Or):
            return BoolOp(op="or", values=[_lower_expr(ctx, v) for v in node.values])
        raise NotImplementedError("Unknown BoolOp")

    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return UnaryNot(value=_lower_expr(ctx, node.operand))
        if isinstance(node.op, ast.USub):
            return BinOp(left=Const(0), op='-', right=_lower_expr(ctx, node.operand))
        if isinstance(node.op, ast.UAdd):
            return _lower_expr(ctx, node.operand)
        raise NotImplementedError(f"Unsupported unary op: {type(node.op).__name__}")

    if isinstance(node, ast.Attribute):
        return Attribute(value=_lower_expr(ctx, node.value), attr=node.attr)

    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute):
            obj = _lower_expr(ctx, node.func.value)
            attr = node.func.attr
            if attr in _BUILTIN_METHODS:
                args = _lower_args(ctx, node.args)
                return Call(func=_BUILTIN_METHODS[attr], args=[obj] + args)
            args = _lower_args(ctx, node.args)
            return MethodCall(obj=obj, method=attr, args=args)

        if isinstance(node.func, ast.Name):
            fname = node.func.id

            if fname in _SINGLE_ARG_BUILTINS:
                if len(node.args) != 1:
                    raise NotImplementedError(f"{fname}() takes exactly one argument")
                return Call(func=_SINGLE_ARG_BUILTINS[fname], args=[_lower_expr(ctx, node.args[0])])

            if fname in _VARIADIC_BUILTINS:
                return Call(func=_VARIADIC_BUILTINS[fname], args=_lower_args(ctx, node.args))

            if fname in ctx.class_names:
                return New(class_name=fname, args=_lower_args(ctx, node.args))

            params = ctx.func_params.get(fname, [])
            final_args: List[Expr] = []
            pos_index = 0
            for a in node.args:
                if isinstance(a, ast.Starred):
                    final_args.append(Starred(_lower_expr(ctx, a.value)))
                else:
                    final_args.append(_lower_expr(ctx, a))
                    pos_index += 1
            kw_pairs: List[Tuple[str, Expr]] = []
            kw_exps: List[Expr] = []
            if node.keywords:
                for kw in node.keywords:
                    if kw.arg is None:
                        kw_exps.append(_lower_expr(ctx, kw.value))
                    else:
                        if kw.arg in params:
                            idx = params.index(kw.arg)
                            while len(final_args) <= idx:
                                final_args.append(Undef())
                            if not isinstance(final_args[idx], Undef):
                                raise NotImplementedError(f"Multiple values for argument '{kw.arg}'")
                            final_args[idx] = _lower_expr(ctx, kw.value)
                        else:
                            kw_pairs.append((kw.arg, _lower_expr(ctx, kw.value)))
            while final_args and isinstance(final_args[-1], Undef):
                final_args.pop()
            if kw_pairs:
                final_args.append(KwargPairs(pairs=kw_pairs))
            for ex in kw_exps:
                final_args.append(KwargExp(value=ex))
            return Call(func=fname, args=final_args)

    if isinstance(node, ast.Compare):
        ops = []
        for op in node.ops:
            mapped = SUPPORTED_CMPOPS.get(type(op))
            if not mapped:
                raise NotImplementedError(f"Unsupported comparison: {type(op).__name__}")
            ops.append(mapped)
        comparators = [_lower_expr(ctx, c) for c in node.comparators]
        if len(ops) > 1 and any(o in ("in", "not in", "is", "is not") for o in ops):
            raise NotImplementedError("Chained 'in/not in/is/is not' comparisons not supported")
        if len(ops) == 1:
            return Compare(left=_lower_expr(ctx, node.left), op=ops[0], right=comparators[0])
        return CompareChain(left=_lower_expr(ctx, node.left), ops=ops, comparators=comparators)

    if isinstance(node, ast.Subscript):
        sl = node.slice
        if hasattr(ast, "Index") and isinstance(sl, ast.Index):  # type: ignore[attr-defined]
            sl = sl.value  # type: ignore[attr-defined]
        if isinstance(sl, ast.Slice):
            start = _lower_expr(ctx, sl.lower) if sl.lower else None
            stop = _lower_expr(ctx, sl.upper) if sl.upper else None
            step = _lower_expr(ctx, sl.step) if sl.step else None
            return Slice(value=_lower_expr(ctx, node.value), start=start, stop=stop, step=step)
        return Subscript(value=_lower_expr(ctx, node.value), index=_lower_expr(ctx, sl))

    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(Const(v.value))
            elif isinstance(v, ast.FormattedValue):
                inner = _lower_expr(ctx, v.value)
                parts.append(Call(func="__str__", args=[inner]))
            else:
                raise NotImplementedError(f"Unsupported f-string piece: {type(v).__name__}")
        if not parts:
            return Const("")
        expr = parts[0]
        for p in parts[1:]:
            expr = BinOp(left=expr, op="+", right=p)
        return expr

    raise NotImplementedError(f"Unsupported expression: {type(node).__name__}")

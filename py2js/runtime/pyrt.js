// === Redeclare-safe global registrar ===
function __reg(name, fn) { if (!globalThis[name]) globalThis[name] = fn; return globalThis[name]; }

// ---- Exceptions ----
__reg("PyError", class PyError extends Error { constructor(pyType, message){ super(message||""); this.pyType=pyType||"Exception"; this.name=this.pyType; }});
__reg("py_raise", function (pyType, message) { throw new PyError(pyType, message); });
__reg("py_wrap_error", function (e) {
  if (e instanceof PyError) return e;
  const pe = new PyError("Exception", (e && e.message) ? e.message : String(e));
  if (e && e.stack) pe.stack = e.stack; return pe;
});
__reg("py_exc_match", function (err, typeName) { if (!err) return false; return err.pyType === typeName || typeName === "Exception"; });

// ---- Tuple helpers ----
__reg("py_tuple", function () { return { __tuple__: true, items: Array.prototype.slice.call(arguments) }; });
__reg("py_tuple_from_array", function (arr) { return { __tuple__: true, items: Array.prototype.slice.call(arr) }; });
__reg("py_is_tuple", function (x) { return !!(x && x.__tuple__ === true); });
__reg("py_tuple_items", function (t) { if (!py_is_tuple(t)) throw new PyError("TypeError", "expected tuple"); return t.items; });

// ---- kwargs merge ----
var py_kwargs_merge = globalThis.py_kwargs_merge || function (dst, src) {
  if (src == null) return;
  for (const k in src) {
    if (Object.prototype.hasOwnProperty.call(src, k)) dst[k] = src[k];
  }
};
globalThis.py_kwargs_merge = py_kwargs_merge;

// ---- Truthiness ----
__reg("py_truth", function (x) {
  if (Array.isArray(x) || typeof x === "string") return x.length !== 0;
  if (py_is_tuple(x)) return x.items.length !== 0;
  if (x === null || x === undefined) return false;
  if (typeof x === "number") return x !== 0;
  if (typeof x === "boolean") return x;
  if (typeof x === "object") return true;
  return !!x;
});

// ---- Arithmetic & operations ----
__reg("py_floor_div", function (a, b) { const q = a / b; return (q >= 0) ? Math.floor(q) : Math.ceil(q - 1e-15); });

__reg("py_add", (function(){
  function base(a, b) {
    const aIsStr = (typeof a === "string"), bIsStr = (typeof b === "string");
    const aIsNum = (typeof a === "number"), bIsNum = (typeof b === "number");
    if (aIsStr && bIsStr) return a + b;
    if (aIsNum && bIsNum) return a + b;
    if (aIsStr || bIsStr) throw new PyError("TypeError", "can only concatenate str with str");
    throw new PyError("TypeError", "unsupported operand type(s) for +");
  }
  return function(a, b){
    if (Array.isArray(a) && Array.isArray(b)) return a.concat(b);
    if (py_is_tuple(a) && py_is_tuple(b)) return py_tuple_from_array(a.items.concat(b.items));
    return base(a, b);
  };
})());

__reg("py_mul", function(a, b){
  const aNum = typeof a === "number", bNum = typeof b === "number";
  if (aNum && bNum) return a * b;
  if (typeof a === "string" && bNum) return a.repeat(b);
  if (typeof b === "string" && aNum) return b.repeat(a);
  if (Array.isArray(a) && bNum) { const out=[]; for(let i=0;i<b;i++) out.push(...a); return out; }
  if (Array.isArray(b) && aNum) { const out=[]; for(let i=0;i<a;i++) out.push(...b); return out; }
  if (py_is_tuple(a) && bNum) { const out=[]; for(let i=0;i<b;i++) out.push(...a.items); return py_tuple_from_array(out); }
  if (py_is_tuple(b) && aNum) { const out=[]; for(let i=0;i<a;i++) out.push(...b.items); return py_tuple_from_array(out); }
  throw new PyError("TypeError", "unsupported operand type(s) for *");
});

// ---- Equality ----
__reg("py_eq", function (a, b) {
  if (a === b) return true;
  if (a === null || b === null) return false;
  if (py_is_tuple(a) || py_is_tuple(b)) {
    if (!(py_is_tuple(a) && py_is_tuple(b))) return false;
    const A = a.items, B = b.items;
    if (A.length !== B.length) return false;
    for (let i = 0; i < A.length; i++) if (!py_eq(A[i], B[i])) return false;
    return true;
  }
  const ta = typeof a, tb = typeof b;
  if (ta !== tb) return false;
  if (ta === "string" || ta === "number" || ta === "boolean") return a === b;
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) if (!py_eq(a[i], b[i])) return false;
    return true;
  }
  if (ta === "object") {
    const ak = Object.keys(a), bk = Object.keys(b);
    if (ak.length !== bk.length) return false;
    ak.sort(); bk.sort();
    for (let i = 0; i < ak.length; i++) if (ak[i] !== bk[i]) return false;
    for (let i = 0; i < ak.length; i++) if (!py_eq(a[ak[i]], b[ak[i]])) return false;
    return true;
  }
  return false;
});

// ---- Length / indexing / membership / iteration ----
__reg("py_len", function (x) {
  if (Array.isArray(x)) return x.length;
  if (py_is_tuple(x)) return x.items.length;
  if (typeof x === "string") return x.length;
  if (x && typeof x === "object") return Object.keys(x).length;
  throw new Error("len() unsupported for this type in v1");
});

__reg("py_getitem", function (obj, key) {
  if (Array.isArray(obj) || typeof obj === "string" || py_is_tuple(obj)) {
    const arr = py_is_tuple(obj) ? obj.items : obj;
    const n = arr.length;
    if (typeof key !== "number") throw new Error("TypeError: indices must be integers");
    let idx = key; if (idx < 0) idx = n + idx;
    if (idx < 0 || idx >= n) throw new Error("IndexError");
    return arr[idx];
  }
  if (obj && typeof obj === "object") {
    const k = String(key);
    if (!(k in obj)) throw new Error("KeyError: " + k);
    return obj[k];
  }
  throw new Error("TypeError: object is not subscriptable");
});

__reg("py_in", function (val, container) {
  if (Array.isArray(container)) {
    for (let i = 0; i < container.length; i++) if (py_eq(container[i], val)) return true;
    return false;
  }
  if (py_is_tuple(container)) {
    const A = container.items;
    for (let i = 0; i < A.length; i++) if (py_eq(A[i], val)) return true;
    return false;
  }
  if (typeof container === "string") {
    if (typeof val !== "string") return false;
    return container.indexOf(val) !== -1;
  }
  if (container && typeof container === "object") {
    const k = String(val);
    return Object.prototype.hasOwnProperty.call(container, k);
  }
  return false;
});

__reg("py_iter", function (container) {
  if (Array.isArray(container)) return container;
  if (py_is_tuple(container)) return container.items;
  if (typeof container === "string") return container.split("");
  if (container && typeof container === "object") return Object.keys(container);
  throw new Error("TypeError: object is not iterable");
});

__reg("py_to_array", function (x) {
  if (Array.isArray(x)) return x;
  if (py_is_tuple(x)) return x.items.slice();
  if (typeof x === "string") return x.split("");
  throw new PyError("TypeError", "can only unpack iterable (list/tuple/str) with *");
});

// ---- range ----
__reg("py_range", function (start, stop, step) {
  if (stop === undefined) { stop = start; start = 0; }
  if (step === undefined) step = 1;
  if (step === 0) throw new Error("ValueError: range() arg 3 must not be zero");
  const out = [];
  if (step > 0) for (let i = start; i < stop; i += step) out.push(i);
  else for (let i = start; i > stop; i += step) out.push(i);
  return out;
});

// ---- slicing ----
__reg("py_slice", function (seq, start, stop, step) {
  let s = (step == null) ? 1 : Number(step);
  if (Number.isNaN(s)) throw new Error("TypeError: slice step must be a number");
  if (s === 0) throw new Error("ValueError: slice step cannot be zero");
  const arr = py_is_tuple(seq) ? seq.items
            : (typeof seq === "string" ? seq.split("") : (Array.isArray(seq) ? seq : null));
  if (!arr) throw new Error("TypeError: object is not subscriptable by slice");
  const res = _slice_array_normalized(arr, start, stop, s);
  if (typeof seq === "string") return res.join("");
  if (py_is_tuple(seq)) return py_tuple_from_array(res);
  return res;
});
__reg("_slice_array_normalized", function (arr, start, stop, step) {
  const n = arr.length;
  const hasStart = !(start == null);
  const hasStop  = !(stop  == null);
  let lo = step > 0 ? (hasStart ? Number(start) : 0)     : (hasStart ? Number(start) : n - 1);
  let hi = step > 0 ? (hasStop  ? Number(stop)  : n)     : (hasStop  ? Number(stop)  : -1);
  if (Number.isNaN(lo) || Number.isNaN(hi)) throw new Error("TypeError: slice indices must be integers or None");
  if (hasStart && lo < 0) lo += n;
  if (hasStop  && hi < 0) hi += n;
  if (lo < -1) lo = -1; if (lo > n) lo = n;
  if (hi < -1) hi = -1; if (hi > n) hi = n;
  const out = [];
  if (step > 0) { for (let i = lo; i < hi; i += step) if (i >= 0 && i < n) out.push(arr[i]); }
  else { for (let i = lo; i > hi; i += step) if (i >= 0 && i < n) out.push(arr[i]); }
  return out;
});

// ---- list methods ----
__reg("py_list_append", function(lst, x){ if (!Array.isArray(lst)) throw new PyError("TypeError", "append() on non-list"); lst.push(x); return null; });
__reg("py_list_pop", function(lst){ if (!Array.isArray(lst)) throw new PyError("TypeError", "pop() on non-list"); if (lst.length === 0) throw new PyError("IndexError", "pop from empty list"); return lst.pop(); });

// ---- string methods ----
__reg("py_str_upper", function (s) { if (typeof s !== "string") throw new PyError("TypeError", "upper() arg must be str"); return s.toUpperCase(); });
__reg("py_str_lower", function (s) { if (typeof s !== "string") throw new PyError("TypeError", "lower() arg must be str"); return s.toLowerCase(); });
__reg("py_str_split", function (s, sep) {
  if (typeof s !== "string") throw new PyError("TypeError", "split() arg must be str");
  if (sep == null) { const parts = s.trim().split(/\s+/); if (parts.length === 1 && parts[0] === "") return []; return parts; }
  if (typeof sep !== "string") throw new PyError("TypeError", "sep must be str");
  return s.split(sep);
});
__reg("py_str_join", function(sep, iterable){ if (typeof sep !== "string") throw new PyError("TypeError","sep must be str"); const arr = py_to_array(iterable); return arr.map(x => (typeof x === "string" ? x : py_str(x))).join(sep); });
__reg("py_str_startswith", function(s, prefix){ if (typeof s !== "string" || typeof prefix !== "string") throw new PyError("TypeError","startswith expects str"); return s.startsWith(prefix); });
__reg("py_str_endswith", function(s, suffix){ if (typeof s !== "string" || typeof suffix !== "string") throw new PyError("TypeError","endswith expects str"); return s.endsWith(suffix); });
__reg("py_str_replace", function(s, oldv, newv){ if (typeof s !== "string" || typeof oldv !== "string" || typeof newv !== "string") throw new PyError("TypeError","replace expects str"); return s.split(oldv).join(newv); });
__reg("py_str_find", function(s, sub){ if (typeof s !== "string" || typeof sub !== "string") throw new PyError("TypeError","find expects str"); return s.indexOf(sub); });

// ---- with-statement helpers ----
__reg("py_with_enter", function(mgr){ if (!mgr || typeof mgr.__enter__ !== "function" || typeof mgr.__exit__ !== "function") throw new PyError("TypeError","context manager requires __enter__ and __exit__"); return mgr.__enter__(); });
__reg("py_with_exit", function(mgr){ try { mgr.__exit__(null, null, null); } catch(e) { throw e; } });

// ---- super() minimal support -----
__reg("py_super", function (self, base) {
  const proxy = {}; const proto = base && base.prototype;
  if (!proto) return proxy;
  for (const k of Object.getOwnPropertyNames(proto)) {
    if (k === "constructor") continue;
    if (typeof proto[k] === "function") proxy[k] = function(){ return proto[k].apply(self, arguments); }
  }
  return proxy;
});

// ---- math shim (extended) ----
__reg("py_math_floor", Math.floor);
__reg("py_math_ceil",  Math.ceil);
__reg("py_math_sqrt",  Math.sqrt);
__reg("py_math_pow",   Math.pow);
__reg("py_math_abs",   Math.abs);

// ---- stringify & print (with __repr__ support) ----
__reg("py_str", function (x) {
  if (x instanceof PyError) return x.pyType + ": " + (x.message || "");
  if (x === true) return "True";
  if (x === false) return "False";
  if (x === null || x === undefined) return "None";
  if (py_is_tuple(x)) {
    const arr = x.items.map(py_str);
    return "(" + (arr.length === 1 ? arr[0] + "," : arr.join(", ")) + ")";
  }
  if (Array.isArray(x)) return "[" + x.map(py_str).join(", ") + "]";
  if (typeof x === "object") {
    if (typeof x.__repr__ === "function") {
      try { return x.__repr__(); } catch (_) {}
    }
    const parts = [];
    for (const k in x) if (Object.prototype.hasOwnProperty.call(x, k)) parts.push(k + ": " + py_str(x[k]));
    return "{" + parts.join(", ") + "}";
  }
  return String(x);
});
__reg("py_print", function () { const out = []; for (let i = 0; i < arguments.length; i++) out.push(py_str(arguments[i])); console.log(out.join(" ")); });

from py2js.cli import transpile


def test_smoke():
    py = "a = 5 // 2\nprint(a)\n"
    out = transpile(py)
    assert "py_floor_div(5, 2)" in out
    assert "console.log(a)" in out
    assert "let a =" in out


def js_contains(js, s):
    assert s in js, f"Missing: {s}"


def test_dict_in_len():
    py = 'd={"a":1,"b":2}\nprint(len(d),"a" in d,"z" in d)\n'
    out = transpile(py)
    js_contains(out, "py_len")
    js_contains(out, "py_in")
    js_contains(out, "({\"a\": 1, \"b\": 2})")


def test_function_return():
    py = 'def add(x,y):\n    return x+y\nprint(add(2,3))\n'
    out = transpile(py)
    js_contains(out, "function add(x, y)")
    js_contains(out, "console.log(add(2, 3))")

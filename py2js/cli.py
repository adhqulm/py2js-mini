import argparse
from pathlib import Path
from .lowering import lower
from .emit_js import Emitter


def transpile(py_src: str) -> str:
    mod = lower(py_src)
    js_body = Emitter().emit_module(mod)
    runtime_path = Path(__file__).parent / "runtime" / "pyrt.js"
    runtime = runtime_path.read_text(encoding="utf-8")
    # bundle runtime + body
    return runtime + "\n\n" + js_body


def main():
    ap = argparse.ArgumentParser(
        description="Transpile a tiny Python subset to JavaScript.")
    ap.add_argument("input", help="Input .py file")
    ap.add_argument("-o", "--out", help="Output .js file (defaults to stdout)")
    args = ap.parse_args()

    src = Path(args.input).read_text(encoding="utf-8")
    out_js = transpile(src)

    if args.out:
        Path(args.out).write_text(out_js, encoding="utf-8")
    else:
        print(out_js)


if __name__ == "__main__":
    main()

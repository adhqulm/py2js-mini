# flake8: noqa

import subprocess as sp, sys, pathlib

ROOT   = pathlib.Path(__file__).resolve().parents[1]
EX     = ROOT / "examples"
GOLDEN = ROOT / "tests" / "golden"
OUTJS  = ROOT / "out.js"

CASES = [p.name for p in EX.glob("*.py")]

def run(cmd):
  p = sp.run(cmd, stdout=sp.PIPE, stderr=sp.STDOUT, text=True, cwd=ROOT)
  return p.returncode, p.stdout

def norm(s: str) -> str:
  return "\n".join(line.rstrip() for line in s.replace("\r\n","\n").replace("\r","\n").split("\n")).strip()

def main():
  fails = []
  for ex in sorted(CASES):
    code, _ = run([sys.executable, "-m", "py2js.cli", str(EX/ex), "-o", str(OUTJS)])
    if code != 0:
      print(f"TRANSPILE FAIL {ex}"); sys.exit(code)
    code, out = run(["node", str(OUTJS)])
    got = norm(out)
    exp = norm((GOLDEN / ex.replace(".py",".out")).read_text(encoding="utf-8"))
    if got != exp:
      print(f"FAIL {ex}"); fails.append((ex, exp, got))
    else:
      print(f"PASS {ex}")
  if fails:
    print("\n--- FAIL DETAILS ---")
    for ex, exp, got in fails:
      print(f"\n[{ex}]"); print("Expected:\n"+exp); print("Got:\n"+got)
    sys.exit(1)

if __name__ == "__main__":
  main()

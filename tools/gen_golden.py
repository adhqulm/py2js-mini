# flake8: noqa

import subprocess as sp, sys, pathlib

ROOT   = pathlib.Path(__file__).resolve().parents[1]
EX     = ROOT / "examples"
GOLDEN = ROOT / "tests" / "golden"
OUTJS  = ROOT / "out.js"

CASES = [p.name for p in EX.glob("*.py")]

def run(cmd):
  p = sp.run(cmd, stdout=sp.PIPE, stderr=sp.STDOUT, text=True, cwd=ROOT)
  if p.returncode != 0:
    print(p.stdout); sys.exit(p.returncode)
  return p.stdout

def norm(s: str) -> str:
  return "\n".join(line.rstrip() for line in s.replace("\r\n","\n").replace("\r","\n").split("\n")).strip()

def main():
  GOLDEN.mkdir(parents=True, exist_ok=True)
  for ex in sorted(CASES):
    print(f"[gen] {ex}")
    run([sys.executable, "-m", "py2js.cli", str(EX/ex), "-o", str(OUTJS)])
    out = run(["node", str(OUTJS)])
    (GOLDEN / (ex.replace(".py", ".out"))).write_text(norm(out) + "\n", encoding="utf-8")

if __name__ == "__main__":
  main()

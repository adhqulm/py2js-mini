$ErrorActionPreference = "Stop"
$examplesDir = Join-Path $PSScriptRoot "examples"
$outFile = Join-Path $PSScriptRoot "out.js"

function Normalize([string]$s) {
  if ($null -eq $s) { return "" }
  $s = $s -replace "`r`n", "`n" -replace "`r", "`n"
  $lines = $s -split "`n" | ForEach-Object { $_.TrimEnd() }
  $joined = ($lines -join "`n").Trim()
  return $joined
}

$expected = @{
  "hello.py" = @"
ok 2
"@;
  "for_list.py" = @"
4 10 40
ok 2
0
1
2
5
3
1
"@;
  "dicts_funcs.py" = @"
2 True False
1
True False
a 1
b 2
15
"@;
  "booleans.py" = @"
True False None [1, 2, True] {x: False}
"@;
  "exc_demo.py" = @"
5
caught ValueError: division by zero
finally runs
key error ok
"@;
  "chains.py" = @"
True
False
"@;
  "slices.py" = @"
[1, 2, 3]
[0, 1, 2]
[3, 4, 5]
[0, 2, 4]
[5, 4, 3, 2, 1, 0]
bcd
fedcba
"@;
  "while_demo.py" = @"
loop 1
loop 2
w 0
w 1
w 2
while-else ran
"@;
  "strings_demo.py" = @"
ab
10 apples
[1, True]
5
"@;
  "defaults_demo.py" = @"
Hello, world
Hello, Alice
Hello, Bob
Hello, Bob
Hello, Bob
"@;
  "for_else_demo.py" = @"
loop 0
loop 1
loop 2
w 0
w 1
w 2
for-else ran
"@;
  "kwargs_demo.py" = @"
paint red 1 1
paint blue 5 1
paint green 1 3
paint yellow 2 4
"@;
  "bool_ops_demo.py" = @"
say 0
0
say 1
say 2
2
say
say ok
ok
True False False
"@;
  "eq_demo.py" = @"
True False
True
True
True
"@;
  "str_methods_demo.py" = @"
HELLO,  WORLD
hello,  world
[Hello, world]
[a, b, c] done.
"@;
  "varargs_demo.py" = @"
a= 1 rest= ()
a= 1 rest= (2, 3)
a= 4 rest= (5,)
a= 9 rest= (4, 5, 10)
"@;
  "tuples_demo.py" = @"
(1, 2, 3)
1 3
(2, 3)
True True
(1,)
False
"@;
  "classes_demo.py" = @"
4 6
0 0
"@;
  "classes_v2_demo.py" = @"
7 10
17
"@;
  "kwargs2_demo.py" = @"
paint red 1 1 {}
paint blue 3 {height: 5} {}
paint green 2 {tag: ui, alpha: 0.5} {}
"@;
  "unpack_demo.py" = @"
1 2
3 4 5
a b c
0 [1, 2, 3] 4
"@;
  "unpack_named_demo.py" = @"
1 [2, 3, 4] 5
"@;
  "repr_demo.py" = @"
<Point 2,3>
"@;
  "math_demo.py" = @"
3 4
4
32
42
"@;
  "todo_demo.py" = @"
0 buy milk
1 walk dog
"@;
  "lists_ops_demo.py" = @"
[1, 2, 3]
[9, 9, 9]
[7, 8, 7, 8]
[1, 2, 3]
3
[1, 2]
"@;
  "str_extras_demo.py" = @"
a,b,c
True True
_br_ c_d_br_
1
"@;
  "imports_demo.py" = @"
3 4
"@;
  "with_demo.py" = @"
42
[enter, exit]
"@;
}

$examples = @(
  "hello.py","for_list.py","dicts_funcs.py","booleans.py","exc_demo.py","chains.py","slices.py",
  "while_demo.py","strings_demo.py","defaults_demo.py","for_else_demo.py","kwargs_demo.py",
  "bool_ops_demo.py","eq_demo.py","str_methods_demo.py","varargs_demo.py","tuples_demo.py",
  "classes_demo.py","classes_v2_demo.py","kwargs2_demo.py","unpack_demo.py","unpack_named_demo.py",
  "repr_demo.py","math_demo.py","todo_demo.py","lists_ops_demo.py","str_extras_demo.py",
  "imports_demo.py","with_demo.py"
)

$passed = 0; $failed = 0; $failDetails = @()

foreach ($ex in $examples) {
  Write-Host "`n==== $ex ====" -ForegroundColor Cyan
  $src = Join-Path $examplesDir $ex

  python -m py2js.cli $src -o $outFile | Out-Null

  $raw = & node $outFile 2>&1
  if ($raw -is [Array]) { $raw = ($raw -join "`n") }

  Write-Output $raw

  $got = Normalize $raw
  if ($expected.ContainsKey($ex)) {
    $exp = Normalize $expected[$ex]
    if ($exp -eq $got) {
      Write-Host "PASS" -ForegroundColor Green
      $passed++
    } else {
      Write-Host "FAIL" -ForegroundColor Red
      $failed++
      $failDetails += @{ Example=$ex; Expected=$exp; Got=$got }
    }
  } else {
    Write-Host "WARN: No expected output registered for $ex" -ForegroundColor Yellow
  }
}

Write-Host "`n======================" -ForegroundColor DarkCyan
Write-Host " Passed: $passed" -ForegroundColor Green
Write-Host " Failed: $failed" -ForegroundColor Red
Write-Host "======================" -ForegroundColor DarkCyan

if ($failed -gt 0) {
  Write-Host "`n--- FAIL DETAILS ---" -ForegroundColor Red
  foreach ($f in $failDetails) {
    Write-Host "`n[$($f.Example)]" -ForegroundColor Red
    Write-Host "Expected:" -ForegroundColor DarkGray
    Write-Host $f.Expected
    Write-Host "Got:" -ForegroundColor DarkGray
    Write-Host $f.Got
  }
  exit 1
}

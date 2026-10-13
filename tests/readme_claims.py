#!/usr/bin/env python3
"""核验 README 里的声称是否与项目真实行为一致。

README 的要求是「必须与项目真实功能一致」。本脚本把 README 当作一份待验证的
声明集合：路径存在性、命令可执行性、数字准确性、退出码、语法细节。
任何一条对不上就报出来，退出码非 0。

只依赖标准库。脚本从自身位置推导项目根，因此可以在任意工作目录下运行。
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

PKG = Path(__file__).resolve().parents[1]
PY = sys.executable

README = (PKG / "README.md").read_text(encoding="utf-8")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))


def run(args, cwd=None):
    return subprocess.run([PY] + [str(a) for a in args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=str(cwd or PKG))


# ───────────────────── 1. README 提到的路径是否都存在 ─────────────────────
print("=" * 68)
print("1. 路径存在性")
print("=" * 68)

paths = set(re.findall(r"`([A-Za-z0-9_][A-Za-z0-9_./\-]*\.(?:py|md|json|txt|yaml|html|cjs|jsonl))`", README))
paths |= set(re.findall(r"\((?:\./)?((?:scripts|assets|references|tests|examples|validation|docs|agents)/[A-Za-z0-9_./\-]+)\)", README))
paths |= {"scripts", "assets", "references", "tests", "validation", "docs", "examples"}
paths |= set(re.findall(r"python\s+(scripts/[A-Za-z0-9_./\-]+\.py)", README))
paths |= set(re.findall(r"node\s+(tests/[A-Za-z0-9_./\-]+\.cjs)", README))

missing = []
checked = 0
# README 里出现的「用户自己生成的产物」名，不必存在于交付包中
GENERATED = {
    "demo.html", "spec.json", "spec.flow-index.json", "spec.verification.jsonl",
    "probe.json", "review.json", "reviews.json", "report.html", "report-static.html",
    "source.md", "browser-check",
}
SEARCH_DIRS = ("scripts", "tests", "assets", "references", "examples/full-pipeline",
               "validation", "docs", "agents")

for p in sorted(paths):
    if p.startswith("http"):
        continue
    checked += 1
    if "/" in p:
        if not (PKG / p).exists():
            missing.append(p)
        continue
    if (PKG / p).exists():
        continue
    if any((PKG / d / p).exists() for d in SEARCH_DIRS):
        continue
    if p in GENERATED:
        continue
    missing.append(p)

check(f"README 提到的 {checked} 条路径全部存在（或为说明性产物名）",
      not missing, f"缺失: {missing}")

# ───────────────────── 2. 帮助命令可执行 ─────────────────────
print("\n2. 帮助命令可执行")
for s in ("flow_plan", "lossy_perturb", "render_report", "anchor_verify", "schedule"):
    r = run([f"scripts/{s}.py", "--help"])
    check(f"python scripts/{s}.py --help 可运行", r.returncode == 0, f"rc={r.returncode}")

# ───────────────────── 3. 快速体验两条命令 ─────────────────────
print("\n3. 快速体验命令")
tmp = tempfile.mkdtemp(prefix="readme-")
work = Path(tmp) / "pkg"
shutil.copytree(PKG, work)

r1 = run(["scripts/anchor_verify.py", "assets/worked_example_https.json",
          "assets/worked_example_https_source.md", "--log", "--write-back"], cwd=work)
check("快速体验①核验退出码为 0", r1.returncode == 0, f"rc={r1.returncode}")
try:
    d = json.loads(r1.stdout)
    check("核验输出 coverage == 1.0", d.get("coverage") == 1.0, str(d.get("coverage")))
    check("核验输出 total == 10", d.get("total") == 10, str(d.get("total")))
    check("核验输出 verified == 10", d.get("verified") == 10, str(d.get("verified")))
    gates = d.get("gates", {})
    check("四道 gates 全为 true", all(gates.get(k) for k in
          ("source_readable", "at_least_one", "coverage_90", "zero_failed")), str(gates))
except Exception as e:
    check("核验输出可解析", False, str(e))

r2 = run(["scripts/render_report.py", "assets/worked_example_https.json",
          "--out", "demo.html"], cwd=work)
check("快速体验②渲染退出码为 0", r2.returncode == 0, f"rc={r2.returncode}")
demo = work / "demo.html"

if demo.exists():
    size = demo.stat().st_size
    check("README 声称 demo.html 为 25,334 字节", size == 25334, f"实得 {size}")
    html = demo.read_text(encoding="utf-8")
    ext = re.findall(r'(?:src|href)="https?://', html)
    check("README 声称外部 http(s) 引用为 0", not ext, f"实得 {len(ext)}")

# ───────────────────── 4. 退出码 ─────────────────────
print("\n4. 退出码")
bad = Path(tmp) / "bad.json"
bad.write_text(json.dumps({"version": "1.0", "topic": "x"}), encoding="utf-8")
check("退出码 2（结构不合规）",
      run(["scripts/render_report.py", bad, "--dry-run"], cwd=work).returncode == 2)

good_src = (work / "assets/html_template.html").read_text(encoding="utf-8")
tpl_miss = Path(tmp) / "miss.html"
tpl_miss.write_text(good_src.replace("@@SOURCES@@", ""), encoding="utf-8")
check("退出码 3（模板缺占位符，真实渲染）",
      run(["scripts/render_report.py", "assets/worked_example_https.json",
           "--template", tpl_miss, "--out", Path(tmp) / "o.html"], cwd=work).returncode == 3)

tpl_extra = Path(tmp) / "extra.html"
tpl_extra.write_text(good_src.replace("</body>", "@@NOT_REAL@@</body>"), encoding="utf-8")
check("退出码 3（模板多出占位符）",
      run(["scripts/render_report.py", "assets/worked_example_https.json",
           "--template", tpl_extra, "--out", Path(tmp) / "o2.html"], cwd=work).returncode == 3)

check("README 声称 dry-run 不会返回 3（返回 0）",
      run(["scripts/render_report.py", "assets/worked_example_https.json",
           "--template", tpl_miss, "--dry-run"], cwd=work).returncode == 0)

spec = json.loads((work / "assets/worked_example_https.json").read_text(encoding="utf-8"))
for fr in spec.get("frames", []):
    for cl in fr.get("claims", []):
        if isinstance(cl, dict) and cl.get("anchor"):
            cl["anchor"] = "源材料里绝对不存在的编造引句QQZZ"
            break
    else:
        continue
    break
fab = Path(tmp) / "fab.json"
fab.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
check("退出码 10（证据门未通过）",
      run(["scripts/anchor_verify.py", fab, "assets/worked_example_https_source.md"],
          cwd=work).returncode == 10)

# ───────────────────── 5. README 引用的数字 ─────────────────────
print("\n5. 数字准确性")

# 12 个占位符
tpl = (PKG / "assets/html_template.html").read_text(encoding="utf-8")
ph = set(re.findall(r"@@([A-Z_]+)@@", tpl))
check("README 声称模板占位符为 12 个", len(ph) == 12, f"实得 {len(ph)}")
check("README 声称占位符语法为 @@NAME@@", bool(ph))

# SHA256SUMS 条目数：README 自己的声称从 README 里解析，避免把数字写死在本脚本中
man = json.loads((PKG / "SHA256SUMS.json").read_text(encoding="utf-8"))
claimed = set(re.findall(r"(\d+)\s*个文件", README))
check("README 关于清单文件数的声称前后一致",
      len(claimed) == 1, f"README 中出现 {sorted(claimed)}")
check("README 声称的清单文件数与被核验清单一致",
      claimed == {str(len(man))}, f"README 声称 {sorted(claimed)}，清单实有 {len(man)}")
check("README 声称 MIT 许可且 LICENSE 文件存在",
      "MIT" in README and (PKG / "LICENSE").exists())
check("LICENSE 版权行含 2026 与署名",
      bool(re.search(r"Copyright \(c\) 2026 \S+", (PKG / "LICENSE").read_text(encoding="utf-8"))))

# 示例 spec 结构
check("README 声称知识帧 4 个", len(spec.get("frames", [])) == 4, str(len(spec.get("frames", []))))
check("README 声称来源锚点 5 条", len(spec.get("sources", [])) == 5, str(len(spec.get("sources", []))))
check("README 声称有损探测 1 题", len(spec.get("probes", [])) == 1, str(len(spec.get("probes", []))))
check("README 声称复述练习区存在（own_words）", "own_words" in spec)

# examples/full-pipeline 文件与大小
fp = PKG / "examples/full-pipeline"
for fn, size in (("report.html", 25371), ("report-static.html", 21765)):
    p = fp / fn
    ok = p.exists() and p.stat().st_size == size
    check(f"README 声称 {fn} 为 {size:,} 字节", ok,
          f"实得 {p.stat().st_size if p.exists() else '缺失'}")

for fn in ("spec.json", "spec.flow-index.json", "probe.json",
           "spec.verification.jsonl", "reviews.json"):
    check(f"README 声称 examples/full-pipeline/{fn} 存在", (fp / fn).exists())

# references 六份
refs = sorted(p.name for p in (PKG / "references").iterdir())
check("README 声称 references 有 6 份文件", len(refs) == 6, f"实得 {len(refs)}: {refs}")

# scripts 数量
sc = sorted(p.name for p in (PKG / "scripts").iterdir() if p.name.endswith(".py"))
check("README 声称 scripts 为五个核心脚本 + common.py", len(sc) == 6, f"实得 {sc}")

# ───────────────────── 6. 依赖与版本声称 ─────────────────────
print("\n6. 依赖声称")

th = (PKG / "requirements-optional.txt").read_text(encoding="utf-8")
check("README 声称可选依赖为 pypdf>=5,<7", "pypdf>=5,<7" in th, th.strip().splitlines()[-1])

imports = set()
for fn in sc:
    src = (PKG / "scripts" / fn).read_text(encoding="utf-8")
    imports |= set(re.findall(r"^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)", src, re.M))
STDLIB_OK = {"argparse", "collections", "datetime", "hashlib", "html", "json", "os",
             "pathlib", "random", "re", "sys", "tempfile", "unicodedata", "common"}
external = sorted(imports - STDLIB_OK)
check("README 声称核心脚本只用标准库", set(external) <= {"pypdf"},
      f"非标准库: {external}")

# ───────────────────── 7. CLI 细节 ─────────────────────
print("\n7. CLI 细节")

r = run(["scripts/schedule.py", "plan", "--help"])
check("schedule.py plan 支持 --intervals", "--intervals" in r.stdout)
r = run(["scripts/flow_plan.py", "assets/worked_example_https_source.md",
         "--topic", "T", "-o", "-"], cwd=work)
try:
    d = json.loads(r.stdout)
    check("README 声称 flow_plan -o - 输出 {spec,index}", set(d) == {"spec", "index"}, str(set(d)))
except Exception as e:
    check("flow_plan -o - 输出可解析", False, str(e))

r = run(["scripts/flow_plan.py", "assets/worked_example_https_source.md",
         "--topic", "T", "-o", Path(tmp) / "s.json"], cwd=work)
check("README 声称骨架 status 提示不可直接渲染", "不可直接渲染" in r.stdout, r.stdout.strip()[:80])

# --log 默认路径
specp = work / "assets/worked_example_https.json"
run(["scripts/anchor_verify.py", specp, work / "assets/worked_example_https_source.md", "--log"], cwd=work)
check("README 声称 --log 默认写入 <spec>.verification.jsonl",
      specp.with_suffix(".verification.jsonl").exists())

# ───────────────────── 8. 测试数量（运行，耗时较长） ─────────────────────
print("\n8. 测试数量（运行，耗时较长）")
r = run(["tests/regression_suite.py"], cwd=work)
m = re.search(r"Ran (\d+) tests", r.stdout + r.stderr)
check("README 声称核心回归 31 项", bool(m) and m.group(1) == "31", f"实得 {m.group(1) if m else '?'}")
check("核心回归退出码 0", r.returncode == 0, f"rc={r.returncode}")

r = run(["tests/extended_suite.py"], cwd=work)
m = re.search(r"Ran (\d+) tests", r.stdout + r.stderr)
check("README 声称扩展回归 16 项", bool(m) and m.group(1) == "16", f"实得 {m.group(1) if m else '?'}")

check("README 已收录本核验脚本（tests/readme_claims.py）",
      "tests/readme_claims.py" in README)

# ───────────────────── 汇总 ─────────────────────
print("\n" + "=" * 68)
print("逐条结果")
print("=" * 68)
for n, ok, d in results:
    print(f"  {'OK  ' if ok else 'FAIL'} {n}" + (f"  — {d}" if d and not ok else ""))

print("\n" + "=" * 68)
passed = [r_ for r_ in results if r_[1]]
failed = [r_ for r_ in results if not r_[1]]
print(f"通过 {len(passed)} 项 / 失败 {len(failed)} 项")
if failed:
    print("\n失败项：")
    for n, _, d in failed:
        print(f"  FAIL {n}" + (f"  — {d}" if d else ""))
print("=" * 68)
shutil.rmtree(tmp, ignore_errors=True)
sys.exit(1 if failed else 0)

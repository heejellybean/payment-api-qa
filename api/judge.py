"""newman 결과 판정. 검증이 없는 요청, 요청 에러, 스크립트 오류도 실패로 센다."""
import argparse
import html
import json
import sys
from datetime import datetime, timedelta, timezone


def judge(result):
    run = result.get("run", {})
    executions = run.get("executions", [])

    script_errors = {}
    for f in run.get("failures", []):
        err = f.get("error", {})
        if err.get("name") == "AssertionError":
            continue
        ref = (f.get("cursor") or {}).get("ref")
        script_errors.setdefault(ref, []).append(f"{err.get('name', 'Error')}: {err.get('message', '')}")

    rows = []
    for ex in executions:
        name = ex.get("item", {}).get("name", "(이름 없음)")
        ref = (ex.get("cursor") or {}).get("ref")
        code = (ex.get("response") or {}).get("code")
        assertions = ex.get("assertions") or []
        problems = []

        if ex.get("requestError"):
            problems.append("요청 에러: " + str(ex["requestError"].get("message", ex["requestError"])))
        if not assertions:
            problems.append("검증 없음 (pm.test가 실행되지 않음)")
        for a in assertions:
            if a.get("error"):
                problems.append(f"{a.get('assertion')}: {a['error'].get('message', '')}")
        problems.extend(script_errors.get(ref, []))

        rows.append({
            "name": name,
            "code": code,
            "tests": len(assertions),
            "passed": sum(1 for a in assertions if not a.get("error")),
            "checks": [(a.get("assertion", ""), not a.get("error")) for a in assertions],
            "problems": problems,
        })
    return rows


def to_markdown(rows):
    total = len(rows)
    failed = [r for r in rows if r["problems"]]
    tests = sum(r["tests"] for r in rows)
    passed_tests = sum(r["passed"] for r in rows)
    status = "✅ 전체 통과" if not failed and total else "❌ 실패 있음"

    lines = [
        "## Toss Payments API 테스트 결과",
        "",
        f"**{status}** / 요청 {total}건 중 실패 {len(failed)}건 / 검증 {tests}개 중 통과 {passed_tests}개",
        "",
        "| 요청 | HTTP | 검증 | 결과 |",
        "|---|---|---|---|",
    ]
    for r in rows:
        mark = "❌" if r["problems"] else "✅"
        lines.append(f"| {r['name']} | {r['code'] or '-'} | {r['passed']}/{r['tests']} | {mark} |")
    if failed:
        lines += ["", "### 실패 상세", ""]
        for r in failed:
            lines.append(f"- **{r['name']}**")
            lines += [f"  - {p}" for p in r["problems"]]
    return "\n".join(lines) + "\n"


def to_html(rows, started_ms):
    failed = [r for r in rows if r["problems"]]
    passed = [r for r in rows if not r["problems"]]
    tests = sum(r["tests"] for r in rows)
    passed_tests = sum(r["passed"] for r in rows)
    kst = timezone(timedelta(hours=9))
    started = datetime.fromtimestamp(started_ms / 1000, kst).strftime("%Y-%m-%d %H:%M KST") if started_ms else "-"
    e = html.escape

    def table(items):
        if not items:
            return "<p class='meta'>해당 요청 없음</p>"
        trs = []
        for r in items:
            checks = "<br>".join(("" if ok else "❌ ") + e(name) for name, ok in r["checks"]) or "-"
            problems = "".join(f"<div class='err'>{e(p)}</div>" for p in r["problems"])
            trs.append(f"<tr><td>{e(r['name'])}</td><td>{r['code'] or '-'}</td><td>{checks}{problems}</td></tr>")
        return "<table><tr><th>요청</th><th>HTTP</th><th>검증 항목</th></tr>" + "".join(trs) + "</table>"

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Toss Payments API 테스트 결과</title>
<style>
body {{ font-family: -apple-system, "Apple SD Gothic Neo", sans-serif; margin: 24px auto; max-width: 960px; padding: 0 16px; color: #222; }}
.meta {{ color: #666; font-size: 13px; }}
.tabs button {{ border: 1px solid #ccc; background: #fff; padding: 8px 16px; font-size: 14px; cursor: pointer; border-radius: 6px 6px 0 0; }}
.tabs button[data-tab="pass"] {{ color: #1a7f37; }}
.tabs button[data-tab="fail"] {{ color: #cf222e; }}
.tabs button[data-tab="pass"].on {{ background: #1a7f37; border-color: #1a7f37; color: #fff; }}
.tabs button[data-tab="fail"].on {{ background: #cf222e; border-color: #cf222e; color: #fff; }}
.panel {{ display: none; }} .panel.on {{ display: block; }}
table {{ border-collapse: collapse; width: 100%; font-size: 14px; table-layout: fixed; }}
th:nth-child(1) {{ width: 32%; }} th:nth-child(2) {{ width: 8%; }}
td {{ word-break: break-all; }}
th, td {{ border-bottom: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }}
th {{ background: #f6f8fa; }}
.err {{ color: #cf222e; margin-top: 4px; }}
</style>
</head>
<body>
<h1>Toss Payments API 테스트 결과</h1>
<p>요청 {len(rows)}건 중 실패 {len(failed)}건 / 검증 {tests}개 중 통과 {passed_tests}개</p>
<p class="meta">실행 시각 {started}</p>
<div class="tabs">
<button data-tab="pass">PASS {len(passed)}</button>
<button data-tab="fail">FAIL {len(failed)}</button>
</div>
<div class="panel" id="pass">{table(passed)}</div>
<div class="panel" id="fail">{table(failed)}</div>
<script>
function show(tab) {{
  document.querySelectorAll(".tabs button").forEach(b => b.classList.toggle("on", b.dataset.tab === tab));
  document.querySelectorAll(".panel").forEach(p => p.classList.toggle("on", p.id === tab));
}}
document.querySelectorAll(".tabs button").forEach(b => b.onclick = () => show(b.dataset.tab));
show("pass");
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("result")
    parser.add_argument("--summary")
    parser.add_argument("--html")
    args = parser.parse_args()

    try:
        with open(args.result, encoding="utf-8") as f:
            result = json.load(f)
    except (OSError, ValueError) as e:
        print(f"결과 파일을 읽을 수 없습니다: {e}", file=sys.stderr)
        return 2

    rows = judge(result)
    if not rows:
        print("실행된 요청이 없습니다.", file=sys.stderr)
        return 2

    md = to_markdown(rows)
    print(md)
    if args.summary:
        with open(args.summary, "w", encoding="utf-8") as f:
            f.write(md)
    if args.html:
        started = result.get("run", {}).get("timings", {}).get("started")
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(to_html(rows, started))
    return 1 if any(r["problems"] for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())

"""newman 결과 판정. 검증이 없는 요청, 요청 에러, 스크립트 오류도 실패로 센다."""
import argparse
import json
import sys


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("result")
    parser.add_argument("--summary")
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
    return 1 if any(r["problems"] for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())

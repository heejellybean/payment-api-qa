#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.."

TOSS_SECRET_KEY="$(grep -E '^TOSS_SECRET_KEY=' .env 2>/dev/null | cut -d= -f2-)"
case "${TOSS_SECRET_KEY:-}" in
  test_sk_*|test_gsk_*) ;;
  *) echo ".env의 TOSS_SECRET_KEY에 테스트 시크릿 키를 넣어 주세요." >&2; exit 2 ;;
esac

RUN_ID="local$(date +%y%m%d%H%M%S)"
mkdir -p reports test-results

npx newman run api/toss-payments.postman_collection.json \
  -e api/environments/toss-test.postman_environment.json \
  --env-var "secretKey=${TOSS_SECRET_KEY}" \
  --env-var "runId=${RUN_ID}" \
  --reporters cli,json \
  --reporter-json-export test-results/newman-result.json \
  --delay-request 200
NEWMAN_EXIT=$?

python3 api/judge.py test-results/newman-result.json --summary reports/summary.md --html reports/index.html
JUDGE_EXIT=$?

# 원본 JSON에는 인증 헤더가 남아 있어서 판정 후 지운다.
rm -f test-results/newman-result.json

[ $NEWMAN_EXIT -eq 0 ] && [ $JUDGE_EXIT -eq 0 ]

# 결제 API 자동화 테스트

토스페이먼츠 API를 테스트 모드로 호출해 결제, 취소, 가상계좌, 빌링 흐름 검증

Postman Collection으로 작성, newman으로 실행

토스페이먼츠 공식 프로젝트가 아닌 개인 프로젝트이며 테스트 키만 사용

## 결과

로컬 실행 기준 (2026-11-09)

- 케이스 18개, 요청 29건 (정리 단계 반복 포함), 검증 58개 전체 통과
- 실행 후 정리 단계에서 결제 4건 중 잔액이 남은 2건 전액취소
- 실행마다 `reports/index.html`(요청별 응답과 검증 결과), `reports/summary.md`(요약 표) 생성

## 케이스

| 영역 | 확인 내용 |
|---|---|
| 인증, 조회 | 잘못된 키 401, 없는 결제 404 |
| 결제 | 키인 결제, paymentKey와 orderId로 조회, 중복 주문번호 거절 |
| 취소 | 부분취소 잔액, 잔액 초과 취소 거절, 멱등키 중복 방지, 전액취소, 재취소 거절 |
| 가상계좌 | 발급, 입금 전 부분취소 거절, 전액취소 |
| 빌링 | 빌링키 발급, 자동결제, 다른 고객키 거절 |

## 설계

- 주문번호를 `qa-{실행ID}-{케이스ID}`로 생성해 실행 간 데이터 분리
- 결제, 취소 후 조회 API로 잔액과 취소 내역 재확인
- 실행 종료 시 테스트가 만든 결제 중 잔액이 남은 건 전액취소
- newman 결과를 재판정해 검증 없는 요청과 요청 에러도 실패 처리

## 구현

- 요청별 Tests 스크립트(`pm.test`)로 상태 코드, 에러 코드, 금액 검증
- 앞 요청의 응답 값(paymentKey 등)을 변수에 저장해 다음 요청에 사용
- 결제 생성 응답은 Collection 공통 스크립트가 기록, `99 정리` 폴더에서 하나씩 조회 후 잔액이 남은 결제만 취소
- `npm test`로 newman 실행, `judge.py` 판정, 결과 요약 생성을 순서대로 수행

## 구조

```
api/
  toss-payments.postman_collection.json   케이스 (폴더 01~05, 99 정리)
  environments/toss-test.postman_environment.json   주소, 테스트 카드 정보
  judge.py                                 결과 판정, 요약 생성
scripts/run-api-tests.sh                   npm test 실행 스크립트
```

## 실행

토스페이먼츠 개발자센터의 테스트 시크릿 키 필요 (https://docs.tosspayments.com/reference/using-api/api-keys)

개발자센터에서 해외 접근을 막아 두었다면 허용 국가에 미국 추가 필요

```bash
npm install
cp .env.example .env   # TOSS_SECRET_KEY 입력
npm test
```

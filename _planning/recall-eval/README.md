# 재현율·열람 성공률

과거 조사와 지금 조사를 숫자로 비교한다. 대상 재현율은 정답 목록 중 몇 개를 다시 찾았는지, 열람 성공률은 예전에 끝내 못 연 URL 을 지금 사다리가 몇 개 여는지를 잰다.

점수는 회귀 감지용이다. 정답지가 이 스킬 자신의 과거 결과이므로 절대 재현율이 아니다. 이름은 공백·하이픈을 빼고 소문자로 맞춘 뒤 같으면 같은 대상으로 본다.

```bash
python recall_eval.py build-truth <조사폴더> --out truth/<이름>.json
python recall_eval.py score --truth truth/<이름>.json --found <대장|universe.md|이름목록.txt>
python recall_eval.py failed-urls <조사폴더> --out urls/<이름>.txt
python recall_eval.py replay urls/<이름>.txt --out runs/<이름>.json --limit 20
```

`compare runs/이전.json runs/이후.json` 은 ok/partial/fail 전환과 URL 목록을 낸다. `demo` 는 네트워크 없이 합성 자료로 점검한다.

구형 fetch-log 는 성공 시도가 한 번이라도 있으면 실패 목록에 넣지 않는다. `kind=final` 이 있으면 그 URL 의 마지막 final status 를 쓴다. 같은 호스트는 직전 요청 뒤 2초가 지나야 다시 연다. `--no-third-party` 는 환경변수 `MDR_NO_THIRD_PARTY=1` 이다. `--fetch-script` 로 다른 `fetch.py` 를 지정할 수 있다.

`truth/` `urls/` `runs/` 는 고객 조사 내용일 수 있어 git 에 넣지 않는다.

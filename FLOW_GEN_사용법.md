# flow_gen.py — 클로드 × 구글 Flow 영상 자동화 사용법

Google Flow(labs.google/fx/tools/flow)는 공개 API가 없어서 **웹 화면에서만** 돌아간다.
그래서 이 스크립트는 "디버깅 포트로 띄운 내 크롬"에 Playwright로 붙어서,
사람 대신 프롬프트를 타이핑하고 → 승인 누르고 → 결과 mp4를 내려받는다.

**사람이 하는 일은 딱 두 개다: 크롬 한 번 띄우기, 구글 로그인 한 번 하기.**

---

## 0. 미리 알아둘 것

| 항목 | 내용 |
|---|---|
| 실행 위치 | **내 PC (맥/윈도우)**. 클라우드·웹 클로드 컨테이너에서는 안 된다 (내 크롬·내 구글 로그인이 필요하므로) |
| 비용 | 실행 1회 = **Flow 크레딧 소모**. 기본값은 「승인」을 자동으로 누른다 |
| 계정 | 구글 UI 자동화는 **약관 회색지대**. 지메일·유튜브 물린 주 계정 말고 **부계정** 권장 |
| 취약점 | Flow 화면 구성이 바뀌면 셀렉터가 깨진다 (그때는 스크립트 수정 필요) |

---

## 1. 준비물 설치 (최초 1회)

```bash
pip install playwright
playwright install chromium
```

- 파이썬 3.9 이상
- 크롬 설치되어 있을 것
- 구글 계정 + Flow 사용 가능한 상태 (현재 무료 구독자도 생성 크레딧이 있다)

---

## 2. 디버깅 포트로 크롬 띄우기 (매번)

**⚠ 평소 쓰던 크롬 창에서는 안 된다.** 아래 명령으로 띄운 전용 크롬이어야 붙을 수 있다.

### macOS
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9333 \
  --user-data-dir="$HOME/flow-profile" \
  --no-first-run --no-default-browser-check \
  "https://labs.google/fx/tools/flow"
```

### Windows (cmd)
```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9333 ^
  --user-data-dir="%USERPROFILE%\flow-profile" ^
  --no-first-run --no-default-browser-check ^
  "https://labs.google/fx/tools/flow"
```

띄워진 창에서 **구글 로그인**을 끝내 둔다. (`flow-profile` 폴더에 저장되므로 다음부터는 로그인 유지)

---

## 3. 실행

```bash
python3 flow_gen.py "a cinematic shot of a cat walking through neon-lit rain" \
  --new-project --out ./out
```

결과:
```
· 새 프로젝트 생성
· 프롬프트 전송
· 승인 클릭
· 저장 flow_0809_143022.mp4 (12.4 MB)
{"ok": true, "files": [{"file": ".../out/flow_0809_143022.mp4", "bytes": 12400000}]}
```

### 옵션

| 옵션 | 설명 |
|---|---|
| `--new-project` | 새 프로젝트를 만들고 시작 (처음이면 거의 필수) |
| `--out ./out` | mp4 저장 폴더 (기본: 현재 폴더) |
| `--port 9333` | 크롬 디버깅 포트 (크롬 띄울 때 준 값과 같아야 함) |
| `--timeout 420` | 영상 생성 대기 상한(초). 기본 7분 |
| `--ask` | 「승인」을 자동으로 안 누르고 사람이 직접 누르게 함 (크레딧 아끼고 싶을 때) |

---

## 4. 클로드에게 시키는 법

셸을 쓸 수 있는 클로드(클로드 데스크톱 / Claude Code)에 이 파일을 두고 이렇게 말하면 된다.

> "flow_gen.py 로 **비 오는 네온 거리를 걷는 고양이** 영상을 뽑아줘. 프롬프트는 영문으로 다듬어서."

클로드가 파일을 읽고 알아서 명령을 만든다.
셸이 없으면 완성된 명령만 받아서 터미널에 붙여넣으면 된다.

---

## 5. 안 될 때

| 증상 | 원인 / 해결 |
|---|---|
| `포트 9333 에 붙지 못했다` | 2번 명령으로 띄운 크롬이 꺼져 있다. 다시 띄울 것 |
| `열린 탭이 없다` / `Flow 탭을 찾지 못했다` | 그 크롬 창에서 flow 페이지를 열어둘 것 |
| `「새 프로젝트」 버튼을 못 찾았다` | Flow UI 문구가 바뀐 것. `NEWPRJ` 튜플에 실제 버튼 문구 추가 |
| `프롬프트 입력창을 못 찾았다` | 프로젝트 안에 안 들어가 있음 → `--new-project` 붙이기 |
| `승인 요청이 안 떴다` | 정상일 수 있다(승인 없이 바로 생성). 그대로 두면 결과를 받아온다 |
| `N초 안에 영상이 안 나왔다` | `--timeout 900` 처럼 늘리기. 크레딧 소진 여부도 확인 |
| 로그인이 자꾸 풀린다 | `--user-data-dir` 경로를 매번 같게 줄 것 |

---

## 6. 코드에 이미 반영된 함정 4가지

원작자가 실제로 겪고 코드에 넣어둔 것들이라, 수정할 때 되돌리지 말 것.

1. **「승인」은 `<button>`이 아니라 커스텀 div** — 표준 셀렉터로 안 잡혀서 텍스트+좌표로 클릭한다
2. **프롬프트 입력창은 리치 에디터(contenteditable)** — 붙여넣기가 안 먹어서 `keyboard.type()`으로 한 글자씩 친다
3. **`video.duration`은 영영 안 잡힐 수 있다**(readyState 0) — `src`만 뜨면 바로 받는다
4. **「새로운 세션」은 채팅 초기화가 아니라 프로젝트 목록으로 나간다** — 쓰지 말 것

그리고 「승인, 다시 묻지 않음」류 버튼은 `NEVER` 목록으로 막아뒀다.
그 확인 한 번이 크레딧이 새는 걸 막는 유일한 장치다.

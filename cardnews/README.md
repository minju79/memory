# 인스타 카드뉴스 자동 생성 (HTML → PNG)

데이터(JSON) 넣으면 인스타 캐러셀용 PNG가 우수수 나옵니다.
**6장에 5초. 무료, 무제한, 로그인 없음.**

```bash
python3 render.py --data data/sample_gwangju_2026-07.json --out out
```

---

## 왜 이 방식인가

`flow_gen.py`(구글 Flow 자동화)와 발상은 같습니다 — **템플릿 1개 + 데이터 N개 → 배치 출력.**
하지만 브라우저를 *조종*하지 않고 *렌더러*로만 씁니다. 그래서 이런 것들이 전부 사라집니다.

| | Flow 자동화 | 이 방식 |
|---|---|---|
| 구글 로그인·크롬 띄우기 | 필요 | **불필요** |
| UI 문구 바뀌면 | 죽음 | 무관 |
| 비용 | 크레딧 소모 | **무료·무제한** |
| 한글 | 뭉개짐 | **Pretendard 완벽** |
| 100장 | 몇 시간 + 계정 리스크 | **1~2분** |
| 약관 | 회색지대 | 깨끗함 |

생성형 AI는 한글 글자를 못 씁니다. 그런데 카드뉴스의 존재 이유가 정확한 글자죠.
그래서 **글자는 코드로 얹고, (필요하면) 배경만 생성형으로** 가 정답입니다.

---

## 설치 (최초 1회)

```bash
pip install playwright
playwright install chromium
```

폰트(Pretendard)는 `assets/` 에 이미 들어 있습니다. 별도 설치 불필요.

---

## 쓰는 법

### 1. 데이터만 바꾸면 끝

`data/sample_gwangju_2026-07.json` 을 복사해서 숫자만 갈아끼우세요.
매달 이 파일 하나만 새로 쓰면 카드뉴스가 나옵니다.

```bash
cp data/sample_gwangju_2026-07.json data/gwangju_2026-08.json
# 편집 후
python3 render.py --data data/gwangju_2026-08.json --out out
```

### 2. 옵션

| 옵션 | 설명 |
|---|---|
| `--data` | 카드 데이터 JSON (필수) |
| `--out` | PNG 저장 폴더 (기본 `out/`) |
| `--template` | 다른 템플릿 쓰기 (기본 `template_gwangju.html`) |
| `--scale 2` | 2160×2700 로 뽑기 (인쇄·확대용) |
| `--prefix` | 파일명 앞부분 (기본: 데이터 파일명) |

### 3. 디자인을 눈으로 고치고 싶을 때

렌더할 때마다 `_build/preview.html` 이 생깁니다. **브라우저로 직접 열립니다.**
개발자도구로 CSS를 만져보고, 맘에 드는 값을 `template_gwangju.html` 에 옮기면 됩니다.

---

## 카드 6종

`type` 만 바꾸면 레이아웃이 바뀝니다. 순서·개수는 자유입니다 (인스타 캐러셀 최대 20장).

| type | 용도 | 필드 |
|---|---|---|
| `cover` | 표지·훅 | `badge` `title` `subtitle` `note` |
| `stat` | 큰 숫자 3개 | `title` `items[{label,value,unit,delta,dir}]` |
| `rank` | 순위 리스트 | `title` `items[{name,sub,value,delta,dir}]` |
| `table` | 실거래 표 | `title` `columns[]` `rows[][]` |
| `insight` | 해설·포인트 | `title` `items[{head,body}]` |
| `cta` | 마무리·댓글 유도 | `title` `body` `handle` |

- `title` 안에 `\n` 을 넣으면 줄바꿈됩니다.
- `dir` 은 `up`(빨강) / `down`(파랑) / 생략(회색). **한국식 색 관습**을 따릅니다.
- `table` 의 `rows` 값이 `+`/`-` 로 시작하면 자동으로 색이 붙습니다.

---

## ⚠ 샘플 데이터 주의

`data/sample_gwangju_2026-07.json` 의 **숫자는 전부 레이아웃 확인용 가짜입니다.**
실거래 통계가 아니므로 그대로 올리면 안 됩니다.

안전장치로 `meta.sample: true` 인 동안 모든 카드에 **SAMPLE 워터마크**가 찍힙니다.
진짜 데이터를 넣은 뒤 `false` 로 바꾸면 사라집니다.

---

## 규격 메모

- 캔버스 **1080×1350 (4:5)** — 요즘 인스타 피드는 1:1보다 4:5가 화면을 더 먹어서 도달이 낫습니다.
- 1:1로 바꾸려면 `template_gwangju.html` 의 `--H:1350px` 를 `1080px` 로.
- 스토리(9:16)는 `--W:1080px; --H:1920px`.

---

## 파일

```
cardnews/
├─ render.py                     렌더러
├─ template_gwangju.html         템플릿 (CSS + 카드 6종 렌더 로직)
├─ assets/*.woff2                Pretendard 4종
├─ data/*.json                   카드 데이터
├─ out/                          결과 PNG   (git 제외)
└─ _build/preview.html           브라우저 미리보기 (git 제외)
```

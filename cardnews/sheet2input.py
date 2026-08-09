#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sheet2input.py — 구글시트(보도자료 수집)에서 개발 레이더 후보를 걸러낸다.

매일 아침 전 기관 보도자료가 수백 건 쌓이는 시트를 그대로 클로드에게 넘기면
낭비다. 여기서 키워드로 기계적으로 1차만 거르고(공짜·즉시), 그 다음 판단은
클로드가 한다.

  수백 건 ──[이 스크립트: 키워드]──> 수십 건 ──[클로드: 부동산 영향도]──> 5건

  python3 sheet2input.py --csv "<시트 CSV 주소>" --out input/이번주.txt

구글시트 CSV 주소 얻는 법 (둘 중 아무거나)
  ① 공유를 '링크가 있는 모든 사용자'로 두고 아래 형태로 바꾼다
     https://docs.google.com/spreadsheets/d/<시트ID>/export?format=csv&gid=<탭GID>
  ② 파일 → 공유 → 웹에 게시 → 해당 탭 → 쉼표로 구분된 값(.csv)

컬럼 이름은 자동으로 찾는다(제목/링크/기관/날짜/분야 계열). 못 찾으면 --col-* 로 지정.
"""
import argparse, csv, io, pathlib, re, sys, urllib.request
from datetime import datetime

# 컬럼 자동 인식 — 시트마다 헤더가 제각각이라 후보를 넉넉히 둔다
GUESS = {
    "title":    ["제목", "헤드라인", "보도자료명", "자료명", "title", "headline", "subject"],
    "url":      ["링크", "url", "주소", "원문", "link", "바로가기"],
    "press":    ["기관", "출처", "부서", "발행처", "언론사", "press", "source", "agency"],
    "date":     ["날짜", "등록일", "배포일", "작성일", "일자", "date"],
    "category": ["분야", "카테고리", "구분", "category"],
}

# 부동산·개발 레이더에 걸릴 만한 말들
KEYWORDS = ("개발 재개발 재건축 정비사업 지구단위 도시계획 용도지역 고시 공고 승인 인가 "
            "착공 준공 개통 분양 산업단지 산단 데이터센터 도로 철도 도시철도 역세권 공항 "
            "터미널 택지 주택공급 아파트 임대주택 공원 학교 관광단지 개발제한구역 그린벨트 "
            "토지거래 재정비 뉴딜 복합개발 이전 유치").split()

# 명백히 관계없는 것 — 키워드가 걸려도 버린다
EXCLUDE = "채용 인사발령 축제 봉사 헌혈 체육대회 공모전 수기 백일장 위촉 표창".split()


def load_csv(src: str) -> list[dict]:
    if re.match(r"^https?://", src):
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=30).read()
    else:
        raw = pathlib.Path(src).expanduser().read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return list(csv.DictReader(io.StringIO(raw.decode(enc))))
        except UnicodeDecodeError:
            continue
    raise SystemExit("CSV 인코딩을 못 읽었다. utf-8 로 저장해 볼 것.")


def map_columns(headers, override):
    """헤더 이름을 보고 어떤 컬럼이 무엇인지 추측한다."""
    norm = {h: re.sub(r"\s", "", (h or "")).lower() for h in headers}
    out = {}
    for key, cands in GUESS.items():
        if override.get(key):
            out[key] = override[key]; continue
        for h, n in norm.items():
            if any(c in n for c in cands):
                out[key] = h; break
    return out


def parse_date(s):
    s = re.sub(r"[^\d]", "-", str(s or "")).strip("-")
    for f in ("%Y-%m-%d", "%y-%m-%d", "%Y-%m-%d-%H-%M-%S", "%Y-%m-%d-%H-%M"):
        try:
            return datetime.strptime(s[:len(datetime.now().strftime(f))], f).date()
        except ValueError:
            continue
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="구글시트 CSV 주소 또는 로컬 csv 경로")
    ap.add_argument("--out", default="input/이번주.txt")
    ap.add_argument("--since", help="이 날짜 이후만 (예: 2026-08-01)")
    ap.add_argument("--region", help="제목·기관에 이 말이 있는 것만 (예: 광주)")
    ap.add_argument("--keywords", help="쉼표로 구분. 지정하면 기본 키워드를 대체한다")
    ap.add_argument("--exclude", help="쉼표로 구분. 지정하면 기본 제외어를 대체한다")
    ap.add_argument("--limit", type=int, default=60, help="최대 몇 건까지 넘길지")
    for k in GUESS:
        ap.add_argument(f"--col-{k}", help=f"{k} 컬럼 이름을 직접 지정")
    a = ap.parse_args()

    rows = load_csv(a.csv)
    if not rows:
        raise SystemExit("시트가 비어 있다.")

    override = {k: getattr(a, f"col_{k}") for k in GUESS}
    col = map_columns(rows[0].keys(), override)
    if "title" not in col:
        raise SystemExit(f"제목 컬럼을 못 찾았다. --col-title 로 지정할 것.\n"
                         f"시트 컬럼: {list(rows[0].keys())}")

    kws = [k.strip() for k in a.keywords.split(",")] if a.keywords else KEYWORDS
    exs = [e.strip() for e in a.exclude.split(",")] if a.exclude else EXCLUDE
    since = parse_date(a.since) if a.since else None

    picked, seen = [], set()
    drop = {"중복": 0, "날짜": 0, "지역": 0, "제외어": 0, "키워드": 0}

    for r in rows:
        title = (r.get(col["title"]) or "").strip()
        if not title:
            continue
        if title in seen:
            drop["중복"] += 1; continue

        url   = (r.get(col.get("url", ""), "") or "").strip()
        press = (r.get(col.get("press", ""), "") or "").strip()
        date  = (r.get(col.get("date", ""), "") or "").strip()
        cat   = (r.get(col.get("category", ""), "") or "").strip()
        hay   = f"{title} {press} {cat}"

        if since:
            d = parse_date(date)
            if d and d < since:
                drop["날짜"] += 1; continue
        if a.region and a.region not in hay:
            drop["지역"] += 1; continue
        if any(e in hay for e in exs):
            drop["제외어"] += 1; continue

        hits = [k for k in kws if k in hay]
        if not hits:
            drop["키워드"] += 1; continue

        seen.add(title)
        picked.append({"title": title, "url": url, "press": press,
                       "date": date, "hits": hits})

    # 키워드가 많이 걸린 것부터 = 개발 소식일 가능성이 높은 것부터
    picked.sort(key=lambda x: len(x["hits"]), reverse=True)
    picked = picked[:a.limit]

    out = pathlib.Path(a.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# 구글시트에서 추출 · {datetime.now():%Y-%m-%d %H:%M}",
        f"# 원본 {len(rows)}건 → 후보 {len(picked)}건"
        + (f" (상위 {a.limit}건으로 제한)" if len(seen) > a.limit else ""),
        f"# 걸러낸 이유: " + ", ".join(f"{k} {v}" for k, v in drop.items() if v),
        f"# 컬럼 매핑: " + ", ".join(f"{k}→{v}" for k, v in col.items()),
        "#",
        "# 클로드에게: 이 목록은 키워드로만 거른 1차 후보다. 여기서 부동산 영향도가",
        "# 큰 것만 골라 개발레이더_작성법.md 규칙대로 카드 JSON 을 만들 것.",
        "",
    ]
    for p in picked:
        lines.append(f"{p['title']}" + (f" | {p['url']}" if p["url"] else ""))
        meta = " · ".join(x for x in (p["press"], p["date"]) if x)
        lines.append(f">> {meta} · 히트: {','.join(p['hits'][:5])}")
        lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")

    print(f"원본 {len(rows)}건 → 후보 {len(picked)}건", file=sys.stderr)
    for k, v in drop.items():
        if v:
            print(f"  · 제외 — {k}: {v}건", file=sys.stderr)
    print(f"→ {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

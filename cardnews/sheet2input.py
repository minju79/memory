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

# ── 투자축 4개 ────────────────────────────────────────────────────────────
# 레이더를 넓게 치면 매일 수십 건이 쌓이기만 하고 아무것도 안 남는다.
# 지금 광주를 실제로 움직이는 축만 남긴다. 여기가 좁을수록 전문성이 선명해진다.
AXES = {
    "통합":     "행정통합 통합특별시 광주전남 전남광주 통합시 특별시출범 시도통합 통합법안 "
                "상생발전 광역행정".split(),
    "반도체AI": "반도체 특화단지 파운드리 소부장 인공지능 데이터센터 첨단3 첨단3지구 실증단지 "
                "국가AI AI집적 클러스터 NPU GPU 슈퍼컴퓨팅".split(),
    "토지허가": "토지거래허가 허가구역 투기과열 조정대상지역 규제지역 지정해제 실거주의무 "
                "허가대상 토지거래".split(),
    "군공항":   "군공항 전투비행장 종전부지 이전부지 소음피해 무안 함평 공항이전 민군공항".split(),
}

# --include-general 을 줬을 때만 쓰는 넓은 그물
KEYWORDS = ("개발 재개발 재건축 정비사업 지구단위 도시계획 용도지역 고시 공고 승인 인가 "
            "착공 준공 개통 분양 산업단지 산단 데이터센터 도로 철도 도시철도 역세권 공항 "
            "터미널 택지 주택공급 아파트 임대주택 공원 학교 관광단지 개발제한구역 그린벨트 "
            "토지거래 재정비 복합개발 이전 유치").split()

# 정부·지자체 발 자료인가, 언론 보도인가 — 포지셔닝이 여기서 갈린다
OFFICIAL = "시 도 청 부 처 청장 공사 공단 위원회 국토교통부 조달청 LH 한국토지주택공사".split()

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
    ap.add_argument("--axis", action="append",
                    help=f"이 투자축만 (반복 가능). 선택지: {'/'.join(AXES)}")
    ap.add_argument("--include-general", action="store_true",
                    help="4개 투자축 밖의 일반 개발 소식까지 넓게 본다 (기본은 축만)")
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

    axes = {k: v for k, v in AXES.items() if not a.axis or k in a.axis}
    if a.axis and not axes:
        raise SystemExit(f"--axis 값이 이상하다. 선택지: {'/'.join(AXES)}")
    kws = [k.strip() for k in a.keywords.split(",")] if a.keywords else KEYWORDS
    exs = [e.strip() for e in a.exclude.split(",")] if a.exclude else EXCLUDE
    since = parse_date(a.since) if a.since else None

    picked, national, seen = [], [], set()
    drop = {"중복": 0, "날짜": 0, "지역": 0, "제외어": 0, "축밖": 0}

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
        if any(e in hay for e in exs):
            drop["제외어"] += 1; continue

        flat = re.sub(r"\s", "", hay)
        hit_axes = {ax: [k for k in ks if k in flat] for ax, ks in axes.items()}
        hit_axes = {ax: ks for ax, ks in hit_axes.items() if ks}

        if hit_axes:
            axis, hits = max(hit_axes.items(), key=lambda x: len(x[1]))
        elif a.include_general and (hits := [k for k in kws if k in hay]):
            axis = "기타"
        else:
            drop["축밖"] += 1; continue

        seen.add(title)
        item = {"title": title, "url": url, "press": press, "date": date,
                "axis": axis, "hits": hits,
                "tier": "공식" if any(o in press for o in OFFICIAL) else "참고"}

        # 중앙부처 자료는 '광주'를 안 쓰는 경우가 많다. 축에 걸렸으면 버리지 말고
        # 따로 모아 둔다 — 반도체 특화단지 지정 같은 건 여기서 나온다.
        if a.region and a.region not in hay:
            drop["지역"] += 1
            national.append(item)
        else:
            picked.append(item)

    # 축에 걸린 것 → 적중 키워드 많은 것 순
    order = list(axes) + ["기타"]
    key = lambda x: (order.index(x["axis"]), -len(x["hits"]))
    picked.sort(key=key); national.sort(key=key)
    picked = picked[:a.limit]; national = national[:12]

    out = pathlib.Path(a.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# 구글시트에서 추출 · {datetime.now():%Y-%m-%d %H:%M}",
        f"# 원본 {len(rows)}건 → 후보 {len(picked)}건"
        + (f" + 지역 미명시 {len(national)}건" if national else "")
        + (f" (상위 {a.limit}건으로 제한)" if len(seen) > a.limit else ""),
        f"# 걸러낸 이유: " + ", ".join(f"{k} {v}" for k, v in drop.items() if v),
        f"# 컬럼 매핑: " + ", ".join(f"{k}→{v}" for k, v in col.items()),
        "#",
        "# 클로드에게: 이 목록은 키워드로만 거른 1차 후보다. 여기서 부동산 영향도가",
        "# 큰 것만 골라 개발레이더_작성법.md 규칙대로 카드 JSON 을 만들 것.",
        "# [공식] = 정부·지자체 발, [참고] = 언론 보도. 공식자료를 우선한다.",
        "",
    ]
    cur = None
    for p in picked:
        if p["axis"] != cur:
            cur = p["axis"]
            lines += [f"── {cur} " + "─" * 40, ""]
        lines.append(f"[{p['tier']}] {p['title']}" + (f" | {p['url']}" if p["url"] else ""))
        meta = " · ".join(x for x in (p["press"], p["date"]) if x)
        lines.append(f">> {meta} · 히트: {','.join(p['hits'][:5])}")
        lines.append("")

    if national:
        lines += ["", "═" * 52,
                  f"# 지역명은 없지만 투자축에 걸린 자료 {len(national)}건",
                  "# 중앙부처 자료는 '광주'를 명시하지 않는 경우가 많다.",
                  "# 광주와 관계있는지 클로드가 원문을 열어 판단할 것.", "═" * 52, ""]
        for p in national:
            lines.append(f"[{p['tier']}] ({p['axis']}) {p['title']}"
                         + (f" | {p['url']}" if p["url"] else ""))
            meta = " · ".join(x for x in (p["press"], p["date"]) if x)
            lines.append(f">> {meta} · 히트: {','.join(p['hits'][:5])}")
            lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")

    print(f"원본 {len(rows)}건 → 후보 {len(picked)}건"
          + (f" (+ 지역 미명시 {len(national)}건)" if national else ""), file=sys.stderr)
    for k, v in drop.items():
        if v:
            print(f"  · 제외 — {k}: {v}건", file=sys.stderr)
    print(f"→ {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

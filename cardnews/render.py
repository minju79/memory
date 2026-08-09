#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render.py — JSON 데이터 + HTML 템플릿 → 인스타 카드뉴스 PNG 여러 장.

flow_gen.py 와 같은 발상(템플릿 1개 + 데이터 N개 → 배치 출력)이지만,
브라우저를 '조종'하는 게 아니라 '렌더러'로만 쓴다. 그래서
로그인·크레딧·UI 변경·약관 문제가 전부 없다.

  python3 render.py --data data/sample_gwangju_2026-07.json --out out

동작
  ① 템플릿 HTML 에 Pretendard 폰트(base64)와 데이터(JSON)를 주입 → _build/preview.html
  ② 헤드리스 크로미움으로 열고, .card 하나하나를 PNG 로 캡처

_build/preview.html 은 브라우저로 직접 열어볼 수 있다. CSS 를 눈으로 고치고 싶으면
그 파일을 열어 조정한 뒤, 같은 내용을 template_*.html 에 반영하면 된다.

준비물
  pip install playwright  →  playwright install chromium
"""
import argparse, base64, json, os, pathlib, sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("playwright 가 없다. `pip install playwright` 후 "
          "`playwright install chromium` 을 한 번 실행할 것.", file=sys.stderr)
    sys.exit(2)

HERE = pathlib.Path(__file__).resolve().parent

# 파일명 → (font-weight, 실제 파일). 없는 건 조용히 건너뛴다.
FONTS = [(400, "Pretendard-Regular.woff2"),
         (600, "Pretendard-SemiBold.woff2"),
         (700, "Pretendard-Bold.woff2"),
         (800, "Pretendard-ExtraBold.woff2")]


def font_css(assets: pathlib.Path) -> str:
    """woff2 를 base64 로 심는다. file:// 에서도 폰트가 확실히 뜨게 하려는 것."""
    out = []
    for weight, name in FONTS:
        f = assets / name
        if not f.exists():
            continue
        b64 = base64.b64encode(f.read_bytes()).decode()
        out.append("@font-face{font-family:Pretendard;font-style:normal;"
                   f"font-weight:{weight};font-display:block;"
                   f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    if not out:
        print("! assets/ 에 Pretendard woff2 가 없다. 한글이 깨져 보일 수 있다.", file=sys.stderr)
    return "\n".join(out)


def find_chromium():
    """크로미움이 별도 경로에 설치된 환경(원격 컨테이너 등) 대비 탐색.
    일반 PC 에서 `playwright install chromium` 을 했다면 None 을 반환하고,
    플레이라이트 기본 경로를 그대로 쓴다."""
    hint = os.environ.get("CHROMIUM_PATH")
    if hint and pathlib.Path(hint).exists():
        return hint
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if not base:
        return None
    for pat in ("chromium-*/chrome-linux/chrome",
                "chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium",
                "chromium-*/chrome-win/chrome.exe"):
        found = sorted(pathlib.Path(base).glob(pat), reverse=True)
        if found:
            return str(found[0])
    return None


def launch(p):
    """기본 경로로 먼저 시도하고, 실패하면 탐색한 크로미움으로 재시도."""
    try:
        return p.chromium.launch()
    except Exception:
        exe = find_chromium()
        if not exe:
            raise
        print(f"· 크로미움 대체 경로 사용: {exe}", file=sys.stderr)
        return p.chromium.launch(executable_path=exe)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="카드 데이터 JSON")
    ap.add_argument("--template", default=str(HERE / "template_gwangju.html"))
    ap.add_argument("--assets", default=str(HERE / "assets"), help="폰트 폴더")
    ap.add_argument("--out", default=str(HERE / "out"), help="PNG 저장 폴더")
    ap.add_argument("--scale", type=float, default=1.0,
                    help="해상도 배율. 2 면 2160x2700 (인쇄·확대용)")
    ap.add_argument("--prefix", default=None, help="파일명 앞부분 (기본: 데이터 파일명)")
    a = ap.parse_args()

    data_path = pathlib.Path(a.data).expanduser().resolve()
    data = json.loads(data_path.read_text(encoding="utf-8"))
    tpl = pathlib.Path(a.template).expanduser().resolve().read_text(encoding="utf-8")

    html = (tpl.replace("/*__FONTS__*/", font_css(pathlib.Path(a.assets).expanduser().resolve()))
               .replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False)))

    build = HERE / "_build"; build.mkdir(exist_ok=True)
    preview = build / "preview.html"
    preview.write_text(html, encoding="utf-8")

    out = pathlib.Path(a.out).expanduser().resolve(); out.mkdir(parents=True, exist_ok=True)
    prefix = a.prefix or data_path.stem

    with sync_playwright() as p:
        br = launch(p)
        pg = br.new_page(viewport={"width": 1080, "height": 1350},
                         device_scale_factor=a.scale)
        pg.goto(preview.as_uri(), wait_until="load")
        pg.evaluate("() => document.fonts.ready")     # 폰트 적용 전에 찍는 사고 방지
        pg.wait_for_timeout(300)

        cards = pg.query_selector_all(".card")
        if not cards:
            print("카드가 하나도 렌더되지 않았다. 데이터의 cards 배열을 확인할 것.", file=sys.stderr)
            br.close(); return 3

        files = []
        for i, el in enumerate(cards, 1):
            f = out / f"{prefix}_{i:02d}.png"
            el.screenshot(path=str(f))
            files.append({"file": str(f), "bytes": f.stat().st_size})
            print(f"· {f.name} ({f.stat().st_size/1024:.0f} KB)", file=sys.stderr)
        br.close()

    print(json.dumps({"ok": True, "count": len(files),
                      "preview": str(preview), "files": files},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

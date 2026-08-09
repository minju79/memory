#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""flow_gen.py — Google Flow 에 프롬프트를 넣고, 생성된 영상 파일을 받아온다.

Flow 는 API 가 없어 웹 화면에서만 돌아간다. 그래서 디버깅 포트로 띄운 크롬에 붙어
사람 대신 조작하고, 결과 mp4 를 받아 저장한다. 사람이 하는 건 크롬 한 번 띄우고
구글 로그인 한 번, 그게 전부다.

  python3 flow_gen.py "프롬프트" --new-project --out ./out

준비물
  · 구글 계정 + Flow 를 쓸 수 있는 구독(크레딧이 있어야 한다)
  · 크롬
  · pip install playwright  →  playwright install chromium

클로드에게 시킬 때는 이렇게 말하면 된다
  "flow_gen.py 로 <원하는 장면> 영상을 뽑아줘. 프롬프트는 영문으로 다듬어서."
  (클로드가 이 파일을 읽고 알아서 명령을 만든다. 실행은 셸이 있으면 클로드가,
   없으면 완성된 명령을 받아 사람이 터미널에 붙여넣으면 된다.)

⚠ 화면 구성이 바뀌면 깨진다. 아래 네 가지는 실제로 겪은 것이라 코드에 반영돼 있다.
  ① 「승인」은 <button> 이 아니라 커스텀 div 다 — 표준 셀렉터로 안 잡힌다
  ② 프롬프트 입력창은 리치 에디터라 붙여넣기가 안 먹는다 — 타이핑해야 한다
  ③ video.duration 은 영영 안 잡힐 수 있다 — src 만 뜨면 바로 받으면 된다
  ④ 「새로운 세션」은 채팅 초기화가 아니라 프로젝트 목록으로 나간다 — 쓰지 말 것

⚠ 구글 UI 자동화는 이용약관 회색지대다. 지메일·유튜브가 물려 있는 주 계정 대신
   이 용도 전용 계정을 쓰는 편이 안전하다.

전제: 아래 명령으로 띄운 크롬이 켜져 있고, 그 창에서 구글 로그인이 끝나 있어야 한다.
  mac   : "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
            --remote-debugging-port=9333 --user-data-dir="$HOME/flow-profile" \
            --no-first-run --no-default-browser-check "https://labs.google/fx/tools/flow"
  win   : "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" ^
            --remote-debugging-port=9333 --user-data-dir="%USERPROFILE%\\flow-profile" ^
            --no-first-run --no-default-browser-check "https://labs.google/fx/tools/flow"

⚠ 실행하면 구독 크레딧이 소모된다. 기본 동작은 "승인"을 자동으로 누르는 것이다.
   사람이 직접 누르고 싶으면 --ask 를 준다.
"""
import argparse, json, os, pathlib, sys, time

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print(json.dumps({"ok": False, "error": "playwright 가 없다. `pip install playwright` 후 "
                                            "`playwright install chromium` 을 한 번 실행할 것."},
                     ensure_ascii=False)); sys.exit(2)

FLOW_URL = "https://labs.google/fx/tools/flow"

# ── UI 문구 (한국어·영어 둘 다) ────────────────────────────────────────────
NEWPRJ  = ("새프로젝트", "newproject")
APPROVE = ("승인", "approve", "confirm")
NEVER   = ("다시", "again", "always", "거부", "reject", "deny", "cancel")   # 절대 누르지 않음

JS_FIND_TEXT = """(args) => {
  const [want, ban, maxW] = args;
  const norm = s => (s||'').replace(/\\s/g,'').toLowerCase();
  let best = null;
  document.querySelectorAll('*').forEach(e => {
    if (e.children.length > 3) return;
    const t = norm(e.innerText);
    if (!t) return;
    if (!want.some(w => t === w || t === 'check'+w || t.endsWith(w) && t.length <= w.length+6)) return;
    if (ban.some(b => t.includes(b))) return;
    const r = e.getBoundingClientRect();
    if (r.width < 18 || r.height < 12 || r.width > maxW) return;
    let d = 0, n = e; while (n) { n = n.parentElement; d++; }
    if (!best || d > best.d) best = {d:d, x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2),
                                     w:Math.round(r.width), h:Math.round(r.height)};
  });
  return best;
}"""

JS_FIND_CONTAINS = """(args) => {
  const [want, maxW] = args;
  const norm = s => (s||'').replace(/\\s/g,'').toLowerCase();
  let best = null;
  document.querySelectorAll('button,[role=button],a,div').forEach(e => {
    if (e.children.length > 4) return;
    const t = norm(e.innerText);
    if (!want.some(w => t.includes(w))) return;
    const r = e.getBoundingClientRect();
    if (r.width < 40 || r.height < 20 || r.width > maxW) return;
    let d = 0, n = e; while (n) { n = n.parentElement; d++; }
    if (!best || d > best.d) best = {d:d, x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2)};
  });
  return best;
}"""

# ⚠ 프롬프트 입력창은 <textarea> 가 아니라 contenteditable 이다. 붙여넣기가 아니라 타이핑해야 한다.
JS_PROMPT_BOX = """() => {
  let b = null;
  document.querySelectorAll('[contenteditable=true],input[type=text],textarea').forEach(e => {
    if ((e.id||'').includes('recaptcha')) return;      // reCAPTCHA 의 숨은 textarea 제외
    const r = e.getBoundingClientRect();
    if (r.width < 60 || r.height < 10) return;
    if (!b || r.y > b.y) b = {x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2), y0:r.y};
  });
  return b;
}"""

# ⚠ video.duration / videoWidth 은 영영 안 잡힐 수 있다(readyState 0). src 만 있으면 받으면 된다.
JS_VIDEOS = """() => [...document.querySelectorAll('video')]
    .map(v => (v.currentSrc || v.src || '')).filter(s => s.startsWith('http'))"""


def log(msg):
    print("· " + msg, file=sys.stderr, flush=True)


def wait_for(fn, secs, every=0.25):
    end = time.time() + secs
    while time.time() < end:
        r = fn()
        if r:
            return r
        time.sleep(every)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", help="영상 프롬프트 (영문이 안정적)")
    ap.add_argument("--out", default=".", help="받은 파일을 저장할 폴더")
    ap.add_argument("--port", type=int, default=9333, help="크롬 디버깅 포트")
    ap.add_argument("--timeout", type=int, default=420, help="생성 대기 상한(초)")
    ap.add_argument("--ask", action="store_true",
                    help="승인을 자동으로 누르지 않는다 (사람이 화면에서 직접 누름)")
    ap.add_argument("--new-project", action="store_true", help="새 프로젝트를 만들고 시작")
    a = ap.parse_args()

    out = pathlib.Path(a.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        try:
            br = p.chromium.connect_over_cdp(f"http://127.0.0.1:{a.port}")
        except Exception:
            print(json.dumps({"ok": False, "error":
                  f"포트 {a.port} 에 붙지 못했다. 디버깅 포트로 띄운 크롬이 켜져 있는지 확인할 것."},
                  ensure_ascii=False)); return 2
        if not br.contexts or not br.contexts[0].pages:
            print(json.dumps({"ok": False, "error": "열린 탭이 없다."}, ensure_ascii=False)); return 2
        ctx = br.contexts[0]

        pg = None
        for q in ctx.pages:
            if "flow" in q.url:
                pg = q
        if pg is None:
            pg = ctx.pages[-1]
            pg.goto(FLOW_URL, wait_until="domcontentloaded")
            pg.wait_for_timeout(3000)
        pg.bring_to_front(); pg.wait_for_timeout(400)

        if "labs.google" not in pg.url:
            print(json.dumps({"ok": False, "error": "Flow 탭을 찾지 못했다."}, ensure_ascii=False)); return 2

        # ① (선택) 새 프로젝트 — ⚠ 「새로운 세션」 버튼은 채팅 초기화가 아니라 목록으로 나간다. 쓰지 말 것.
        if a.new_project:
            if "/project/" in pg.url:
                pg.goto(FLOW_URL, wait_until="domcontentloaded"); pg.wait_for_timeout(3000)
            hit = wait_for(lambda: pg.evaluate(JS_FIND_CONTAINS, [list(NEWPRJ), 400]), 12)
            if not hit:
                print(json.dumps({"ok": False, "error": "「새 프로젝트」 버튼을 못 찾았다."},
                                 ensure_ascii=False)); return 3
            pg.mouse.click(hit["x"], hit["y"]); pg.wait_for_timeout(4500)
            log("새 프로젝트 생성")

        # ② 프롬프트 입력 — 타이핑
        box = wait_for(lambda: pg.evaluate(JS_PROMPT_BOX), 20)
        if not box:
            print(json.dumps({"ok": False, "error":
                  "프롬프트 입력창을 못 찾았다. 프로젝트 안에 들어가 있는지 확인할 것(--new-project)."},
                  ensure_ascii=False)); return 3
        pg.mouse.click(box["x"], box["y"]); pg.wait_for_timeout(400)
        pg.keyboard.type(a.prompt, delay=18)
        pg.wait_for_timeout(500)
        pg.keyboard.press("Enter")
        log("프롬프트 전송")

        # ③ 승인 — ⚠ 「승인」만 누른다. 「승인, 다시 묻지 않음」은 절대 누르지 않는다.
        #    그 확인 한 번이 크레딧이 새는 걸 막는 유일한 장치다.
        find_ok = lambda: pg.evaluate(JS_FIND_TEXT, [list(APPROVE), list(NEVER), 340])
        hit = wait_for(find_ok, 150 if a.ask else 120)
        if hit and not a.ask:
            pg.mouse.click(hit["x"], hit["y"])
            log("승인 클릭")
        elif hit and a.ask:
            log("승인 대기 — 화면에서 직접 눌러 주세요")
            wait_for(lambda: not find_ok(), 300, 1.0)
        else:
            log("승인 요청이 안 떴다 — 승인 없이 바로 생성 중일 수 있다")

        # ④ 결과 회수 — src 만 뜨면 받는다 (duration 을 기다리지 않는다)
        srcs = wait_for(lambda: pg.evaluate(JS_VIDEOS) or None, a.timeout, 1.0)
        if not srcs:
            print(json.dumps({"ok": False, "error": f"{a.timeout}초 안에 영상이 안 나왔다."},
                             ensure_ascii=False)); return 4

        stamp = time.strftime("%m%d_%H%M%S")
        files = []
        for i, s in enumerate(srcs, 1):
            r = pg.request.get(s)
            if r.status != 200:
                log(f"HTTP {r.status} — 건너뜀"); continue
            body = r.body()
            f = out / (f"flow_{stamp}_{i}.mp4" if len(srcs) > 1 else f"flow_{stamp}.mp4")
            f.write_bytes(body)
            files.append({"file": str(f), "bytes": len(body)})
            log(f"저장 {f.name} ({len(body)/1e6:.1f} MB)")

        print(json.dumps({"ok": bool(files), "files": files}, ensure_ascii=False, indent=1))
        return 0 if files else 4


if __name__ == "__main__":
    sys.exit(main())

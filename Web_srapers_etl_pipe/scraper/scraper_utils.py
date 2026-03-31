# shared utilities — stealth, retry, logging, file helpers

import asyncio
import functools
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright_stealth import Stealth as _Stealth

_stealth = _Stealth()

LOG_DIR = Path(__file__).parent / "logs"


def get_log(name: str):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    log_fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(log_fmt)
    logger.addHandler(ch)

    log_file = LOG_DIR / f"scraping_{datetime.now().strftime('%Y%m%d')}.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(log_fmt)
    logger.addHandler(fh)

    return logger


_util_log = get_log("utils")


async def rnd_sleep(min_secs: float = 2.0, max_secs: float = 5.0):
    # randomising so the request pattern doesn't look like a metronome
    delay = random.uniform(min_secs, max_secs)
    await asyncio.sleep(delay)


def try_again(max_tries: int = 3, base_delay: float = 2.0):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < max_tries:
                try:
                    return await func(*args, **kwargs)
                except Exception as err:
                    attempt += 1
                    if attempt >= max_tries:
                        _util_log.error(f"giving up on {func.__name__} after {max_tries} tries")
                        raise err
                    # exponential + jitter, cap at 30s
                    wait_t = min(base_delay * (2 ** (attempt - 1)), 30.0)
                    wait_t += random.uniform(0, wait_t * 0.25)
                    _util_log.warning(
                        f"attempt {attempt} failed ({func.__name__}): {err}. retrying in {wait_t:.1f}s"
                    )
                    await asyncio.sleep(wait_t)
        return wrapper
    return decorator


# these suppress Chromium's obvious automation tells in the process args
BROWSER_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-accelerated-2d-canvas",
    "--no-first-run",
    "--no-zygote",
    "--disable-gpu",
    "--disable-infobars",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-default-apps",
    "--disable-sync",
    "--metrics-recording-only",
    "--mute-audio",
    "--no-default-browser-check",
    "--window-size=1366,768",
    "--start-maximized",
    # these two matter for hCaptcha — removes headless-only API surface
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process",
]

# updated to Chrome 124/125 — older versions look suspicious to hCaptcha's UA parser
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.207 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.118 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# kept for backwards compat
USER_AGENT_POOL = UA_POOL

_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1366, "height": 768},
    {"width": 1280, "height": 800},
]

# Sec-CH-UA must match the UA string — inconsistency here is a big hCaptcha signal
# keyed by Chrome major version extracted from the UA above
_SEC_CH_UA_MAP = {
    "125": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
    "124": '"Google Chrome";v="124", "Chromium";v="124", "Not.A/Brand";v="24"',
}

def _pick_ua_and_headers():
    ua = random.choice(UA_POOL)
    # pull major version from UA string
    import re
    m = re.search(r"Chrome/(\d+)", ua)
    major = m.group(1) if m else "124"
    sec_ch = _SEC_CH_UA_MAP.get(major, _SEC_CH_UA_MAP["124"])
    # platform string must also match the UA
    platform = '"Windows"' if "Windows" in ua else '"macOS"'
    return ua, sec_ch, platform


# extra patches on top of playwright-stealth — covers things stealth_async doesn't touch
_EXTRA_JS = """
(() => {
    // hCaptcha specifically checks this — stealth_async handles webdriver but not this
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'ar'] });

    // Canvas fingerprint noise — tiny random salt added so each session looks different
    // without this, headless Chrome canvases are identical across sessions = easy to flag
    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        const ctx2d = this.getContext('2d');
        if (ctx2d) {
            const imgData = ctx2d.getImageData(0, 0, this.width, this.height);
            const d = imgData.data;
            // add tiny imperceptible noise to a few pixels
            for (let i = 0; i < 8; i++) {
                const idx = Math.floor(Math.random() * d.length / 4) * 4;
                d[idx] = d[idx] ^ (Math.floor(Math.random() * 3));
            }
            ctx2d.putImageData(imgData, 0, 0);
        }
        return origToDataURL.apply(this, arguments);
    };

    // also patch toBlob for the same reason
    const origToBlob = HTMLCanvasElement.prototype.toBlob;
    HTMLCanvasElement.prototype.toBlob = function(cb, type, quality) {
        return origToBlob.call(this, cb, type, quality);
    };

    // WebGL — patch BOTH contexts (stealth_async only does WebGLRenderingContext)
    const _patchWebGL = (ctxProto) => {
        if (!ctxProto) return;
        const orig = ctxProto.getParameter;
        ctxProto.getParameter = function(param) {
            if (param === 37445) return 'Intel Inc.';
            if (param === 37446) return 'Intel Iris OpenGL Engine';
            return orig.call(this, param);
        };
    };
    try { _patchWebGL(WebGLRenderingContext.prototype); } catch(e) {}
    try { _patchWebGL(WebGL2RenderingContext.prototype); } catch(e) {}

    // AudioContext fingerprint — hCaptcha uses this as a secondary signal
    try {
        const origGetChannelData = AudioBuffer.prototype.getChannelData;
        AudioBuffer.prototype.getChannelData = function(ch) {
            const arr = origGetChannelData.call(this, ch);
            // noise only on first call per buffer so performance impact is negligible
            if (arr.length > 200 && !this._noised) {
                this._noised = true;
                arr[0] += Math.random() * 0.0001 - 0.00005;
            }
            return arr;
        };
    } catch(e) {}

    // hCaptcha checks window.outerWidth/outerHeight match viewport — headless sets these to 0
    if (window.outerWidth === 0) {
        Object.defineProperty(window, 'outerWidth', { get: () => window.innerWidth + 16 });
    }
    if (window.outerHeight === 0) {
        Object.defineProperty(window, 'outerHeight', { get: () => window.innerHeight + 88 });
    }

    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
    Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
    Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
    Object.defineProperty(screen, 'pixelDepth',  { get: () => 24 });
})();
"""


async def mk_stealth(browser, headless: bool = True, storage_state: Optional[str] = None):
    ua, sec_ch_ua, platform = _pick_ua_and_headers()
    vp = random.choice(_VIEWPORTS)

    context_kwargs = {
        "user_agent": ua,
        "viewport": vp,
        "locale": "en-AE",
        "timezone_id": "Asia/Dubai",
        "color_scheme": "light",
        "device_scale_factor": 1,
        "has_touch": False,
        "is_mobile": False,
        "java_script_enabled": True,
        "extra_http_headers": {
            "Accept-Language":           "en-US,en;q=0.9,ar;q=0.8",
            "Accept-Encoding":           "gzip, deflate, br",
            "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Connection":                "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest":            "document",
            "Sec-Fetch-Mode":            "navigate",
            "Sec-Fetch-Site":            "none",
            "Sec-Fetch-User":            "?1",
            # these must stay consistent with the UA — mismatch = instant flag
            "Sec-CH-UA":                 sec_ch_ua,
            "Sec-CH-UA-Mobile":          "?0",
            "Sec-CH-UA-Platform":        platform,
        },
    }
    if storage_state:
        context_kwargs["storage_state"] = storage_state

    ctx = await browser.new_context(**context_kwargs)

    # playwright-stealth patches ~20 detection vectors including webdriver, iframe contentWindow,
    # permission API, chrome runtime, and more
    await _stealth.apply_stealth_async(ctx)

    # our extra patches on top — canvas noise, WebGL2, audio, outerWidth
    await ctx.add_init_script(_EXTRA_JS)

    # print("debug:", ua[:55])
    return ctx


async def human_mouse_move(page):
    # move mouse in a loose curve before scrolling — idle pointer = bot signal for hCaptcha
    try:
        vp = page.viewport_size or {"width": 1366, "height": 768}
        w, h = vp["width"], vp["height"]
        # pick a few waypoints in the upper-mid area of the page
        pts = [
            (random.randint(w // 4, w * 3 // 4), random.randint(80, h // 3)),
            (random.randint(w // 3, w * 2 // 3), random.randint(h // 4, h // 2)),
            (random.randint(w // 4, w * 3 // 4), random.randint(h // 3, h * 2 // 3)),
        ]
        for px, py in pts:
            await page.mouse.move(px, py)
            await asyncio.sleep(random.uniform(0.05, 0.18))
    except Exception:
        pass


async def slow_scroll(page, steps: int = 4):
    # scrolling a bit so it looks like a human actually reading the page
    try:
        total_h = await page.evaluate("document.body.scrollHeight")
        step_px = max(total_h // steps, 200)
        scrolled = 0
        while scrolled < total_h:
            scrolled = min(scrolled + step_px, total_h)
            await page.evaluate(f"window.scrollTo(0, {scrolled})")
            await asyncio.sleep(random.uniform(0.3, 0.9))
        # scroll back up a bit — humans don't stay at the bottom
        await page.evaluate(f"window.scrollTo(0, {int(total_h * 0.15)})")
        await asyncio.sleep(random.uniform(0.2, 0.5))
    except Exception:
        pass


# strong signals — any single one = definitely blocked
_BLOCK_STRONG = [
    "captcha", "cloudflare", "datadome", "ddos-guard",
    "verify you are human", "checking your browser",
    "ray id",
]

# weaker signals — need 2+ to call it blocked
# "please wait" alone is too common (Bayut loading spinners also say it)
_BLOCK_WEAK = [
    "challenge", "access denied", "bot protection",
    "security check", "please wait", "just a moment",
    "enable javascript", "you have been blocked",
]


async def is_blocked(page) -> bool:
    # checking again just in case site returns challenge page instead of real content
    try:
        title = (await page.title()).lower()
        body_txt = (await page.inner_text("body")).lower()
    except Exception:
        return False

    combined = title + " " + body_txt[:5000]

    if any(s in combined for s in _BLOCK_STRONG):
        return True

    weak_hits = sum(1 for s in _BLOCK_WEAK if s in combined)
    return weak_hits >= 2


def sv_json(data, file_path: Path):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, default=str)


def ld_json(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def strip_val(value):
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped if stripped else None

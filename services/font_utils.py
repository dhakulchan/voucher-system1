import os
import hashlib
from functools import lru_cache
from typing import List, Tuple
from utils.logging_config import get_logger

logger = get_logger(__name__)

FONT_DIRS = [
    os.path.join(os.getcwd(), 'static', 'fonts'),
    os.path.join(os.getcwd(), 'fonts'),
]

NOTO_FILES = {
    # Thai script fonts
    'NotoSansThai-Regular.ttf': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansThai/NotoSansThai-Regular.ttf',
    'NotoSansThai-Bold.ttf': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansThai/NotoSansThai-Bold.ttf',
    # Latin (and many other scripts) general UI font – nicer than Helvetica; does NOT include Thai glyphs
    'NotoSans-Regular.ttf': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf',
    'NotoSans-Bold.ttf': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Bold.ttf',
    'NotoSans-Medium.ttf': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Medium.ttf',
    'NotoSans-Italic.ttf': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Italic.ttf',
    # (Optional) Chinese Simplified subset (Single weight) for CJK block coverage.
    # Large file; only downloaded if Config.PDF_AUTO_DOWNLOAD_CJK true and requested in fallback list.
    'NotoSansCJKsc-Regular.otf': 'https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf',
}

_CJK_ONLY = {
    'NotoSansCJKsc-Regular.otf': 'https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf'
}

def ensure_font_dirs():
    created = []
    for d in FONT_DIRS:
        try:
            os.makedirs(d, exist_ok=True)
            created.append(d)
        except Exception:
            pass
    return created

def existing_noto_paths() -> List[str]:
    paths = []
    for d in FONT_DIRS:
        for fname in NOTO_FILES.keys():
            p = os.path.join(d, fname)
            if os.path.exists(p) and os.path.getsize(p) > 0:
                paths.append(p)
    return paths

def _file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

# Some Noto font subsets (compressed/hinted) can be ~35-40KB; lower threshold to avoid false corruption flags.
EXPECTED_MIN_SIZE = 30_000  # bytes heuristic (reduced from 50k)

def download_noto_if_missing(download: bool = True) -> List[str]:
    ensure_font_dirs()
    paths = existing_noto_paths()
    if paths or not download:
        return paths
    try:
        import requests
    except Exception:
        return paths
    from config import Config
    for fname, url in NOTO_FILES.items():
        if 'CJKsc' in fname and not getattr(Config,'PDF_AUTO_DOWNLOAD_CJK', True):
            continue
        target = os.path.join(FONT_DIRS[0], fname)
        if os.path.exists(target) and os.path.getsize(target) > 0:
            continue
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 200 and len(r.content) > 1024:
                with open(target, 'wb') as f:
                    f.write(r.content)
                logger.info("Downloaded font %s (%d bytes)", fname, len(r.content))
            else:
                logger.warning("Font download failed %s status=%s size=%d", fname, r.status_code, len(r.content))
        except Exception as e:
            logger.warning("Font download error %s err=%s", fname, e)
    return existing_noto_paths()

@lru_cache(maxsize=1)
def ensure_cjk_fonts(download: bool = True) -> List[str]:
    """Ensure CJK (Chinese) font available (separate cache to avoid earlier Thai-only cache)."""
    from config import Config
    if not getattr(Config,'PDF_AUTO_DOWNLOAD_CJK', True):
        return []
    ensure_font_dirs()
    # If already present return
    present = []
    for d in FONT_DIRS:
        p = os.path.join(d, 'NotoSansCJKsc-Regular.otf')
        if os.path.exists(p) and os.path.getsize(p) > 0:
            present.append(p)
    if present:
        return present
    if not download:
        return present
    # attempt download
    try:
        import requests
        fname, url = next(iter(_CJK_ONLY.items()))
        target = os.path.join(FONT_DIRS[0], fname)
        if not os.path.exists(target):
            r = requests.get(url, timeout=40)
            if r.status_code == 200 and len(r.content) > 1024:
                with open(target,'wb') as f:
                    f.write(r.content)
                logger.info("Downloaded CJK font %s (%d bytes)", fname, len(r.content))
            else:
                logger.warning("CJK font download failed status=%s size=%d", r.status_code, len(r.content))
    except Exception as e:
        logger.warning("CJK font download error %s", e)
    # Re-scan
    present = []
    for d in FONT_DIRS:
        p = os.path.join(d, 'NotoSansCJKsc-Regular.otf')
        if os.path.exists(p) and os.path.getsize(p) > 0:
            present.append(p)
    return present

@lru_cache(maxsize=1)
def ensure_thai_fonts(download: bool = True) -> List[str]:
    """Ensure Thai fonts exist locally; attempt download if missing.
    Returns list of file paths present after operation.
    Cached so repeated calls in same process are cheap."""
    paths = download_noto_if_missing(download=download)
    valid: List[str] = []
    for p in paths:
        try:
            size = os.path.getsize(p)
            if size < EXPECTED_MIN_SIZE:
                logger.warning("Font file too small - possible corruption %s size=%d", p, size)
                continue
            digest = _file_sha256(p)
            logger.debug("Font verified %s size=%d sha256=%s", p, size, digest[:10])
            valid.append(p)
        except Exception as e:
            logger.warning("Font validation error %s err=%s", p, e)
    if not valid:
        logger.error("No valid Thai font files available after ensure_thai_fonts")
    return valid


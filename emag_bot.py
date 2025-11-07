import time
import unicodedata
import base64
import io
from PIL import Image
import numpy as np
import cv2
import pytesseract
import re
import torch
import open_clip
from pathlib import Path
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
CLIP_MODEL = None
CLIP_PREPROCESS = None
CLIP_TOKENIZER = None
BASE_DIR = Path(__file__).resolve().parent
MAIN_URL = 'https://www.emag.ro/bilet-festival-beach-please-2026-persoana-general-access-costinesti-8-2-iulie-2026-1/pd/DJBBJQ3BM/'
TEST_URL = (BASE_DIR / 'test.html').as_uri()
CAPTCHA_TEST_URL = 'https://www.emag.ro/help/formular-de-retur/'
COOKIE_FILE = BASE_DIR / 'cookie.txt'
BLACK_FRIDAY_BANNER_URL = 'https://emag-video2.akamaized.net/encoding/delivery/thumbnail/126932_3904481065.jpg'
CAPTCHA_PLACEHOLDER = 'pune aici codu sa completezi captcha'
BUTTON_SELECTORS = ("//button[contains(translate(normalize-space(.), 'ĂÂÎȘȚăâîșț', 'AAISTaaist'), 'adauga in cos')]", "//a[contains(translate(normalize-space(.), 'ĂÂÎȘȚăâîșț', 'AAISTaaist'), 'adauga in cos')]", "//button[contains(@class, 'btn-add-to-cart')]", '.btn-add-to-cart', "button[name='addtocart']")
CART_SELECTORS = ("//i[contains(@class, 'navbar-icon')]", '.navbar-icon.d-flex.align-items-center.justify-content-center.icon-svg', "//svg[@viewBox='0 0 26 26']", "//a[contains(@href, 'cart')]")

CATEGORY_SYNONYMS_RAW = {
    "gălețile": "bucket",
    "găleata": "bucket",
    "galeata": "bucket",
    "găleți": "bucket",
    "păturile": "blanket",
    "perdelele": "curtain",
    "draperiile": "curtain",
    "draperie": "curtain",
    "pălăriile": "hat",
    "pălăria": "hat",
    "pălării": "hat",
    "palarie": "hat",
    "palaria": "hat",
    "florile": "flower",
    "floarea": "flower",
    "copacii": "tree",
    "copacul": "tree",
    "gentile": "bag",
    "gențile": "bag",
    "geanta": "bag",
    "geantă": "bag",
    "paturile": "bed",
    "patul": "bed",
    "pat": "bed",
    "ceasurile": "clock",
    "ceasul": "clock",
}

CATEGORY_SYNONYMS_NORMALIZED = {
    "galetile": "bucket",
    "galeata": "bucket",
    "galeti": "bucket",
    "gentile": "bag",
    "genti": "bag",
    "geanta": "bag",
    "poseta": "bag",
    "draperiile": "curtain",
    "perdelele": "curtain",
    "perdea": "curtain",
    "palariile": "hat",
    "palarie": "hat",
    "palarii": "hat",
    "palaria": "hat",
    "palari": "hat",
    "florile": "flower",
    "floare": "flower",
    "flori": "flower",
    "copacii": "tree",
    "copac": "tree",
    "paturile": "bed",
    "pat": "bed",
    "patura": "blanket",
    "paturi": "bed",
    "blanket": "blanket",
    "bed": "bed",
    "curtain": "curtain",
    "bag": "bag",
    "bucket": "bucket",
    "clock": "clock",
    "masini": "car",
    "masina": "car",
    "auto": "car",
    "cars": "car",
    "animale": "animal",
    "animal": "animal",
    "caini": "animal",
    "caine": "animal",
    "pisici": "animal",
    "pisica": "animal",
    "copaci": "tree",
    "tree": "tree"
}

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1280,720')
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
    chrome_options.add_argument('--allow-running-insecure-content')
    chrome_options.add_argument('--disable-setuid-sandbox')
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    prefs = {'credentials_enable_service': False, 'profile.password_manager_enabled': False, 'webrtc.ip_handling_policy': 'disable_non_proxied_udp', 'webrtc.multiple_routes_enabled': False, 'webrtc.nonproxied_udp_enabled': False}
    chrome_options.add_experimental_option('prefs', prefs)
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(8)
    try:
        driver.execute_cdp_cmd('Network.enable', {})
        driver.execute_cdp_cmd('Network.setCacheDisabled', {'cacheDisabled': True})
    except Exception:
        pass
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': "\n            Object.defineProperty(navigator, 'webdriver', {\n                get: () => undefined\n            });\n\n            Object.defineProperty(navigator, 'plugins', {\n                get: () => [1, 2, 3, 4, 5]\n            });\n\n            Object.defineProperty(navigator, 'languages', {\n                get: () => ['en-US', 'en']\n            });\n\n            window.chrome = {\n                runtime: {},\n                loadTimes: function() {},\n                csi: function() {},\n                app: {}\n            };\n\n            Object.defineProperty(navigator, 'permissions', {\n                get: () => ({\n                    query: () => Promise.resolve({ state: 'granted' })\n                })\n            });\n\n            const originalQuery = window.navigator.permissions.query;\n            window.navigator.permissions.query = (parameters) => (\n                parameters.name === 'notifications' ?\n                    Promise.resolve({ state: Notification.permission }) :\n                    originalQuery(parameters)\n            );\n\n            Object.defineProperty(navigator, 'platform', {\n                get: () => 'Win32'\n            });\n\n            Object.defineProperty(navigator, 'vendor', {\n                get: () => 'Google Inc.'\n            });\n\n            Object.defineProperty(navigator, 'appVersion', {\n                get: () => '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'\n            });\n\n            Object.defineProperty(navigator, 'maxTouchPoints', {\n                get: () => 0\n            });\n\n            Object.defineProperty(navigator, 'hardwareConcurrency', {\n                get: () => 8\n            });\n\n            Object.defineProperty(navigator, 'deviceMemory', {\n                get: () => 8\n            });\n\n            const getParameter = WebGLRenderingContext.prototype.getParameter;\n            WebGLRenderingContext.prototype.getParameter = function(parameter) {\n                if (parameter === 37445) {\n                    return 'Intel Inc.';\n                }\n                if (parameter === 37446) {\n                    return 'Intel Iris OpenGL Engine';\n                }\n                return getParameter.apply(this, arguments);\n            };\n\n            const getParameter2 = WebGL2RenderingContext.prototype.getParameter;\n            WebGL2RenderingContext.prototype.getParameter = function(parameter) {\n                if (parameter === 37445) {\n                    return 'Intel Inc.';\n                }\n                if (parameter === 37446) {\n                    return 'Intel Iris OpenGL Engine';\n                }\n                return getParameter2.apply(this, arguments);\n            };\n        "})

    def interceptor(request):
        return
    driver.request_interceptor = interceptor
    return driver

def simplify_text(value):
    if not value:
        return ''
    normalized = unicodedata.normalize('NFD', value)
    stripped = ''.join((ch for ch in normalized if unicodedata.category(ch) != 'Mn'))
    return stripped.lower()

def normalize_keyword(value):
    return simplify_text(value).strip()

def get_canonical_category(target):
    if not target:
        return None
    raw = target.strip().lower()
    if raw in CATEGORY_SYNONYMS_RAW:
        return CATEGORY_SYNONYMS_RAW[raw]
    normalized = normalize_keyword(raw)
    return CATEGORY_SYNONYMS_NORMALIZED.get(normalized)

def candidate_add_to_cart_elements(driver):
    elements = driver.find_elements(By.TAG_NAME, 'button') + driver.find_elements(By.TAG_NAME, 'a')
    for element in elements:
        text_sources = filter(None, [element.get_attribute('innerText'), element.text])
        flat_text = ' '.join(text_sources).strip()
        simplified = simplify_text(flat_text)
        if 'adauga' in simplified and 'cos' in simplified:
            yield element

def fast_click(driver, selector, wait):
    try:
        if selector.startswith('//'):
            element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
        else:
            element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
        driver.execute_script('arguments[0].click();', element)
        return True
    except Exception:
        return False

def find_add_to_cart_via_script(driver):
    script = "\n        const simplify = (value) => {\n            if (!value) return '';\n            return value.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();\n        };\n        const nodes = Array.from(document.querySelectorAll('button, a'));\n        const preferred = [];\n        for (const node of nodes) {\n            if (node.classList.contains('btn-add-to-cart') || node.classList.contains('yeahIWantThisProduct')) {\n                return node;\n            }\n            const text = [\n                node.innerText,\n                node.textContent,\n                node.getAttribute('title'),\n                node.getAttribute('aria-label')\n            ]\n                .filter(Boolean)\n                .join(' ')\n                .trim();\n            const simplified = simplify(text);\n            if (simplified.includes('adauga') && simplified.includes('cos')) {\n                return node;\n            }\n            const className = simplify(node.className || '');\n            const identifiers = [\n                node.getAttribute('data-offer-id'),\n                node.getAttribute('data-pnk'),\n                node.id,\n            ]\n                .filter(Boolean)\n                .map(simplify)\n                .join(' ');\n            if (className.includes('yeahiwantthisproduct') || className.includes('addtocart') ||\n                identifiers.includes('offer') || identifiers.includes('pnk')) {\n                preferred.push(node);\n            }\n        }\n        return preferred.length ? preferred[0] : null;\n    "
    try:
        element = driver.execute_script(script)
    except Exception:
        return None
    return element

def dismiss_banners(driver, timeout=5):
    end = time.monotonic() + timeout
    keywords = ('accept', 'acord', 'de acord', 'ok', 'close', 'inchide', 'consent')
    while time.monotonic() < end:
        dismissed = False
        elements = driver.find_elements(By.TAG_NAME, 'button') + driver.find_elements(By.TAG_NAME, 'a')
        for element in elements:
            text_sources = filter(None, [element.get_attribute('innerText'), element.get_attribute('textContent'), element.get_attribute('aria-label'), element.text])
            flat_text = ' '.join(text_sources).strip()
            simplified = simplify_text(flat_text)
            if not simplified:
                continue
            if any((kw in simplified for kw in keywords)):
                try:
                    driver.execute_script('arguments[0].click();', element)
                    dismissed = True
                    break
                except Exception:
                    pass
        if not dismissed:
            break
        time.sleep(0.1)

def wait_for_dom_ready(driver, timeout=10):
    WebDriverWait(driver, timeout).until(lambda d: d.execute_script('return document.readyState') == 'complete')

def find_captcha_container(driver):
    find_container_js = '\n    function analyze(elem) {\n        const rect = elem.getBoundingClientRect();\n        const style = window.getComputedStyle(elem);\n        const width = rect.width;\n        const height = rect.height;\n        const goodSize = width > 250 && width < 800 && height > 300 && height < 800;\n        const winWidth = window.innerWidth;\n        const centered = Math.abs((rect.left + rect.right) / 2 - winWidth / 2) < winWidth * 0.2;\n        const hasBorder = style.border !== \'none\' || style.boxShadow !== \'none\';\n        const hasBackground = style.backgroundColor !== \'rgba(0, 0, 0, 0)\' && style.backgroundColor !== \'transparent\';\n        const hasCanvas = elem.querySelector(\'canvas\') !== null;\n        const buttonCount = elem.querySelectorAll(\'button\').length;\n        const hasButtons = buttonCount >= 9;\n        const hasSubmit = elem.querySelector(\'button[type="submit"]\') !== null;\n        const text = elem.innerText || elem.textContent || \'\';\n        const hasText = /captcha|alege|select|toate|verify|security/i.test(text);\n        let score = 0;\n        if (goodSize) score += 3;\n        if (centered) score += 2;\n        if (hasBorder) score += 1;\n        if (hasBackground) score += 1;\n        if (hasCanvas) score += 4;\n        if (hasButtons) score += 3;\n        if (hasSubmit) score += 2;\n        if (hasText) score += 2;\n        return { element: elem, score, hasCanvas, buttonCount, rect };\n    }\n    const results = [];\n    document.querySelectorAll(\'div, section, form, article\').forEach(elem => {\n        const analysis = analyze(elem);\n        if (analysis.score > 5) {\n            results.push({\n                selector: elem.id ? \'#\' + elem.id : null,\n                score: analysis.score,\n                rect: analysis.rect,\n                hasCanvas: analysis.hasCanvas,\n                buttonCount: analysis.buttonCount\n            });\n        }\n    });\n    results.sort((a, b) => b.score - a.score);\n    return results[0] || null;\n    '
    try:
        return driver.execute_script(find_container_js)
    except Exception:
        return None

def detecting_captcha_frfr(driver):
    container = find_captcha_container(driver)
    if container:
        return True
    return detect_captcha(driver)

def detect_captcha(driver):
    detect_js = '\n    const targetDiv = document.querySelector(\'div[data-t="1"]\');\n    if (targetDiv) {\n        const text = targetDiv.innerText || targetDiv.textContent || \'\';\n        if (text.includes(\'Alegeți\') || text.includes(\'Selectați\')) {\n            return true;\n        }\n    }\n    if (document.querySelector(\'canvas button\')) {\n        return true;\n    }\n    const nodes = document.querySelectorAll(\'*\');\n    for (const node of nodes) {\n        const text = node.innerText || node.textContent || \'\';\n        if (text.includes(\'Am detectat trafic neobișnuit\') ||\n            text.includes(\'Alegeți toate\') ||\n            text.includes(\'Selectați toate\') ||\n            text.includes(\'verificare securitate\') ||\n            text.includes(\'security check\')) {\n            return true;\n        }\n    }\n    const canvases = document.querySelectorAll(\'canvas\');\n    for (const canvas of canvases) {\n        if ((canvas.width === 320 && canvas.height === 320) ||\n            (canvas.width === 300 && canvas.height === 300) ||\n            (canvas.width === 270 && canvas.height === 270)) {\n            return true;\n        }\n    }\n    if (document.querySelector(\'.amzn-captcha-container\')) {\n        return true;\n    }\n    const frames = document.querySelectorAll(\'iframe\');\n    for (const frame of frames) {\n        if (frame.src && (frame.src.includes(\'captcha\') || frame.src.includes(\'challenge\'))) {\n            return true;\n        }\n    }\n    return false;\n    '
    try:
        if driver.execute_script(detect_js):
            return True
        iframes = driver.find_elements(By.TAG_NAME, 'iframe')
        for iframe in iframes:
            try:
                driver.switch_to.frame(iframe)
                if driver.execute_script(detect_js):
                    driver.switch_to.default_content()
                    return True
                driver.switch_to.default_content()
            except:
                driver.switch_to.default_content()
        return False
    except Exception:
        return False

def get_captcha_target_from_image(driver):
    try:
        screenshot = driver.get_screenshot_as_png()
        img = Image.open(io.BytesIO(screenshot))
        img_array = np.array(img)
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        height, width = img_cv.shape[:2]
        captcha_region = img_cv[0:int(height * 0.5), 0:width]
        gray = cv2.cvtColor(captcha_region, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        text = pytesseract.image_to_string(thresh, lang='ron+eng')
        patterns = ['Alege[țt]i toate\\s+(.+?)(?:\\.|$)', 'Selecta[țt]i toate\\s+(.+?)(?:\\.|$)', 'toate\\s+(.+?)(?:\\.|$)', 'all\\s+(?:the\\s+)?(.+?)(?:\\.|$)', 'select\\s+all\\s+(?:the\\s+)?(.+?)(?:\\.|$)']
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                target = match.group(1).strip()
                target = target.replace('|', 'l').replace('0', 'o').replace('1', 'i')
                return target.lower()
        return None
    except Exception:
        return None

def get_captcha_target(driver):
    get_target_js = '\n    const mainDiv = document.querySelector(\'div[data-t="1"]\');\n    if (mainDiv) {\n        const boldUnderline = mainDiv.querySelector(\'b u\');\n        if (boldUnderline) {\n            const text = boldUnderline.innerText || boldUnderline.textContent;\n            if (text) return text;\n        }\n    }\n    const canvases = document.querySelectorAll(\'canvas\');\n    for (const canvas of canvases) {\n        let sibling = canvas.parentElement ? canvas.parentElement.previousElementSibling : null;\n        while (sibling) {\n            const text = sibling.innerText || sibling.textContent || \'\';\n            if (text.includes(\'Alegeți\') || text.includes(\'Selectați\')) {\n                const boldUnderline = sibling.querySelector(\'b u\');\n                if (boldUnderline) {\n                    const candidate = boldUnderline.innerText || boldUnderline.textContent;\n                    if (candidate) return candidate;\n                }\n            }\n            sibling = sibling.previousElementSibling;\n        }\n    }\n    const divs = document.querySelectorAll(\'div\');\n    for (const div of divs) {\n        const text = (div.innerText || div.textContent || \'\').trim();\n        if (text.includes(\'Alegeți toate\') || text.includes(\'Selectați toate\')) {\n            const boldUnderline = div.querySelector(\'b u\');\n            if (boldUnderline) {\n                const candidate = boldUnderline.innerText || boldUnderline.textContent;\n                if (candidate) return candidate;\n            }\n            const underline = div.querySelector(\'u\');\n            if (underline) {\n                const candidate = underline.innerText || underline.textContent;\n                if (candidate) return candidate;\n            }\n        }\n    }\n    const allBoldUnderlines = document.querySelectorAll(\'b u\');\n    for (const bu of allBoldUnderlines) {\n        const parent = bu.closest(\'div\');\n        if (!parent) continue;\n        const text = parent.innerText || parent.textContent || \'\';\n        if (text.includes(\'Alegeți\') || text.includes(\'Selectați\') || text.includes(\'Choose\') || text.includes(\'Select\')) {\n            const candidate = bu.innerText || bu.textContent;\n            if (candidate) return candidate;\n        }\n    }\n    return null;\n    '
    try:
        target = driver.execute_script(get_target_js)
        if target:
            return target.lower().strip()
        return None
    except Exception:
        return None

def get_captcha_canvas_data(driver):
    canvas_js = '\n    let canvas = document.querySelector(\'canvas[width="320"][height="320"]\') ||\n                 document.querySelector(\'canvas[width="300"][height="300"]\') ||\n                 document.querySelector(\'canvas.captcha-image\') ||\n                 document.querySelector(\'#amzn-captcha-internal-image-container canvas\') ||\n                 document.querySelector(\'canvas\');\n    if (!canvas) {\n        return null;\n    }\n    const rect = canvas.getBoundingClientRect();\n    const dpr = window.devicePixelRatio || 1;\n    return {\n        cssWidth: rect.width,\n        cssHeight: rect.height,\n        domWidth: canvas.width,\n        domHeight: canvas.height,\n        top: rect.top,\n        left: rect.left,\n        scrollX: window.scrollX,\n        scrollY: window.scrollY,\n        devicePixelRatio: dpr\n    };\n    '
    try:
        return driver.execute_script(canvas_js)
    except Exception:
        return None

def get_captcha_container_rect(driver):
    container_js = '\n    const instruction = document.querySelector(\'div[data-t="1"]\');\n    if (!instruction) return null;\n    let container = instruction.nextElementSibling;\n    while (container && container.nodeType !== 1) {\n        container = container.nextElementSibling;\n    }\n    if (!container) {\n        container = instruction.parentElement;\n    }\n    if (!container) return null;\n    const rect = container.getBoundingClientRect();\n    const dpr = window.devicePixelRatio || 1;\n    const buttons = container.querySelectorAll(\'button[type="button"]\');\n    return {\n        cssWidth: rect.width,\n        cssHeight: rect.height,\n        top: rect.top,\n        left: rect.left,\n        scrollX: window.scrollX,\n        scrollY: window.scrollY,\n        devicePixelRatio: dpr,\n        buttonCount: buttons.length\n    };\n    '
    try:
        return driver.execute_script(container_js)
    except Exception:
        return None

def extract_target_from_canvas_area(driver):
    try:
        canvas_data = get_captcha_canvas_data(driver)
        if not canvas_data:
            return None
        screenshot = driver.get_screenshot_as_png()
        img = Image.open(io.BytesIO(screenshot))
        dpr = canvas_data.get('devicePixelRatio', 1.0)
        css_width = canvas_data.get('cssWidth', canvas_data.get('domWidth', 0))
        canvas_top = int((canvas_data['top'] + canvas_data.get('scrollY', 0)) * dpr)
        canvas_left = int((canvas_data['left'] + canvas_data.get('scrollX', 0)) * dpr)
        instruction_height = int(150 * dpr)
        instruction_area = img.crop((max(0, canvas_left - 50), max(0, canvas_top - instruction_height), min(img.width, canvas_left + int(css_width * dpr) + 50), min(img.height, canvas_top)))
        img_array = np.array(instruction_area)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
        text = pytesseract.image_to_string(binary, lang='ron+eng')
        patterns = ['Alege[țt]i?\\s+toate\\s+([^\\s.]+)', 'Select(?:ați|eaza)?\\s+toate\\s+([^\\s.]+)', 'toate\\s+([^\\s.]+)']
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).lower().strip()
        return None
    except Exception:
        return None

def extract_images_from_full_screenshot(image):
    try:
        np_img = np.array(image)
        gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 40, 120)
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        height, width = gray.shape
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if 200 < w < 600 and 200 < h < 600:
                aspect = abs(w - h) / max(w, h)
                if aspect < 0.25:
                    area = w * h
                    candidates.append((area, x, y, w, h))
        if not candidates:
            return []
        candidates.sort(reverse=True)
        _, x, y, w, h = candidates[0]
        pad = 10
        x = max(0, x - pad)
        y = max(0, y - pad)
        w = min(width - x, w + pad * 2)
        h = min(height - y, h + pad * 2)
        grid_img = image.crop((x, y, x + w, y + h))
        grid_img.save('captcha_canvas.png')
        cell_width = max(1, w // 3)
        cell_height = max(1, h // 3)
        images = []
        for i in range(9):
            row = i // 3
            col = i % 3
            left = col * cell_width
            top = row * cell_height
            right = w if col == 2 else left + cell_width
            bottom = h if row == 2 else top + cell_height
            cell_img = grid_img.crop((left, top, right, bottom))
            buffer = io.BytesIO()
            cell_img.save(buffer, format='PNG')
            img_data = base64.b64encode(buffer.getvalue()).decode()
            images.append({'index': i + 1, 'dataUrl': f'data:image/png;base64,{img_data}', 'position': {'row': row, 'col': col}})
            cell_img.save(f'captcha_cell_{i + 1}.png')
        return images
    except Exception:
        return []

def extract_images_from_screenshot(driver):
    try:
        driver.execute_script('window.scrollBy(0, 300);')
        time.sleep(0.3)
        driver.execute_script("\n            const canvas = document.querySelector('canvas');\n            if (canvas) {\n                canvas.scrollIntoView({behavior: 'smooth', block: 'center'});\n            }\n        ")
        time.sleep(0.5)
        screenshot = driver.get_screenshot_as_png()
        img = Image.open(io.BytesIO(screenshot))
        canvas_info = get_captcha_canvas_data(driver)
        source_label = 'canvas'
        if not canvas_info:
            canvas_info = get_captcha_container_rect(driver)
            source_label = 'container'
        if not canvas_info:
            return extract_images_from_full_screenshot(img)
        dpr = canvas_info.get('devicePixelRatio', 1.0)
        css_width = canvas_info.get('cssWidth', canvas_info.get('domWidth', 0))
        css_height = canvas_info.get('cssHeight', canvas_info.get('domHeight', 0))
        x = int((canvas_info['left'] + canvas_info.get('scrollX', 0)) * dpr)
        y = int((canvas_info['top'] + canvas_info.get('scrollY', 0)) * dpr)
        width = int(css_width * dpr)
        height = int(css_height * dpr)
        x = max(0, min(x, img.width - 1))
        y = max(0, min(y, img.height - 1))
        x_end = max(x + 1, min(img.width, x + width))
        y_end = max(y + 1, min(img.height, y + height))
        canvas_img = img.crop((x, y, x_end, y_end))
        canvas_img.save('captcha_canvas.png')
        images = []
        actual_width = max(1, x_end - x)
        actual_height = max(1, y_end - y)
        cell_width = max(1, actual_width // 3)
        cell_height = max(1, actual_height // 3)
        for i in range(9):
            row = i // 3
            col = i % 3
            left = col * cell_width
            top = row * cell_height
            right = actual_width if col == 2 else left + cell_width
            bottom = actual_height if row == 2 else top + cell_height
            cell_img = canvas_img.crop((left, top, right, bottom))
            buffer = io.BytesIO()
            cell_img.save(buffer, format='PNG')
            img_data = base64.b64encode(buffer.getvalue()).decode()
            images.append({'index': i + 1, 'dataUrl': f'data:image/png;base64,{img_data}', 'position': {'row': row, 'col': col}})
            cell_img.save(f'captcha_cell_{i + 1}.png')
        return images
    except Exception:
        try:
            return extract_images_from_full_screenshot(Image.open(io.BytesIO(driver.get_screenshot_as_png())))
        except Exception as inner:
            return []

def get_captcha_images_advanced(driver):
    images = extract_images_from_screenshot(driver)
    if images:
        return images
    container = find_captcha_container(driver)
    get_images_js = '\n    function chooseCanvas(containerData) {\n        if (containerData && containerData.selector) {\n            const container = document.querySelector(containerData.selector);\n            if (container) {\n                const found = container.querySelector(\'canvas\');\n                if (found) return { canvas: found, strategy: \'container\' };\n            }\n        }\n        const bySize = Array.from(document.querySelectorAll(\'canvas\')).find(c => (c.width >= 270 && c.width <= 400) && (c.height >= 270 && c.height <= 400));\n        if (bySize) return { canvas: bySize, strategy: \'size\' };\n        const winWidth = window.innerWidth;\n        const byPosition = Array.from(document.querySelectorAll(\'canvas\')).find(c => {\n            const rect = c.getBoundingClientRect();\n            const center = rect.left + rect.width / 2;\n            return Math.abs(center - winWidth / 2) < winWidth * 0.3;\n        });\n        if (byPosition) return { canvas: byPosition, strategy: \'position\' };\n        const anyCanvas = document.querySelector(\'canvas\');\n        if (anyCanvas) return { canvas: anyCanvas, strategy: \'any\' };\n        return { canvas: null, strategy: \'\' };\n    }\n    const pick = chooseCanvas(arguments[0]);\n    if (!pick.canvas) return null;\n    const images = [];\n    const grid = 3;\n    const cellW = pick.canvas.width / grid;\n    const cellH = pick.canvas.height / grid;\n    for (let i = 0; i < grid * grid; i++) {\n        const row = Math.floor(i / grid);\n        const col = i % grid;\n        const temp = document.createElement(\'canvas\');\n        temp.width = cellW;\n        temp.height = cellH;\n        const ctx = temp.getContext(\'2d\');\n        ctx.drawImage(pick.canvas, col * cellW, row * cellH, cellW, cellH, 0, 0, cellW, cellH);\n        images.push({ index: i + 1, dataUrl: temp.toDataURL(\'image/png\'), position: { row, col } });\n    }\n    const buttons = [];\n    const buttonElements = pick.canvas.parentElement ? pick.canvas.parentElement.querySelectorAll(\'button[type="button"]\') : [];\n    buttonElements.forEach((btn, idx) => {\n        buttons.push({ index: idx + 1, tabIndex: btn.tabIndex, disabled: btn.disabled });\n    });\n    return { images, canvasInfo: { width: pick.canvas.width, height: pick.canvas.height, strategy: pick.strategy }, buttons };\n    '
    try:
        result = driver.execute_script(get_images_js, container)
        if result and result.get('images'):
            images = result['images']
            if result.get('buttons'):
                pass
            return images
        return []
    except Exception:
        return []

def get_captcha_images(driver):
    images = get_captcha_images_advanced(driver)
    if images:
        return images
    get_images_js = '\n    let canvas = document.querySelector(\'canvas[width="320"][height="320"]\') ||\n                 document.querySelector(\'canvas[width="300"][height="300"]\') ||\n                 document.querySelector(\'canvas.captcha-image\') ||\n                 document.querySelector(\'#amzn-captcha-internal-image-container canvas\') ||\n                 document.querySelector(\'canvas\');\n    if (!canvas) {\n        return null;\n    }\n    const images = [];\n    const grid = 3;\n    const cellWidth = canvas.width / grid;\n    const cellHeight = canvas.height / grid;\n    for (let i = 0; i < 9; i++) {\n        const row = Math.floor(i / 3);\n        const col = i % 3;\n        const tempCanvas = document.createElement(\'canvas\');\n        tempCanvas.width = cellWidth;\n        tempCanvas.height = cellHeight;\n        const tempCtx = tempCanvas.getContext(\'2d\');\n        tempCtx.drawImage(canvas, col * cellWidth, row * cellHeight, cellWidth, cellHeight, 0, 0, cellWidth, cellHeight);\n        images.push({ index: i + 1, dataUrl: tempCanvas.toDataURL(\'image/png\') });\n    }\n    return images;\n    '
    try:
        result = driver.execute_script(get_images_js)
        if result:
            return result
        return []
    except Exception:
        return []

def initialize_clip_model():
    global CLIP_MODEL, CLIP_PREPROCESS, CLIP_TOKENIZER
    if CLIP_MODEL is not None:
        return
    CLIP_MODEL, _, CLIP_PREPROCESS = open_clip.create_model_and_transforms('ViT-L-14', pretrained='laion2b_s32b_b82k')
    CLIP_TOKENIZER = open_clip.get_tokenizer('ViT-L-14')
    CLIP_MODEL.eval()

def analyze_image_with_clip(pil_image, target_category):
    initialize_clip_model()
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    image_tensor = CLIP_PREPROCESS(pil_image).unsqueeze(0)
    positive_prompts = []
    negative_prompts = []
    if target_category == 'bag':
        positive_prompts = ['a photo of a handbag', 'a photo of a purse', 'a photo of a bag with handles', 'a photo of a shoulder bag', 'a photo of a tote bag']
        negative_prompts = ['a photo of a bed', 'a photo of furniture', 'a photo of a clock', 'a photo of a hat']
    elif target_category == 'bed':
        positive_prompts = ['a photo of a bed', 'a photo of a mattress with pillows', 'a photo of bedroom furniture', 'a photo of a bed with headboard', 'a photo of bedding']
        negative_prompts = ['a photo of a bag', 'a photo of a purse', 'a photo of a clock', 'a photo of a hat']
    elif target_category == 'clock':
        positive_prompts = ['a photo of a clock', 'a photo of a wall clock', 'a photo of a timepiece']
        negative_prompts = ['a photo of a bag', 'a photo of a bed', 'a photo of furniture']
    elif target_category == 'hat':
        positive_prompts = ['a photo of a hat', 'a photo of a cap', 'a photo of headwear']
        negative_prompts = ['a photo of a bag', 'a photo of a bed', 'a photo of a clock']
    elif target_category == 'bucket':
        positive_prompts = ['a photo of a bucket', 'a photo of a pail', 'a photo of a metal bucket']
        negative_prompts = ['a photo of a bag', 'a photo of furniture']
    elif target_category == 'curtain':
        positive_prompts = ['a photo of curtains', 'a photo of drapes', 'a photo of window curtains']
        negative_prompts = ['a photo of a bed', 'a photo of a bag']
    elif target_category == 'chair':
        positive_prompts = ['a photo of a chair', 'a photo of an armchair', 'a photo of a seat', 'a photo of furniture to sit on']
        negative_prompts = ['a photo of a bed', 'a photo of a table', 'a photo of a bag']
    else:
        positive_prompts = [f'a photo of {target_category}', f'a photo of a {target_category}']
        negative_prompts = ['something else']
    all_prompts = positive_prompts + negative_prompts
    text_tokens = CLIP_TOKENIZER(all_prompts)
    with torch.no_grad():
        image_features = CLIP_MODEL.encode_image(image_tensor)
        text_features = CLIP_MODEL.encode_text(text_tokens)
        image_features /= image_features.norm(dim=-1, keepdim=True)
        text_features /= text_features.norm(dim=-1, keepdim=True)
        similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
    positive_score = similarity[0, :len(positive_prompts)].mean().item()
    negative_score = similarity[0, len(positive_prompts):].mean().item()
    final_score = positive_score / (positive_score + negative_score)
    return final_score

def analyze_image_with_ai(image_data_url, target):
    try:
        header, encoded = image_data_url.split(',', 1)
        image_data = base64.b64decode(encoded)
        image = Image.open(io.BytesIO(image_data))
        raw_target = target.strip().lower()
        normalized_target = normalize_keyword(raw_target)
        canonical = CATEGORY_SYNONYMS_RAW.get(raw_target, CATEGORY_SYNONYMS_NORMALIZED.get(normalized_target))
        if not canonical:
            return False
        clip_score = analyze_image_with_clip(image, canonical)
        return clip_score > 0.55
    except Exception:
        return analyze_image_for_target(image_data_url, target)

def analyze_with_embedding(embedding, canonical):
    emb_mean = np.mean(embedding)
    emb_std = np.std(embedding)
    emb_max = np.max(embedding)
    if canonical == 'bed':
        score = min(1.0, emb_std / 0.3) * 0.5 + min(1.0, emb_mean / 0.1) * 0.5
    elif canonical == 'bag':
        score = min(1.0, emb_std / 0.25) * 0.6 + (1 - min(1.0, emb_mean / 0.15)) * 0.4
    elif canonical == 'clock':
        score = min(1.0, emb_max / 0.5) * 0.7 + min(1.0, emb_std / 0.2) * 0.3
    else:
        score = 0.5
    return score

def analyze_with_features(features, canonical):
    if canonical == 'bed':
        score = features['has_bed_structure'] * 0.4 + min(1.0, features['horizontal_line_strength'] * 2.0) * 0.2 + features['has_bilateral_symmetry'] * 0.15 + (1 - features['has_bag_handle']) * 0.15 + (1 - features['has_circles']) * 0.1
        return score
    elif canonical == 'bag':
        score = features['has_bag_handle'] * 0.5 + features['has_handle_shape'] * 0.2 + (1 - features['has_bed_structure']) * 0.2 + (1 - features['has_circles']) * 0.1
        return score
    elif canonical == 'clock':
        score = features['has_circles'] * 0.5 + features['has_radial_symmetry'] * 0.3 + (1 - features['has_bed_structure']) * 0.2
        return score
    else:
        return 0.5

def analyze_image_for_target(image_data_url, target):
    try:
        header, encoded = image_data_url.split(',', 1)
        image_data = base64.b64decode(encoded)
        image = Image.open(io.BytesIO(image_data))
        img_array = np.array(image)
        height, width = img_array.shape[:2]
        if len(img_array.shape) == 2:
            img_array = np.stack([img_array] * 3, axis=-1)
        elif img_array.shape[2] == 4:
            img_array = img_array[:, :, :3]
        normalized_img = img_array.astype(float) / 255.0
        canonical = get_canonical_category(target)
        if not canonical:
            return (False, f"unknown category '{target}'")
        features = extract_image_features(normalized_img)
        if canonical == 'bucket':
            score = 0
            score += features['has_metallic_color'] * 0.3
            score += features['has_curved_edges'] * 0.3
            score += features['has_vertical_symmetry'] * 0.2
            score += features['has_handle_shape'] * 0.2
            return (score > 0.5, f"bucket score {score:.2f} (metallic {features['has_metallic_color']:.2f}, curved {features['has_curved_edges']:.2f}, symmetry {features['has_vertical_symmetry']:.2f}, handle {features['has_handle_shape']:.2f})")
        elif canonical == 'car':
            score = 0
            score += features['has_circles'] * 0.3
            score += features['is_horizontal'] * 0.2
            score += features['has_rectangular_shapes'] * 0.2
            score += features['has_dark_bottom'] * 0.3
            return (score > 0.5, f"car score {score:.2f} (circles {features['has_circles']}, horizontal {features['is_horizontal']}, rectangles {features['has_rectangular_shapes']}, dark_bottom {features['has_dark_bottom']:.2f})")
        elif canonical == 'flower':
            score = 0
            score += features['is_colorful'] * 0.3
            score += features['has_center_pattern'] * 0.3
            score += features['has_radial_symmetry'] * 0.2
            score += features['has_organic_shapes'] * 0.2
            return (score > 0.5, f"flower score {score:.2f} (colorful {features['is_colorful']:.2f}, center {features['has_center_pattern']}, radial {features['has_radial_symmetry']:.2f}, organic {features['has_organic_shapes']})")
        elif canonical == 'animal':
            score = 0
            score += features['has_texture'] * 0.3
            score += features['has_irregular_shape'] * 0.2
            score += features['has_bilateral_symmetry'] * 0.3
            score += features['has_face_features'] * 0.2
            return (score > 0.5, f"animal score {score:.2f} (texture {features['has_texture']}, irregular {features['has_irregular_shape']}, symmetry {features['has_bilateral_symmetry']:.2f}, face {features['has_face_features']:.2f})")
        elif canonical == 'tree':
            score = 0
            score += features['has_green_color'] * 0.3
            score += features['is_vertical'] * 0.3
            score += features['has_branching_pattern'] * 0.4
            return (score > 0.5, f"tree score {score:.2f} (green {features['has_green_color']}, vertical {features['is_vertical']}, branching {features['has_branching_pattern']})")
        elif canonical == 'bag':
            score = 0.0
            score += features['has_bag_handle'] * 0.5
            score += features['has_handle_shape'] * 0.2
            score += (1 - features['has_bed_structure']) * 0.2
            score += (1 - features['has_circles']) * 0.1
            return (score > 0.5, f'bag score {score:.2f}')
        elif canonical == 'blanket':
            score = 0
            score += min(1.0, features['horizontal_line_strength'] * 1.5) * 0.3
            score += features['has_texture'] * 0.3
            score += features['is_horizontal'] * 0.2
            score += (1 - features['has_handle_shape']) * 0.2
            return (score > 0.55, f"blanket score {score:.2f} (horizontal_lines {features['horizontal_line_strength']:.2f}, texture {features['has_texture']}, horizontal {features['is_horizontal']}, handle {features['has_handle_shape']})")
        elif canonical == 'bed':
            score = 0
            score += features['has_bed_structure'] * 0.4
            score += min(1.0, features['horizontal_line_strength'] * 2.0) * 0.2
            score += features['has_bilateral_symmetry'] * 0.15
            score += (1 - features['has_bag_handle']) * 0.15
            score += (1 - features['has_circles']) * 0.1
            return (score > 0.55, f'bed score {score:.2f}')
        elif canonical == 'curtain':
            score = 0
            score += features['is_vertical'] * 0.25
            score += min(1.0, features['vertical_line_strength'] * 1.3) * 0.35
            score += features['has_vertical_lines'] * 0.2
            score += (1 - features['has_circles']) * 0.2
            return (score > 0.6, f"curtain score {score:.2f} (vertical {features['is_vertical']}, vertical_lines {features['vertical_line_strength']:.2f}, has_vertical_lines {features['has_vertical_lines']}, circles {features['has_circles']})")
        elif canonical == 'clock':
            score = 0
            score += features['has_circles'] * 0.4
            score += features['has_radial_symmetry'] * 0.3
            score += (1 - features['has_rectangular_shapes']) * 0.2
            score += features['has_vertical_symmetry'] * 0.1
            return (score > 0.55, f"clock score {score:.2f} (circles {features['has_circles']}, radial {features['has_radial_symmetry']:.2f}, rectangles {features['has_rectangular_shapes']}, symmetry {features['has_vertical_symmetry']:.2f})")
        elif canonical == 'hat':
            score = 0
            score += features['has_curved_edges'] * 0.4
            score += features['has_circles'] * 0.3
            score += features['is_horizontal'] * 0.1
            score += (1 - features['has_rectangular_shapes']) * 0.2
            return (score > 0.55, f"hat score {score:.2f} (curved {features['has_curved_edges']}, circles {features['has_circles']}, horizontal {features['is_horizontal']}, rectangles {features['has_rectangular_shapes']})")
        return (False, f"no rule for category '{canonical}'")
    except Exception as e:
        return (False, f'error analyzing image: {e}')

def extract_image_features(img):
    features = {}
    mean_color = np.mean(img, axis=(0, 1))
    std_color = np.std(img, axis=(0, 1))
    features['has_metallic_color'] = np.all(std_color < 0.15) and np.all(np.abs(mean_color - 0.5) < 0.3)
    features['has_green_color'] = mean_color[1] > mean_color[0] and mean_color[1] > mean_color[2]
    features['is_colorful'] = np.mean(std_color) > 0.2
    gray = np.mean(img, axis=2)
    edges = detect_edges(gray)
    features['has_vertical_symmetry'] = calculate_symmetry(edges, axis='vertical')
    features['has_bilateral_symmetry'] = calculate_symmetry(edges, axis='horizontal')
    features['has_radial_symmetry'] = calculate_radial_symmetry(edges)
    horizontal_strength = float(np.mean(np.sum(edges, axis=1) / max(1, edges.shape[1])))
    vertical_strength = float(np.mean(np.sum(edges, axis=0) / max(1, edges.shape[0])))
    features['horizontal_line_strength'] = horizontal_strength
    features['vertical_line_strength'] = vertical_strength
    features['has_horizontal_lines'] = horizontal_strength > 0.4
    features['has_vertical_lines'] = vertical_strength > 0.4
    features['has_circles'] = detect_circles_advanced(edges)
    features['has_curved_edges'] = np.sum(edges) > 0 and detect_curved_lines(img)
    features['has_rectangular_shapes'] = detect_rectangles(edges)
    features['has_handle_shape'] = detect_handle_pattern(edges)
    features['has_bed_structure'] = detect_bed_structure(gray)
    features['has_bag_handle'] = detect_bag_handle(gray, edges)
    features['is_horizontal'] = img.shape[1] > img.shape[0] * 1.3
    features['is_vertical'] = img.shape[0] > img.shape[1] * 1.3
    features['has_texture'] = calculate_texture_score(gray)
    features['has_center_pattern'] = detect_center_pattern(img)
    features['has_branching_pattern'] = detect_branching(edges)
    features['has_organic_shapes'] = detect_organic_shapes(edges)
    features['aspect_ratio'] = img.shape[1] / max(1, img.shape[0])
    features['has_dark_bottom'] = np.mean(gray[int(gray.shape[0] * 0.7):, :]) < np.mean(gray[:int(gray.shape[0] * 0.3), :])
    features['has_face_features'] = detect_face_like_features(gray)
    features['has_irregular_shape'] = calculate_shape_irregularity(edges)
    features['has_distinct_object'] = np.sum(edges) > edges.size * 0.05
    center_region = gray[int(gray.shape[0] * 0.25):int(gray.shape[0] * 0.75), int(gray.shape[1] * 0.25):int(gray.shape[1] * 0.75)]
    features['has_large_central_object'] = np.std(center_region) > 0.1
    return features

def detect_edges(gray_img):
    dx = np.abs(np.diff(gray_img, axis=1))
    dy = np.abs(np.diff(gray_img, axis=0))
    edges = np.zeros_like(gray_img)
    edges[:-1, :-1] = dx[:-1, :] + dy[:, :-1] > 0.1
    return edges

def calculate_symmetry(img, axis='vertical'):
    if axis == 'vertical':
        left = img[:, :img.shape[1] // 2]
        right = img[:, img.shape[1] // 2:]
        right_flipped = np.fliplr(right)
    else:
        top = img[:img.shape[0] // 2, :]
        bottom = img[img.shape[0] // 2:, :]
        right_flipped = np.flipud(bottom)
        left = top
    min_shape = (min(left.shape[0], right_flipped.shape[0]), min(left.shape[1], right_flipped.shape[1]))
    left = left[:min_shape[0], :min_shape[1]]
    right_flipped = right_flipped[:min_shape[0], :min_shape[1]]
    return 1 - np.mean(np.abs(left - right_flipped))

def calculate_radial_symmetry(img):
    center = (img.shape[0] // 2, img.shape[1] // 2)
    scores = []
    for angle in range(0, 360, 45):
        rotated = rotate_image(img, angle, center)
        similarity = 1 - np.mean(np.abs(img - rotated))
        scores.append(similarity)
    return np.mean(scores)

def rotate_image(img, angle, center):
    return img

def detect_circles_advanced(edges):
    h, w = edges.shape
    center = (h // 2, w // 2)
    radius_range = range(min(h, w) // 6, min(h, w) // 2)
    for r in radius_range:
        circle_pixels = 0
        total_pixels = 0
        for angle in np.linspace(0, 2 * np.pi, 36):
            x = int(center[1] + r * np.cos(angle))
            y = int(center[0] + r * np.sin(angle))
            if 0 <= x < w and 0 <= y < h:
                total_pixels += 1
                if edges[y, x]:
                    circle_pixels += 1
        if total_pixels > 0 and circle_pixels / total_pixels > 0.5:
            return True
    return False

def detect_rectangles(edges):
    h, w = edges.shape
    horizontal_lines = np.sum(edges, axis=1) > w * 0.5
    vertical_lines = np.sum(edges, axis=0) > h * 0.5
    return np.sum(horizontal_lines) >= 2 and np.sum(vertical_lines) >= 2

def detect_handle_pattern(edges):
    h, w = edges.shape
    top_half = edges[:h // 2, :]
    curve_score = 0
    for row in range(h // 4):
        row_edges = top_half[row, :]
        if np.sum(row_edges) > w * 0.2 and np.sum(row_edges) < w * 0.8:
            left_concentration = np.sum(row_edges[:w // 3])
            right_concentration = np.sum(row_edges[2 * w // 3:])
            middle_concentration = np.sum(row_edges[w // 3:2 * w // 3])
            if left_concentration + right_concentration > middle_concentration * 2:
                curve_score += 1
    return curve_score > h // 8

def calculate_texture_score(gray_img):
    dx = np.diff(gray_img, axis=1)
    dy = np.diff(gray_img, axis=0)
    texture = np.std(dx) + np.std(dy)
    return texture > 0.1 and texture < 0.5

def detect_branching(edges):
    h, w = edges.shape
    vertical_concentration = np.sum(edges[:, w // 3:2 * w // 3], axis=0)
    has_trunk = np.any(vertical_concentration > h * 0.5)
    top_spread = np.sum(edges[:h // 3, :]) > np.sum(edges[2 * h // 3:, :]) * 1.5
    return has_trunk and top_spread

def detect_organic_shapes(edges):
    h, w = edges.shape
    irregularity = 0
    for i in range(1, h - 1):
        for j in range(1, w - 1):
            if edges[i, j]:
                neighbors = edges[i - 1:i + 2, j - 1:j + 2]
                if 2 <= np.sum(neighbors) <= 4:
                    irregularity += 1
    return irregularity > np.sum(edges) * 0.3

def detect_face_like_features(gray_img):
    h, w = gray_img.shape
    upper_half = gray_img[:h // 2, :]
    dark_spots = upper_half < np.mean(upper_half) - np.std(upper_half)
    left_dark = np.sum(dark_spots[:, :w // 2])
    right_dark = np.sum(dark_spots[:, w // 2:])
    return abs(left_dark - right_dark) < dark_spots.size * 0.1 and left_dark > dark_spots.size * 0.02

def calculate_shape_irregularity(edges):
    if np.sum(edges) == 0:
        return 0
    contour = edges.copy()
    perimeter = np.sum(contour)
    area = np.sum(edges)
    if area == 0:
        return 0
    ratio = perimeter / np.sqrt(area)
    return ratio > 5

def detect_bed_structure(gray):
    h, w = gray.shape
    thirds = h // 3
    top_band = gray[:thirds, :]
    middle_band = gray[thirds:2 * thirds, :]
    bottom_band = gray[2 * thirds:, :]
    top_mean = np.mean(top_band)
    middle_mean = np.mean(middle_band)
    bottom_mean = np.mean(bottom_band)
    h_edges = np.abs(np.diff(gray, axis=0))
    strong_horizontal_rows = np.sum(h_edges, axis=1) > w * 0.5 * 0.1
    has_wide_horizontal = np.sum(strong_horizontal_rows) > h * 0.1
    col_variance = np.std(gray, axis=0)
    occupied_cols = np.sum(col_variance > 0.05)
    fills_width = occupied_cols > w * 0.7
    row_variance = np.std(gray, axis=1)
    occupied_rows = np.sum(row_variance > 0.05)
    fills_height = occupied_rows > h * 0.6
    score = 0.0
    if has_wide_horizontal:
        score += 0.35
    if fills_width:
        score += 0.35
    if fills_height:
        score += 0.3
    return score

def detect_bag_handle(gray, edges):
    h, w = gray.shape
    top_region = gray[:h // 3, :]
    top_edges = edges[:h // 3, :]
    top_mean = np.mean(top_region)
    left_edge_density = np.sum(top_edges[:, :w // 4]) / max(1, h // 3 * (w // 4))
    right_edge_density = np.sum(top_edges[:, 3 * w // 4:]) / max(1, h // 3 * (w // 4))
    center_edge_density = np.sum(top_edges[:, w // 4:3 * w // 4]) / max(1, h // 3 * (w // 2))
    has_side_connections = left_edge_density + right_edge_density > center_edge_density * 1.5
    top_middle_col = top_region[:, w // 2]
    has_arch = np.std(top_middle_col) > 0.1
    score = 0
    if has_side_connections:
        score += 0.5
    if has_arch:
        score += 0.3
    if top_mean < np.mean(gray[h // 2:, :]):
        score += 0.2
    return score

def detect_curved_lines(img):
    try:
        if len(img.shape) == 3:
            gray = np.mean(img, axis=2)
        else:
            gray = img
        edges = detect_edges(gray)
        h, w = edges.shape
        curve_count = 0
        for i in range(1, h - 1):
            for j in range(1, w - 1):
                if edges[i, j]:
                    neighbors = edges[i - 1:i + 2, j - 1:j + 2]
                    if np.sum(neighbors) == 3:
                        curve_count += 1
        return curve_count > np.sum(edges) * 0.2
    except:
        return False

def detect_center_pattern(img):
    try:
        if len(img.shape) == 3:
            gray = np.mean(img, axis=2)
        else:
            gray = img
        h, w = gray.shape
        center_y, center_x = (h // 2, w // 2)
        center_region = gray[max(0, center_y - h // 6):min(h, center_y + h // 6), max(0, center_x - w // 6):min(w, center_x + w // 6)]
        radial_score = 0
        for r in range(min(h, w) // 6, min(h, w) // 2, 5):
            ring_values = []
            for angle in np.linspace(0, 2 * np.pi, 16):
                x = int(center_x + r * np.cos(angle))
                y = int(center_y + r * np.sin(angle))
                if 0 <= x < w and 0 <= y < h:
                    ring_values.append(gray[y, x])
            if ring_values:
                radial_score += np.std(ring_values) < 0.2
        return radial_score > 3 and np.mean(center_region) != np.mean(gray)
    except:
        return False

def solve_captcha(driver):
    if not detect_captcha(driver):
        return True
    print('Captcha detectat')
    try:
        driver.save_screenshot('captcha_debug.png')
    except:
        pass
    start_time = time.time()
    target = get_captcha_target(driver)
    attempt = 0
    while not target and time.time() - start_time < 20:
        attempt += 1
        time.sleep(0.25)
        try:
            driver.switch_to.default_content()
        except Exception:
            pass
        target = get_captcha_target(driver)
        if not target:
            try:
                underlined = driver.execute_script("\n                    const underlines = document.querySelectorAll('u');\n                    for (const u of underlines) {\n                        const text = u.innerText || u.textContent;\n                        if (text && text.length > 2 && text.length < 20) {\n                            return text;\n                        }\n                    }\n                    return null;\n                ")
                if underlined:
                    target = underlined
                    continue
                iframes = driver.find_elements(By.TAG_NAME, 'iframe')
                for iframe in iframes:
                    try:
                        driver.switch_to.frame(iframe)
                        target = get_captcha_target(driver)
                        driver.switch_to.default_content()
                        if target:
                            break
                    except:
                        driver.switch_to.default_content()
                if not target:
                    pattern_search = driver.execute_script('\n                        const allText = document.body.innerText;\n                        const patterns = [\n                            /select.{0,10}all.{0,10}(.+?)(?:\\.|$)/i,\n                            /choose.{0,10}all.{0,10}(.+?)(?:\\.|$)/i,\n                            /toate\\s+(.+?)(?:\\.|$)/i,\n                            /all\\s+the\\s+(.+?)(?:\\.|$)/i\n                        ];\n\n                        for (const pattern of patterns) {\n                            const match = allText.match(pattern);\n                            if (match && match[1]) {\n                                return match[1].trim();\n                            }\n                        }\n                        return null;\n                    ')
                    if pattern_search:
                        target = pattern_search
                    if not target and attempt % 3 == 0:
                        ocr_target = get_captcha_target_from_image(driver)
                        if ocr_target:
                            target = ocr_target
                        else:
                            canvas_ocr = extract_target_from_canvas_area(driver)
                            if canvas_ocr:
                                target = canvas_ocr
            except Exception:
                pass
    if not target:
        return False
    print(f'Cuvant Captcha: {target}')
    canonical = get_canonical_category(target)
    images = get_captcha_images(driver)
    if not images:
        return False
    selected_indices = []
    for img_data in images:
        if analyze_image_with_ai(img_data['dataUrl'], target):
            selected_indices.append(img_data['index'])
    if not selected_indices:
        selected_indices = [1, 4, 7]
    print(f"Captcha corect: {','.join((str(i) for i in selected_indices))}")
    CAPTCHA_PLACEHOLDER
    return False

def apply_emag_cookies(driver):
    if not COOKIE_FILE.exists():
        return False
    try:
        raw = COOKIE_FILE.read_text(encoding='utf-8').strip()
    except Exception:
        return False
    if not raw:
        return False
    try:
        driver.get('https://www.emag.ro/')
        driver.delete_all_cookies()
        segments = []
        for line in raw.splitlines():
            segments.extend([part.strip() for part in line.split(';') if part.strip()])
        applied = False
        for segment in segments:
            if '=' not in segment:
                continue
            name, value = segment.split('=', 1)
            cookie = {'name': name.strip(), 'value': value.strip(), 'domain': '.emag.ro'}
            try:
                driver.add_cookie(cookie)
                applied = True
            except Exception:
                continue
        if applied:
            driver.refresh()
        return applied
    except Exception:
        return False

def ensure_initial_captcha(driver):
    if detecting_captcha_frfr(driver):
        solve_captcha(driver)

def wait_for_black_friday_banner(driver, timeout=120, refresh_delay=0.35):
    deadline = time.monotonic() + timeout
    target_url = driver.current_url
    while time.monotonic() < deadline:
        try:
            source = driver.execute_script('return document.body ? document.body.innerHTML : ""')
        except Exception:
            source = driver.page_source
        if BLACK_FRIDAY_BANNER_URL not in source:
            return True
        print('ERROARE: BLACK FRIDAY NU A INCEPUT')
        try:
            driver.execute_script('window.stop();')
        except Exception:
            pass
        try:
            driver.get(target_url)
        except Exception:
            driver.refresh()
        try:
            wait_for_dom_ready(driver, timeout=5)
        except Exception:
            pass
        ensure_initial_captcha(driver)
        time.sleep(refresh_delay)
    return False

def check_product_added(driver):
    check_js = "\n    const elements = document.querySelectorAll('*');\n    for (const elem of elements) {\n        const text = (elem.innerText || elem.textContent || '').toLowerCase();\n        if (text.includes('produsul a fost adaugat in cos')) {\n            return true;\n        }\n    }\n    return false;\n    "
    try:
        return driver.execute_script(check_js)
    except Exception:
        return False

def click_add_to_cart(driver):
    initial_url = driver.current_url
    refresh_count = 0
    max_refreshes = 10
    product_added = False
    solve_captcha(driver)
    while refresh_count < max_refreshes and (not product_added):
        fast_click_js = '\n        const buttons = Array.from(document.querySelectorAll(\'button, a\'));\n        for (const btn of buttons) {\n            const rect = btn.getBoundingClientRect();\n            if (rect.width > 80 && rect.width < 400 && rect.height > 30 && rect.height < 80) {\n                const style = window.getComputedStyle(btn);\n                const bg = style.backgroundColor;\n                if (bg.includes(\'rgb\') && \n                    (bg.includes(\'255, 9\') || bg.includes(\'255, 10\') || \n                     bg.includes(\'254, 9\') || bg.includes(\'254, 10\') ||\n                     bg.includes(\'255, 0\') || bg.includes(\'254, 0\'))) {\n                    btn.scrollIntoView({block: \'center\'});\n                    btn.click();\n                    return true;\n                }\n            }\n        }\n\n        const simplify = (text) => text.normalize(\'NFD\').replace(/[̀-ͯ]/g, \'\').toLowerCase();\n        for (const elem of buttons) {\n            const text = simplify(elem.innerText || elem.textContent || \'\');\n            if (text.includes(\'adauga\') && (text.includes(\'cos\') || text.includes(\'cost\'))) {\n                elem.scrollIntoView({block: \'center\'});\n                elem.click();\n                return true;\n            }\n        }\n\n        const selectors = [\n            \'.btn-add-to-cart\',\n            \'[data-offer-id]\',\n            \'[data-pnk]\',\n            \'.yeahIWantThisProduct\',\n            \'button[type="submit"]\'\n        ];\n        for (const sel of selectors) {\n            const elem = document.querySelector(sel);\n            if (elem) {\n                elem.scrollIntoView({block: \'center\'});\n                elem.click();\n                return true;\n            }\n        }\n\n        return false;\n        '
        try:
            driver.execute_script("\n                document.querySelectorAll('button').forEach(btn => {\n                    const text = (btn.innerText || '').toLowerCase();\n                    if (text.includes('accept') || text.includes('consent') || \n                        text.includes('acord') || text === 'ok') {\n                        btn.click();\n                    }\n                });\n            ")
            clicked = driver.execute_script(fast_click_js)
            if clicked:
                time.sleep(0.5)
                if check_product_added(driver):
                    product_added = True
                    time.sleep(0.5)
                    if click_vezi_detalii(driver):
                        return True
                if driver.current_url != initial_url or 'cos' in driver.current_url.lower():
                    return True
        except Exception:
            pass
        try:
            wait = WebDriverWait(driver, 2)
            for selector in BUTTON_SELECTORS[:3]:
                try:
                    if selector.startswith('//'):
                        elem = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                    else:
                        elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    driver.execute_script('arguments[0].click();', elem)
                    time.sleep(0.5)
                    if check_product_added(driver):
                        product_added = True
                        time.sleep(0.5)
                        if click_vezi_detalii(driver):
                            return True
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        if not product_added:
            time.sleep(1)
            driver.refresh()
            refresh_count += 1
            time.sleep(2)
            solve_captcha(driver)
    return product_added

def click_cart_icon(driver):
    cart_click_js = '\n    const selectors = [\n        \'i.navbar-icon\',\n        \'svg[viewBox="0 0 26 26"]\',\n        \'a[href*="cart"]\',\n        \'a[href*="cos"]\',\n        \'.icon-svg\'\n    ];\n\n    for (const sel of selectors) {\n        const elem = document.querySelector(sel);\n        if (elem) {\n            const clickable = elem.closest(\'a, button\') || elem;\n            clickable.click();\n            return true;\n        }\n    }\n\n    const svgs = document.querySelectorAll(\'svg\');\n    for (const svg of svgs) {\n        if (svg.innerHTML.includes(\'M8.63116 16.8992\') || \n            svg.innerHTML.includes(\'M0.879591 2.81684\')) {\n            const clickable = svg.closest(\'a, button\') || svg.parentElement;\n            if (clickable) {\n                clickable.click();\n                return true;\n            }\n        }\n    }\n\n    return false;\n    '
    try:
        if driver.execute_script(cart_click_js):
            return True
    except Exception:
        pass
    try:
        wait = WebDriverWait(driver, 2)
        elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='cart'], a[href*='cos']")))
        driver.execute_script('arguments[0].click();', elem)
        return True
    except Exception:
        pass
    return False

def resolve_user_choice():
    prompt = '[1] main\n[2] test\n[3] captcha emag test\n[4] Cookie Help\n'
    while True:
        choice = input(prompt).strip()
        if choice == '4':
            continue
        if choice in ('1', '2', '3'):
            return choice

def main():
    driver = setup_driver()
    try:
        choice = resolve_user_choice()
        if choice == '1':
            apply_emag_cookies(driver)
            driver.get(MAIN_URL)
            ensure_initial_captcha(driver)
            wait_for_black_friday_banner(driver)
            ensure_initial_captcha(driver)
            click_add_to_cart(driver)
            time.sleep(5)
        elif choice == '2':
            driver.get(TEST_URL)
            ensure_initial_captcha(driver)
            click_add_to_cart(driver)
            time.sleep(5)
        else:
            driver.get(CAPTCHA_TEST_URL)
            ensure_initial_captcha(driver)
            for _ in range(10):
                if detecting_captcha_frfr(driver):
                    break
                time.sleep(1)
            solve_captcha(driver)
            time.sleep(5)
    finally:
        driver.quit()
if __name__ == '__main__':
    main()

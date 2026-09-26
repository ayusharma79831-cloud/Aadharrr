# ============================================================
# AADHAAR PDF BOT — FINAL (Windows + Railway)
# Owner: @L0RD_DANZO
# Storage: JSON (reset pe clear)
# Buttons: COLORED (primary/success/danger)
# QR: /addqr se add, /removeqr se remove (owner only)
# ============================================================

import requests, json, base64, uuid, re, os, sys, time, logging, random, string, threading
from datetime import datetime
from io import BytesIO
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
import PyPDF2

# ============== OCR PRE-LOAD ==============
try:
    import ddddocr as _ddddocr
    _DDDD_MAIN = _ddddocr.DdddOcr(show_ad=False)
    try: _DDDD_BETA = _ddddocr.DdddOcr(show_ad=False, beta=True)
    except Exception: _DDDD_BETA = None
    _DDDD_OK = True
except Exception as _e:
    _DDDD_MAIN = _DDDD_BETA = None; _DDDD_OK = False
    print(f"[WARN] ddddocr: {_e}")

try:
    import pytesseract as _pytesseract
    _pytesseract.get_tesseract_version(); _TESS_OK = True
except Exception as _e:
    _TESS_OK = False; print(f"[WARN] pytesseract: {_e}")

# ============== LOGGING ==============
logging.basicConfig(level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

# ============== CONFIG ==============
TELEGRAM_BOT_TOKEN = "8843463127:AAG1eZZ3hTe9hsQ4JsST07RbD4IBSwj-oPw"
BOT_NAME           = "AYUSH_AADHAR_PDF_BOT"
OWNER_ID           = 8696846732
OWNER_USERNAME     = "@L0RD_DANZO"
APPROVER_ID        = 8696846732
CHANNEL_USERNAME   = "@AYUSH_X_GOD"
CHANNEL_LINK       = "https://t.me/AYUSH_X_GOD"
SESSION_TIMEOUT    = 600
UIDAI_PROXY        = "http://117.236.124.166:3128"
DIVIDER            = "━━━━━━━━━━━━━━━━━━━━━━━"
UPI_ID             = "ayush.sharma798@fam"
UPI_NAME           = "AYUSH"

# ============== PATHS ==============
DATA_DIR = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", ".")
os.makedirs(DATA_DIR, exist_ok=True)
USERS_FILE    = os.path.join(DATA_DIR, "users.json")
CODES_FILE    = os.path.join(DATA_DIR, "codes.json")
VIDEOS_FILE   = os.path.join(DATA_DIR, "videos.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
PENDING_FILE  = os.path.join(DATA_DIR, "pending_payments.json")
QR_FILE       = os.path.join(DATA_DIR, "qr.jpg")

def get_qr_path():
    return QR_FILE if os.path.exists(QR_FILE) else None

# ============== JSON ==============
_file_lock = threading.Lock()

def load_json(path, default=None):
    if default is None: default = {}
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"load_json {path}: {e}")
    return default

def save_json(path, data):
    try:
        tmp = path + ".tmp"
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        return True
    except Exception as e:
        logger.error(f"save_json {path}: {e}")
        return False

# ============== SETTINGS ==============
def get_settings(): return load_json(SETTINGS_FILE, {'bot_locked': False})
def save_settings(s): save_json(SETTINGS_FILE, s)
def is_bot_locked(): return get_settings().get('bot_locked', False)

# ============== USERS ==============
def _load_users(): return load_json(USERS_FILE, {})
def _save_users(d): save_json(USERS_FILE, d)

def get_user(uid): return _load_users().get(str(uid))

def ensure_user(uid, referrer_id=None, username=None, first_name=None):
    with _file_lock:
        data = _load_users(); k = str(uid)
        if k in data:
            data[k]['username'] = username; data[k]['first_name'] = first_name
            _save_users(data); return False
        data[k] = {
            'credits': 1, 'referred_by': str(referrer_id) if referrer_id else None,
            'referral_count': 0, 'joined': datetime.now().isoformat(),
            'is_premium': False, 'is_admin': False, 'is_banned': False,
            'username': username, 'first_name': first_name,
        }
        if referrer_id and str(referrer_id) != k:
            rk = str(referrer_id)
            if rk in data:
                data[rk]['credits'] = data[rk].get('credits', 0) + 1
                data[rk]['referral_count'] = data[rk].get('referral_count', 0) + 1
                try:
                    send_message(int(rk), f"<b>{BOT_NAME}</b>\n{DIVIDER}\n"
                        f"<b>[ Referral Reward ]</b>\n\n"
                        f"◈  New user joined!\n◈  +1 credit\n"
                        f"◈  Total: {data[rk]['credits']}\n\n{DIVIDER}")
                except Exception: pass
        _save_users(data); return True

def get_credits(uid):
    u = get_user(uid); return u.get('credits', 0) if u else 0

def has_credits(uid):
    u = get_user(uid)
    if u and (u.get('is_premium') or u.get('is_admin')): return True
    return get_credits(uid) > 0

def add_credits(uid, amount):
    with _file_lock:
        data = _load_users(); k = str(uid)
        if k not in data:
            data[k] = {'credits': 0, 'joined': datetime.now().isoformat(),
                       'is_premium': False, 'is_admin': False, 'is_banned': False}
        data[k]['credits'] = data[k].get('credits', 0) + amount
        _save_users(data)

def deduct_credit(uid):
    u = get_user(uid)
    if u and (u.get('is_premium') or u.get('is_admin')): return
    with _file_lock:
        data = _load_users(); k = str(uid)
        if k in data:
            data[k]['credits'] = max(0, data[k].get('credits', 0) - 1)
            _save_users(data)

def set_premium(uid, status):
    with _file_lock:
        data = _load_users(); k = str(uid)
        if k in data: data[k]['is_premium'] = bool(status); _save_users(data)

def set_admin(uid, status):
    with _file_lock:
        data = _load_users(); k = str(uid)
        if k in data: data[k]['is_admin'] = bool(status); _save_users(data)

def set_banned(uid, status):
    with _file_lock:
        data = _load_users(); k = str(uid)
        if k in data: data[k]['is_banned'] = bool(status); _save_users(data)

def is_owner(uid): return uid == OWNER_ID
def is_admin(uid):
    if uid == OWNER_ID: return True
    u = get_user(uid); return bool(u and u.get('is_admin'))
def is_premium(uid):
    if uid == OWNER_ID: return True
    u = get_user(uid); return bool(u and (u.get('is_premium') or u.get('is_admin')))
def is_banned(uid):
    u = get_user(uid); return bool(u and u.get('is_banned'))

# ============== VIDEOS ==============
def _load_videos(): return load_json(VIDEOS_FILE, [])
def _save_videos(v): save_json(VIDEOS_FILE, v)

def add_video(file_id, caption=None):
    vids = _load_videos()
    if any(v['file_id'] == file_id for v in vids): return False
    vids.append({'file_id': file_id, 'caption': caption, 'added': datetime.now().isoformat()})
    _save_videos(vids); return True

def get_random_video():
    vids = _load_videos(); return random.choice(vids) if vids else None

def get_all_videos(): return _load_videos()

def delete_video(idx):
    vids = _load_videos()
    if 0 <= idx < len(vids): vids.pop(idx); _save_videos(vids); return True
    return False

def video_count(): return len(_load_videos())

# ============== CODES ==============
def _load_codes(): return load_json(CODES_FILE, {})
def _save_codes(c): save_json(CODES_FILE, c)

def gen_code(amount):
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    with _file_lock:
        codes = _load_codes()
        codes[code] = {'amount': amount, 'used': False, 'created': datetime.now().isoformat()}
        _save_codes(codes)
    return code

def redeem_code(uid, code):
    code = code.upper().strip()
    with _file_lock:
        codes = _load_codes()
        if code not in codes: return False, "Invalid code"
        if codes[code]['used']: return False, "Code already used"
        amount = codes[code]['amount']
        codes[code]['used'] = True; codes[code]['used_by'] = uid
        codes[code]['used_at'] = datetime.now().isoformat()
        _save_codes(codes)
    add_credits(uid, amount); return True, amount

# ============== PENDING PAYMENTS ==============
def _load_pending(): return load_json(PENDING_FILE, {})
def _save_pending(p): save_json(PENDING_FILE, p)

def add_pending(user_id, credits, price, screenshot_file_id):
    with _file_lock:
        p = _load_pending()
        req_id = str(int(time.time() * 1000))[-10:]
        p[req_id] = {'user_id': user_id, 'credits': credits, 'price': price,
                     'screenshot': screenshot_file_id, 'status': 'pending',
                     'created': datetime.now().isoformat()}
        _save_pending(p); return req_id

def get_pending(req_id): return _load_pending().get(str(req_id))

def approve_pending(req_id):
    with _file_lock:
        p = _load_pending()
        if str(req_id) not in p: return None
        if p[str(req_id)]['status'] != 'pending': return None
        p[str(req_id)]['status'] = 'approved'; _save_pending(p)
        return p[str(req_id)]

def reject_pending(req_id):
    with _file_lock:
        p = _load_pending()
        if str(req_id) not in p: return None
        p[str(req_id)]['status'] = 'rejected'; _save_pending(p)
        return p[str(req_id)]

# ============== SESSION FACTORY ==============
def create_session(use_proxy=False, proxy_string=None):
    s = requests.Session()
    s.mount('https://', requests.adapters.HTTPAdapter(
        pool_connections=5, pool_maxsize=5, max_retries=3, pool_block=False))
    if use_proxy and proxy_string:
        parsed = urlparse(proxy_string)
        pu = f"{parsed.scheme}://{parsed.netloc}"
        s.proxies = {'http': pu, 'https': pu}
    return s

telegram_session = None
def get_telegram_session():
    global telegram_session
    if telegram_session is None: telegram_session = create_session(False, None)
    return telegram_session

uidai_session = None
def get_uidai_session():
    global uidai_session
    if uidai_session is None: uidai_session = create_session(True, UIDAI_PROXY)
    return uidai_session

def set_uidai_proxy(p):
    global UIDAI_PROXY, uidai_session, bot
    UIDAI_PROXY = p
    uidai_session = create_session(True, p)
    bot.session = uidai_session
    bot.session.headers.update(bot.base_headers)

# ============== PDF CRACKER ==============
class PDFPasswordCracker:
    def try_password(self, path, pwd):
        try:
            with open(path, 'rb') as f:
                r = PyPDF2.PdfReader(f)
                if r.decrypt(pwd): return True
        except Exception: pass
        return False
    def decrypt_pdf(self, path, pwd):
        try:
            out = path.replace('.pdf', '_dec.pdf')
            with open(path, 'rb') as f:
                r = PyPDF2.PdfReader(f); r.decrypt(pwd)
                w = PyPDF2.PdfWriter()
                for pg in r.pages: w.add_page(pg)
                with open(out, 'wb') as o: w.write(o)
            return out
        except Exception: return None
    def crack_pdf(self, path, name):
        n = name.upper(); prefix = n[:4] if len(n) >= 4 else n
        yr_now = datetime.now().year
        cands = []
        for y in range(1940, yr_now + 1):
            cands += [f"{prefix}{y}", f"{prefix.lower()}{y}", f"{prefix}@{y}", f"{prefix}#{y}"]
        cands += [prefix, prefix.lower()]
        seen = set()
        for p in cands:
            if p in seen: continue
            seen.add(p)
            if self.try_password(path, p):
                return True, p, self.decrypt_pdf(path, p)
        return False, None, None

# ============== AADHAAR BOT ==============
class AadhaarBot:
    def __init__(self):
        self.session = get_uidai_session()
        self.base_headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en_IN',
            'Content-Type': 'application/json',
            'Origin': 'https://myaadhaar.uidai.gov.in',
            'Referer': 'https://myaadhaar.uidai.gov.in/',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
            'appid': 'MYAADHAAR',
        }
        self.session.headers.update(self.base_headers)
        self.cracker = PDFPasswordCracker()
    def gen_txid(self): return str(uuid.uuid4())
    def is_b64(self, s):
        if not isinstance(s, str) or len(s) < 100: return False
        if s.startswith('data:'): s = s.split(',')[1] if ',' in s else s
        if len(s) % 4 != 0: return False
        try: base64.b64decode(s); return True
        except Exception: return False
    def file_type(self, b):
        if b[:4] == b'%PDF': return 'pdf'
        if b[:8] == b'\x89PNG\r\n\x1a\n': return 'png'
        if b[:2] == b'\xff\xd8': return 'jpg'
        return 'unknown'
    def decode_b64(self, data, fname="x", save=False):
        out = []
        if isinstance(data, dict):
            for k, v in list(data.items()):
                if isinstance(v, str) and len(v) > 100 and self.is_b64(v):
                    try:
                        clean = v.split(',')[1] if v.startswith('data:') and ',' in v else v
                        raw = base64.b64decode(clean); ft = self.file_type(raw)
                        if save and ft in ['pdf','png','jpg']:
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            ext = {'pdf':'pdf','png':'png','jpg':'jpg'}.get(ft, 'bin')
                            fn = os.path.join(DATA_DIR, f"dec_{fname}_{k}_{ts}.{ext}")
                            with open(fn, 'wb') as f: f.write(raw)
                            out.append({'filename': fn, 'type': ft})
                        elif not save:
                            out.append({'type': ft, 'data': raw})
                    except Exception: pass
                if isinstance(v, (dict, list)): out += self.decode_b64(v, f"{fname}.{k}", save)
        elif isinstance(data, list):
            for i, it in enumerate(data):
                if isinstance(it, (dict, list)): out += self.decode_b64(it, f"{fname}[{i}]", save)
        return out
    def get_captcha(self):
        tid = self.gen_txid()
        self.session.headers.update({'x-request-id': tid, 'transactionId': tid})
        try:
            r = self.session.post(
                'https://tathya.uidai.gov.in/audioCaptchaService/api/captcha/v3/generation',
                json={'captchaLength': '6', 'captchaType': '2', 'audioCaptchaRequired': True},
                timeout=15)
            if r.status_code != 200: return None, None, None
            j = r.json(); ctxn = j.get('transactionId'); b64 = j.get('imageBase64')
            if not b64:
                for _, v in j.items():
                    if isinstance(v, str) and len(v) > 100 and self.is_b64(v): b64 = v; break
            if not b64: return None, None, None
            if b64.startswith('data:image'): b64 = b64.split(',')[1]
            return base64.b64decode(b64), ctxn, tid
        except Exception: return None, None, None
    def send_aadhaar_otp(self, uid, num, captcha, ctxn, tid, id_type='eid'):
        self.session.headers.update({'x-request-id': tid, 'transactionId': tid})
        key = 'eidNumber' if id_type == 'eid' else 'uidNumber'
        try:
            r = self.session.post(
                'https://tathya.uidai.gov.in/unifiedAppAuthService/api/v2/generate/aadhaar/otp',
                json={key: num, 'idType': id_type, 'captchaTxnId': ctxn,
                      'captchaValue': captcha, 'transactionId': tid, 'resendOTP': False},
                timeout=15)
            if r.status_code == 200:
                j = r.json()
                if j.get('txnId') and j.get('status') == "Success":
                    return True, j['txnId'], j.get('message')
                return False, None, j.get('message')
            return False, None, f"HTTP {r.status_code}"
        except Exception as e: return False, None, str(e)
    def download_pdf(self, uid, num, otp, otp_txn, tid, mask=False, id_type='eid'):
        self.session.headers.update({'x-request-id': tid, 'transactionId': tid})
        key = 'eid' if id_type == 'eid' else 'uid'
        try:
            r = self.session.post(
                'https://tathya.uidai.gov.in/downloadAadhaarService/api/aadhaar/download',
                json={key: num, 'mask': mask, 'otp': otp, 'otpTxnId': otp_txn},
                timeout=20)
            if r.status_code == 200:
                j = r.json(); files = self.decode_b64(j, "dl", save=True)
                if files: return True, files[0]['filename']
                if j.get('status') == 'Error' or j.get('errorCode'):
                    return False, j.get('message', j.get('errorMessage', 'Unknown'))
                return False, "No PDF data"
            return False, f"HTTP {r.status_code}"
        except Exception as e: return False, str(e)
    def send_eid_otp(self, uid, mobile, name, captcha, ctxn, tid):
        self.session.headers.update({'x-request-id': tid, 'transactionId': tid})
        try:
            r = self.session.post(
                'https://tathya.uidai.gov.in/retrieveEidUid/ext/v1/generic/retrieveuideid',
                json={'mobileNumber': mobile, 'dob': None, 'email': None, 'name': name.upper(),
                      'option': 'EID', 'otp': None, 'otpTxnId': None,
                      'captchaTxnId': ctxn, 'captcha': captcha, 'resendOtp': False},
                timeout=15)
            if r.status_code == 200:
                j = r.json()
                if 'responseData' in j:
                    rd = j['responseData']
                    if rd.get('otpTxnId') and rd.get('status') == "Success":
                        return True, rd['otpTxnId']
                    return False, rd.get('message', 'Unknown')
                return False, 'Invalid response'
            return False, f'HTTP {r.status_code}'
        except Exception as e: return False, str(e)
    def verify_eid_otp(self, uid, mobile, name, otp, otp_txn, ctxn, captcha):
        self.session.headers.update({'x-request-id': self.gen_txid()})
        try:
            r = self.session.post(
                'https://tathya.uidai.gov.in/retrieveEidUid/ext/v1/generic/retrieveuideid',
                json={'mobileNumber': mobile, 'dob': None, 'name': name.upper(), 'email': None,
                      'option': 'EID', 'otp': otp, 'otpTxnId': otp_txn,
                      'captchaTxnId': ctxn, 'captcha': captcha, 'resendOtp': False},
                timeout=15)
            if r.status_code == 200:
                j = r.json()
                if j.get('status') == 200 or j.get('status') == "Success":
                    if 'responseData' in j:
                        rd = j['responseData']
                        return True, rd.get('eidNumber'), rd.get('name', name)
                    return False, None, "Invalid response"
                return False, None, j.get('errorDetails', {}).get('messageEnglish', 'Failed')
            return False, None, f'HTTP {r.status_code}'
        except Exception as e: return False, None, str(e)
    def crack_pdf(self, path, name): return self.cracker.crack_pdf(path, name)
    def auto_captcha(self, img_bytes):
        try:
            from PIL import Image
            if not _DDDD_OK: return None
            def _c(r): return re.sub(r'[^A-Za-z0-9]', '', r)
            def _dd(b):
                for eng in [_DDDD_MAIN, _DDDD_BETA]:
                    if not eng: continue
                    try:
                        r = _c(eng.classification(b))
                        if 4 <= len(r) <= 8: return r
                    except Exception: pass
                return None
            r = _dd(img_bytes)
            if r: return r
            try:
                img = Image.open(BytesIO(img_bytes)).convert('L')
                img2 = img.resize((img.width*2, img.height*2), Image.LANCZOS)
                buf = BytesIO(); img2.save(buf, format='PNG')
                return _dd(buf.getvalue())
            except Exception: return None
        except Exception: return None
    def fetch_solve_captcha(self, max_retries=20):
        last = (None, None, None)
        for _ in range(max_retries):
            img, ctxn, tid = self.get_captcha()
            if not img: time.sleep(0.4); continue
            last = (img, ctxn, tid)
            s = self.auto_captcha(img)
            if s and 4 <= len(s) <= 8: return img, ctxn, tid, s
            time.sleep(0.2)
        return last[0], last[1], last[2], None

bot = AadhaarBot()

# ============== TELEGRAM API ==============
def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup: data['reply_markup'] = json.dumps(reply_markup)
    try: return get_telegram_session().post(url, json=data, timeout=10).json()
    except Exception as e: logger.error(f"send_message: {e}"); return None

def answer_callback(cqid, text=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    data = {'callback_query_id': cqid}
    if text: data['text'] = text
    try: get_telegram_session().post(url, json=data, timeout=5)
    except Exception: pass

def send_photo(chat_id, photo, caption=None, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    data = {'chat_id': chat_id, 'parse_mode': 'HTML'}
    if caption: data['caption'] = caption
    if reply_markup: data['reply_markup'] = json.dumps(reply_markup)
    try:
        if isinstance(photo, bytes):
            files = {'photo': ('img.png', photo, 'image/png')}
            return get_telegram_session().post(url, data=data, files=files, timeout=20).json()
        else:
            data['photo'] = photo
            return get_telegram_session().post(url, json=data, timeout=20).json()
    except Exception as e: logger.error(f"send_photo: {e}"); return None

def send_photo_file(chat_id, file_path, caption=None, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    data = {'chat_id': chat_id, 'parse_mode': 'HTML'}
    if caption: data['caption'] = caption
    if reply_markup: data['reply_markup'] = json.dumps(reply_markup)
    try:
        with open(file_path, 'rb') as f:
            return get_telegram_session().post(url, data=data, files={'photo': f}, timeout=20).json()
    except Exception as e: logger.error(f"send_photo_file: {e}"); return None

def send_document(chat_id, file_path, caption=None, filename="Aadhaar.pdf"):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    try:
        with open(file_path, 'rb') as f:
            files = {'document': (filename, f, 'application/pdf')}
            data = {'chat_id': chat_id, 'parse_mode': 'HTML'}
            if caption: data['caption'] = caption
            r = get_telegram_session().post(url, data=data, files=files, timeout=30).json()
        try: os.remove(file_path)
        except Exception: pass
        return r
    except Exception as e: logger.error(f"send_document: {e}"); return None

def send_video(chat_id, file_id, caption=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    data = {'chat_id': chat_id, 'video': file_id, 'parse_mode': 'HTML'}
    if caption: data['caption'] = caption
    try: return get_telegram_session().post(url, json=data, timeout=30).json()
    except Exception as e: logger.error(f"send_video: {e}"); return None

# ============== COLORED BUTTONS ==============
def _btn(text, cb, style='primary'):
    """primary=blue, success=green, danger=red"""
    return {'text': text, 'callback_data': cb, 'style': style}

def get_main_keyboard():
    return {'keyboard': [
        ['◆  Mobile Number', '◆  Aadhaar Number'],
        ['◆  EID'],
        ['◇  Credits', '◇  Buy Credits', '◇  Referral'],
    ], 'resize_keyboard': True}

def get_cancel_keyboard():
    return {'inline_keyboard': [[_btn('Cancel', 'cancel', 'danger')]]}

def get_name_auto_keyboard():
    return {'inline_keyboard': [[_btn('Find Automatically', 'auto_name', 'success')]]}

def get_buy_keyboard():
    return {'inline_keyboard': [
        [_btn('10 Credits — ₹200', 'buy_10', 'primary')],
        [_btn('20 Credits — ₹350', 'buy_20', 'success')],
        [_btn('50 Credits — ₹700', 'buy_50', 'primary')],
        [_btn('100 Credits — ₹1000', 'buy_100', 'success')],
    ]}

def get_join_keyboard():
    return {'inline_keyboard': [
        [{'text': 'Join Channel', 'url': CHANNEL_LINK, 'style': 'primary'}],
        [_btn('I have joined', 'check_join', 'success')],
    ]}

def get_member_help_keyboard():
    return {'inline_keyboard': [
        [_btn('Download Aadhaar PDF', 'menu_download', 'primary')],
        [_btn('My Credits', 'menu_credits', 'success'), _btn('Buy Credits', 'menu_buy', 'success')],
        [_btn('Referral Link', 'menu_referral', 'primary'), _btn('Redeem Code', 'menu_redeem', 'primary')],
        [_btn('Media Gallery', 'menu_gallery', 'primary')],
    ]}

def get_premium_help_keyboard():
    return {'inline_keyboard': [
        [_btn('Download Aadhaar PDF', 'menu_download', 'primary')],
        [_btn('My Credits', 'menu_credits', 'success'), _btn('Buy Credits', 'menu_buy', 'success')],
        [_btn('Referral Link', 'menu_referral', 'primary'), _btn('Redeem Code', 'menu_redeem', 'primary')],
        [_btn('Media Gallery', 'menu_gallery', 'primary')],
        [_btn('PREMIUM — Unlimited Access', 'menu_premium_info', 'success')],
    ]}

def get_admin_help_keyboard():
    return {'inline_keyboard': [
        [_btn('Download Aadhaar PDF', 'menu_download', 'primary')],
        [_btn('My Credits', 'menu_credits', 'success'), _btn('Buy Credits', 'menu_buy', 'success')],
        [_btn('Referral Link', 'menu_referral', 'primary'), _btn('Redeem Code', 'menu_redeem', 'primary')],
        [_btn('Media Gallery', 'menu_gallery', 'primary')],
        [_btn('ADMIN PANEL', 'admin_panel', 'danger')],
    ]}

def get_owner_help_keyboard():
    return {'inline_keyboard': [
        [_btn('Download Aadhaar PDF', 'menu_download', 'primary')],
        [_btn('My Credits', 'menu_credits', 'success'), _btn('Buy Credits', 'menu_buy', 'success')],
        [_btn('Referral Link', 'menu_referral', 'primary'), _btn('Redeem Code', 'menu_redeem', 'primary')],
        [_btn('Media Gallery', 'menu_gallery', 'primary')],
        [_btn('ADMIN PANEL', 'admin_panel', 'danger')],
        [_btn('OWNER PANEL', 'owner_panel', 'danger')],
    ]}

def get_admin_panel_keyboard():
    return {'inline_keyboard': [
        [_btn('Stats', 'admin_stats', 'primary'), _btn('Users List', 'admin_users', 'primary')],
        [_btn('Add Credits — ALL Users', 'admin_addcredits_all', 'success')],
        [_btn('Remove Credits — ALL Users', 'admin_removecredits_all', 'danger')],
        [_btn('Add Credits — Specific User', 'admin_addcredits_user', 'success')],
        [_btn('Remove Credits — Specific User', 'admin_removecredits_user', 'danger')],
        [_btn('Add Premium', 'admin_addpremium', 'success'), _btn('Remove Premium', 'admin_removepremium', 'danger')],
        [_btn('Ban User', 'admin_ban', 'danger'), _btn('Unban User', 'admin_unban', 'success')],
        [_btn('Lock Bot', 'admin_lock', 'danger'), _btn('Unlock Bot', 'admin_unlock', 'success')],
        [_btn('Generate Redeem Code', 'admin_gencode', 'primary')],
        [_btn('Broadcast Message', 'admin_broadcast', 'primary')],
        [_btn('List Banned Users', 'admin_listbanned', 'primary')],
        [_btn('List Premium Users', 'admin_listpremium', 'primary')],
        [_btn('Back to Help', 'menu_help', 'primary')],
    ]}

def get_owner_panel_keyboard():
    return {'inline_keyboard': [
        [_btn('Promote to Admin', 'owner_promote', 'success')],
        [_btn('Demote Admin', 'owner_demote', 'danger')],
        [_btn('Change UIDAI Proxy', 'owner_proxy', 'primary')],
        [_btn('Add Video to Gallery', 'owner_addvideo', 'success')],
        [_btn('Remove Video from Gallery', 'owner_removevideo', 'danger')],
        [_btn('List Gallery Videos', 'owner_listvideos', 'primary')],
        [_btn('Remove Payment QR', 'owner_removeqr', 'danger')],
        [_btn('Back to Help', 'menu_help', 'primary')],
    ]}

# ============== SESSIONS ==============
user_sessions = {}
_sess_lock = threading.Lock()

def get_session(cid):
    with _sess_lock:
        return user_sessions.get(cid, {'step': 'main', 'data': {}, 'created_at': time.time()})

def set_session(cid, step, data=None):
    with _sess_lock:
        existing = user_sessions.get(cid, {})
        created = existing.get('created_at', time.time()) if existing.get('step', 'main') != 'main' else time.time()
        d = data if data is not None else existing.get('data', {})
        user_sessions[cid] = {'step': step, 'data': d, 'created_at': created}

def clear_session(cid):
    with _sess_lock:
        user_sessions[cid] = {'step': 'main', 'data': {}, 'created_at': time.time()}

# ============== GATES ==============
def is_channel_member(uid):
    try:
        r = get_telegram_session().get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChatMember",
            params={'chat_id': CHANNEL_USERNAME, 'user_id': uid}, timeout=6).json()
        if r.get('ok'):
            return r['result']['status'] in ('member', 'administrator', 'creator')
    except Exception: pass
    return False

def channel_gate(cid):
    if is_admin(cid) or is_channel_member(cid): return True
    send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Channel Required ]</b>\n\n"
                      f"▸  Join <b>{CHANNEL_USERNAME}</b> to use this bot.\n\n{DIVIDER}",
                 reply_markup=get_join_keyboard())
    return False

def credit_gate(cid):
    if has_credits(cid): return True
    send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ No Credits ]</b>\n\n"
                      f"◈  Balance  ·  <b>0</b>\n\n"
                      f"▸  Tap Buy Credits or Referral.\n\n{DIVIDER}")
    return False

def locked_gate(cid):
    if is_bot_locked() and not (is_admin(cid) or is_premium(cid)):
        send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Bot Locked ]</b>\n\n<i>◌  Maintenance mode.</i>")
        return False
    return True

def banned_gate(cid):
    if is_banned(cid):
        send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Banned ]</b>\n\n<i>✗  You are banned.</i>")
        return False
    return True

# ============== HELP MENU ==============
def show_help_menu(cid):
    if is_owner(cid):
        kb = get_owner_help_keyboard(); role = "OWNER"
    elif is_admin(cid):
        kb = get_admin_help_keyboard(); role = "ADMIN"
    elif is_premium(cid):
        kb = get_premium_help_keyboard(); role = "PREMIUM"
    else:
        kb = get_member_help_keyboard(); role = "MEMBER"
    send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n"
                      f"<b>[ Help Menu — {role} ]</b>\n\n"
                      f"◈  Balance  ·  {get_credits(cid)}\n"
                      f"◈  Status   ·  {'Premium' if is_premium(cid) else 'Standard'}\n\n"
                      f"{DIVIDER}\n"
                      f"<i>◌  Tap any button below.</i>",
                 reply_markup=kb)

# ============== AUTO CAPTCHA ==============
def auto_send_eid_otp(cid, mobile, name, d):
    send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Sending OTP ]</b>\n\n<i>◌  Please wait…</i>")
    BREAK = ('no record', 'not found', 'not registered', 'not linked', 'no aadhaar',
             'not exist', 'does not exist', 'name mismatch', 'dob mismatch', 'mobile not')
    last = (None, None, None)
    def _try(try_name, max_attempts):
        nonlocal last
        consec = 0; last_msg = None
        for _ in range(max_attempts):
            img, ctxn, tid, solved = bot.fetch_solve_captcha()
            if not img: time.sleep(0.4); continue
            last = (img, ctxn, tid)
            if not solved: return ('retry_fail', None)
            ok, res = bot.send_eid_otp(cid, mobile, try_name, solved, ctxn, tid)
            if ok:
                sd = {**d, 'name': try_name, 'captcha_code': solved,
                      'captcha1_txn_id': ctxn, 'transaction_id': tid, 'eid_otp_txn_id': res}
                return ('ok', sd)
            err = str(res).lower()
            if any(k in err for k in BREAK):
                consec += 1; last_msg = str(res)
                if consec >= 3: return ('no_record', last_msg)
                time.sleep(0.5); continue
            consec = 0; time.sleep(0.5)
        return ('retry_fail', None)

    if name and name != 'MR':
        st, pl = _try(name, 5)
        if st == 'ok': return True, pl
    st, pl = _try('MR', 10)
    if st == 'ok': return True, pl
    if st == 'no_record': return 'no_record', pl
    if last[0]: return False, last
    img, ctxn, tid = bot.get_captcha()
    return False, (img, ctxn, tid)

def auto_send_aadhaar_otp(cid, eid, id_type, d):
    send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Sending OTP ]</b>\n\n<i>◌  Please wait…</i>")
    BREAK = ('no record', 'not found', 'not registered', 'not linked', 'no aadhaar',
             'not exist', 'does not exist')
    last = (None, None, None); definitive = None
    for _ in range(10):
        img, ctxn, tid, solved = bot.fetch_solve_captcha()
        if not img: time.sleep(0.4); continue
        last = (img, ctxn, tid)
        if not solved: return False, (img, ctxn, tid)
        ok, txn, msg = bot.send_aadhaar_otp(cid, eid, solved, ctxn, tid, id_type=id_type)
        if ok:
            return True, {**d, 'captcha2_code': solved, 'captcha2_txn_id': ctxn,
                          'transaction_id2': tid, 'pdf_otp_txn_id': txn}
        err = str(msg).lower()
        if any(k in err for k in BREAK):
            definitive = str(msg); break
        time.sleep(0.5)
    if definitive: return 'no_record', definitive
    if last[0]: return False, last
    img, ctxn, tid = bot.get_captcha()
    return False, (img, ctxn, tid)

# ============== PDF DELIVERY ==============
def deliver_pdf(cid, pdf_path, verified_name):
    name_disp = verified_name if verified_name and verified_name.strip() else "Mr."
    send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Processing ]</b>\n\n<i>◌  Decrypting…</i>")
    try:
        ok, pwd, dec = bot.crack_pdf(pdf_path, name_disp)
        if ok and dec:
            cap = (f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Document Ready ]</b>\n\n"
                   f"◈  Name    ·  {name_disp}\n◈  Format  ·  e-Aadhaar PDF\n"
                   f"◈  Status  ·  Unlocked\n{DIVIDER}")
            send_document(cid, dec, caption=cap, filename="Aadhaar.pdf")
            try: os.remove(pdf_path)
            except Exception: pass
        else:
            cap = (f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Document Ready ]</b>\n\n"
                   f"◈  Name    ·  {name_disp}\n◈  Status  ·  Password Protected\n{DIVIDER}")
            send_document(cid, pdf_path, caption=cap, filename="Aadhaar.pdf")
    except Exception as e: logger.error(f"PDF delivery: {e}")
    deduct_credit(cid)
    cr = get_credits(cid)
    clear_session(cid)
    send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Download Complete ]</b>\n\n"
                      f"◈  Credits remaining  ·  {cr}\n\n{DIVIDER}",
                 reply_markup=get_main_keyboard())
    send_random_gallery_video(cid)

def send_random_gallery_video(cid):
    v = get_random_video()
    if v: send_video(cid, v['file_id'], caption=v.get('caption') or "🎬")

# ============== STEP HANDLERS ==============
def _step_mobile(cid, text, d):
    if re.match(r'^\d{10}$', text):
        set_session(cid, 'awaiting_name', {**d, 'mobile': text})
        send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Step 2 — Name ]</b>\n\n"
                          f"▸  Enter full name as on Aadhaar\n\n<i>◌  Unknown? Tap below.</i>",
                     reply_markup=get_name_auto_keyboard())
    else: send_message(cid, "✗  Enter 10-digit mobile.")

def _step_name(cid, text, d):
    name = text.strip().upper() if len(text.strip()) >= 2 else "MR"
    ok, res = auto_send_eid_otp(cid, d.get('mobile', ''), name, d)
    if ok is True:
        set_session(cid, 'awaiting_otp', res)
        send_message(cid, "<b>[ OTP Sent ]</b>\n\n▸  Enter 6-digit OTP",
                     reply_markup=get_cancel_keyboard())
    elif ok == 'no_record':
        clear_session(cid)
        send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n✗  <b>No Records Found</b>\n\n"
                          f"<i>◌  This mobile is not linked.</i>")
    else:
        img, ctxn, tid = res if res else (None, None, None)
        if img:
            set_session(cid, 'awaiting_captcha1', {**d, 'name': name, 'captcha1_txn_id': ctxn, 'transaction_id': tid})
            send_photo(cid, img, caption="<i>▸  Auto-solve failed. Type captcha:</i>")
        else: clear_session(cid); send_message(cid, "✗  Captcha unavailable.")

def _step_otp(cid, text, d):
    if not re.match(r'^\d{6}$', text): send_message(cid, "✗  Invalid OTP."); return
    send_message(cid, "<b>[ Verifying ]</b>\n<i>◌  Checking…</i>")
    ok, eid, name = bot.verify_eid_otp(cid, d['mobile'], d['name'], text,
                                       d['eid_otp_txn_id'], d['captcha1_txn_id'], d['captcha_code'])
    if not ok:
        clear_session(cid); send_message(cid, f"✗  Verification failed — {eid}"); return
    vname = name if name and name.strip() else "Mr."
    send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Verified ]</b>\n\n"
                      f"◈  Name  ·  {vname}\n◈  EID   ·  <code>{eid}</code>\n\n{DIVIDER}")
    base = {**d, 'eid': eid, 'verified_name': vname, 'id_type': 'eid'}
    ok2, res2 = auto_send_aadhaar_otp(cid, eid, 'eid', base)
    if ok2 is True:
        set_session(cid, 'awaiting_pdf_otp', res2)
        send_message(cid, "<b>[ OTP Sent ]</b>\n\n▸  Enter 6-digit OTP",
                     reply_markup=get_cancel_keyboard())
    elif ok2 == 'no_record':
        clear_session(cid); send_message(cid, f"✗  <b>Aadhaar Not Found</b>")
    else:
        img, ctxn, tid = res2 if res2 else (None, None, None)
        if img:
            set_session(cid, 'awaiting_captcha2', {**base, 'captcha2_txn_id': ctxn, 'transaction_id2': tid})
            send_photo(cid, img, caption="<i>▸  Type captcha manually:</i>")
        else: clear_session(cid); send_message(cid, "✗  Captcha unavailable.")

def _step_pdf_otp(cid, text, d):
    if not re.match(r'^\d{6}$', text): send_message(cid, "✗  Invalid OTP."); return
    send_message(cid, "<b>[ Downloading ]</b>\n<i>◌  Fetching PDF…</i>")
    ok, path = bot.download_pdf(cid, d['eid'], text, d['pdf_otp_txn_id'],
                                d['transaction_id2'], False, id_type=d.get('id_type', 'eid'))
    if ok and path and '.pdf' in path: deliver_pdf(cid, path, d.get('verified_name', 'Mr.'))
    else: clear_session(cid); send_message(cid, f"✗  Download failed — {path}")

def _step_captcha1(cid, text, d):
    set_session(cid, 'sending_otp', {**d, 'captcha_code': text.strip()})
    send_message(cid, "<b>[ Sending OTP ]</b>\n<i>◌  Please wait…</i>")
    sd = get_session(cid)['data']
    ok, res = bot.send_eid_otp(cid, sd['mobile'], sd['name'], sd['captcha_code'],
                               sd['captcha1_txn_id'], sd['transaction_id'])
    if ok:
        set_session(cid, 'awaiting_otp', {**sd, 'eid_otp_txn_id': res})
        send_message(cid, "<b>[ OTP Sent ]</b>\n\n▸  Enter 6-digit OTP",
                     reply_markup=get_cancel_keyboard())
    else: clear_session(cid); send_message(cid, "✗  Failed. Try again.")

def _step_captcha2(cid, text, d):
    sd = {**d, 'captcha2_code': text.strip()}
    set_session(cid, 'sending_pdf_otp', sd)
    send_message(cid, "<b>[ Sending OTP ]</b>\n<i>◌  Please wait…</i>")
    ok, txn, msg = bot.send_aadhaar_otp(cid, sd['eid'], sd['captcha2_code'],
                                        sd['captcha2_txn_id'], sd['transaction_id2'],
                                        id_type=sd.get('id_type', 'eid'))
    if ok:
        set_session(cid, 'awaiting_pdf_otp', {**sd, 'pdf_otp_txn_id': txn})
        send_message(cid, "<b>[ OTP Sent ]</b>\n\n▸  Enter 6-digit OTP",
                     reply_markup=get_cancel_keyboard())
    else: clear_session(cid); send_message(cid, f"✗  OTP failed — {msg}")

def _step_aadhaar(cid, text, d):
    uid = text.strip().replace(' ', '')
    if re.match(r'^\d{12}$', uid):
        set_session(cid, 'awaiting_name_direct', {**d, 'eid': uid, 'id_type': 'uid'})
        send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Step 2 — Name ]</b>\n\n"
                          f"▸  Enter full name as on Aadhaar")
    else: send_message(cid, "✗  Enter 12-digit Aadhaar.")

def _step_eid_input(cid, text, d):
    if len(text.strip()) >= 10:
        set_session(cid, 'awaiting_name_direct', {**d, 'eid': text.strip(), 'id_type': 'eid'})
        send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Step 2 — Name ]</b>\n\n"
                          f"▸  Enter full name as on Aadhaar")
    else: send_message(cid, "✗  Invalid EID.")

def _step_name_direct(cid, text, d):
    name = text.strip().upper() if len(text.strip()) >= 2 else "MR"
    base = {**d, 'verified_name': name}
    ok, res = auto_send_aadhaar_otp(cid, d.get('eid', ''), d.get('id_type', 'eid'), base)
    if ok is True:
        set_session(cid, 'awaiting_pdf_otp_direct', res)
        send_message(cid, "<b>[ OTP Sent ]</b>\n\n▸  Enter 6-digit OTP",
                     reply_markup=get_cancel_keyboard())
    elif ok == 'no_record':
        clear_session(cid); send_message(cid, f"✗  <b>Aadhaar Not Found</b>")
    else:
        img, ctxn, tid = res if res else (None, None, None)
        if img:
            set_session(cid, 'awaiting_captcha_direct', {**base, 'captcha2_txn_id': ctxn, 'transaction_id2': tid})
            send_photo(cid, img, caption="<i>▸  Type captcha manually:</i>")
        else: clear_session(cid); send_message(cid, "✗  Captcha unavailable.")

def _step_captcha_direct(cid, text, d):
    sd = {**d, 'captcha2_code': text.strip()}
    set_session(cid, 'sending_pdf_otp_direct', sd)
    send_message(cid, "<b>[ Sending OTP ]</b>\n<i>◌  Please wait…</i>")
    ok, txn, msg = bot.send_aadhaar_otp(cid, sd['eid'], sd['captcha2_code'],
                                        sd['captcha2_txn_id'], sd['transaction_id2'],
                                        id_type=sd.get('id_type', 'eid'))
    if ok:
        set_session(cid, 'awaiting_pdf_otp_direct', {**sd, 'pdf_otp_txn_id': txn})
        send_message(cid, "<b>[ OTP Sent ]</b>\n\n▸  Enter 6-digit OTP",
                     reply_markup=get_cancel_keyboard())
    else: clear_session(cid); send_message(cid, f"✗  OTP failed — {msg}")

def _step_pdf_otp_direct(cid, text, d):
    if not re.match(r'^\d{6}$', text): send_message(cid, "✗  Invalid OTP."); return
    send_message(cid, "<b>[ Downloading ]</b>\n<i>◌  Fetching PDF…</i>")
    ok, path = bot.download_pdf(cid, d['eid'], text, d['pdf_otp_txn_id'],
                                d['transaction_id2'], False, id_type=d.get('id_type', 'eid'))
    if ok and path and '.pdf' in path: deliver_pdf(cid, path, d.get('verified_name', 'Mr.'))
    else: clear_session(cid); send_message(cid, f"✗  Download failed — {path}")

# ============== MESSAGE HANDLER ==============
_KB_ACTIONS = {
    '◆  mobile number': 'search_mobile',
    '◆  aadhaar number': 'search_aadhaar',
    '◆  eid': 'search_eid',
    '◇  credits': 'credits',
    '◇  buy credits': 'buy',
    '◇  referral': 'referral',
}

def handle_message(cid, text, username=None, first_name=None):
    ensure_user(cid, username=username, first_name=first_name)
    if not banned_gate(cid): return
    if not locked_gate(cid): return

    if is_owner(cid) and text.startswith('/'):
        if handle_owner_cmd(cid, text): return

    if text.strip().lower() in ('/help', 'help', '/start'):
        clear_session(cid)
        if not channel_gate(cid): return
        show_help_menu(cid); return

    if text.startswith('/redeem'):
        parts = text.split()
        if len(parts) == 2:
            ok, res = redeem_code(cid, parts[1])
            if ok:
                send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n"
                                  f"<b>[ Redeemed ]</b>\n\n◈  Amount  ·  +{res}\n"
                                  f"◈  Balance ·  {get_credits(cid)}\n\n{DIVIDER}")
                send_message(APPROVER_ID, f"<b>[ Code Redeemed ]</b>\n\n◈  User ·  <code>{cid}</code>\n◈  Amount · {res}")
            else: send_message(cid, f"✗  {res}")
        return

    action = _KB_ACTIONS.get(text.strip().lower())
    if action:
        if action in ('search_mobile', 'search_aadhaar', 'search_eid'):
            if not channel_gate(cid): return
            if not credit_gate(cid): return
            clear_session(cid)
            if action == 'search_mobile':
                set_session(cid, 'awaiting_mobile', {'mode': 'mobile'})
                send_message(cid, f"{BOT_NAME}\n{DIVIDER}\n<b>[ Mobile Search ]</b>\n\n"
                                  f"▸  Enter 10-digit mobile", reply_markup=get_cancel_keyboard())
            elif action == 'search_aadhaar':
                set_session(cid, 'awaiting_aadhaar', {'mode': 'aadhaar'})
                send_message(cid, f"{BOT_NAME}\n{DIVIDER}\n<b>[ Aadhaar Search ]</b>\n\n"
                                  f"▸  Enter 12-digit Aadhaar", reply_markup=get_cancel_keyboard())
            elif action == 'search_eid':
                set_session(cid, 'awaiting_eid_input', {'mode': 'eid'})
                send_message(cid, f"{BOT_NAME}\n{DIVIDER}\n<b>[ EID Search ]</b>\n\n"
                                  f"▸  Enter EID", reply_markup=get_cancel_keyboard())
        elif action == 'credits': show_credits(cid)
        elif action == 'buy': show_buy(cid)
        elif action == 'referral': show_referral(cid)
        return

    s = get_session(cid); step = s.get('step', 'main'); d = s.get('data', {})
    if step == 'main': return

    if time.time() - s.get('created_at', time.time()) > SESSION_TIMEOUT:
        clear_session(cid)
        send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Session Expired ]</b>")
        return

    if text.lower() in ('/cancel', 'cancel'):
        clear_session(cid)
        send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<i>✗  Cancelled.</i>")
        return

    handlers = {
        'awaiting_mobile': _step_mobile, 'awaiting_name': _step_name,
        'awaiting_otp': _step_otp, 'awaiting_captcha1': _step_captcha1,
        'awaiting_captcha2': _step_captcha2, 'awaiting_pdf_otp': _step_pdf_otp,
        'awaiting_aadhaar': _step_aadhaar, 'awaiting_eid_input': _step_eid_input,
        'awaiting_name_direct': _step_name_direct,
        'awaiting_captcha_direct': _step_captcha_direct,
        'awaiting_pdf_otp_direct': _step_pdf_otp_direct,
    }
    fn = handlers.get(step)
    if fn: fn(cid, text, d)

# ============== DISPLAY ==============
def show_credits(cid):
    u = get_user(cid); cr = get_credits(cid)
    rc = u.get('referral_count', 0) if u else 0
    joined = u.get('joined', '')[:10] if u else '—'
    send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ My Credits ]</b>\n\n"
                      f"◈  Balance     ·  {cr}\n◈  Referrals   ·  {rc}\n"
                      f"◈  Member since·  {joined}\n\n{DIVIDER}\n"
                      f"<i>◌  1 credit = 1 Aadhaar download</i>")

def show_buy(cid):
    send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Buy Credits ]</b>\n\n"
                      f"◈  10 credits    ·  <b>₹200</b>\n◈  20 credits    ·  <b>₹350</b>\n"
                      f"◈  50 credits    ·  <b>₹700</b>\n◈  100 credits   ·  <b>₹1000</b>\n\n{DIVIDER}\n"
                      f"<i>◌  Tap a plan below.</i>",
                 reply_markup=get_buy_keyboard())

def show_referral(cid):
    try:
        r = get_telegram_session().get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe", timeout=5).json()
        uname = r['result']['username'] if r.get('ok') else 'bot'
    except Exception: uname = 'bot'
    link = f"https://t.me/{uname}?start=ref_{cid}"
    u = get_user(cid); rc = u.get('referral_count', 0) if u else 0
    send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Referral ]</b>\n\n"
                      f"<code>{link}</code>\n\n◈  Friends joined  ·  {rc}\n"
                      f"◈  Credits earned  ·  {rc}\n\n{DIVIDER}")

# ============== PAYMENT ==============
def start_payment(cid, plan_key):
    PLANS = {'10': (10, '₹200'), '20': (20, '₹350'), '50': (50, '₹700'), '100': (100, '₹1000')}
    if plan_key not in PLANS: return
    credits, price = PLANS[plan_key]
    set_session(cid, 'awaiting_payment_screenshot', {'plan_credits': credits, 'plan_price': price})
    msg = (f"<b>{BOT_NAME}</b>\n{DIVIDER}\n"
           f"<b>[ Payment — {price} ]</b>\n\n"
           f"◈  Plan    ·  {credits} credits\n◈  Amount  ·  <b>{price}</b>\n\n{DIVIDER}\n"
           f"<b>UPI ID</b>\n<code>{UPI_ID}</code>\n\n"
           f"▸  Pay <b>{price}</b> to the UPI ID above\n"
           f"▸  After payment, send the screenshot here\n\n{DIVIDER}\n"
           f"<i>◌  Credits will be added after admin approves.</i>")
    qr = get_qr_path()
    if qr: send_photo_file(cid, qr, caption=msg)
    else: send_message(cid, msg + "\n\n⚠️ QR not configured. Use UPI ID above.")

# ============== CALLBACK HANDLER ==============
def handle_callback(cid, cqid, data):
    answer_callback(cqid)
    ensure_user(cid)
    if not banned_gate(cid): return

    if data == 'cancel':
        clear_session(cid)
        send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<i>✗  Cancelled.</i>")
        return
    if data == 'menu_help': show_help_menu(cid); return

    if data == 'menu_download':
        if not channel_gate(cid): return
        if not locked_gate(cid): return
        if not credit_gate(cid): return
        send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Choose Method ]</b>",
                     reply_markup={'inline_keyboard': [
                         [_btn('Mobile Number', 'dl_mobile', 'primary')],
                         [_btn('Aadhaar Number', 'dl_aadhaar', 'primary')],
                         [_btn('EID', 'dl_eid', 'primary')],
                         [_btn('Cancel', 'cancel', 'danger')]]})
        return

    if data == 'dl_mobile':
        if not credit_gate(cid): return
        clear_session(cid); set_session(cid, 'awaiting_mobile', {'mode': 'mobile'})
        send_message(cid, f"{BOT_NAME}\n{DIVIDER}\n<b>[ Mobile Search ]</b>\n\n"
                          f"▸  Enter 10-digit mobile", reply_markup=get_cancel_keyboard())
        return
    if data == 'dl_aadhaar':
        if not credit_gate(cid): return
        clear_session(cid); set_session(cid, 'awaiting_aadhaar', {'mode': 'aadhaar'})
        send_message(cid, f"{BOT_NAME}\n{DIVIDER}\n<b>[ Aadhaar Search ]</b>\n\n"
                          f"▸  Enter 12-digit Aadhaar", reply_markup=get_cancel_keyboard())
        return
    if data == 'dl_eid':
        if not credit_gate(cid): return
        clear_session(cid); set_session(cid, 'awaiting_eid_input', {'mode': 'eid'})
        send_message(cid, f"{BOT_NAME}\n{DIVIDER}\n<b>[ EID Search ]</b>\n\n"
                          f"▸  Enter EID", reply_markup=get_cancel_keyboard())
        return

    if data == 'menu_credits': show_credits(cid); return
    if data == 'menu_buy': show_buy(cid); return
    if data == 'menu_referral': show_referral(cid); return

    if data == 'menu_redeem':
        clear_session(cid); set_session(cid, 'awaiting_redeem_code', {})
        send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Redeem Code ]</b>\n\n"
                          f"▸  Send your redeem code", reply_markup=get_cancel_keyboard())
        return

    if data == 'menu_gallery':
        send_random_gallery_video(cid)
        send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<i>◌  Random video sent.</i>")
        return

    if data == 'menu_premium_info':
        send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Premium ]</b>\n\n"
                          f"◈  Status  ·  Active\n◈  Benefit ·  Unlimited downloads\n\n{DIVIDER}")
        return

    if data == 'check_join':
        if is_channel_member(cid): show_help_menu(cid)
        else: send_message(cid, f"✗  Not joined yet.", reply_markup=get_join_keyboard())
        return

    if data == 'auto_name':
        d = get_session(cid).get('data', {})
        ok, res = auto_send_eid_otp(cid, d.get('mobile', ''), 'MR', d)
        if ok is True:
            set_session(cid, 'awaiting_otp', res)
            send_message(cid, "<b>[ OTP Sent ]</b>\n\n▸  Enter 6-digit OTP",
                         reply_markup=get_cancel_keyboard())
        elif ok == 'no_record':
            clear_session(cid); send_message(cid, "✗  No records found.")
        else:
            img, ctxn, tid = res if res else (None, None, None)
            if img:
                set_session(cid, 'awaiting_captcha1', {**d, 'name': 'MR',
                            'captcha1_txn_id': ctxn, 'transaction_id': tid})
                send_photo(cid, img, caption="<i>▸  Type captcha manually:</i>")
        return

    if data.startswith('buy_'):
        start_payment(cid, data.split('_')[1]); return

    # Payment approvals
    if data.startswith('approve_'):
        req_id = data.replace('approve_', '')
        rec = approve_pending(req_id)
        if not rec: answer_callback(cqid, "Already processed"); return
        uid = rec['user_id']; credits = rec['credits']
        add_credits(uid, credits)
        send_message(cid, f"✓ Approved. {credits} credits added to <code>{uid}</code>.")
        try:
            send_message(uid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Payment Approved ]</b>\n\n"
                              f"◈  Credits Added  ·  +{credits}\n"
                              f"◈  New Balance   ·  {get_credits(uid)}\n\n{DIVIDER}\n"
                              f"<i>◌  Thank you!</i>", reply_markup=get_main_keyboard())
        except Exception: pass
        return
    if data.startswith('reject_'):
        req_id = data.replace('reject_', '')
        rec = reject_pending(req_id)
        if not rec: answer_callback(cqid, "Already processed"); return
        uid = rec['user_id']
        send_message(cid, f"✗ Rejected request {req_id} from <code>{uid}</code>.")
        try:
            send_message(uid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Payment Rejected ]</b>\n\n"
                              f"<i>◌  Contact {OWNER_USERNAME}</i>", reply_markup=get_main_keyboard())
        except Exception: pass
        return

    # Admin/Owner restriction
    if not (is_admin(cid) or is_owner(cid)):
        if data.startswith('admin_') or data.startswith('owner_'):
            answer_callback(cqid, "Admin only"); return

    if data == 'admin_panel':
        send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Admin Panel ]</b>",
                     reply_markup=get_admin_panel_keyboard())
        return

    if data == 'admin_stats':
        users = _load_users()
        tu = len(users)
        tp = sum(1 for u in users.values() if u.get('is_premium'))
        ta = sum(1 for u in users.values() if u.get('is_admin'))
        tb = sum(1 for u in users.values() if u.get('is_banned'))
        codes = _load_codes()
        uc = sum(1 for c in codes.values() if not c.get('used'))
        pending = _load_pending()
        up = sum(1 for p in pending.values() if p.get('status') == 'pending')
        send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Stats ]</b>\n\n"
                          f"◈  Users        ·  {tu}\n◈  Premium      ·  {tp}\n"
                          f"◈  Admins       ·  {ta}\n◈  Banned       ·  {tb}\n"
                          f"◈  Active Codes ·  {uc}\n◈  Pending Pay  ·  {up}\n"
                          f"◈  Videos       ·  {video_count()}\n\n{DIVIDER}",
                     reply_markup=get_admin_panel_keyboard())
        return

    if data == 'admin_users':
        users = _load_users()
        rows = sorted(users.items(), key=lambda x: int(x[0]), reverse=True)[:30]
        lines = [f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Recent 30 Users ]</b>\n"]
        for uid, u in rows:
            badges = ""
            if u.get('is_premium'): badges += "P"
            if u.get('is_admin'): badges += "A"
            if u.get('is_banned'): badges += "B"
            lines.append(f"◈  <code>{uid}</code>  ·  {u.get('credits',0)} cr  ·  {badges or '-'}")
        send_message(cid, "\n".join(lines) + f"\n\n{DIVIDER}",
                     reply_markup=get_admin_panel_keyboard())
        return

    if data == 'admin_listpremium':
        users = _load_users()
        prem = [uid for uid, u in users.items() if u.get('is_premium')]
        if not prem: send_message(cid, "◈  No premium users.", reply_markup=get_admin_panel_keyboard()); return
        lines = ["<b>[ Premium Users ]</b>\n"] + [f"◈  <code>{u}</code>" for u in prem[:50]]
        send_message(cid, "\n".join(lines), reply_markup=get_admin_panel_keyboard())
        return

    if data == 'admin_listbanned':
        users = _load_users()
        bann = [uid for uid, u in users.items() if u.get('is_banned')]
        if not bann: send_message(cid, "◈  No banned users.", reply_markup=get_admin_panel_keyboard()); return
        lines = ["<b>[ Banned Users ]</b>\n"] + [f"◈  <code>{u}</code>" for u in bann[:50]]
        send_message(cid, "\n".join(lines), reply_markup=get_admin_panel_keyboard())
        return

    admin_steps = {
        'admin_addcredits_all': ('adm_addcredits_all', "[ Add Credits to ALL ]\n\n▸  Send amount (e.g. 10)"),
        'admin_removecredits_all': ('adm_removecredits_all', "[ Remove Credits from ALL ]\n\n▸  Send amount"),
        'admin_addcredits_user': ('adm_addcredits_user', "[ Add Credits to User ]\n\n▸  Send: USER_ID AMOUNT"),
        'admin_removecredits_user': ('adm_removecredits_user', "[ Remove Credits from User ]\n\n▸  Send: USER_ID AMOUNT"),
        'admin_addpremium': ('adm_addpremium', "[ Add Premium ]\n\n▸  Send USER_ID"),
        'admin_removepremium': ('adm_removepremium', "[ Remove Premium ]\n\n▸  Send USER_ID"),
        'admin_ban': ('adm_ban', "[ Ban User ]\n\n▸  Send USER_ID"),
        'admin_unban': ('adm_unban', "[ Unban User ]\n\n▸  Send USER_ID"),
        'admin_gencode': ('adm_gencode', "[ Generate Code ]\n\n▸  Send amount"),
        'admin_broadcast': ('adm_broadcast', "[ Broadcast ]\n\n▸  Send message text"),
    }
    if data in admin_steps:
        step, prompt = admin_steps[data]
        clear_session(cid); set_session(cid, step, {})
        send_message(cid, prompt,
                     reply_markup={'inline_keyboard': [[_btn('Cancel', 'admin_cancel', 'danger')]]})
        return

    if data == 'admin_lock':
        s = get_settings(); s['bot_locked'] = True; save_settings(s)
        send_message(cid, "<b>[ Bot Locked ]</b>", reply_markup=get_admin_panel_keyboard()); return
    if data == 'admin_unlock':
        s = get_settings(); s['bot_locked'] = False; save_settings(s)
        send_message(cid, "<b>[ Bot Unlocked ]</b>", reply_markup=get_admin_panel_keyboard()); return
    if data == 'admin_cancel':
        clear_session(cid); send_message(cid, "✗  Cancelled.", reply_markup=get_admin_panel_keyboard()); return

    # Owner panel
    if data == 'owner_panel' and is_owner(cid):
        send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Owner Panel ]</b>",
                     reply_markup=get_owner_panel_keyboard())
        return
    if data == 'owner_promote' and is_owner(cid):
        clear_session(cid); set_session(cid, 'own_promote', {})
        send_message(cid, "[ Promote to Admin ]\n\n▸  Send USER_ID",
                     reply_markup={'inline_keyboard': [[_btn('Cancel', 'admin_cancel', 'danger')]]})
        return
    if data == 'owner_demote' and is_owner(cid):
        clear_session(cid); set_session(cid, 'own_demote', {})
        send_message(cid, "[ Demote Admin ]\n\n▸  Send USER_ID",
                     reply_markup={'inline_keyboard': [[_btn('Cancel', 'admin_cancel', 'danger')]]})
        return
    if data == 'owner_proxy' and is_owner(cid):
        clear_session(cid); set_session(cid, 'own_proxy', {})
        send_message(cid, "[ Change Proxy ]\n\n▸  Send proxy URL",
                     reply_markup={'inline_keyboard': [[_btn('Cancel', 'admin_cancel', 'danger')]]})
        return
    if data == 'owner_addvideo' and is_owner(cid):
        clear_session(cid); set_session(cid, 'own_addvideo', {})
        send_message(cid, "[ Add Video ]\n\n▸  Send a video message",
                     reply_markup={'inline_keyboard': [[_btn('Cancel', 'admin_cancel', 'danger')]]})
        return
    if data == 'owner_removevideo' and is_owner(cid):
        vids = get_all_videos()
        if not vids: send_message(cid, "◈  No videos.", reply_markup=get_owner_panel_keyboard()); return
        rows = [[_btn(f"Delete #{i} — {v.get('caption') or 'no cap'}", f"own_delvid_{i}", 'danger')]
                for i, v in enumerate(vids[:20])]
        rows.append([_btn('Cancel', 'admin_cancel', 'danger')])
        send_message(cid, "[ Remove Video ]", reply_markup={'inline_keyboard': rows})
        return
    if data.startswith('own_delvid_') and is_owner(cid):
        idx = int(data.split('_')[-1])
        if delete_video(idx):
            send_message(cid, f"✓ Video #{idx} deleted.", reply_markup=get_owner_panel_keyboard())
        else: send_message(cid, "✗  Not found.", reply_markup=get_owner_panel_keyboard())
        return
    if data == 'owner_listvideos' and is_owner(cid):
        vids = get_all_videos()
        if not vids: send_message(cid, "◈  No videos.", reply_markup=get_owner_panel_keyboard()); return
        lines = [f"<b>[ Videos — {len(vids)} ]</b>\n"]
        for i, v in enumerate(vids[:30]): lines.append(f"◈  #{i}  ·  {v.get('caption') or '(no caption)'}")
        send_message(cid, "\n".join(lines), reply_markup=get_owner_panel_keyboard())
        return
    if data == 'owner_removeqr' and is_owner(cid):
        if os.path.exists(QR_FILE):
            try:
                os.remove(QR_FILE)
                send_message(cid, f"<b>[ QR Removed ]</b>\n\n◈  Deleted successfully.",
                             reply_markup=get_owner_panel_keyboard())
            except Exception as e:
                send_message(cid, f"✗  Failed: {e}", reply_markup=get_owner_panel_keyboard())
        else: send_message(cid, "✗  No QR exists.", reply_markup=get_owner_panel_keyboard())
        return

# ============== ADMIN STEP HANDLER ==============
def handle_admin_step(cid, text, step):
    if step == 'adm_addcredits_all':
        try:
            amt = int(text.strip())
            if amt <= 0: raise ValueError
        except ValueError: send_message(cid, "✗  Invalid amount."); return
        users = _load_users(); ok = 0
        for uid in list(users.keys()):
            add_credits(int(uid), amt)
            try:
                send_message(int(uid), f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Credits Received ]</b>\n\n"
                                       f"◈  +{amt}\n◈  Balance ·  {get_credits(int(uid))}\n\n{DIVIDER}",
                             reply_markup=get_main_keyboard())
            except Exception: pass
            ok += 1; time.sleep(0.05)
        clear_session(cid)
        send_message(cid, f"✓ Added {amt} to {ok} users.", reply_markup=get_admin_panel_keyboard())
        return

    if step == 'adm_removecredits_all':
        try:
            amt = int(text.strip())
            if amt <= 0: raise ValueError
        except ValueError: send_message(cid, "✗  Invalid amount."); return
        with _file_lock:
            users = _load_users()
            for k in users: users[k]['credits'] = max(0, users[k].get('credits', 0) - amt)
            _save_users(users); n = len(users)
        clear_session(cid)
        send_message(cid, f"✓ Removed {amt} from {n} users.", reply_markup=get_admin_panel_keyboard())
        return

    if step in ('adm_addcredits_user', 'adm_removecredits_user'):
        parts = text.strip().split()
        if len(parts) != 2: send_message(cid, "✗  Send: USER_ID AMOUNT"); return
        try:
            uid = int(parts[0]); amt = int(parts[1])
            if amt <= 0: raise ValueError
        except ValueError: send_message(cid, "✗  Invalid."); return
        if step == 'adm_addcredits_user':
            add_credits(uid, amt)
            try:
                send_message(uid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Credits Received ]</b>\n\n"
                                  f"◈  +{amt}\n◈  Balance ·  {get_credits(uid)}\n\n{DIVIDER}",
                             reply_markup=get_main_keyboard())
            except Exception: pass
            send_message(cid, f"✓ Added {amt} to {uid}.", reply_markup=get_admin_panel_keyboard())
        else:
            with _file_lock:
                users = _load_users(); k = str(uid)
                if k in users:
                    users[k]['credits'] = max(0, users[k].get('credits', 0) - amt)
                    _save_users(users)
            send_message(cid, f"✓ Removed {amt} from {uid}.", reply_markup=get_admin_panel_keyboard())
        clear_session(cid); return

    if step == 'adm_addpremium':
        try: uid = int(text.strip())
        except ValueError: send_message(cid, "✗  Invalid ID."); return
        ensure_user(uid); set_premium(uid, True)
        try: send_message(uid, "💎 You are now PREMIUM!")
        except Exception: pass
        clear_session(cid)
        send_message(cid, f"✓ {uid} is now premium.", reply_markup=get_admin_panel_keyboard())
        return

    if step == 'adm_removepremium':
        try: uid = int(text.strip())
        except ValueError: send_message(cid, "✗  Invalid ID."); return
        set_premium(uid, False)
        clear_session(cid)
        send_message(cid, f"✓ {uid} removed from premium.", reply_markup=get_admin_panel_keyboard())
        return

    if step == 'adm_ban':
        try: uid = int(text.strip())
        except ValueError: send_message(cid, "✗  Invalid ID."); return
        if uid == OWNER_ID: send_message(cid, "✗  Cannot ban owner."); return
        ensure_user(uid); set_banned(uid, True)
        try: send_message(uid, "🚫 You have been banned.")
        except Exception: pass
        clear_session(cid)
        send_message(cid, f"✓ {uid} banned.", reply_markup=get_admin_panel_keyboard())
        return

    if step == 'adm_unban':
        try: uid = int(text.strip())
        except ValueError: send_message(cid, "✗  Invalid ID."); return
        set_banned(uid, False)
        try: send_message(uid, "✓ You have been unbanned.")
        except Exception: pass
        clear_session(cid)
        send_message(cid, f"✓ {uid} unbanned.", reply_markup=get_admin_panel_keyboard())
        return

    if step == 'adm_gencode':
        try: amt = int(text.strip())
        except ValueError: send_message(cid, "✗  Invalid."); return
        code = gen_code(amt)
        clear_session(cid)
        send_message(cid, f"<b>[ Code Generated ]</b>\n\n◈  <code>{code}</code>\n◈  Value ·  {amt}",
                     reply_markup=get_admin_panel_keyboard())
        return

    if step == 'adm_broadcast':
        users = _load_users(); ok = 0
        for uid in list(users.keys()):
            try: send_message(int(uid), text, reply_markup=get_main_keyboard()); ok += 1
            except Exception: pass
            time.sleep(0.05)
        clear_session(cid)
        send_message(cid, f"✓ Broadcast sent to {ok} users.", reply_markup=get_admin_panel_keyboard())
        return

    if step == 'own_promote':
        try: uid = int(text.strip())
        except ValueError: send_message(cid, "✗  Invalid ID."); return
        ensure_user(uid); set_admin(uid, True)
        try: send_message(uid, "✓ You are now an admin.")
        except Exception: pass
        clear_session(cid)
        send_message(cid, f"✓ {uid} is now admin.", reply_markup=get_owner_panel_keyboard())
        return
    if step == 'own_demote':
        try: uid = int(text.strip())
        except ValueError: send_message(cid, "✗  Invalid ID."); return
        set_admin(uid, False)
        clear_session(cid)
        send_message(cid, f"✓ {uid} demoted.", reply_markup=get_owner_panel_keyboard())
        return
    if step == 'own_proxy':
        set_uidai_proxy(text.strip())
        clear_session(cid)
        send_message(cid, f"✓ Proxy updated.", reply_markup=get_owner_panel_keyboard())
        return
    if step == 'own_addvideo':
        send_message(cid, "▸  Send a video now.", reply_markup=get_cancel_keyboard())
        return

# ============== VIDEO HANDLER ==============
def handle_video_message(cid, video_file_id, caption=None):
    if is_owner(cid):
        s = get_session(cid)
        if s.get('step') == 'own_addvideo':
            if add_video(video_file_id, caption):
                clear_session(cid)
                send_message(cid, "✓ Video added to gallery.", reply_markup=get_owner_panel_keyboard())
            else: send_message(cid, "✗  Already exists.")
            return

# ============== SCREENSHOT HANDLER ==============
def handle_screenshot(cid, file_id, caption=None):
    s = get_session(cid)
    if s.get('step') != 'awaiting_payment_screenshot': return
    d = s['data']
    credits = d.get('plan_credits'); price = d.get('plan_price')
    req_id = add_pending(cid, credits, price, file_id)

    send_message(cid,
        f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Screenshot Received ]</b>\n\n"
        f"◈  Request ID  ·  <code>{req_id}</code>\n"
        f"◈  Plan       ·  {credits} credits\n"
        f"◈  Amount     ·  {price}\n"
        f"◈  Status     ·  PENDING APPROVAL\n\n{DIVIDER}\n"
        f"<i>◌  Credits will be added after admin approval.</i>",
        reply_markup=get_main_keyboard())

    u = get_user(cid) or {}
    uname = u.get('username') or 'unknown'
    fname = u.get('first_name') or 'user'
    owner_msg = (f"<b>🔔 New Payment Request</b>\n{DIVIDER}\n"
                 f"◈  User    ·  {fname} (@{uname})\n"
                 f"◈  Chat ID ·  <code>{cid}</code>\n"
                 f"◈  Plan    ·  {credits} credits\n"
                 f"◈  Amount  ·  {price}\n"
                 f"◈  Req ID  ·  <code>{req_id}</code>\n\n{DIVIDER}")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    data = {'chat_id': APPROVER_ID, 'photo': file_id, 'caption': owner_msg,
            'parse_mode': 'HTML',
            'reply_markup': json.dumps({'inline_keyboard': [[
                _btn('✓ Approve', f'approve_{req_id}', 'success'),
                _btn('✗ Reject', f'reject_{req_id}', 'danger')]]})}
    try: get_telegram_session().post(url, json=data, timeout=15)
    except Exception as e: logger.error(f"notify owner: {e}")
    clear_session(cid)

# ============== /addqr & /removeqr ==============
def handle_qr_commands(cid, text, msg):
    """Handle /addqr and /removeqr. Returns True if handled."""
    t = text.strip().lower()
    if t == '/removeqr':
        if not is_owner(cid):
            send_message(cid, "✗  Owner only."); return True
        if os.path.exists(QR_FILE):
            try:
                os.remove(QR_FILE)
                send_message(cid, f"<b>[ QR Removed ]</b>\n\n◈  Deleted successfully.",
                             reply_markup=get_owner_panel_keyboard())
            except Exception as e:
                send_message(cid, f"✗  Failed to delete: {e}")
        else:
            send_message(cid, "✗  No QR file exists.")
        return True

    if t == '/addqr':
        if not is_owner(cid):
            send_message(cid, "✗  Owner only."); return True
        reply = msg.get('reply_to_message')
        if not reply or 'photo' not in reply:
            send_message(cid,
                f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Add QR — How To ]</b>\n\n"
                f"1. Send QR image as photo to this chat\n"
                f"2. Reply to that photo with <code>/addqr</code>\n\n"
                f"{DIVIDER}\n<i>◌  Bot will save it automatically.</i>")
            return True
        photos = reply['photo']
        file_id = photos[-1]['file_id']
        try:
            r = get_telegram_session().get(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile",
                params={'file_id': file_id}, timeout=10).json()
            if not r.get('ok'):
                send_message(cid, "✗  Could not fetch file info."); return True
            file_path = r['result']['file_path']
            dl_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
            resp = get_telegram_session().get(dl_url, timeout=30)
            if resp.status_code != 200:
                send_message(cid, f"✗  Download failed: HTTP {resp.status_code}"); return True
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(QR_FILE, 'wb') as f: f.write(resp.content)
            send_message(cid,
                f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ QR Saved ]</b>\n\n"
                f"◈  File    ·  <code>{os.path.basename(QR_FILE)}</code>\n"
                f"◈  Size    ·  {len(resp.content)} bytes\n"
                f"◈  Status  ·  Active\n\n{DIVIDER}\n"
                f"<i>◌  Buy Credits me ye QR bhej di jayegi.</i>",
                reply_markup=get_owner_panel_keyboard())
        except Exception as e:
            logger.error(f"/addqr error: {e}")
            send_message(cid, f"✗  Error: {e}")
        return True
    return False

# ============== OWNER SLASH ==============
def handle_owner_cmd(cid, text):
    parts = text.strip().split()
    if not parts: return False
    cmd = parts[0].lower()

    if cmd == '/gen' and len(parts) == 2:
        try:
            amt = int(parts[1]); code = gen_code(amt)
            send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Code Generated ]</b>\n\n"
                              f"◈  <code>{code}</code>\n◈  Credits ·  {amt}\n\n{DIVIDER}")
            return True
        except ValueError: return True
    if cmd == '/ip' and len(parts) == 2:
        set_uidai_proxy(parts[1]); send_message(cid, f"✓ Proxy updated to {parts[1]}"); return True
    if cmd == '/stats':
        users = _load_users()
        send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Stats ]</b>\n\n"
                          f"◈  Users  ·  {len(users)}\n◈  Videos ·  {video_count()}\n\n{DIVIDER}")
        return True
    return False

# ============== UPDATES LOOP ==============
def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {'timeout': 30, 'allowed_updates': ['message', 'callback_query']}
    if offset: params['offset'] = offset
    try:
        r = get_telegram_session().get(url, params=params, timeout=35)
        j = r.json(); return j.get('result', []) if j.get('ok') else []
    except Exception as e: logger.error(f"getUpdates: {e}"); return []

def session_cleanup():
    while True:
        time.sleep(20)
        try:
            expired = []
            with _sess_lock:
                for cid, s in list(user_sessions.items()):
                    if s.get('step') != 'main' and time.time() - s.get('created_at', time.time()) > SESSION_TIMEOUT:
                        user_sessions[cid] = {'step': 'main', 'data': {}, 'created_at': time.time()}
                        expired.append(cid)
            for cid in expired:
                try: send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Session Expired ]</b>",
                                  reply_markup=get_main_keyboard())
                except Exception: pass
        except Exception: pass

# ============== PROCESS UPDATE ==============
def process_update(update):
    try:
        if 'callback_query' in update:
            cq = update['callback_query']
            cid = cq['message']['chat']['id']; cqid = cq['id']
            handle_callback(cid, cqid, cq.get('data', ''))
            return
        if 'message' not in update: return
        msg = update['message']
        cid = msg.get('chat', {}).get('id')
        if not cid: return
        from_user = msg.get('from', {})
        username = from_user.get('username'); first_name = from_user.get('first_name')
        text = msg.get('text', '').strip()

        # /addqr /removeqr handled first
        if text and (text.strip().lower() in ('/addqr', '/removeqr')):
            ensure_user(cid, username=username, first_name=first_name)
            handle_qr_commands(cid, text, msg)
            return

        # Photo (screenshot)
        if 'photo' in msg:
            file_id = msg['photo'][-1]['file_id']
            handle_screenshot(cid, file_id, msg.get('caption'))
            return

        # Video
        if 'video' in msg:
            handle_video_message(cid, msg['video']['file_id'], msg.get('caption'))
            return

        if not text: return

        # /start
        if text.startswith('/start'):
            parts = text.split()
            referrer_id = None
            if len(parts) > 1 and parts[1].startswith('ref_'):
                try: referrer_id = int(parts[1][4:])
                except ValueError: pass
            ensure_user(cid, referrer_id, username, first_name)
            clear_session(cid)
            if is_banned(cid):
                send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Banned ]</b>\n\n<i>✗  You are banned.</i>")
                return
            if not is_admin(cid) and not is_channel_member(cid):
                send_message(cid, f"<b>{BOT_NAME}</b>\n{DIVIDER}\n<b>[ Channel Required ]</b>\n\n"
                                  f"▸  Join <b>{CHANNEL_USERNAME}</b>.\n\n{DIVIDER}",
                             reply_markup=get_join_keyboard())
                return
            v = get_random_video()
            if v: send_video(cid, v['file_id'], caption=v.get('caption') or "🎬")
            send_message(cid,
                f"<b>{BOT_NAME}</b>\n{DIVIDER}\n\n"
                f"<b>e-Aadhaar PDF  —  straight to Telegram</b>\n\n"
                f"◈  Source    ·  Official UIDAI portal\n"
                f"◈  Delivery  ·  Auto-unlocked, no password\n"
                f"◈  Methods   ·  Mobile  ·  Aadhaar  ·  EID\n\n{DIVIDER}\n"
                f"◈  Credits  ·  {get_credits(cid)}\n\n"
                f"<i>◌  Tap Help for menu or select a method below.</i>",
                reply_markup=get_main_keyboard())
            return

        s = get_session(cid); step = s.get('step', 'main')
        if step.startswith('adm_') or step.startswith('own_'):
            handle_admin_step(cid, text, step); return

        if step == 'awaiting_redeem_code':
            ok, res = redeem_code(cid, text.strip())
            clear_session(cid)
            if ok:
                send_message(cid, f"<b>[ Redeemed ]</b>\n\n◈  +{res} credits\n"
                                  f"◈  Balance ·  {get_credits(cid)}",
                             reply_markup=get_main_keyboard())
            else: send_message(cid, f"✗  {res}", reply_markup=get_main_keyboard())
            return

        if step == 'awaiting_payment_screenshot':
            send_message(cid, "<i>◌  Please send the payment screenshot as a photo.</i>")
            return

        handle_message(cid, text, username, first_name)
    except Exception as e:
        logger.error(f"process_update: {e}", exc_info=True)

# ============== MAIN ==============
def main():
    print("━" * 50)
    print(f"  {BOT_NAME}  —  FINAL")
    print("━" * 50)
    print(f"[ OCR ]  ddddocr   : {'OK' if _DDDD_OK else 'MISSING'}")
    print(f"[ OCR ]  tesseract : {'OK' if _TESS_OK else 'MISSING'}")
    print(f"[ DB  ]  {DATA_DIR}")
    print(f"[ QR  ]  {get_qr_path() or 'NOT SET — use /addqr'}")
    print(f"[ Pay ]  UPI {UPI_ID}  |  Approver {APPROVER_ID}")
    print(f"[ Owner ] {OWNER_ID} — {OWNER_USERNAME}")
    print("━" * 50)
    try:
        r = get_telegram_session().get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe", timeout=10).json()
        if r.get('ok'): print(f"[ online ]  @{r['result']['username']}")
        else: print(f"[ error ]  {r}"); return
    except Exception as e: print(f"[ error ]  {e}"); return

    ensure_user(OWNER_ID); set_admin(OWNER_ID, True)
    threading.Thread(target=session_cleanup, daemon=True).start()

    print("━" * 50)
    print("  running  —  Ctrl+C to stop")
    print("━" * 50)

    last_id = 0
    executor = ThreadPoolExecutor(max_workers=20)
    while True:
        try:
            updates = get_updates(last_id + 1)
            for u in updates:
                if u.get('update_id'): last_id = u['update_id']
                executor.submit(process_update, u)
            time.sleep(0.3)
        except KeyboardInterrupt:
            print("\n[ stopped ]"); executor.shutdown(wait=False); break
        except Exception as e:
            logger.error(f"Main loop: {e}"); time.sleep(5)

if __name__ == "__main__":
    main()
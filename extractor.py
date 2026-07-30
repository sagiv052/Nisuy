import re
import html
import time
import random
import requests
import concurrent.futures
from typing import List, Tuple, Optional, Dict, Set, Any
from bs4 import BeautifulSoup

# Patterns
DRIVE_URL_PATTERN = re.compile(r'https?://(?:drive\.google\.com|www\.drive\.google\.com)[^\s"\'<\)>]+')
EMOJI_PATTERN = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF\U0000FE00-\U0000FE0F\U0001F000-\U0001F02F\U0001F0A0-\U0001F0FF]', flags=re.UNICODE)

QUALITY_PATTERNS = {
    "4K": re.compile(r'\b(4k|2160p|uhd)\b', re.IGNORECASE),
    "1080p": re.compile(r'\b(1080p|fhd)\b', re.IGNORECASE),
    "720p": re.compile(r'\b(720p|hd)\b', re.IGNORECASE),
    "480p": re.compile(r'\b(480p|sd)\b', re.IGNORECASE),
}

JUNK_PATTERNS = [
    re.compile(r'(?i)הועלה\s+על\s+ידי\s+.*'),
    re.compile(r'(?i)קרדיט\s+ל.*'),
    re.compile(r'(?i)מבית\s+.*'),
    re.compile(r'(?i)סרטים\s+וסדרות\s+בדרייב'),
    re.compile(r'(?i)driveflix|qbzn|h264|h265|x264|x265|web-dl|brrip|bluray'),
    re.compile(r'(?i)גוזלן|לולו\s+סרטים|ת\.מ|ע"י\s+.*|לצפייה\s+ישירה|תרגום\s+מובנה|מדובב|סדרות'),
    re.compile(r'(?i)עונה\s*\d+\s*פרק\s*\d+'),
    re.compile(r'(?i)ע\d+פ\d+'),
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

def detect_quality(name: str) -> str:
    for q, p in QUALITY_PATTERNS.items():
        if p.search(name): return f"[{q}]"
    return ""

def clean_series_name(title: str) -> str:
    if not title: return ''
    title = html.unescape(title)
    # EMOJI_PATTERN.sub('', title)  # Disabled to keep emojis
    title = re.sub(r'\.(?:mp4|mkv|avi|pdf|zip|rar|txt|jpg|jpeg|png|gif|webm|mov|srt)\b', '', title, flags=re.IGNORECASE)
    for jp in JUNK_PATTERNS: title = jp.sub('', title)
    title = re.sub(r'[_*+\-=|~#]', ' ', title)
    title = re.sub(r'(?i)\b(?:4k|2160p|1080p|720p|480p|fhd|hd|sd)\b', '', title)
    title = re.sub(r'(?i)(?:עונה|ע|Season|S)\s*\d+', '', title)
    title = re.sub(r'(?i)(?:פרק|פ|Episode|E)\s*\d+', '', title)
    title = re.sub(r'(?i)ע\d+פ\d+', '', title)
    title = re.sub(r'\s+', ' ', title)
    return title.strip(' -/\\•').strip()

def extract_id_and_type(input_str: str) -> Tuple[str, str]:
    input_str = input_str.strip()
    if '/file/d/' in input_str:
        match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', input_str)
        if match: return match.group(1), 'file'
    patterns = [r'/folders/([a-zA-Z0-9_-]+)', r'id=([a-zA-Z0-9_-]+)']
    for p in patterns:
        match = re.search(p, input_str)
        if match: return match.group(1), 'folder'
    if re.match(r'^[a-zA-Z0-9_-]{25,}$', input_str): return input_str, 'folder'
    raise ValueError("קישור לא תקין")

def parse_season_episode(name: str) -> Tuple[Optional[int], Optional[int]]:
    name = html.unescape(name.replace('_', ' ')).strip()
    patterns = [r'[Ss](\d+)[Ee](\d+)', r'(?:עונה|ע)\s*(\d+)\s*.*?(?:פרק|פ)\s*(\d+)', r'(\d+)x(\d+)']
    for p in patterns:
        m = re.search(p, name, re.IGNORECASE)
        if m: return int(m.group(1)), int(m.group(2))
    s = re.search(r'(?:עונה|ע|Season|S)\s*(\d+)', name, re.IGNORECASE)
    e = re.search(r'(?:פרק|פ|Episode|E)\s*(\d+)', name, re.IGNORECASE)
    return (int(s.group(1)) if s else None, int(e.group(1)) if e else None)

class DriveExtractor:
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.seen_files = set()
        self.seen_folders = set()
        # Create a pool of sessions, one for each User Agent
        self.sessions = []
        for ua in USER_AGENTS:
            s = requests.Session()
            s.headers.update({'User-Agent': ua})
            s.mount('https://', requests.adapters.HTTPAdapter(pool_connections=5, pool_maxsize=5))
            self.sessions.append(s)
        self.num_sessions = len(self.sessions)

    def get_html(self, item_id: str, is_folder: bool = True, session_idx: int = 0) -> Tuple[Optional[str], Optional[str]]:
        url = f'https://drive.google.com/embeddedfolderview?id={item_id}#grid' if is_folder else f'https://drive.google.com/file/d/{item_id}/view'
        try:
            # Use the assigned session
            session = self.sessions[session_idx % self.num_sessions]
            time.sleep(random.uniform(0.05, 0.15))
            r = session.get(url, timeout=15)
            r.raise_for_status()
            return r.text, None
        except Exception as e: return None, str(e)

    def parse_content(self, content: str, update_seen: bool = True) -> Tuple[List[Tuple[str, str]], List[str]]:
        files, subfolders = [], []
        soup = BeautifulSoup(content, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/file/d/' in href:
                try:
                    fid, _ = extract_id_and_type(href)
                    if not update_seen or fid not in self.seen_files:
                        if update_seen: self.seen_files.add(fid)
                        title = a.get_text().strip() or a.find_parent('div').get_text().strip()
                        files.append((title, f"https://drive.google.com/file/d/{fid}/view"))
                except: pass
            elif '/folders/' in href or 'id=' in href:
                try:
                    fid, itype = extract_id_and_type(href)
                    if itype == 'folder' and fid not in subfolders: subfolders.append(fid)
                except: pass
        if not files and not subfolders:
            for fid in re.findall(r'/file/d/([a-zA-Z0-9_-]{25,})', content):
                if not update_seen or fid not in self.seen_files:
                    if update_seen: self.seen_files.add(fid)
                    files.append(("קובץ", f"https://drive.google.com/file/d/{fid}/view"))
            for fid in re.findall(r'/folders/([a-zA-Z0-9_-]{25,})', content):
                if fid not in subfolders: subfolders.append(fid)
        return files, subfolders

    def scan_recursive(self, folder_id: str, max_depth=10) -> List[Tuple[str, str]]:
        all_files = []
        queue = [(folder_id, 0)]
        self.seen_folders.add(folder_id)
        
        # Use as many workers as we have sessions/User Agents
        max_workers = self.num_sessions
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            while queue:
                batch = queue
                queue = []
                # Distribute tasks among sessions using session_idx
                futures = {
                    executor.submit(self.get_html, fid, True, i): (fid, depth) 
                    for i, (fid, depth) in enumerate(batch) if depth <= max_depth
                }
                for f in concurrent.futures.as_completed(futures):
                    fid, depth = futures[f]
                    c, _ = f.result()
                    if not c: continue
                    fs, sfs = self.parse_content(c)
                    all_files.extend(fs)
                    if self.progress_callback: self.progress_callback(f"נמצאו {len(all_files)} קבצים", current=len(all_files))
                    for sf in sfs:
                        if sf not in self.seen_folders:
                            self.seen_folders.add(sf)
                            queue.append((sf, depth + 1))
        return all_files

    def get_series_list(self, url: str) -> List[Any]:
        try:
            fid, itype = extract_id_and_type(url)
            if itype == 'file': return [f"{fid}#file"]
            c, _ = self.get_html(fid, True)
            if not c: return [fid]
            fs, sfs = self.parse_content(c, False)
            return sfs if sfs and len(fs) < 3 else [fid]
        except: return [url]

    def extract_series(self, target: str) -> List[Dict[str, Any]]:
        self.seen_files, self.seen_folders = set(), set()
        if "#file" in target: return [self.process_item(target.replace("#file",""), False)]
        try:
            fid, itype = extract_id_and_type(target)
            if itype == 'file': return [self.process_item(fid, False)]
            c, _ = self.get_html(fid, True)
            if not c: return [{"error": "לא ניתן לגשת", "title": "שגיאה"}]
            fs, sfs = self.parse_content(c, False)
            if sfs and len(fs) < 3:
                results = []
                # Use sessions for processing sub-items as well
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, self.num_sessions)) as ex:
                    futures = [ex.submit(self.process_item, sf, True, None, i) for i, sf in enumerate(sfs)]
                    for f in concurrent.futures.as_completed(futures): results.append(f.result())
                return results
            return [self.process_item(fid, True, c)]
        except: return [{"error": "קישור לא תקין", "title": "שגיאה"}]

    def process_item(self, fid: str, is_folder: bool, content=None, session_idx=0) -> Dict[str, Any]:
        c = content or self.get_html(fid, is_folder, session_idx)[0]
        if not c: return {"error": "שגיאה", "title": "לא ידוע"}
        t = clean_series_name(re.search(r'<title>(.*?)</title>', c).group(1).replace(' - Google Drive','') if re.search(r'<title>(.*?)</title>', c) else "סדרה")
        entries = [(t, f"https://drive.google.com/file/d/{fid}/view")] if not is_folder else self.scan_recursive(fid)
        if not entries: return {"error": "ריק", "title": t}
        g = {}
        for rn, u in entries:
            q, n = detect_quality(rn), clean_series_name(rn)
            s, e = parse_season_episode(rn)
            sk = f"עונה {s}" if s else "כללי"
            if sk not in g: g[sk] = []
            if not any(x['episode'] == e and e is not None for x in g[sk]):
                g[sk].append({"name": f"{n} {q}".strip(), "url": u, "episode": e})
        for sk in g: g[sk].sort(key=lambda x: x['episode'] if x['episode'] is not None else 999)
        return {"title": t, "data": g, "stats": {"total_episodes": sum(len(x) for x in g.values()), "total_seasons": len(g)}}

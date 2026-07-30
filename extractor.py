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
    title = EMOJI_PATTERN.sub('', title)
    title = re.sub(r'\.(?:mp4|mkv|avi|pdf|zip|rar|txt|jpg|jpeg|png|gif|webm|mov|srt)\b', '', title, flags=re.IGNORECASE)
    for jp in JUNK_PATTERNS:
        title = jp.sub('', title)
    title = re.sub(r'[_*+\-=|~#]', ' ', title)
    title = re.sub(r'(?i)\b(?:4k|2160p|1080p|720p|480p|fhd|hd|sd)\b', '', title)
    title = re.sub(r'(?i)(?:עונה|ע|Season|S)\s*\d+', '', title)
    title = re.sub(r'(?i)(?:פרק|פ|Episode|E)\s*\d+', '', title)
    title = re.sub(r'(?i)ע\d+פ\d+', '', title)
    title = re.sub(r'\s+', ' ', title)
    return title.strip(' -/\\•').strip()

def extract_id_and_type(input_str: str) -> Tuple[str, str]:
    input_str = input_str.strip()
    file_patterns = [r'/file/d/([a-zA-Z0-9_-]+)']
    for p in file_patterns:
        match = re.search(p, input_str)
        if match: return match.group(1), 'file'
    folder_patterns = [
        r'/folders/([a-zA-Z0-9_-]+)',
        r'/drive/u/\d+/folders/([a-zA-Z0-9_-]+)',
        r'/embeddedfolderview\?id=([a-zA-Z0-9_-]+)',
        r'/open\?id=([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
    ]
    for p in folder_patterns:
        match = re.search(p, input_str)
        if match: return match.group(1), 'folder'
    if re.match(r'^[a-zA-Z0-9_-]{25,}$', input_str): 
        return input_str, 'folder'
    raise ValueError(f"קישור לא תקין.")

def parse_season_episode(name: str) -> Tuple[Optional[int], Optional[int]]:
    name = html.unescape(name.replace('_', ' ')).strip()
    patterns = [
        r'[Ss](\d+)[Ee](\d+)',
        r'(?:עונה|ע)\s*(\d+)\s*(?:[-–—:|/\\]?\s*)?(?:פרק|פ)\s*(\d+)',
        r'(?:פרק|פ)\s*(\d+)\s*(?:[-–—:|/\\]?\s*)?(?:עונה|ע)\s*(\d+)',
        r'[Ss]eason\s*(\d+)\s*[Ee]pisode\s*(\d+)',
        r'(\d+)x(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match: return int(match.group(1)), int(match.group(2))
    s_match = re.search(r'(?:עונה|ע|Season|S)\s*(\d+)', name, re.IGNORECASE)
    e_match = re.search(r'(?:פרק|פ|Episode|E)\s*(\d+)', name, re.IGNORECASE)
    return (int(s_match.group(1)) if s_match else None, 
            int(e_match.group(1)) if e_match else None)

class DriveExtractor:
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.seen_files = set()
        self.seen_folders = set()
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
        self.session.mount('https://', adapter)
        self.session.headers.update({'User-Agent': random.choice(USER_AGENTS)})

    def get_html(self, item_id: str, is_folder: bool = True) -> Tuple[Optional[str], Optional[str]]:
        url = f'https://drive.google.com/embeddedfolderview?id={item_id}#grid' if is_folder else f'https://drive.google.com/file/d/{item_id}/view'
        try:
            headers = {'User-Agent': random.choice(USER_AGENTS)}
            time.sleep(random.uniform(0.05, 0.15))
            response = self.session.get(url, headers=headers, timeout=15)
            if response.status_code == 404: return None, "לא נמצא"
            if response.status_code == 403: return None, "אין גישה"
            response.raise_for_status()
            return response.text, None
        except Exception as e:
            return None, str(e)

    def parse_content(self, content: str, update_seen: bool = True) -> Tuple[List[Tuple[str, str]], List[str]]:
        files, subfolders = [], []
        soup = BeautifulSoup(content, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            title = a.get_text().strip()
            if '/file/d/' in href:
                if not title:
                    parent = a.find_parent('div')
                    title = parent.get_text().strip() if parent else "קובץ ללא שם"
                try:
                    fid, _ = extract_id_and_type(href)
                    if not update_seen or fid not in self.seen_files:
                        if update_seen: self.seen_files.add(fid)
                        files.append((title, f"https://drive.google.com/file/d/{fid}/view"))
                except: pass
            elif '/folders/' in href or 'id=' in href:
                try:
                    fid, itype = extract_id_and_type(href)
                    if itype == 'folder' and fid and fid not in subfolders: subfolders.append(fid)
                except: pass
        if not files and not subfolders:
            fids = re.findall(r'/file/d/([a-zA-Z0-9_-]{25,})', content)
            for fid in fids:
                if not update_seen or fid not in self.seen_files:
                    if update_seen: self.seen_files.add(fid)
                    files.append(("קובץ שזוהה", f"https://drive.google.com/file/d/{fid}/view"))
            fids = re.findall(r'/folders/([a-zA-Z0-9_-]{25,})', content)
            for fid in fids:
                if fid not in subfolders: subfolders.append(fid)
        return files, subfolders

    def scan_recursive_concurrent(self, folder_id: str, max_depth=10) -> List[Tuple[str, str]]:
        all_files = []
        folders_to_scan = [(folder_id, 0)]
        self.seen_folders.add(folder_id)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            while folders_to_scan:
                current_batch = folders_to_scan
                folders_to_scan = []
                future_to_folder = {executor.submit(self.get_html, fid, True): (fid, depth) for fid, depth in current_batch if depth <= max_depth}
                
                for future in concurrent.futures.as_completed(future_to_folder):
                    content, _ = future.result()
                    if not content: continue
                    files, subfolders = self.parse_content(content)
                    all_files.extend(files)
                    if self.progress_callback:
                        self.progress_callback(f"🔍 נמצאו {len(all_files)} קבצים...", current=len(all_files))
                    for sf_id in subfolders:
                        if sf_id not in self.seen_folders:
                            self.seen_folders.add(sf_id)
                            folders_to_scan.append((sf_id, future_to_folder[future][1] + 1))
        return all_files

    def get_series_list(self, folder_url: str) -> List[Any]:
        try:
            item_id, item_type = extract_id_and_type(folder_url)
            if item_type == 'file': return [f"{item_id}#file"]
            content, _ = self.get_html(item_id, is_folder=True)
            if not content: return [item_id]
            files, subfolders = self.parse_content(content, update_seen=False)
            return subfolders if subfolders and len(files) < 3 else [item_id]
        except: return [folder_url]

    def extract_series(self, folder_url_or_id: str) -> List[Dict[str, Any]]:
        self.seen_files = set()
        self.seen_folders = set()
        is_direct_file = False
        if isinstance(folder_url_or_id, str) and "#file" in folder_url_or_id:
            folder_id, is_direct_file = folder_url_or_id.replace("#file", ""), True
        else:
            try:
                folder_id, itype = extract_id_and_type(folder_url_or_id)
                is_direct_file = (itype == 'file')
            except: folder_id = folder_url_or_id
        
        if is_direct_file: return [self.process_single_item(folder_id, is_folder=False)]
        
        content, _ = self.get_html(folder_id, is_folder=True)
        if not content: return [{"error": "לא ניתן לגשת", "title": "שגיאה"}]
        files, subfolders = self.parse_content(content, update_seen=False)
        
        if subfolders and len(files) < 3:
            results = []
            # Use separate executor to avoid nesting issues
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(self.process_single_item, sf_id, True) for sf_id in subfolders]
                for f in concurrent.futures.as_completed(futures):
                    results.append(f.result())
            return results
        return [self.process_single_item(folder_id, is_folder=True, preloaded_content=content)]

    def process_single_item(self, item_id: str, is_folder: bool = True, preloaded_content=None) -> Dict[str, Any]:
        content = preloaded_content or self.get_html(item_id, is_folder=is_folder)[0]
        if not content: return {"error": "שגיאה בגישה", "title": "לא ידוע"}
        
        title_match = re.search(r'<title>(.*?)</title>', content)
        item_title = clean_series_name(title_match.group(1).replace(' - Google Drive', '')) if title_match else "סדרה ללא שם"
        
        all_entries = [(item_title, f"https://drive.google.com/file/d/{item_id}/view")] if not is_folder else self.scan_recursive_concurrent(item_id)
        if not all_entries: return {"error": "לא נמצאו קבצים", "title": item_title}
        
        grouped = {}
        total_episodes = 0
        for raw_name, url in all_entries:
            quality, name = detect_quality(raw_name), clean_series_name(raw_name)
            season, episode = parse_season_episode(raw_name)
            s_key = f"עונה {season}" if season else "כללי"
            if s_key not in grouped: grouped[s_key] = []
            if not any(e['episode'] == episode and episode is not None for e in grouped[s_key]):
                grouped[s_key].append({"name": f"{name} {quality}".strip(), "url": url, "episode": episode})
                total_episodes += 1
        for s in grouped: grouped[s].sort(key=lambda x: x['episode'] if x['episode'] is not None else 999)
        return {"title": item_title, "data": grouped, "stats": {"total_episodes": total_episodes, "total_seasons": len(grouped)}}

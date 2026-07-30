import re
import html
import time
import random
import requests
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

def detect_quality(name: str) -> str:
    for q, p in QUALITY_PATTERNS.items():
        if p.search(name): return f"[{q}]"
    return ""

def clean_series_name(title: str) -> str:
    if not title: return ''
    title = EMOJI_PATTERN.sub('', title)
    title = re.sub(r'\.(?:mp4|mkv|avi|pdf|zip|rar|txt|jpg|jpeg|png|gif|webm|mov|srt)\b', '', title, flags=re.IGNORECASE)
    
    # Remove junk patterns
    for jp in JUNK_PATTERNS:
        title = jp.sub('', title)
        
    title = re.sub(r'[_*+\-=|~#]', ' ', title)
    
    # Clean up specific series patterns
    title = re.sub(r'(?i)\b(?:4k|2160p|1080p|720p|480p|fhd|hd|sd)\b', '', title)
    
    # Remove Season/Episode mentions from the main title to keep it clean
    title = re.sub(r'(?i)(?:עונה|ע|Season|S)\s*\d+', '', title)
    title = re.sub(r'(?i)(?:פרק|פ|Episode|E)\s*\d+', '', title)
    title = re.sub(r'(?i)ע\d+פ\d+', '', title)
    
    title = re.sub(r'\s+', ' ', title)
    return title.strip(' -/\\').strip()

def extract_folder_id(input_str: str) -> str:
    input_str = input_str.strip()
    patterns = [
        r'/file/d/([a-zA-Z0-9_-]+)',
        r'/folders/([a-zA-Z0-9_-]+)',
        r'/drive/u/\d+/folders/([a-zA-Z0-9_-]+)',
        r'/embeddedfolderview\?id=([a-zA-Z0-9_-]+)',
        r'/open\?id=([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, input_str)
        if match: return match.group(1)
    if re.match(r'^[a-zA-Z0-9_-]+$', input_str): return input_str
    raise ValueError(f"קישור לא תקין. וודא שהעתקת את הקישור המלא מהדפדפן.")

def parse_season_episode(name: str) -> Tuple[Optional[int], Optional[int]]:
    name = name.replace('_', ' ').strip()
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
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        })

    def get_html(self, folder_id: str) -> Tuple[Optional[str], Optional[str]]:
        url = f'https://drive.google.com/embeddedfolderview?id={folder_id}#grid'
        try:
            response = self.session.get(url, timeout=20)
            if response.status_code == 404:
                return None, "התיקייה לא נמצאה. ייתכן שהקישור שבור."
            if response.status_code == 403:
                return None, "אין גישה לתיקייה. וודא שהיא מוגדרת כציבורית ('כל מי שקיבל את הקישור')."
            response.raise_for_status()
            return response.text, None
        except requests.exceptions.Timeout:
            return None, "החיבור לשרת Google Drive התעכב יותר מדי. נסה שוב בעוד רגע."
        except Exception as e:
            return None, f"שגיאת תקשורת: {str(e)}"

    def parse_content(self, content: str) -> Tuple[List[Tuple[str, str]], List[str]]:
        files = []
        subfolders = []
        soup = BeautifulSoup(content, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/file/d/' in href:
                title = a.get_text().strip()
                if not title:
                    parent = a.find_parent('div')
                    title = parent.get_text().strip() if parent else "קובץ ללא שם"
                
                if href.startswith('/'): href = f"https://drive.google.com{href}"
                if href not in self.seen_files:
                    self.seen_files.add(href)
                    files.append((title, href))
            elif '/folders/' in href or 'id=' in href:
                try:
                    fid = extract_folder_id(href)
                    if fid and fid not in subfolders: subfolders.append(fid)
                except: pass
        return files, subfolders

    def scan_recursive(self, folder_id: str, depth=0, max_depth=5) -> List[Tuple[str, str]]:
        if depth > max_depth: return []
        
        content, err = self.get_html(folder_id)
        if not content: return []
        
        # Use a more memory-efficient way to find folder name
        folder_name = "תיקייה"
        title_start = content.find('<title>')
        title_end = content.find('</title>')
        if title_start != -1 and title_end != -1:
            folder_name = content[title_start+7:title_end].replace(' - Google Drive', '')

        if self.progress_callback: 
            self.progress_callback(f"🔍 סורק: {folder_name} (עומק {depth})")
        
        files, subfolders = self.parse_content(content)
        all_files = files
        
        # Limit total subfolders to prevent infinite loops or extreme memory usage
        for sf_id in subfolders[:50]: 
            if sf_id != folder_id:
                all_files.extend(self.scan_recursive(sf_id, depth + 1, max_depth))
        
        return all_files

    def extract_series(self, folder_url: str) -> Dict[str, Any]:
        self.seen_files = set()
        try:
            folder_id = extract_folder_id(folder_url)
        except ValueError as e: return {"error": str(e)}

        if self.progress_callback: self.progress_callback("📡 מתחבר ל-Google Drive...")
        
        # Get initial title
        content, err = self.get_html(folder_id)
        if not content:
            return {"error": err or "לא ניתן לגשת לתיקייה. וודא שהיא ציבורית."}
            
        folder_title = "סדרה ללא שם"
        soup = BeautifulSoup(content, 'html.parser')
        title_tag = soup.find('title')
        if title_tag: 
            folder_title = clean_series_name(title_tag.get_text().replace(' - Google Drive', ''))

        # Recursive scan
        all_entries = self.scan_recursive(folder_id)
        if not all_entries: 
            return {"error": "לא נמצאו קבצים בתיקייה. וודא שיש בה קבצי וידאו והיא פתוחה לצפייה."}

        grouped = {}
        total_episodes = 0
        total_count = len(all_entries)
        
        # Use a more efficient grouping for large datasets
        for idx, (raw_name, url) in enumerate(all_entries, 1):
            if self.progress_callback and (idx % 20 == 0 or idx == total_count):
                self.progress_callback(f"⚙️ מעבד קובץ {idx} מתוך {total_count}...", current=idx, total=total_count)
                
            quality = detect_quality(raw_name)
            name = clean_series_name(raw_name)
            season, episode = parse_season_episode(raw_name)
            
            s_key = f"עונה {season}" if season else "כללי"
            if s_key not in grouped: grouped[s_key] = []
            
            # Duplicate check
            is_duplicate = False
            for existing in grouped[s_key]:
                if existing['episode'] == episode and episode is not None:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                display_name = f"{name} {quality}".strip()
                grouped[s_key].append({"name": display_name, "url": url, "episode": episode})
                total_episodes += 1

        for s in grouped:
            grouped[s].sort(key=lambda x: x['episode'] if x['episode'] is not None else 999)

        return {
            "title": folder_title,
            "data": grouped,
            "stats": {"total_episodes": total_episodes, "total_seasons": len(grouped)}
        }

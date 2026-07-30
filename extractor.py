import re
import html
import time
import random
import urllib.request
import urllib.error
from typing import List, Tuple, Optional, Dict, Set, Any
from bs4 import BeautifulSoup

# Patterns
DRIVE_URL_PATTERN = re.compile(r'https?://(?:drive\.google\.com|www\.drive\.google\.com)[^\s"\'<\)>]+')
LINK_PATTERN = re.compile(r'(https?://(?:drive\.google\.com|www\.drive\.google\.com)[^\s"\'<>)]+)')
EMOJI_PATTERN = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF\U0000FE00-\U0000FE0F\U0001F000-\U0001F02F\U0001F0A0-\U0001F0FF]', flags=re.UNICODE)

def clean_series_name(title: str) -> str:
    if not title: return ''
    title = EMOJI_PATTERN.sub('', title)
    title = re.sub(r'[=_\*-]{5,}', '', title)
    title = re.sub(r'[\u200b\u200c\u200d\u200e\u200f\u2060\uFEFF]', '', title)
    title = re.sub(r'(?i)\b(?:720p|1080p|2160p|480p|4k|hd|sd|driveflix|qbzn)\b', '', title)
    title = re.sub(r'\.(?:mp4|mkv|avi|pdf|zip|rar|txt|jpg|jpeg|png|gif|webm|mov|srt)\b', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+', ' ', title)
    return title.strip()

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
    raise ValueError(f"Invalid folder ID or URL: {input_str}")

def parse_season_episode(name: str) -> Tuple[Optional[int], Optional[int]]:
    name = name.strip()
    patterns = [
        r'[Ss](\d+)[Ee](\d+)',
        r'(?:עונה|ע)\s*(\d+)\s*(?:[-–—:|/\\]?\s*)?(?:פרק|פ)\s*(\d+)',
        r'(?:פרק|פ)\s*(\d+)\s*(?:[-–—:|/\\]?\s*)?(?:עונה|ע)\s*(\d+)',
        r'[Ss]eason\s*(\d+)\s*[Ee]pisode\s*(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            return int(match.group(1)), int(match.group(2))
    
    # Fallback for single values
    s_match = re.search(r'(?:עונה|ע|Season|S)\s*(\d+)', name, re.IGNORECASE)
    e_match = re.search(r'(?:פרק|פ|Episode|E)\s*(\d+)', name, re.IGNORECASE)
    return (int(s_match.group(1)) if s_match else None, 
            int(e_match.group(1)) if e_match else None)

class DriveExtractor:
    def __init__(self, use_browser: bool = False):
        self.use_browser = use_browser
        self.playwright_available = False
        try:
            from playwright.sync_api import sync_playwright
            self.sync_playwright = sync_playwright
            self.playwright_available = True
        except ImportError:
            pass

    def get_html(self, folder_id: str) -> Optional[str]:
        if self.use_browser and self.playwright_available:
            return self.render_with_playwright(folder_id)
        return self.download_html(folder_id)

    def download_html(self, folder_id: str) -> Optional[str]:
        url = f'https://drive.google.com/embeddedfolderview?id={folder_id}#grid'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                return response.read().decode('utf-8', errors='ignore')
        except Exception:
            return None

    def render_with_playwright(self, folder_id: str) -> Optional[str]:
        url = f'https://drive.google.com/embeddedfolderview?id={folder_id}#grid'
        try:
            with self.sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until='networkidle', timeout=45000)
                for _ in range(5):
                    page.evaluate('window.scrollBy(0, document.body.scrollHeight)')
                    time.sleep(0.5)
                content = page.content()
                browser.close()
                return content
        except Exception:
            return None

    def parse_entries(self, content: str) -> List[Tuple[str, str]]:
        entries = []
        soup = BeautifulSoup(content, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/file/d/' in href:
                # Try to get title from parent or children
                title = a.get_text().strip()
                if not title:
                    parent = a.find_parent('div')
                    if parent:
                        title = parent.get_text().strip()
                
                if not title:
                    title = "File " + href.split('/d/')[1][:8]
                
                full_url = href
                if href.startswith('/'):
                    full_url = f"https://drive.google.com{href}"
                
                entries.append((clean_series_name(title), full_url))
        return entries

    def extract_series(self, folder_url: str) -> Dict[str, Any]:
        try:
            folder_id = extract_folder_id(folder_url)
        except ValueError as e:
            return {"error": str(e)}

        content = self.get_html(folder_id)
        if not content:
            return {"error": "Could not fetch folder content. Make sure it's public."}

        # Try to get folder title
        soup = BeautifulSoup(content, 'html.parser')
        title_tag = soup.find('title')
        folder_title = clean_series_name(title_tag.get_text().replace(' - Google Drive', '')) if title_tag else "Unknown Series"

        entries = self.parse_entries(content)
        if not entries:
            # Try subfolders if no files found
            subfolders = []
            for a in soup.find_all('a', href=True):
                if '/folders/' in a['href']:
                    subfolders.append(a['href'])
            
            if subfolders:
                # For simplicity in this version, we just notify about subfolders
                return {"error": "This folder contains subfolders. Please provide the link to the specific season folder.", "subfolders": subfolders}
            return {"error": "No files found in this folder."}

        grouped = {}
        for name, url in entries:
            season, episode = parse_season_episode(name)
            s_key = f"Season {season}" if season else "General"
            if s_key not in grouped:
                grouped[s_key] = []
            grouped[s_key].append({"name": name, "url": url, "episode": episode})

        # Sort by episode
        for s in grouped:
            grouped[s].sort(key=lambda x: x['episode'] if x['episode'] is not None else 999)

        return {
            "title": folder_title,
            "folder_id": folder_id,
            "data": grouped
        }

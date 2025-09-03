#!/usr/bin/env python3
"""
Enhanced Flask Backend with Advanced TikTok Bypass
Uses multiple extraction methods and proxy-like techniques
"""

import os
import sys
import json
import time
import uuid
import threading
import re
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging
import requests
import yt_dlp
from urllib.parse import unquote, parse_qs, urlparse, quote
import base64
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app, origins=["*"])
socketio = SocketIO(app, cors_allowed_origins="*", logger=False, engineio_logger=False)

# Global variables
active_downloads = {}

class AdvancedTikTokExtractor:
    """Advanced TikTok extractor with multiple bypass methods"""
    
    def __init__(self):
        # Rotate through different user agents
        self.mobile_user_agents = [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 15_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 11; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Mobile Safari/537.36',
        ]
        
        self.desktop_user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
        ]
        
        # Third-party services (use responsibly and check their terms)
        self.fallback_services = [
            'https://tikwm.com/api/',
            'https://tiktok.livegram.net/api/download',
            'https://musicaldown.com/api/download',
        ]

    def extract_tiktok_video(self, url):
        """Main TikTok extraction with multiple methods"""
        errors = []
        
        # Clean URL first
        url = self._clean_tiktok_url(url)
        logger.info(f"Processing TikTok URL: {url}")
        
        # Method 1: Updated yt-dlp with fresh options
        try:
            return self._extract_with_fresh_ytdlp(url)
        except Exception as e:
            errors.append(f"yt-dlp method: {str(e)}")
            logger.warning(f"yt-dlp failed: {str(e)}")
        
        # Method 2: Direct API approach with rotation
        try:
            return self._extract_with_api_rotation(url)
        except Exception as e:
            errors.append(f"API rotation: {str(e)}")
            logger.warning(f"API rotation failed: {str(e)}")
        
        # Method 3: Browser simulation
        try:
            return self._extract_with_browser_sim(url)
        except Exception as e:
            errors.append(f"Browser simulation: {str(e)}")
            logger.warning(f"Browser simulation failed: {str(e)}")
        
        # Method 4: Fallback services (last resort)
        try:
            return self._extract_with_fallback_service(url)
        except Exception as e:
            errors.append(f"Fallback services: {str(e)}")
            logger.warning(f"Fallback services failed: {str(e)}")
        
        # All methods failed
        error_msg = f"All TikTok extraction methods failed:\n" + "\n".join(errors)
        logger.error(error_msg)
        raise Exception("TikTok extraction failed. This video may be private, deleted, or TikTok has implemented new protections.")

    def _clean_tiktok_url(self, url):
        """Clean and standardize TikTok URL"""
        # Remove tracking parameters and clean up
        url = re.sub(r'[?&].*$', '', url)  # Remove query parameters
        
        # Handle different TikTok URL formats
        if 'vm.tiktok.com' in url or 'vt.tiktok.com' in url:
            # Resolve short URL
            try:
                session = requests.Session()
                session.max_redirects = 10
                response = session.head(url, allow_redirects=True, timeout=10)
                url = response.url
            except:
                pass
        
        return url

    def _extract_with_fresh_ytdlp(self, url):
        """Extract using yt-dlp with latest configurations"""
        # Use fresh yt-dlp options optimized for current TikTok
        options = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best',
            'nocheckcertificate': True,
            'http_headers': {
                'User-Agent': random.choice(self.mobile_user_agents),
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.tiktok.com/',
                'Origin': 'https://www.tiktok.com',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"iOS"',
            },
            'extractor_args': {
                'tiktok': {
                    'api_hostname': 'api16-normal-c-useast1a.tiktokv.com',
                    'app_version': '26.2.0',
                    'manifest_app_version': '2022600040',
                    'aid': '1988',
                }
            },
            'socket_timeout': 60,
            'retries': 3,
        }
        
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                raise Exception("No video info extracted")
            
            return self._format_tiktok_response(info, url)

    def _extract_with_api_rotation(self, url):
        """Extract using TikTok API with endpoint rotation"""
        video_id = self._extract_video_id(url)
        if not video_id:
            raise Exception("Could not extract video ID")
        
        # Multiple API endpoints to try
        api_endpoints = [
            f"https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/feed/?aweme_id={video_id}",
            f"https://api19-core-c-useast1a.tiktokv.com/aweme/v1/feed/?aweme_id={video_id}",
            f"https://api16-core-c-useast1a.tiktokv.com/aweme/v1/feed/?aweme_id={video_id}",
            f"https://www.tiktok.com/api/item/detail/?itemId={video_id}",
        ]
        
        for user_agent in self.mobile_user_agents[:2]:  # Try top 2 user agents
            headers = {
                'User-Agent': user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.tiktok.com/',
                'Origin': 'https://www.tiktok.com',
                'DNT': '1',
                'Connection': 'keep-alive',
                'X-Requested-With': 'XMLHttpRequest',
            }
            
            for api_url in api_endpoints:
                try:
                    session = requests.Session()
                    response = session.get(api_url, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Handle different API response formats
                        video_data = None
                        if 'aweme_list' in data and data['aweme_list']:
                            video_data = data['aweme_list'][0]
                        elif 'itemInfo' in data and 'itemStruct' in data['itemInfo']:
                            video_data = data['itemInfo']['itemStruct']
                        
                        if video_data and 'video' in video_data:
                            return self._parse_api_response(video_data, video_id)
                            
                except Exception as e:
                    logger.debug(f"API endpoint {api_url} with UA {user_agent[:50]}... failed: {str(e)}")
                    continue
        
        raise Exception("All API endpoints failed")

    def _extract_with_browser_sim(self, url):
        """Extract by simulating browser behavior"""
        session = requests.Session()
        
        # First request: Get the page
        headers = {
            'User-Agent': random.choice(self.desktop_user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        try:
            response = session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            html_content = response.text
            video_id = self._extract_video_id(response.url) or self._extract_video_id(url)
            
            # Look for SIGI_STATE or __UNIVERSAL_DATA_FOR_REHYDRATION__
            patterns = [
                r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>',
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                r'<script>window\.__SIGI_STATE__\s*=\s*({.*?});</script>',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html_content, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        video_data = self._find_video_in_data(data, video_id)
                        if video_data:
                            return self._parse_extracted_data(video_data, video_id)
                    except json.JSONDecodeError:
                        continue
            
            # Fallback: Look for direct video URLs in HTML
            return self._extract_from_html_patterns(html_content, video_id)
            
        except Exception as e:
            logger.error(f"Browser simulation error: {str(e)}")
            raise e

    def _extract_with_fallback_service(self, url):
        """Use third-party services as last resort"""
        video_id = self._extract_video_id(url)
        
        # Try tikwm.com API
        try:
            api_url = f"https://www.tikwm.com/api/"
            data = {
                'url': url,
                'hd': 1
            }
            
            headers = {
                'User-Agent': random.choice(self.desktop_user_agents),
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': 'https://www.tikwm.com/',
            }
            
            response = requests.post(api_url, data=data, headers=headers, timeout=20)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('code') == 0 and 'data' in result:
                    video_data = result['data']
                    
                    # Get the highest quality video URL
                    video_url = video_data.get('hdplay') or video_data.get('play')
                    
                    if video_url:
                        return {
                            'direct_url': video_url,
                            'title': video_data.get('title', f'TikTok_Video_{video_id}'),
                            'filename': f"TikTok_{self._clean_filename(video_data.get('title', 'video'))}_{video_id}.mp4",
                            'filesize': None,
                            'duration': video_data.get('duration'),
                            'platform': 'tiktok',
                            'headers': {
                                'User-Agent': random.choice(self.mobile_user_agents),
                                'Referer': 'https://www.tiktok.com/',
                            },
                            'thumbnail': video_data.get('cover'),
                            'uploader': video_data.get('author', {}).get('unique_id', 'unknown'),
                            'view_count': video_data.get('play_count', 0)
                        }
        except Exception as e:
            logger.warning(f"Fallback service failed: {str(e)}")
        
        raise Exception("All fallback services failed")

    def _extract_video_id(self, url):
        """Extract TikTok video ID from various URL formats"""
        patterns = [
            r'tiktok\.com/.*?/video/(\d+)',
            r'tiktok\.com/@[^/]+/video/(\d+)',
            r'vm\.tiktok\.com/([a-zA-Z0-9]+)',
            r'vt\.tiktok\.com/([a-zA-Z0-9]+)',
            r'tiktok\.com/t/([a-zA-Z0-9]+)',
            r'/video/(\d+)',
            r'itemId[=:](\d+)',
            r'aweme_id[=:](\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None

    def _find_video_in_data(self, data, video_id):
        """Recursively find video data in nested JSON"""
        if isinstance(data, dict):
            # Check common paths
            if 'ItemModule' in data:
                for key, item in data['ItemModule'].items():
                    if video_id and video_id in str(key):
                        return item
            
            if 'webapp.video-detail' in data:
                detail_data = data['webapp.video-detail']
                if 'itemModule' in detail_data:
                    for key, item in detail_data['itemModule'].items():
                        if item and isinstance(item, dict) and 'video' in item:
                            return item
            
            # Recursive search
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    result = self._find_video_in_data(value, video_id)
                    if result:
                        return result
                        
        elif isinstance(data, list):
            for item in data:
                result = self._find_video_in_data(item, video_id)
                if result:
                    return result
        
        return None

    def _parse_api_response(self, video_data, video_id):
        """Parse API response data"""
        video_info = video_data.get('video', {})
        
        # Get video URL
        download_addr = video_info.get('download_addr', {})
        play_addr = video_info.get('play_addr', {})
        
        video_url = None
        if download_addr and 'url_list' in download_addr:
            video_url = download_addr['url_list'][0]
        elif play_addr and 'url_list' in play_addr:
            video_url = play_addr['url_list'][0]
        
        if not video_url:
            raise Exception("No video URL found in API response")
        
        # Try to remove watermark
        if 'playwm' in video_url:
            video_url = video_url.replace('playwm', 'play')
        
        title = video_data.get('desc', f'TikTok_Video_{video_id}')
        
        return {
            'direct_url': video_url,
            'title': title,
            'filename': f"TikTok_{self._clean_filename(title)}_{video_id}.mp4",
            'filesize': None,
            'duration': video_info.get('duration', 0) / 1000 if video_info.get('duration') else None,
            'platform': 'tiktok',
            'headers': {
                'User-Agent': random.choice(self.mobile_user_agents),
                'Referer': 'https://www.tiktok.com/',
            },
            'thumbnail': video_info.get('origin_cover', {}).get('url_list', [None])[0],
            'uploader': video_data.get('author', {}).get('unique_id', 'unknown'),
            'view_count': video_data.get('statistics', {}).get('play_count', 0)
        }

    def _parse_extracted_data(self, video_data, video_id):
        """Parse extracted data from HTML"""
        video_info = video_data.get('video', {})
        
        download_addr = video_info.get('downloadAddr')
        play_addr = video_info.get('playAddr')
        
        video_url = download_addr or play_addr
        if not video_url:
            raise Exception("No video URL in extracted data")
        
        title = video_data.get('desc', f'TikTok_Video_{video_id}')
        
        return {
            'direct_url': video_url,
            'title': title,
            'filename': f"TikTok_{self._clean_filename(title)}_{video_id}.mp4",
            'filesize': None,
            'duration': video_info.get('duration', 0) / 1000 if video_info.get('duration') else None,
            'platform': 'tiktok',
            'headers': {
                'User-Agent': random.choice(self.mobile_user_agents),
                'Referer': 'https://www.tiktok.com/',
            },
            'thumbnail': video_info.get('originCover'),
            'uploader': video_data.get('author', {}).get('uniqueId', 'unknown'),
            'view_count': video_data.get('stats', {}).get('playCount', 0)
        }

    def _extract_from_html_patterns(self, html_content, video_id):
        """Extract video URLs using regex patterns on HTML"""
        patterns = [
            r'"downloadAddr":"([^"]+)"',
            r'"playAddr":"([^"]+)"',
            r'https://[^"]*\.tiktokcdn[^"]*\.com/[^"]*\.mp4[^"]*',
            r'https://v\d{2}[^"]*\.tiktokcdn[^"]*\.com/[^"]*',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                video_url = matches[0]
                video_url = video_url.replace('\\u002F', '/').replace('\\/', '/')
                video_url = unquote(video_url)
                
                if 'playwm' in video_url:
                    video_url = video_url.replace('playwm', 'play')
                
                title_match = re.search(r'"desc":"([^"]+)"', html_content)
                title = title_match.group(1) if title_match else f'TikTok_Video_{video_id}'
                
                return {
                    'direct_url': video_url,
                    'title': title,
                    'filename': f"TikTok_{self._clean_filename(title)}_{video_id}.mp4",
                    'filesize': None,
                    'duration': None,
                    'platform': 'tiktok',
                    'headers': {
                        'User-Agent': random.choice(self.mobile_user_agents),
                        'Referer': 'https://www.tiktok.com/',
                    },
                    'thumbnail': None,
                    'uploader': 'unknown',
                    'view_count': 0
                }
        
        raise Exception("No video URLs found in HTML")

    def _format_tiktok_response(self, info, url):
        """Format yt-dlp response for TikTok"""
        direct_url = info.get('url')
        if not direct_url and 'formats' in info:
            formats = info['formats']
            if formats:
                direct_url = formats[0]['url']
        
        if not direct_url:
            raise Exception("No direct URL found")
        
        video_id = self._extract_video_id(url)
        title = info.get('title', f'TikTok_Video_{video_id}')
        
        return {
            'direct_url': direct_url,
            'title': title,
            'filename': f"TikTok_{self._clean_filename(title)}_{video_id}.mp4",
            'filesize': info.get('filesize'),
            'duration': info.get('duration'),
            'platform': 'tiktok',
            'headers': {
                'User-Agent': random.choice(self.mobile_user_agents),
                'Referer': 'https://www.tiktok.com/',
            },
            'thumbnail': info.get('thumbnail'),
            'uploader': info.get('uploader'),
            'view_count': info.get('view_count')
        }

    def _clean_filename(self, filename):
        """Clean filename for safe file operations"""
        if not filename:
            return 'video'
        clean_name = re.sub(r'[<>:"/\\|?*]', '', filename)
        clean_name = re.sub(r'[^\w\s-]', '', clean_name)
        clean_name = re.sub(r'[-\s]+', '-', clean_name).strip('-')
        return clean_name[:30] if clean_name else 'video'

class StreamingVideoExtractor:
    """Main video extractor with enhanced TikTok support"""
    
    def __init__(self):
        self.tiktok_extractor = AdvancedTikTokExtractor()
        self.base_options = {
            'quiet': True,
            'no_warnings': True,
            'extractaudio': False,
            'format': 'best[height<=1080]',
            'nocheckcertificate': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
            },
            'retries': 3,
            'socket_timeout': 30,
        }
    
    def extract_direct_url(self, url):
        """Main extraction method"""
        platform = self.detect_platform(url)
        logger.info(f"Extracting from {platform}: {url}")
        
        if platform == 'tiktok':
            return self.tiktok_extractor.extract_tiktok_video(url)
        else:
            return self._extract_other_platform(url, platform)
    
    def _extract_other_platform(self, url, platform):
        """Extract from non-TikTok platforms"""
        options = self.base_options.copy()
        
        if platform == 'youtube':
            options['format'] = 'best[height<=1080]/bestvideo[height<=1080]+bestaudio/best'
        
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            
            direct_url = info.get('url')
            if not direct_url and 'formats' in info:
                formats = info['formats']
                for fmt in formats:
                    if fmt.get('url'):
                        direct_url = fmt['url']
                        break
            
            if not direct_url:
                raise Exception("Could not extract video URL")
            
            title = info.get('title', 'video')
            ext = info.get('ext', 'mp4')
            
            return {
                'direct_url': direct_url,
                'title': title,
                'filename': f"{platform.title()}_{self._clean_filename(title)}.{ext}",
                'filesize': info.get('filesize'),
                'duration': info.get('duration'),
                'platform': platform,
                'headers': self.base_options['http_headers'],
                'thumbnail': info.get('thumbnail'),
                'uploader': info.get('uploader'),
                'view_count': info.get('view_count')
            }
    
    def _clean_filename(self, filename):
        """Clean filename"""
        clean_name = re.sub(r'[<>:"/\\|?*]', '', filename)
        clean_name = re.sub(r'[^\w\s-]', '', clean_name)
        clean_name = re.sub(r'[-\s]+', '-', clean_name).strip('-')
        return clean_name[:30] if clean_name else 'video'
    
    def detect_platform(self, url):
        """Detect platform"""
        domain = url.lower()
        
        if any(x in domain for x in ['tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com']):
            return 'tiktok'
        elif any(x in domain for x in ['youtube.com', 'youtu.be', 'm.youtube.com']):
            return 'youtube'
        elif any(x in domain for x in ['instagram.com', 'instagr.am']):
            return 'instagram'
        elif any(x in domain for x in ['facebook.com', 'fb.watch', 'm.facebook.com']):
            return 'facebook'
        else:
            return 'unknown'

# Initialize extractor
extractor = StreamingVideoExtractor()

# Flask routes (same as before)
@app.route('/api/download/quick', methods=['POST'])
def quick_download():
    """Quick download endpoint"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        logger.info(f"Processing quick download for: {url}")
        
        try:
            video_info = extractor.extract_direct_url(url)
            logger.info(f"Successfully extracted: {video_info['title']}")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Extraction failed: {error_msg}")
            
            if "TikTok" in error_msg or "tiktok" in error_msg.lower():
                error_msg = "TikTok extraction failed. The video might be private, deleted, or protected by new anti-bot measures."
            
            return jsonify({'error': error_msg}), 400
        
        download_id = str(uuid.uuid4())
        
        active_downloads[download_id] = {
            'id': download_id,
            'url': url,
            'status': 'ready',
            'platform': video_info['platform'],
            'title': video_info['title'],
            'filename': video_info['filename'],
            'filesize': video_info['filesize'],
            'created_at': datetime.now().isoformat(),
            'type': 'streaming'
        }
        
        return jsonify({
            'download_id': download_id,
            'stream_url': f'/api/stream/{download_id}',
            'filename': video_info['filename'],
            'filesize': video_info['filesize'],
            'title': video_info['title'],
            'platform': video_info['platform'],
            'duration': video_info.get('duration'),
            'thumbnail': video_info.get('thumbnail'),
            'uploader': video_info.get('uploader')
        })
        
    except Exception as e:
        logger.error(f"Quick download setup error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stream/<download_id>')
def stream_video(download_id):
    """Stream video endpoint with enhanced error handling"""
    try:
        if download_id not in active_downloads:
            return jsonify({'error': 'Download not found'}), 404
        
        download_info = active_downloads[download_id]
        url = download_info['url']
        
        logger.info(f"Starting stream for: {download_id}")
        
        # Get fresh video info (URLs may expire)
        try:
            video_info = extractor.extract_direct_url(url)
            logger.info(f"Refreshed video info for streaming")
        except Exception as e:
            error_msg = f'Could not refresh video URL: {str(e)}'
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 400
        
        direct_url = video_info['direct_url']
        filename = video_info['filename']
        
        def generate_stream():
            """Stream video data with enhanced progress tracking"""
            try:
                active_downloads[download_id]['status'] = 'streaming'
                socketio.emit('download_status', {
                    'id': download_id,
                    'status': 'streaming'
                })
                
                logger.info(f"Streaming from: {direct_url[:50]}...")
                
                # Prepare headers
                stream_headers = video_info.get('headers', {})
                stream_headers.update({
                    'Accept': '*/*',
                    'Accept-Encoding': 'identity',
                    'Connection': 'keep-alive',
                })
                
                # Handle range requests
                range_header = request.headers.get('Range')
                if range_header:
                    stream_headers['Range'] = range_header
                
                max_retries = 3
                retry_count = 0
                
                while retry_count < max_retries:
                    try:
                        logger.info(f"Stream attempt {retry_count + 1}")
                        
                        with requests.get(direct_url, headers=stream_headers, stream=True, timeout=60) as r:
                            r.raise_for_status()
                            
                            total_size = int(r.headers.get('content-length', 0))
                            downloaded = 0
                            chunk_size = 65536  # 64KB chunks
                            
                            logger.info(f"Stream started, size: {total_size}")
                            
                            active_downloads[download_id]['total_bytes'] = total_size
                            active_downloads[download_id]['status'] = 'streaming'
                            
                            start_time = time.time()
                            last_progress_time = start_time
                            
                            for chunk in r.iter_content(chunk_size=chunk_size):
                                if chunk:
                                    downloaded += len(chunk)
                                    current_time = time.time()
                                    
                                    if current_time - last_progress_time >= 1.0:
                                        elapsed_time = current_time - start_time
                                        speed = downloaded / elapsed_time if elapsed_time > 0 else 0
                                        percentage = (downloaded / total_size * 100) if total_size > 0 else 0
                                        eta = (total_size - downloaded) / speed if speed > 0 else 0
                                        
                                        progress_data = {
                                            'id': download_id,
                                            'status': 'streaming',
                                            'downloaded_bytes': downloaded,
                                            'total_bytes': total_size,
                                            'speed': speed,
                                            'percentage': round(percentage, 1),
                                            'eta': eta
                                        }
                                        
                                        active_downloads[download_id].update(progress_data)
                                        socketio.emit('download_progress', progress_data)
                                        last_progress_time = current_time
                                    
                                    yield chunk
                            
                            # Mark as completed
                            total_time = time.time() - start_time
                            active_downloads[download_id]['status'] = 'completed'
                            active_downloads[download_id]['total_time'] = total_time
                            
                            logger.info(f"Stream completed in {total_time:.2f}s")
                            
                            socketio.emit('download_status', {
                                'id': download_id,
                                'status': 'completed',
                                'percentage': 100,
                                'total_time': total_time
                            })
                            
                            return
                            
                    except requests.exceptions.RequestException as e:
                        retry_count += 1
                        error_msg = f"Network error (attempt {retry_count}): {str(e)}"
                        logger.warning(error_msg)
                        
                        if retry_count >= max_retries:
                            raise Exception(f"Failed after {max_retries} attempts: {str(e)}")
                        else:
                            time.sleep(2 ** retry_count)
                            continue
                    
            except Exception as e:
                logger.error(f"Streaming error for {download_id}: {str(e)}")
                if download_id in active_downloads:
                    active_downloads[download_id]['status'] = 'error'
                    active_downloads[download_id]['error'] = str(e)
                
                socketio.emit('download_status', {
                    'id': download_id,
                    'status': 'error',
                    'error': str(e)
                })
                raise
        
        response = Response(
            stream_with_context(generate_stream()),
            mimetype='video/mp4',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Cache-Control': 'no-cache',
                'Access-Control-Allow-Origin': '*',
                'Accept-Ranges': 'bytes'
            }
        )
        
        if video_info.get('filesize'):
            response.headers['Content-Length'] = str(video_info['filesize'])
        
        return response
        
    except Exception as e:
        logger.error(f"Error streaming video {download_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/video-info', methods=['POST'])
def get_video_info():
    """Get video information"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        try:
            video_info = extractor.extract_direct_url(url)
        except Exception as e:
            return jsonify({'error': str(e)}), 400
        
        return jsonify({
            'title': video_info['title'],
            'filename': video_info['filename'],
            'filesize': video_info['filesize'],
            'duration': video_info.get('duration'),
            'platform': video_info['platform'],
            'thumbnail': video_info.get('thumbnail'),
            'uploader': video_info.get('uploader'),
            'view_count': video_info.get('view_count'),
            'streaming_available': True
        })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/downloads', methods=['GET'])
def list_downloads():
    """Get list of downloads"""
    return jsonify({
        'active_downloads': list(active_downloads.values()),
        'total_active': len(active_downloads)
    })

@app.route('/api/downloads/clear', methods=['POST'])
def clear_downloads():
    """Clear completed downloads"""
    global active_downloads
    
    before_count = len(active_downloads)
    active_downloads = {
        k: v for k, v in active_downloads.items() 
        if v['status'] in ['queued', 'starting', 'streaming', 'ready']
    }
    cleared_count = before_count - len(active_downloads)
    
    socketio.emit('downloads_cleared')
    
    return jsonify({
        'message': 'Downloads cleared',
        'cleared_count': cleared_count,
        'remaining': len(active_downloads)
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check"""
    try:
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'active_downloads': len(active_downloads),
            'streaming_enabled': True,
            'version': 'advanced_tiktok_bypass',
            'features': {
                'tiktok_multi_method': True,
                'api_rotation': True,
                'fallback_services': True,
                'browser_simulation': True
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# WebSocket handlers
@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {
        'message': 'Connected to advanced TikTok downloader',
        'active_downloads': len(active_downloads)
    })

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('get_downloads')
def handle_get_downloads():
    emit('downloads_update', {
        'downloads': list(active_downloads.values()),
        'total': len(active_downloads)
    })

@app.route('/')
def serve_frontend():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

def main():
    print("Advanced TikTok Video Downloader Starting...")
    print("Multiple extraction methods enabled for maximum success rate!")
    
    try:
        import yt_dlp
        print(f"yt-dlp version: {yt_dlp.version.__version__}")
    except ImportError:
        print("Error: yt-dlp not installed")
        sys.exit(1)
    
    port = int(os.environ.get('PORT', 4000))
    host = '0.0.0.0'
    
    print(f"Server starting at: http://{host}:{port}")
    print("Enhanced TikTok support with 4 extraction methods:")
    print("  1. Advanced yt-dlp with fresh configs")
    print("  2. TikTok API endpoint rotation") 
    print("  3. Browser simulation with data extraction")
    print("  4. Third-party service fallbacks")
    
    try:
        socketio.run(
            app,
            host=host,
            port=port,
            debug=False,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        print("Server stopped")
    except Exception as e:
        print(f"Server error: {str(e)}")

if __name__ == '__main__':
    main()
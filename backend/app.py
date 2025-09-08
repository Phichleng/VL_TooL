"""
Enhanced Flask Backend with Advanced TikTok Bypass - COMPLETE FINAL VERSION
Uses multiple extraction methods and proxy services for maximum success rate
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

# Disable SSL warnings for proxy services
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    """Advanced TikTok extractor with multiple bypass methods including proxy services"""
    
    def __init__(self):
        # Rotate through different user agents
        self.mobile_user_agents = [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 15_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 11; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
        ]
        
        self.desktop_user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
        ]

    def extract_tiktok_video(self, url):
        """Main TikTok extraction with all methods including proxy services"""
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
        
        # Method 4: Third-party proxy services
        try:
            return self._extract_with_proxy_services(url)
        except Exception as e:
            errors.append(f"Proxy services: {str(e)}")
            logger.warning(f"Proxy services failed: {str(e)}")
        
        # Method 5: Use SSSTik API as fallback
        try:
            return self._extract_with_ssstik(url)
        except Exception as e:
            errors.append(f"SSSTik method: {str(e)}")
            logger.warning(f"SSSTik method failed: {str(e)}")
        
        # All methods failed
        error_msg = f"All TikTok extraction methods failed:\n" + "\n".join(errors)
        logger.error(error_msg)
        raise Exception("TikTok extraction failed completely. This video may be private, deleted, or TikTok has implemented new protections.")

    def _extract_with_proxy_services(self, url):
        """Try multiple proxy services for TikTok extraction"""
        proxy_services = [
            ("SnapTik", self._extract_with_snaptik),
            ("TikMate", self._extract_with_tikmate),
            ("SaveTT", self._extract_with_savett),
            ("TikWM", self._extract_with_tikwm),
            ("CORS Proxy", self._extract_with_cors_proxy)
        ]
        
        for service_name, extract_func in proxy_services:
            try:
                logger.info(f"Trying {service_name} service...")
                return extract_func(url)
            except Exception as e:
                logger.debug(f"{service_name} failed: {str(e)}")
                continue
        
        raise Exception("All proxy services failed")

    def _extract_with_snaptik(self, url):
        """Extract using SnapTik service"""
        try:
            session = requests.Session()
            
            headers = {
                'User-Agent': random.choice(self.desktop_user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Get SnapTik page
            response = session.get('https://snaptik.app/', headers=headers, timeout=20)
            response.raise_for_status()
            
            # Extract token
            token_match = re.search(r'name="token" value="([^"]+)"', response.text)
            if not token_match:
                raise Exception("Could not find SnapTik token")
            
            token = token_match.group(1)
            
            # Submit URL
            post_data = {
                'url': url,
                'token': token
            }
            
            headers.update({
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://snaptik.app',
                'Referer': 'https://snaptik.app/',
            })
            
            response = session.post('https://snaptik.app/abc', data=post_data, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Find download link
            download_matches = re.findall(r'href="([^"]*)"[^>]*>.*?Download', response.text, re.IGNORECASE | re.DOTALL)
            
            download_url = None
            for match in download_matches:
                if 'http' in match and ('tiktok' in match or 'snaptik' in match or 'tikcdn' in match):
                    download_url = match
                    break
            
            if not download_url:
                raise Exception("Could not find SnapTik download link")
            
            # Extract title
            title_match = re.search(r'<h3[^>]*>([^<]+)</h3>', response.text)
            title = title_match.group(1).strip() if title_match else f"TikTok_Video_{self._extract_video_id(url)}"
            
            return {
                'direct_url': download_url,
                'title': title,
                'filename': f"TikTok_SnapTik_{self._clean_filename(title)}.mp4",
                'filesize': None,
                'duration': None,
                'platform': 'tiktok',
                'headers': {
                    'User-Agent': random.choice(self.mobile_user_agents),
                    'Referer': 'https://snaptik.app/',
                },
                'thumbnail': None,
                'uploader': 'unknown',
                'view_count': 0
            }
            
        except Exception as e:
            raise Exception(f"SnapTik extraction failed: {str(e)}")

    def _extract_with_tikmate(self, url):
        """Extract using TikMate service"""
        try:
            session = requests.Session()
            
            headers = {
                'User-Agent': random.choice(self.desktop_user_agents),
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://tikmate.online',
                'Referer': 'https://tikmate.online/',
            }
            
            # Submit to TikMate
            data = {'url': url}
            response = session.post('https://tikmate.online/download', data=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Try JSON first
            try:
                result = response.json()
                if result.get('success'):
                    download_url = result.get('url')
                    title = result.get('title', f"TikTok_Video_{self._extract_video_id(url)}")
                else:
                    raise Exception("TikMate API returned error")
            except:
                # Parse HTML response
                download_match = re.search(r'href="([^"]*)"[^>]*>.*?Download', response.text, re.IGNORECASE | re.DOTALL)
                if not download_match:
                    raise Exception("Could not find TikMate download link")
                
                download_url = download_match.group(1)
                title = f"TikTok_Video_{self._extract_video_id(url)}"
            
            if not download_url:
                raise Exception("No download URL from TikMate")
            
            return {
                'direct_url': download_url,
                'title': title,
                'filename': f"TikTok_TikMate_{self._clean_filename(title)}.mp4",
                'filesize': None,
                'duration': None,
                'platform': 'tiktok',
                'headers': {
                    'User-Agent': random.choice(self.mobile_user_agents),
                    'Referer': 'https://tikmate.online/',
                },
                'thumbnail': None,
                'uploader': 'unknown',
                'view_count': 0
            }
            
        except Exception as e:
            raise Exception(f"TikMate extraction failed: {str(e)}")

    def _extract_with_savett(self, url):
        """Extract using SaveTT service"""
        try:
            session = requests.Session()
            
            headers = {
                'User-Agent': random.choice(self.desktop_user_agents),
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Content-Type': 'application/json',
                'Origin': 'https://savett.cc',
                'Referer': 'https://savett.cc/',
            }
            
            # Submit to SaveTT
            data = json.dumps({'url': url})
            response = session.post('https://savett.cc/api/ajaxSearch', data=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('status') != 'ok':
                raise Exception("SaveTT API returned error")
            
            # Extract video URL
            data = result.get('data', {})
            video_url = data.get('hd') or data.get('sd')
            
            if not video_url:
                raise Exception("No video URL from SaveTT")
            
            title = data.get('title', f"TikTok_Video_{self._extract_video_id(url)}")
            
            return {
                'direct_url': video_url,
                'title': title,
                'filename': f"TikTok_SaveTT_{self._clean_filename(title)}.mp4",
                'filesize': None,
                'duration': data.get('duration'),
                'platform': 'tiktok',
                'headers': {
                    'User-Agent': random.choice(self.mobile_user_agents),
                    'Referer': 'https://savett.cc/',
                },
                'thumbnail': data.get('thumbnail'),
                'uploader': data.get('author', 'unknown'),
                'view_count': 0
            }
            
        except Exception as e:
            raise Exception(f"SaveTT extraction failed: {str(e)}")

    def _extract_with_tikwm(self, url):
        """Extract using TikWM service"""
        try:
            session = requests.Session()
            
            headers = {
                'User-Agent': random.choice(self.desktop_user_agents),
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': 'https://www.tikwm.com/',
            }
            
            # Try tikwm.com API
            api_url = "https://www.tikwm.com/api/"
            data = {
                'url': url,
                'hd': 1
            }
            
            response = session.post(api_url, data=data, headers=headers, timeout=20)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('code') == 0 and 'data' in result:
                video_data = result['data']
                
                # Get the highest quality video URL
                video_url = video_data.get('hdplay') or video_data.get('play')
                
                if not video_url:
                    raise Exception("No video URL from TikWM")
                
                return {
                    'direct_url': video_url,
                    'title': video_data.get('title', f'TikTok_Video_{self._extract_video_id(url)}'),
                    'filename': f"TikTok_TikWM_{self._clean_filename(video_data.get('title', 'video'))}.mp4",
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
            else:
                raise Exception("TikWM API returned error or no data")
                
        except Exception as e:
            raise Exception(f"TikWM extraction failed: {str(e)}")

    def _extract_with_cors_proxy(self, url):
        """Use public CORS proxy services"""
        try:
            proxies = [
                'https://api.allorigins.win/raw?url=',
                'https://api.codetabs.com/v1/proxy?quest=',
            ]
            
            session = requests.Session()
            
            for proxy in proxies:
                try:
                    headers = {
                        'User-Agent': random.choice(self.mobile_user_agents),
                    }
                    
                    proxy_url = f"{proxy}{requests.utils.quote(url, safe='')}"
                    response = session.get(proxy_url, headers=headers, timeout=25)
                    response.raise_for_status()
                    
                    # Parse for video data
                    html_content = response.text
                    video_id = self._extract_video_id(url)
                    
                    patterns = [
                        r'"downloadAddr":"([^"]+)"',
                        r'"playAddr":"([^"]+)"',
                        r'https://[^"]*\.tiktokcdn[^"]*\.com/[^"]*\.mp4[^"]*',
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, html_content)
                        if matches:
                            video_url = matches[0].replace('\\u002F', '/').replace('\\/', '/')
                            
                            title_match = re.search(r'"desc":"([^"]+)"', html_content)
                            title = title_match.group(1) if title_match else f'TikTok_Video_{video_id}'
                            
                            return {
                                'direct_url': video_url,
                                'title': title,
                                'filename': f"TikTok_Proxy_{self._clean_filename(title)}.mp4",
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
                    
                except Exception as e:
                    logger.debug(f"CORS proxy {proxy} failed: {str(e)}")
                    continue
            
            raise Exception("All CORS proxies failed")
            
        except Exception as e:
            raise Exception(f"CORS proxy extraction failed: {str(e)}")

    def _extract_with_ssstik(self, url):
        """Use SSSTik API as a reliable fallback"""
        try:
            api_url = "https://ssstik.io/abc"
            
            headers = {
                'User-Agent': random.choice(self.desktop_user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://ssstik.io',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Referer': 'https://ssstik.io/',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
            }
            
            # First get the page to get the token
            session = requests.Session()
            response = session.get("https://ssstik.io/", headers=headers, timeout=30)
            response.raise_for_status()
            
            # Extract the token from the page
            token_match = re.search(r'name="token" value="([^"]+)"', response.text)
            if not token_match:
                raise Exception("Could not extract token from SSSTik")
                
            token = token_match.group(1)
            
            # Prepare the form data
            data = {
                'id': url,
                'locale': 'en',
                'tt': token,
            }
            
            # Submit the form
            response = session.post(api_url, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse the response
            result_match = re.search(r'<a href="([^"]+)"[^>]*>Download Without Watermark', response.text)
            if not result_match:
                raise Exception("Could not find download link in SSSTik response")
                
            download_url = result_match.group(1)
            
            # Extract title
            title_match = re.search(r'<p class="maintext">([^<]+)</p>', response.text)
            title = title_match.group(1) if title_match else f"TikTok_Video_{self._extract_video_id(url)}"
            
            return {
                'direct_url': download_url,
                'title': title,
                'filename': f"TikTok_SSSTik_{self._clean_filename(title)}.mp4",
                'filesize': None,
                'duration': None,
                'platform': 'tiktok',
                'headers': {
                    'User-Agent': random.choice(self.mobile_user_agents),
                    'Referer': 'https://ssstik.io/',
                },
                'thumbnail': None,
                'uploader': 'unknown',
                'view_count': 0
            }
            
        except Exception as e:
            raise Exception(f"SSSTik extraction failed: {str(e)}")

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
                headers = {'User-Agent': random.choice(self.mobile_user_agents)}
                response = session.head(url, headers=headers, allow_redirects=True, timeout=10)
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
            r'aweme_id[=:](\raweme_id[=:](\d+)',
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
        
        # Try to remove watermark - Simple URL manipulation
        # This replaces 'playwm' (play with watermark) with 'play' (potentially without watermark)
        # Note: This is just URL manipulation, not video processing
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
                
                # Try to remove watermark - Simple URL manipulation
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
        """Extract from non-TikTok platforms with enhanced YouTube support"""
        options = self.base_options.copy()
        
        if platform == 'youtube':
            # Enhanced YouTube options to fix extraction issues
            options.update({
                'format': 'best[height<=1080]/bestvideo[height<=1080]+bestaudio/best',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Sec-Fetch-Mode': 'navigate',
                },
                'extractor_args': {
                    'youtube': {
                        'skip': ['dash', 'hls'],  # Skip problematic formats
                        'player_client': ['android', 'web'],  # Try different clients
                    }
                },
                'cookies': None,  # Don't use cookies
                'age_limit': None,  # Don't enforce age limits
            })
        elif platform == 'instagram':
            options['http_headers']['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
        
        # Try multiple extraction attempts for YouTube
        if platform == 'youtube':
            return self._extract_youtube_with_fallback(url, options)
        else:
            return self._extract_generic_platform(url, platform, options)
    
    def _extract_youtube_with_fallback(self, url, base_options):
        """Extract YouTube with multiple fallback methods"""
        errors = []
        
        # Method 1: Standard extraction
        try:
            options = base_options.copy()
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
                return self._format_platform_response(info, 'youtube')
        except Exception as e:
            errors.append(f"Standard method: {str(e)}")
            logger.warning(f"YouTube standard extraction failed: {str(e)}")
        
        # Method 2: Try with different client
        try:
            options = base_options.copy()
            options['extractor_args']['youtube']['player_client'] = ['android']
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
                return self._format_platform_response(info, 'youtube')
        except Exception as e:
            errors.append(f"Android client: {str(e)}")
            logger.warning(f"YouTube Android client failed: {str(e)}")
        
        # Method 3: Try with embed client
        try:
            options = base_options.copy()
            options['extractor_args']['youtube']['player_client'] = ['web_embedded']
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
                return self._format_platform_response(info, 'youtube')
        except Exception as e:
            errors.append(f"Embedded client: {str(e)}")
            logger.warning(f"YouTube embedded client failed: {str(e)}")
        
        # Method 4: Try without extractor args
        try:
            options = base_options.copy()
            options.pop('extractor_args', None)
            options['format'] = 'worst'  # Try worst quality as fallback
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
                return self._format_platform_response(info, 'youtube')
        except Exception as e:
            errors.append(f"Basic method: {str(e)}")
            logger.warning(f"YouTube basic method failed: {str(e)}")
        
        # All methods failed
        error_summary = "All YouTube extraction methods failed:\n" + "\n".join(errors)
        logger.error(error_summary)
        raise Exception("YouTube video extraction failed. This video may be age-restricted, private, or unavailable in your region.")
    
    def _extract_generic_platform(self, url, platform, options):
        """Extract from generic platforms"""
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            return self._format_platform_response(info, platform)
    
    def _format_platform_response(self, info, platform):
        """Format response for any platform"""
        if not info:
            raise Exception("No video info extracted")
        
        # Get direct URL
        direct_url = info.get('url')
        if not direct_url and 'formats' in info:
            formats = info['formats']
            # Try to find best format with video+audio
            best_format = None
            for fmt in formats:
                if fmt.get('url') and fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                    if not best_format or (fmt.get('height', 0) > best_format.get('height', 0)):
                        best_format = fmt
            
            # Fallback to any format with URL
            if not best_format:
                for fmt in formats:
                    if fmt.get('url'):
                        best_format = fmt
                        break
            
            if best_format:
                direct_url = best_format['url']
        
        if not direct_url:
            raise Exception("Could not extract video URL from available formats")
        
        title = info.get('title', 'video')
        ext = info.get('ext', 'mp4')
        
        return {
            'direct_url': direct_url,
            'title': title,
            'filename': f"{platform.title()}_{self._clean_filename(title)}.{ext}",
            'filesize': info.get('filesize') or info.get('filesize_approx'),
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

# Helper functions for proxy services
def clean_filename(filename):
    """Clean filename for safe file operations"""
    if not filename:
        return 'video'
    clean_name = re.sub(r'[<>:"/\\|?*]', '', filename)
    clean_name = re.sub(r'[^\w\s-]', '', clean_name)
    clean_name = re.sub(r'[-\s]+', '-', clean_name).strip('-')
    return clean_name[:30] if clean_name else 'video'

def extract_video_id_from_url(url):
    """Extract video ID from TikTok URL"""
    patterns = [
        r'tiktok\.com/.*?/video/(\d+)',
        r'tiktok\.com/@[^/]+/video/(\d+)',
        r'vm\.tiktok\.com/([a-zA-Z0-9]+)',
        r'vt\.tiktok\.com/([a-zA-Z0-9]+)',
        r'/video/(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return str(int(time.time()))

# Standalone proxy extraction functions
def extract_with_snaptik(url):
    """Extract using SnapTik service"""
    try:
        session = requests.Session()
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Get SnapTik page
        response = session.get('https://snaptik.app/', headers=headers, timeout=20)
        response.raise_for_status()
        
        # Extract token
        token_match = re.search(r'name="token" value="([^"]+)"', response.text)
        if not token_match:
            raise Exception("Could not find SnapTik token")
        
        token = token_match.group(1)
        
        # Submit URL
        post_data = {
            'url': url,
            'token': token
        }
        
        headers.update({
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://snaptik.app',
            'Referer': 'https://snaptik.app/',
        })
        
        response = session.post('https://snaptik.app/abc', data=post_data, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Find download link
        download_matches = re.findall(r'href="([^"]*)"[^>]*>.*?Download', response.text, re.IGNORECASE | re.DOTALL)
        
        download_url = None
        for match in download_matches:
            if 'http' in match and ('tiktok' in match or 'snaptik' in match or 'tikcdn' in match):
                download_url = match
                break
        
        if not download_url:
            raise Exception("Could not find SnapTik download link")
        
        # Extract title
        title_match = re.search(r'<h3[^>]*>([^<]+)</h3>', response.text)
        title = title_match.group(1).strip() if title_match else f"TikTok_Video_{extract_video_id_from_url(url)}"
        
        return {
            'direct_url': download_url,
            'title': title,
            'filename': f"TikTok_SnapTik_{clean_filename(title)}.mp4",
            'filesize': None,
            'duration': None,
            'platform': 'tiktok',
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://snaptik.app/',
            },
            'thumbnail': None,
            'uploader': 'unknown',
            'view_count': 0
        }
        
    except Exception as e:
        raise Exception(f"SnapTik extraction failed: {str(e)}")

# Flask routes
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
    """COMPLETE FIXED streaming endpoint with intelligent TikTok handling"""
    if download_id not in active_downloads:
        return jsonify({'error': 'Download not found'}), 404
    
    download_info = active_downloads[download_id]
    url = download_info['url']
    platform = download_info.get('platform', extractor.detect_platform(url))
    
    logger.info(f"Starting stream for {platform}: {download_id}")
    
    def generate_stream():
        """Main streaming generator with proper error handling"""
        try:
            # Update status
            active_downloads[download_id]['status'] = 'streaming'
            socketio.emit('download_status', {
                'id': download_id,
                'status': 'streaming'
            })
            
            # Use different strategies based on platform
            if platform == 'tiktok':
                yield from handle_tiktok_streaming(download_id, url)
            else:
                yield from handle_regular_streaming(download_id, url)
                
        except Exception as e:
            logger.error(f"Streaming generator error: {str(e)}")
            
            # Update status
            if download_id in active_downloads:
                active_downloads[download_id].update({
                    'status': 'error',
                    'error': str(e)
                })
            
            socketio.emit('download_status', {
                'id': download_id,
                'status': 'error',
                'error': str(e)
            })
            
            # Yield error message instead of raising StopIteration
            error_msg = f"Streaming failed: {str(e)}"
            yield error_msg.encode('utf-8')
    
    def handle_tiktok_streaming(download_id, url):
        """Enhanced TikTok handling with proxy-based fallbacks"""
        
        # Updated method list with all proxy techniques
        tiktok_methods = [
            ('Primary yt-dlp', lambda u: extractor.extract_direct_url(u)),
            ('Fresh yt-dlp', lambda u: extractor.tiktok_extractor._extract_with_fresh_ytdlp(u)),
            ('API rotation', lambda u: extractor.tiktok_extractor._extract_with_api_rotation(u)),
            ('Browser simulation', lambda u: extractor.tiktok_extractor._extract_with_browser_sim(u)),
            ('SnapTik service', lambda u: extractor.tiktok_extractor._extract_with_snaptik(u)),
            ('TikMate service', lambda u: extractor.tiktok_extractor._extract_with_tikmate(u)),
            ('SaveTT service', lambda u: extractor.tiktok_extractor._extract_with_savett(u)),
            ('TikWM service', lambda u: extractor.tiktok_extractor._extract_with_tikwm(u)),
            ('CORS proxy', lambda u: extractor.tiktok_extractor._extract_with_cors_proxy(u)),
            ('SSSTik fallback', lambda u: extractor.tiktok_extractor._extract_with_ssstik(u))
        ]
        
        for method_name, extract_func in tiktok_methods:
            logger.info(f"Trying TikTok method: {method_name}")
            
            try:
                # Get video info using this method
                video_info = extract_func(url)
                if not video_info or not video_info.get('direct_url'):
                    logger.warning(f"{method_name} returned no URL")
                    continue
                
                # For third-party services, try direct streaming (they often provide working URLs)
                if any(service in method_name.lower() for service in ['snaptik', 'tikmate', 'savett', 'tikwm']):
                    # These services often provide URLs that work directly
                    try:
                        logger.info(f"  {method_name} - direct streaming attempt")
                        
                        yield from perform_streaming(
                            video_info['direct_url'],
                            video_info,
                            download_id,
                            video_info['filename']
                        )
                        
                        logger.info(f"TikTok streaming succeeded with {method_name}")
                        return
                        
                    except Exception as stream_error:
                        logger.warning(f"  {method_name} streaming failed: {str(stream_error)}")
                        continue
                
                else:
                    # For yt-dlp methods, try with retry logic
                    for attempt in range(2):
                        try:
                            logger.info(f"  {method_name} attempt {attempt + 1}/2")
                            
                            yield from perform_streaming(
                                video_info['direct_url'],
                                video_info,
                                download_id,
                                video_info['filename']
                            )
                            
                            logger.info(f"TikTok streaming succeeded with {method_name}")
                            return
                            
                        except Exception as stream_error:
                            error_str = str(stream_error)
                            
                            if "403" in error_str or "Forbidden" in error_str:
                                logger.warning(f"  {method_name} got 403, attempt {attempt + 1}")
                                if attempt == 0:
                                    time.sleep(1)
                                    continue
                            else:
                                logger.error(f"  {method_name} streaming failed: {error_str}")
                            
                            break
                            
            except Exception as extract_error:
                logger.warning(f"{method_name} extraction failed: {str(extract_error)}")
                continue
        
        # All methods failed
        error_msg = "All TikTok extraction and streaming methods failed. The video appears to be heavily protected by TikTok's anti-bot systems."
        logger.error(error_msg)
        
        active_downloads[download_id].update({
            'status': 'error',
            'error': error_msg
        })
        
        socketio.emit('download_status', {
            'id': download_id,
            'status': 'error',
            'error': error_msg
        })
        
        yield error_msg.encode('utf-8')
    
    def handle_regular_streaming(download_id, url):
        """Handle non-TikTok platforms with standard retry logic"""
        max_retries = 3
        
        for retry in range(max_retries):
            try:
                logger.info(f"Regular streaming attempt {retry + 1}/{max_retries}")
                
                # Get fresh video info on each retry
                video_info = extractor.extract_direct_url(url)
                
                yield from perform_streaming(
                    video_info['direct_url'],
                    video_info,
                    download_id,
                    video_info['filename']
                )
                
                # Success - exit retry loop
                logger.info(f"Regular streaming succeeded on attempt {retry + 1}")
                return
                
            except Exception as e:
                logger.warning(f"Regular streaming attempt {retry + 1} failed: {str(e)}")
                
                if retry < max_retries - 1:
                    # Wait before retry
                    wait_time = min(2 ** retry, 5)  # Cap at 5 seconds
                    time.sleep(wait_time)
                    continue
                else:
                    # Final failure
                    error_msg = f"Regular streaming failed after {max_retries} attempts: {str(e)}"
                    logger.error(error_msg)
                    
                    active_downloads[download_id].update({
                        'status': 'error',
                        'error': error_msg
                    })
                    
                    socketio.emit('download_status', {
                        'id': download_id,
                        'status': 'error',
                        'error': error_msg
                    })
                    
                    yield error_msg.encode('utf-8')
    
    def perform_streaming(direct_url, video_info, download_id, filename):
        """Core streaming logic with proper error handling - FIXED VERSION"""
        logger.info(f"Streaming from: {direct_url[:100]}...")
        
        # Prepare headers
        headers = video_info.get('headers', {}).copy()
        
        # Platform-specific headers
        if 'tiktok' in direct_url.lower():
            headers.update({
                'Accept': '*/*',
                'Accept-Encoding': 'identity',
                'Connection': 'keep-alive',
                'Referer': 'https://www.tiktok.com/',
                'Origin': 'https://www.tiktok.com',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
                'sec-ch-ua': '"Chromium";v="119", "Not?A_Brand";v="24"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"iOS"',
                'Sec-Fetch-Dest': 'video',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site',
            })
        else:
            headers.update({
                'Accept': '*/*',
                'Accept-Encoding': 'identity',
                'Connection': 'keep-alive',
            })
        
        # Handle range requests
        range_header = request.headers.get('Range')
        if range_header:
            headers['Range'] = range_header
        
        # Create session with FIXED retry strategy
        session = requests.Session()
        session.max_redirects = 3
        
        # FIXED: Use allowed_methods instead of deprecated method_whitelist
        from urllib3.util.retry import Retry
        from requests.adapters import HTTPAdapter
        
        retry_strategy = Retry(
            total=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],  # FIXED: was method_whitelist
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        try:
            # Make the request
            response = session.get(
                direct_url,
                headers=headers,
                stream=True,
                timeout=(10, 30),  # 10s connect, 30s read
                allow_redirects=True,
                verify=False  # Skip SSL verification for problematic CDNs
            )
            
            # Handle specific error codes
            if response.status_code == 403:
                raise requests.exceptions.RequestException(f"403 Forbidden: {direct_url}")
            elif response.status_code == 404:
                raise requests.exceptions.RequestException(f"404 Not Found: Video may have been deleted")
            elif response.status_code >= 400:
                raise requests.exceptions.RequestException(f"HTTP {response.status_code}: {response.reason}")
            
            # Get content information
            total_size = int(response.headers.get('content-length', 0))
            content_type = response.headers.get('content-type', 'video/mp4')
            
            logger.info(f"Stream connected - Size: {total_size} bytes, Type: {content_type}")
            
            # Update download info
            active_downloads[download_id].update({
                'total_bytes': total_size,
                'status': 'streaming',
                'content_type': content_type
            })
            
            # Stream the content
            downloaded = 0
            chunk_size = 16384  # 16KB chunks for better performance
            start_time = time.time()
            last_progress_time = start_time
            
            try:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if not chunk:  # Skip empty chunks
                        continue
                    
                    downloaded += len(chunk)
                    current_time = time.time()
                    
                    # Update progress every second
                    if current_time - last_progress_time >= 1.0 or downloaded >= total_size:
                        elapsed_time = current_time - start_time
                        speed = downloaded / elapsed_time if elapsed_time > 0 else 0
                        percentage = (downloaded / total_size * 100) if total_size > 0 else 0
                        eta = (total_size - downloaded) / speed if speed > 0 and downloaded < total_size else 0
                        
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
                
                # Streaming completed successfully
                total_time = time.time() - start_time
                final_speed = downloaded / total_time if total_time > 0 else 0
                
                active_downloads[download_id].update({
                    'status': 'completed',
                    'total_time': total_time,
                    'percentage': 100,
                    'final_speed': final_speed
                })
                
                logger.info(f"Streaming completed successfully in {total_time:.2f}s")
                
                socketio.emit('download_status', {
                    'id': download_id,
                    'status': 'completed',
                    'percentage': 100,
                    'total_time': total_time
                })
                
            except Exception as streaming_error:
                logger.error(f"Error during content streaming: {str(streaming_error)}")
                raise
                
        except Exception as request_error:
            logger.error(f"Request failed: {str(request_error)}")
            raise
        finally:
            try:
                session.close()
            except:
                pass
    
    # Get initial video info for response headers
    try:
        initial_video_info = extractor.extract_direct_url(url)
        filename = initial_video_info['filename']
        filesize = initial_video_info.get('filesize')
        content_type = 'video/mp4'
        
        logger.info(f"Initial extraction successful: {filename}")
        
    except Exception as e:
        logger.error(f"Initial video extraction failed: {str(e)}")
        return jsonify({
            'error': f'Could not extract video information: {str(e)}',
            'details': 'The video may be private, deleted, or temporarily unavailable'
        }), 400
    
    # Create streaming response
    try:
        response = Response(
            stream_with_context(generate_stream()),
            mimetype=content_type,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
                'Access-Control-Allow-Headers': 'Range, Content-Range, Content-Length',
                'Access-Control-Expose-Headers': 'Content-Length, Content-Range, Accept-Ranges',
                'Accept-Ranges': 'bytes'
            }
        )
        
        if filesize and filesize > 0:
            response.headers['Content-Length'] = str(filesize)
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to create streaming response: {str(e)}")
        return jsonify({'error': f'Streaming setup failed: {str(e)}'}), 500

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
            'version': 'complete_proxy_enhanced_final',
            'features': {
                'tiktok_multi_method': True,
                'api_rotation': True,
                'fallback_services': True,
                'browser_simulation': True,
                'proxy_services': True,
                'snaptik': True,
                'tikmate': True,
                'savett': True,
                'tikwm': True,
                'cors_proxy': True,
                'ssstik': True,
                'fixed_streaming': True,
                'watermark_removal': True
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
        'message': 'Connected to enhanced TikTok downloader with all proxy services',
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
    print("Enhanced TikTok Video Downloader Starting - COMPLETE FINAL VERSION...")
    print("Multiple extraction methods + All proxy services enabled!")
    print("FEATURES:")
    print("- 10 different TikTok extraction methods")
    print("- Third-party proxy services (SnapTik, TikMate, SaveTT, TikWM)")
    print("- CORS proxy fallbacks")
    print("- Enhanced error handling and watermark removal attempts")
    print("- Fixed all urllib3 deprecation warnings")
    print("- Comprehensive streaming with intelligent fallbacks")
    
    try:
        import yt_dlp
        print(f"yt-dlp version: {yt_dlp.version.__version__}")
    except ImportError:
        print("Error: yt-dlp not installed")
        sys.exit(1)
    
    port = int(os.environ.get('PORT', 4000))
    host = '0.0.0.0'
    
    print(f"Server starting at: http://{host}:{port}")
    print("Enhanced TikTok support with 10 extraction methods:")
    print("  1. Advanced yt-dlp with fresh configs")
    print("  2. TikTok API endpoint rotation") 
    print("  3. Browser simulation with data extraction")
    print("  4. SnapTik proxy service")
    print("  5. TikMate proxy service")
    print("  6. SaveTT proxy service")
    print("  7. TikWM proxy service")
    print("  8. CORS proxy services")
    print("  9. SSSTik fallback service")
    print("  10. Multiple streaming retry strategies")
    print("\nALL ISSUES FIXED:")
    print("  ✓ urllib3 deprecation warnings")
    print("  ✓ StopIteration generator errors")
    print("  ✓ 403 Forbidden error handling with intelligent fallbacks")
    print("  ✓ TikTok URL expiration handling")
    print("  ✓ Complete proxy service integration")
    print("  ✓ Watermark removal attempts (URL manipulation)")
    print("  ✓ Comprehensive fallback system")
    
    try:
        socketio.run(
            app,
            host=host,
            port=port,
            debug=True,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        print("Server stopped")
    except Exception as e:
        print(f"Server error: {str(e)}")

if __name__ == '__main__':
    main()#!/usr/bin/env python3

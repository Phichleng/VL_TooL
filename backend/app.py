#!/usr/bin/env python3
"""
Enhanced Flask Backend with Fixed TikTok Support and Better Error Handling
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
import io
import logging
import requests
import yt_dlp
from urllib.parse import unquote, parse_qs, urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app, origins=["*"])
socketio = SocketIO(app, cors_allowed_origins="*", logger=False, engineio_logger=False)

# Global variables
active_downloads = {}

class StreamingVideoExtractor:
    """Enhanced video extractor with robust TikTok support"""
    
    def __init__(self):
        self.base_options = {
            'quiet': True,
            'no_warnings': True,
            'extractaudio': False,
            'format': 'best[height<=1080]',
            'nocheckcertificate': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            'retries': 5,
            'fragment_retries': 5,
            'socket_timeout': 60,
            'extractor_retries': 5,
        }
    
    def extract_direct_url(self, url):
        """Extract direct video URL with enhanced error handling"""
        try:
            # Clean and validate URL
            url = url.strip()
            if not url:
                raise Exception("Empty URL provided")
            
            # Detect platform
            platform = self.detect_platform(url)
            logger.info(f"Detected platform: {platform} for URL: {url}")
            
            # Use different extraction methods based on platform
            if platform == 'tiktok':
                return self._extract_tiktok_enhanced(url)
            else:
                return self._extract_generic_video(url, platform)
                
        except Exception as e:
            logger.error(f"Error extracting video info from {url}: {str(e)}")
            raise e
    
    def _extract_tiktok_enhanced(self, url):
        """Enhanced TikTok extraction with multiple fallback methods"""
        errors = []
        
        # Method 1: Try latest yt-dlp with updated options
        try:
            options = self.base_options.copy()
            options.update({
                'format': 'best/worst',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
                    'Referer': 'https://www.tiktok.com/',
                    'Accept': '*/*',
                },
                'extractor_args': {
                    'tiktok': {
                        'api_hostname': 'api16-normal-c-useast1a.tiktokv.com',
                        'app_version': '26.2.0',
                        'manifest_app_version': '2022600040',
                    }
                },
                'cookiefile': None,  # Don't use cookies
            })
            
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info and ('url' in info or 'formats' in info):
                    return self._format_tiktok_response(info, url)
                    
        except Exception as e:
            error_msg = str(e)
            errors.append(f"Method 1 (yt-dlp): {error_msg}")
            logger.warning(f"TikTok method 1 failed: {error_msg}")
        
        # Method 2: Try alternative TikTok extraction
        try:
            return self._extract_tiktok_alternative(url)
        except Exception as e:
            errors.append(f"Method 2 (alternative): {str(e)}")
            logger.warning(f"TikTok method 2 failed: {str(e)}")
        
        # Method 3: Try web scraping approach
        try:
            return self._extract_tiktok_web_scraping(url)
        except Exception as e:
            errors.append(f"Method 3 (web scraping): {str(e)}")
            logger.warning(f"TikTok method 3 failed: {str(e)}")
        
        # All methods failed
        error_summary = "All TikTok extraction methods failed:\n" + "\n".join(errors)
        logger.error(error_summary)
        raise Exception("TikTok video extraction failed. The video might be private, deleted, or TikTok has updated their protection. Please try another video.")
    
    def _extract_tiktok_alternative(self, url):
        """Alternative TikTok extraction using different approach"""
        try:
            # First, resolve short URLs
            resolved_url = self._resolve_short_url(url)
            video_id = self._extract_tiktok_id(resolved_url or url)
            
            if not video_id:
                raise Exception("Could not extract TikTok video ID")
            
            # Try multiple extraction approaches
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.tiktok.com/',
                'Origin': 'https://www.tiktok.com',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            }
            
            # Try API endpoint
            api_url = f"https://www.tiktok.com/api/item/detail/?itemId={video_id}"
            
            session = requests.Session()
            response = session.get(api_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'itemInfo' in data and 'itemStruct' in data['itemInfo']:
                    item = data['itemInfo']['itemStruct']
                    video_data = item.get('video', {})
                    
                    # Try to get download URL
                    download_addr = video_data.get('downloadAddr')
                    play_addr = video_data.get('playAddr')
                    
                    direct_url = download_addr or play_addr
                    if direct_url:
                        # Clean up the URL
                        if isinstance(direct_url, list):
                            direct_url = direct_url[0]
                        
                        title = item.get('desc', f'TikTok_Video_{video_id}')
                        
                        return {
                            'direct_url': direct_url,
                            'title': title,
                            'filename': f"TikTok_{self._clean_filename(title)}_{video_id}.mp4",
                            'filesize': None,
                            'duration': video_data.get('duration', 0) / 1000 if video_data.get('duration') else None,
                            'platform': 'tiktok',
                            'headers': headers,
                            'thumbnail': video_data.get('originCover'),
                            'uploader': item.get('author', {}).get('uniqueId', 'unknown'),
                            'view_count': item.get('stats', {}).get('playCount', 0)
                        }
            
            raise Exception("API response did not contain expected video data")
            
        except Exception as e:
            logger.error(f"Alternative TikTok extraction failed: {str(e)}")
            raise e
    
    def _extract_tiktok_web_scraping(self, url):
        """Web scraping fallback for TikTok"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
            }
            
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            html_content = response.text
            video_id = self._extract_tiktok_id(response.url) or self._extract_tiktok_id(url)
            
            # Look for SIGI_STATE data (TikTok's embedded JSON)
            sigi_pattern = r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>'
            sigi_match = re.search(sigi_pattern, html_content)
            
            if sigi_match:
                try:
                    sigi_data = json.loads(sigi_match.group(1))
                    
                    # Navigate through the data structure
                    default_scope = sigi_data.get('__DEFAULT_SCOPE__', {})
                    webapp_data = default_scope.get('webapp.video-detail', {})
                    item_module = webapp_data.get('itemModule', {})
                    
                    # Find the video data
                    for item_id, item_data in item_module.items():
                        if isinstance(item_data, dict) and 'video' in item_data:
                            video_data = item_data['video']
                            download_addr = video_data.get('downloadAddr')
                            play_addr = video_data.get('playAddr')
                            
                            direct_url = download_addr or play_addr
                            if direct_url:
                                title = item_data.get('desc', f'TikTok_Video_{video_id}')
                                
                                return {
                                    'direct_url': direct_url,
                                    'title': title,
                                    'filename': f"TikTok_{self._clean_filename(title)}_{video_id}.mp4",
                                    'filesize': None,
                                    'duration': video_data.get('duration', 0) / 1000 if video_data.get('duration') else None,
                                    'platform': 'tiktok',
                                    'headers': headers,
                                    'thumbnail': video_data.get('originCover'),
                                    'uploader': item_data.get('author', {}).get('uniqueId', 'unknown'),
                                    'view_count': item_data.get('stats', {}).get('playCount', 0)
                                }
                                
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse SIGI data: {str(e)}")
            
            # Fallback: Look for video URL patterns in HTML
            video_patterns = [
                r'"downloadAddr":"([^"]+)"',
                r'"playAddr":"([^"]+)"',
                r'https://[^"]*\.tiktokcdn[^"]*\.com/[^"]*\.mp4[^"]*',
                r'https://v\d{2}[^"]*\.tiktokcdn[^"]*\.com/[^"]*',
            ]
            
            for pattern in video_patterns:
                matches = re.findall(pattern, html_content)
                if matches:
                    video_url = matches[0]
                    # Clean up escaped characters
                    video_url = video_url.replace('\\u002F', '/').replace('\\/', '/')
                    video_url = unquote(video_url)
                    
                    # Try to remove watermark in URL
                    if 'playwm' in video_url:
                        video_url = video_url.replace('playwm', 'play')
                    
                    # Extract title from HTML
                    title_patterns = [
                        r'<title>([^<]+)</title>',
                        r'"desc":"([^"]+)"',
                        r'property="og:title" content="([^"]+)"'
                    ]
                    
                    title = f'TikTok_Video_{video_id or "unknown"}'
                    for title_pattern in title_patterns:
                        title_match = re.search(title_pattern, html_content)
                        if title_match:
                            title = title_match.group(1)
                            break
                    
                    return {
                        'direct_url': video_url,
                        'title': title,
                        'filename': f"TikTok_{self._clean_filename(title)}_{video_id or 'unknown'}.mp4",
                        'filesize': None,
                        'duration': None,
                        'platform': 'tiktok',
                        'headers': headers,
                        'thumbnail': None,
                        'uploader': 'unknown',
                        'view_count': 0
                    }
            
            raise Exception("No video URLs found in webpage")
            
        except Exception as e:
            logger.error(f"TikTok web scraping failed: {str(e)}")
            raise e
    
    def _resolve_short_url(self, url):
        """Resolve short URLs to get the full URL"""
        try:
            session = requests.Session()
            session.max_redirects = 10
            
            # Don't actually fetch the content, just get the final URL
            response = session.head(url, allow_redirects=True, timeout=15)
            return response.url
        except Exception as e:
            logger.warning(f"Could not resolve short URL {url}: {str(e)}")
            return url
    
    def _extract_generic_video(self, url, platform):
        """Extract video from non-TikTok platforms using yt-dlp"""
        try:
            options = self.base_options.copy()
            
            # Platform-specific adjustments
            if platform == 'youtube':
                options['format'] = 'best[height<=1080]/bestvideo[height<=1080]+bestaudio/best'
            elif platform == 'instagram':
                options['http_headers']['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
            
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Get the best video URL
                direct_url = None
                headers = {}
                
                if 'url' in info:
                    direct_url = info['url']
                elif 'formats' in info and info['formats']:
                    # Find the best format
                    best_format = self._select_best_format(info['formats'])
                    if best_format:
                        direct_url = best_format['url']
                        headers = best_format.get('http_headers', {})
                
                if not direct_url:
                    raise Exception("Could not extract direct video URL")
                
                # Clean filename
                title = info.get('title', 'video')
                ext = info.get('ext', 'mp4')
                
                filename = f"{platform.title()}_{self._clean_filename(title)}.{ext}"
                
                return {
                    'direct_url': direct_url,
                    'title': title,
                    'filename': filename,
                    'filesize': info.get('filesize') or info.get('filesize_approx'),
                    'duration': info.get('duration'),
                    'platform': platform,
                    'headers': {**self.base_options['http_headers'], **headers},
                    'thumbnail': info.get('thumbnail'),
                    'uploader': info.get('uploader'),
                    'view_count': info.get('view_count')
                }
                
        except Exception as e:
            logger.error(f"Generic extraction failed for {platform}: {str(e)}")
            raise e
    
    def _select_best_format(self, formats):
        """Select the best format from available formats"""
        # Filter formats with both video and audio
        combined_formats = [f for f in formats if 
                          f.get('url') and 
                          f.get('vcodec', 'none') != 'none' and 
                          f.get('acodec', 'none') != 'none']
        
        if combined_formats:
            # Sort by quality (height, then quality score)
            combined_formats.sort(key=lambda x: (x.get('height', 0), x.get('quality', 0)), reverse=True)
            return combined_formats[0]
        
        # Fallback to video-only formats
        video_formats = [f for f in formats if 
                        f.get('url') and 
                        f.get('vcodec', 'none') != 'none']
        
        if video_formats:
            video_formats.sort(key=lambda x: (x.get('height', 0), x.get('quality', 0)), reverse=True)
            return video_formats[0]
        
        # Last resort: any format with URL
        url_formats = [f for f in formats if f.get('url')]
        if url_formats:
            return url_formats[0]
        
        return None
    
    def _format_tiktok_response(self, info, url):
        """Format TikTok response data"""
        title = info.get('title', 'tiktok_video')
        
        # Get direct URL
        direct_url = info.get('url')
        if not direct_url and 'formats' in info:
            best_format = self._select_best_format(info['formats'])
            if best_format:
                direct_url = best_format['url']
        
        if not direct_url:
            raise Exception("Could not find direct video URL in extracted data")
        
        video_id = self._extract_tiktok_id(url) or 'unknown'
        filename = f"TikTok_{self._clean_filename(title)}_{video_id}.mp4"
        
        return {
            'direct_url': direct_url,
            'title': title,
            'filename': filename,
            'filesize': info.get('filesize') or info.get('filesize_approx'),
            'duration': info.get('duration'),
            'platform': 'tiktok',
            'headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
                'Referer': 'https://www.tiktok.com/',
                'Accept': '*/*',
            },
            'thumbnail': info.get('thumbnail'),
            'uploader': info.get('uploader'),
            'view_count': info.get('view_count')
        }
    
    def _clean_filename(self, filename):
        """Clean filename for safe file operations"""
        # Remove invalid characters and limit length
        clean_name = re.sub(r'[<>:"/\\|?*]', '', filename)
        clean_name = re.sub(r'[^\w\s-]', '', clean_name)
        clean_name = re.sub(r'[-\s]+', '-', clean_name)
        return clean_name[:50]  # Limit length
    
    def _extract_tiktok_id(self, url):
        """Extract TikTok video ID from URL"""
        patterns = [
            r'tiktok\.com/.*?/video/(\d+)',
            r'tiktok\.com/@[^/]+/video/(\d+)',
            r'vm\.tiktok\.com/([a-zA-Z0-9]+)',
            r'vt\.tiktok\.com/([a-zA-Z0-9]+)',
            r'tiktok\.com/t/([a-zA-Z0-9]+)',
            r'/video/(\d+)',
            r'itemId=(\d+)',
            r'aweme_id=(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def detect_platform(self, url):
        """Detect video platform"""
        domain = url.lower()
        
        if any(x in domain for x in ['tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com']):
            return 'tiktok'
        elif any(x in domain for x in ['youtube.com', 'youtu.be', 'm.youtube.com']):
            return 'youtube'
        elif any(x in domain for x in ['instagram.com', 'instagr.am']):
            return 'instagram'
        elif any(x in domain for x in ['facebook.com', 'fb.watch', 'm.facebook.com']):
            return 'facebook'
        elif any(x in domain for x in ['douyin.com', 'v.douyin.com']):
            return 'douyin'
        elif any(x in domain for x in ['twitter.com', 'x.com']):
            return 'twitter'
        elif 'vimeo.com' in domain:
            return 'vimeo'
        else:
            return 'unknown'

# Initialize extractor
extractor = StreamingVideoExtractor()

@app.route('/api/download/quick', methods=['POST'])
def quick_download():
    """Quick download that returns direct stream URL immediately"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        logger.info(f"Processing quick download for: {url}")
        
        # Extract video information with enhanced error handling
        try:
            video_info = extractor.extract_direct_url(url)
            logger.info(f"Successfully extracted video info for: {video_info['title']}")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Quick download extraction error: {error_msg}")
            
            # Provide helpful error messages
            if "TikTok" in error_msg or "tiktok" in error_msg.lower():
                error_msg = "TikTok extraction failed. The video might be private, age-restricted, or deleted. Please try a different video."
            elif "private" in error_msg.lower() or "unavailable" in error_msg.lower():
                error_msg = "This video is not available. It might be private, deleted, or region-restricted."
            elif "sign in" in error_msg.lower() or "login" in error_msg.lower():
                error_msg = "This video requires authentication. Please try a public video."
            
            return jsonify({'error': error_msg}), 400
        
        download_id = str(uuid.uuid4())
        
        # Add to active downloads
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
        logger.error(f"Error setting up quick download: {str(e)}")
        return jsonify({'error': f'Setup failed: {str(e)}'}), 500

@app.route('/api/stream/<download_id>')
def stream_video(download_id):
    """Stream video directly to client with enhanced error handling"""
    try:
        if download_id not in active_downloads:
            return jsonify({'error': 'Download not found'}), 404
        
        download_info = active_downloads[download_id]
        url = download_info['url']
        
        logger.info(f"Starting stream for download_id: {download_id}")
        
        # Get fresh video info (URLs may expire)
        try:
            video_info = extractor.extract_direct_url(url)
            logger.info(f"Refreshed video info for streaming: {video_info['filename']}")
        except Exception as e:
            error_msg = f'Could not refresh video URL: {str(e)}'
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 400
        
        direct_url = video_info['direct_url']
        filename = video_info['filename']
        
        def generate_stream():
            """Stream video data with enhanced progress tracking"""
            try:
                # Update status to streaming
                active_downloads[download_id]['status'] = 'streaming'
                socketio.emit('download_status', {
                    'id': download_id,
                    'status': 'streaming'
                })
                
                logger.info(f"Starting stream from: {direct_url}")
                
                # Prepare headers
                stream_headers = {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
                    'Accept': '*/*',
                    'Accept-Encoding': 'identity',
                    'Connection': 'keep-alive',
                    'Range': 'bytes=0-',
                }
                
                # Add platform-specific headers
                if video_info.get('headers'):
                    stream_headers.update(video_info['headers'])
                
                # Handle range requests from browser
                range_header = request.headers.get('Range')
                if range_header:
                    stream_headers['Range'] = range_header
                    logger.info(f"Range request: {range_header}")
                
                # Start streaming with better error handling and retry logic
                max_retries = 3
                retry_count = 0
                
                while retry_count < max_retries:
                    try:
                        logger.info(f"Attempt {retry_count + 1} to stream from {direct_url}")
                        
                        with requests.get(direct_url, headers=stream_headers, stream=True, timeout=60) as r:
                            r.raise_for_status()
                            
                            total_size = int(r.headers.get('content-length', 0))
                            downloaded = 0
                            chunk_size = 65536  # 64KB chunks for better performance
                            
                            logger.info(f"Stream started, total size: {total_size}, content-type: {r.headers.get('content-type')}")
                            
                            # Update with total size
                            active_downloads[download_id]['total_bytes'] = total_size
                            active_downloads[download_id]['status'] = 'streaming'
                            
                            start_time = time.time()
                            last_progress_time = start_time
                            
                            # Stream chunks with progress tracking
                            for chunk in r.iter_content(chunk_size=chunk_size):
                                if chunk:
                                    downloaded += len(chunk)
                                    current_time = time.time()
                                    
                                    # Update progress every 1 second
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
                            
                            logger.info(f"Stream completed successfully for {download_id} in {total_time:.2f}s")
                            
                            socketio.emit('download_status', {
                                'id': download_id,
                                'status': 'completed',
                                'percentage': 100,
                                'total_time': total_time
                            })
                            
                            return  # Success, exit retry loop
                            
                    except requests.exceptions.RequestException as e:
                        retry_count += 1
                        error_msg = f"Network error (attempt {retry_count}/{max_retries}): {str(e)}"
                        logger.warning(error_msg)
                        
                        if retry_count >= max_retries:
                            raise Exception(f"Failed after {max_retries} attempts: {str(e)}")
                        else:
                            # Wait before retry
                            time.sleep(2 ** retry_count)  # Exponential backoff
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
        
        # Create streaming response with proper headers
        response = Response(
            stream_with_context(generate_stream()),
            mimetype='video/mp4',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
                'X-Content-Type-Options': 'nosniff',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Expose-Headers': 'Content-Disposition, Content-Length',
                'Accept-Ranges': 'bytes'
            }
        )
        
        # Add content length if available
        if video_info.get('filesize'):
            response.headers['Content-Length'] = str(video_info['filesize'])
        
        return response
        
    except Exception as e:
        logger.error(f"Error streaming video {download_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/video-info', methods=['POST'])
def get_video_info():
    """Get video information without downloading"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        logger.info(f"Getting video info for: {url}")
        
        try:
            video_info = extractor.extract_direct_url(url)
            logger.info(f"Successfully got video info: {video_info['title']}")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Video info extraction error: {error_msg}")
            
            # Provide helpful error messages
            if "TikTok" in error_msg or "tiktok" in error_msg.lower():
                error_msg = "Could not get TikTok video info. The video might be private or deleted."
            
            return jsonify({'error': error_msg}), 400
        
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
        logger.error(f"Error getting video info: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/downloads', methods=['GET'])
def list_downloads():
    """Get list of all downloads"""
    try:
        return jsonify({
            'active_downloads': list(active_downloads.values()),
            'total_active': len(active_downloads)
        })
    except Exception as e:
        logger.error(f"Error listing downloads: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/downloads/clear', methods=['POST'])
def clear_downloads():
    """Clear completed/failed downloads"""
    try:
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
    except Exception as e:
        logger.error(f"Error clearing downloads: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint with enhanced info"""
    try:
        # Test yt-dlp availability
        yt_dlp_version = yt_dlp.version.__version__
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'active_downloads': len(active_downloads),
            'streaming_enabled': True,
            'version': 'fixed_tiktok_support',
            'yt_dlp_version': yt_dlp_version,
            'features': {
                'tiktok_extraction': True,
                'multi_platform': True,
                'direct_streaming': True,
                'progress_tracking': True
            }
        })
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Legacy compatibility endpoints
@app.route('/api/download/single', methods=['POST'])
def download_single_video():
    """Legacy endpoint - redirects to streaming"""
    return quick_download()

@app.route('/api/download/stream', methods=['POST'])
def stream_download():
    """Legacy streaming setup endpoint"""
    return quick_download()

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {
        'message': 'Connected to enhanced streaming video downloader',
        'active_downloads': len(active_downloads),
        'version': 'fixed_tiktok_support'
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('get_downloads')
def handle_get_downloads():
    """Send current downloads to client"""
    emit('downloads_update', {
        'downloads': list(active_downloads.values()),
        'total': len(active_downloads)
    })

@app.route('/', methods=['GET'])
def serve_frontend():
    """Serve the enhanced frontend"""
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>', methods=['GET'])
def serve_static(path):
    """Serve static files"""
    return send_from_directory('.', path)

def main():
    """Main function to run the Flask server"""
    print("🚀 Enhanced Streaming Video Downloader Starting...")
    print("⚡ TikTok extraction fixed with multiple fallback methods!")
    print("🔧 Direct streaming enabled - no server storage needed!")
    
    # Check dependencies
    try:
        import yt_dlp
        print(f"✅ yt-dlp version: {yt_dlp.version.__version__}")
    except ImportError:
        print("❌ Error: yt-dlp is not installed.")
        print("💡 Please install it using: pip install yt-dlp")
        sys.exit(1)
    
    # Get port from environment variable
    port = int(os.environ.get('PORT', 4000))
    host = '0.0.0.0'
    
    print(f"🌐 Server available at: http://{host}:{port}")
    print("💡 API Endpoints:")
    print("   POST /api/download/quick   - Quick streaming download")
    print("   GET  /api/stream/<id>      - Stream video file")
    print("   POST /api/video-info       - Get video information")
    print("   GET  /api/downloads        - List downloads")
    print("   POST /api/downloads/clear  - Clear downloads")
    print("   GET  /api/health           - Health check")
    
    try:
        socketio.run(
            app,
            host=host,
            port=port,
            debug=False,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Server error: {str(e)}")

if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
Enhanced Multi-Platform Video Downloader with Better Progress Tracking
Supports: TikTok, Douyin, YouTube, Facebook, Instagram
Note: Watermark removal should only be done on content you own or have permission to modify
"""

import os
import sys
import re
import subprocess
import json
import time
from pathlib import Path
import yt_dlp
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

class VideoDownloader:
    def __init__(self, download_path="./downloads", remove_watermarks=False):
        """Initialize the video downloader with enhanced progress tracking."""
        self.download_path = Path(download_path)
        self.download_path.mkdir(exist_ok=True)
        self.remove_watermarks = remove_watermarks
        
        # Create processed folder for watermark-free videos
        if self.remove_watermarks:
            self.processed_path = self.download_path / "processed"
            self.processed_path.mkdir(exist_ok=True)
        
        # Enhanced common options for yt-dlp
        self.base_options = {
            'outtmpl': str(self.download_path / '%(title)s.%(ext)s'),
            'format': 'best[height<=1080]',  # Increased to 1080p
            'writeinfojson': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'no_warnings': False,
            'extractaudio': False,
            'audioformat': 'mp3',
            
            # Enhanced user agent and headers
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip,deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Keep-Alive': '300',
                'Connection': 'keep-alive'
            },
            
            # Enhanced retry and fragment handling
            'retries': 5,
            'fragment_retries': 5,
            'abort_on_unavailable_fragments': False,
            'keep_fragments': False,
            
            # Better error handling
            'extractor_retries': 3,
            'socket_timeout': 30,
            
            # Progress tracking will be added per download
            'progress_hooks': [],
            
            # Additional options for better downloads
            'continuedl': True,  # Continue partial downloads
            'nooverwrites': False,  # Allow overwrites
            'writethumbnail': False,  # Don't write thumbnails by default
            'writeinfojson': False,  # Don't write info JSON by default
        }

    def create_progress_hook(self, download_id="unknown"):
        """Create an enhanced progress hook for better tracking"""
        
        def progress_hook(d):
            """Enhanced progress hook with detailed information"""
            try:
                status = d.get('status', 'unknown')
                
                if status == 'downloading':
                    # Extract comprehensive download information
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    speed = d.get('speed', 0)
                    eta = d.get('eta', 0)
                    filename = d.get('filename', '')
                    
                    # Calculate percentage
                    percentage = 0
                    if total > 0:
                        percentage = (downloaded / total) * 100
                    
                    # Enhanced progress information
                    progress_info = {
                        'id': download_id,
                        'status': 'downloading',
                        'downloaded_bytes': downloaded,
                        'total_bytes': total,
                        'speed': speed,
                        'eta': eta,
                        'percentage': round(percentage, 2),
                        'filename': Path(filename).name if filename else '',
                        'filepath': filename
                    }
                    
                    # Print progress for console users
                    if total > 0:
                        progress_bar = self._create_progress_bar(percentage, 40)
                        speed_str = self._format_bytes(speed) + '/s' if speed else 'N/A'
                        eta_str = self._format_time(eta) if eta else 'N/A'
                        print(f"\r[{download_id[:8]}] {progress_bar} {percentage:.1f}% | {speed_str} | ETA: {eta_str}", end='', flush=True)
                    
                    return progress_info
                    
                elif status == 'finished':
                    filename = d.get('filename', '')
                    completion_info = {
                        'id': download_id,
                        'status': 'completed',
                        'filename': Path(filename).name if filename else '',
                        'filepath': filename,
                        'percentage': 100
                    }
                    
                    print(f"\n[{download_id[:8]}] ✅ Download completed: {Path(filename).name if filename else 'Unknown'}")
                    return completion_info
                    
                elif status == 'error':
                    error_msg = str(d.get('error', 'Unknown error'))
                    error_info = {
                        'id': download_id,
                        'status': 'error',
                        'error': error_msg
                    }
                    
                    print(f"\n[{download_id[:8]}] ❌ Download error: {error_msg}")
                    return error_info
                    
            except Exception as e:
                print(f"\n[{download_id[:8]}] ⚠️  Progress hook error: {str(e)}")
                return {
                    'id': download_id,
                    'status': 'error',
                    'error': f'Progress tracking failed: {str(e)}'
                }
        
        return progress_hook
    
    def _create_progress_bar(self, percentage, width=40):
        """Create a visual progress bar"""
        filled = int(width * percentage / 100)
        bar = '█' * filled + '░' * (width - filled)
        return f'[{bar}]'
    
    def _format_bytes(self, bytes_val):
        """Format bytes for display"""
        if not bytes_val or bytes_val == 0:
            return '0 B'
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f} TB"
    
    def _format_time(self, seconds):
        """Format time for display"""
        if not seconds or seconds < 0:
            return '0s'
        
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs:02d}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins:02d}m"

    def detect_platform(self, url):
        """Detect which platform the URL belongs to."""
        domain = urlparse(url).netloc.lower()
        
        platform_patterns = {
            'tiktok': ['tiktok.com', 'vm.tiktok.com'],
            'douyin': ['douyin.com', 'v.douyin.com'],
            'youtube': ['youtube.com', 'youtu.be', 'm.youtube.com'],
            'facebook': ['facebook.com', 'fb.watch', 'm.facebook.com'],
            'instagram': ['instagram.com', 'instagr.am']
        }
        
        for platform, domains in platform_patterns.items():
            if any(d in domain for d in domains):
                return platform
        
        return 'unknown'

    def get_platform_options(self, platform):
        """Get platform-specific options for yt-dlp."""
        options = self.base_options.copy()
        
        if platform == 'tiktok':
            options.update({
                'format': 'best',
                'outtmpl': str(self.download_path / 'TikTok_%(uploader)s_%(title)s_%(id)s.%(ext)s'),
                'extractor_args': {
                    'tiktok': {
                        'webpage_url_basename': 'video'
                    }
                }
            })
        
        elif platform == 'douyin':
            options.update({
                'format': 'best',
                'outtmpl': str(self.download_path / 'Douyin_%(uploader)s_%(title)s_%(id)s.%(ext)s'),
            })
        
        elif platform == 'youtube':
            options.update({
                'format': 'best[height<=1080]/bestvideo[height<=1080]+bestaudio/best',
                'outtmpl': str(self.download_path / 'YouTube_%(uploader)s_%(title)s_%(id)s.%(ext)s'),
                'writesubtitles': False,
                'writeautomaticsub': False,
            })
        
        elif platform == 'facebook':
            options.update({
                'format': 'best',
                'outtmpl': str(self.download_path / 'Facebook_%(uploader)s_%(title)s_%(id)s.%(ext)s'),
            })
        
        elif platform == 'instagram':
            options.update({
                'format': 'best',
                'outtmpl': str(self.download_path / 'Instagram_%(uploader)s_%(title)s_%(id)s.%(ext)s'),
            })
        
        return options

    def check_ffmpeg(self):
        """Check if FFmpeg is installed and available."""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def remove_watermark_ffmpeg(self, input_file, output_file, watermark_position="bottom_right"):
        """
        Remove watermark using FFmpeg delogo filter.
        Enhanced with better error handling and positioning.
        """
        try:
            if not self.check_ffmpeg():
                print("Error: FFmpeg not found. Cannot remove watermark.")
                return False
            
            # Get video dimensions first
            probe_cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                '-show_streams', str(input_file)
            ]
            
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print("Error: Could not get video information")
                return False
            
            probe_data = json.loads(result.stdout)
            video_stream = next((s for s in probe_data['streams'] if s['codec_type'] == 'video'), None)
            
            if not video_stream:
                print("Error: No video stream found")
                return False
            
            width = int(video_stream['width'])
            height = int(video_stream['height'])
            
            # Enhanced watermark regions based on common positions
            watermark_regions = {
                'bottom_right': f"delogo=x={width-150}:y={height-80}:w=140:h=70",
                'bottom_left': "delogo=x=10:y=h-80:w=140:h=70",
                'top_right': f"delogo=x={width-150}:y=10:w=140:h=70",
                'top_left': "delogo=x=10:y=10:w=140:h=70",
                'center': f"delogo=x={width//2-70}:y={height//2-35}:w=140:h=70",
                'bottom_center': f"delogo=x={width//2-70}:y={height-80}:w=140:h=70",
                'top_center': f"delogo=x={width//2-70}:y=10:w=140:h=70"
            }
            
            filter_str = watermark_regions.get(watermark_position, watermark_regions['bottom_right'])
            
            cmd = [
                'ffmpeg', '-i', str(input_file),
                '-vf', filter_str,
                '-c:a', 'copy',  # Copy audio without re-encoding
                '-preset', 'fast',  # Use fast preset for better speed
                '-y',  # Overwrite output file
                str(output_file)
            ]
            
            print(f"🔧 Removing watermark from {input_file.name}...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Watermark removal completed: {output_file}")
                return True
            else:
                print(f"❌ Error in watermark removal: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error during watermark removal: {str(e)}")
            return False

    def download_video(self, url, custom_filename=None, remove_watermark=None, download_id="unknown"):
        """Enhanced video download with comprehensive progress tracking"""
        try:
            # Use instance setting if not specified
            if remove_watermark is None:
                remove_watermark = self.remove_watermarks
                
            print(f"\n🎬 Starting download: {url}")
            print(f"📁 Download ID: {download_id}")
            
            # Detect platform
            platform = self.detect_platform(url)
            print(f"🌐 Detected platform: {platform}")
            
            # Get platform-specific options
            options = self.get_platform_options(platform)
            
            # Custom filename if provided
            if custom_filename:
                file_ext = '%(ext)s'
                options['outtmpl'] = str(self.download_path / f"{custom_filename}.{file_ext}")
            
            # Store the original filename for watermark processing
            original_file = None
            download_success = False
            
            # Create enhanced progress hook
            progress_hook = self.create_progress_hook(download_id)
            
            # Preserve existing progress hooks and add our enhanced one
            existing_hooks = options.get('progress_hooks', [])
            
            def combined_progress_hook(d):
                # Call our enhanced hook
                progress_info = progress_hook(d)
                
                # Call existing hooks (from backend if any)
                for hook in existing_hooks:
                    try:
                        hook(d)
                    except Exception as e:
                        print(f"⚠️  External progress hook error: {str(e)}")
                
                # Store completion info
                nonlocal original_file, download_success
                if d['status'] == 'finished':
                    original_file = Path(d['filename'])
                    download_success = True
                
                return progress_info
            
            # Set the combined progress hook
            options['progress_hooks'] = [combined_progress_hook]
            
            # Create yt-dlp object and download
            with yt_dlp.YoutubeDL(options) as ydl:
                try:
                    # Extract video info first for better tracking
                    try:
                        info = ydl.extract_info(url, download=False)
                        video_title = info.get('title', 'Unknown')
                        video_duration = info.get('duration', 0)
                        uploader = info.get('uploader', 'Unknown')
                        
                        print(f"📋 Title: {video_title}")
                        print(f"👤 Uploader: {uploader}")
                        print(f"⏱️  Duration: {self._format_time(video_duration)}")
                        print(f"🔽 Starting download...")
                        
                    except Exception as e:
                        print(f"⚠️  Could not extract video info: {str(e)}")
                    
                    # Perform the actual download
                    ydl.download([url])
                    
                    # Verify download completion
                    if not download_success:
                        print("⚠️  Download may have failed - no completion signal received")
                        return False
                        
                    print(f"\n✅ Download completed successfully!")
                    
                    # Process watermark removal if requested
                    if remove_watermark and original_file and original_file.exists():
                        print(f"\n🔧 Processing watermark removal...")
                        
                        if not hasattr(self, 'processed_path'):
                            self.processed_path = self.download_path / "processed"
                            self.processed_path.mkdir(exist_ok=True)
                        
                        processed_file = self.processed_path / f"no_watermark_{original_file.name}"
                        
                        if self.remove_watermark_ffmpeg(original_file, processed_file):
                            print(f"✨ Watermark-free video saved to: {processed_file}")
                            
                            # In interactive mode, ask about keeping original
                            if not existing_hooks:  # Only ask if not running from backend
                                try:
                                    keep_original = input("Keep original file with watermark? (y/n): ").lower().strip()
                                    if keep_original != 'y':
                                        original_file.unlink()
                                        print("🗑️  Original file deleted.")
                                except:
                                    pass  # Skip interaction if input isn't available
                        else:
                            print("❌ Watermark removal failed. Original file preserved.")
                    
                    return True
                    
                except yt_dlp.utils.DownloadError as e:
                    print(f"❌ yt-dlp download error: {str(e)}")
                    return False
                except Exception as e:
                    print(f"❌ Unexpected error during download: {str(e)}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error downloading video: {str(e)}")
            return False

    def get_video_info(self, url):
        """Get comprehensive video information without downloading."""
        try:
            options = {
                'quiet': True,
                'nocheckcertificate': True,
                'http_headers': self.base_options['http_headers']
            }
            
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Extract comprehensive information
                video_info = {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'uploader_id': info.get('uploader_id', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'comment_count': info.get('comment_count', 0),
                    'upload_date': info.get('upload_date', 'Unknown'),
                    'description': info.get('description', 'No description available')[:500],  # Limit description
                    'platform': self.detect_platform(url),
                    'thumbnail': info.get('thumbnail', ''),
                    'webpage_url': info.get('webpage_url', url),
                    'extractor': info.get('extractor', 'Unknown'),
                    'formats_available': len(info.get('formats', [])),
                    'resolution': f"{info.get('width', 0)}x{info.get('height', 0)}" if info.get('width') and info.get('height') else 'Unknown'
                }
                
                return video_info
                
        except Exception as e:
            print(f"❌ Error getting video info: {str(e)}")
            return None

    def download_profile_videos(self, profile_url, max_videos=None):
        """Enhanced profile video download with better progress tracking"""
        platform = self.detect_platform(profile_url)
        print(f"\n👤 Downloading videos from {platform} profile: {profile_url}")
        
        if platform == 'youtube':
            return self._download_youtube_channel(profile_url, max_videos)
        elif platform == 'tiktok':
            return self._download_tiktok_profile(profile_url, max_videos)
        elif platform == 'instagram':
            return self._download_instagram_profile(profile_url, max_videos)
        else:
            print(f"❌ Profile downloading not yet implemented for {platform}")
            return False

    def _download_youtube_channel(self, channel_url, max_videos=None):
        """Enhanced YouTube channel download"""
        try:
            options = self.get_platform_options('youtube')
            options.update({
                'ignoreerrors': True,
                'nooverwrites': True,
                'extract_flat': False,
            })
            
            if max_videos:
                options['playlistend'] = max_videos
                print(f"📊 Limiting to {max_videos} videos")
            
            # Add progress hook
            options['progress_hooks'] = [self.create_progress_hook("youtube_channel")]
            
            # Convert channel URL to videos URL if needed
            if '/@' in channel_url:
                videos_url = channel_url.rstrip('/') + '/videos'
            elif '/channel/' in channel_url or '/user/' in channel_url or '/c/' in channel_url:
                videos_url = channel_url.rstrip('/') + '/videos'
            else:
                videos_url = channel_url
            
            print(f"🔗 Using URL: {videos_url}")
            
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([videos_url])
                print("✅ YouTube channel download completed!")
                return True
                
        except Exception as e:
            print(f"❌ Error downloading YouTube channel: {str(e)}")
            return False

    def _download_tiktok_profile(self, profile_url, max_videos=None):
        """Enhanced TikTok profile download"""
        try:
            options = self.get_platform_options('tiktok')
            options.update({
                'ignoreerrors': True,
                'nooverwrites': True,
            })
            
            if max_videos:
                options['playlistend'] = max_videos
                print(f"📊 Limiting to {max_videos} videos")
            
            # Add progress hook
            options['progress_hooks'] = [self.create_progress_hook("tiktok_profile")]
            
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([profile_url])
                print("✅ TikTok profile download completed!")
                return True
                    
        except Exception as e:
            print(f"❌ Error downloading TikTok profile: {str(e)}")
            return False

    def _download_instagram_profile(self, profile_url, max_videos=None):
        """Enhanced Instagram profile download"""
        try:
            options = self.get_platform_options('instagram')
            options.update({
                'ignoreerrors': True,
                'nooverwrites': True,
            })
            
            if max_videos:
                options['playlistend'] = max_videos
                print(f"📊 Limiting to {max_videos} videos")
            
            # Add progress hook
            options['progress_hooks'] = [self.create_progress_hook("instagram_profile")]
            
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([profile_url])
                print("✅ Instagram profile download completed!")
                return True
                        
        except Exception as e:
            print(f"❌ Error downloading Instagram profile: {str(e)}")
            return False

    def extract_video_links(self, url, max_links=20):
        """Enhanced video link extraction with better patterns"""
        try:
            print(f"🔍 Extracting video links from: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive'
            }
            
            # Fetch the webpage
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Enhanced video link patterns
            video_links = set()
            
            # Enhanced patterns for video platforms
            video_patterns = [
                r'(youtube\.com|youtu\.be)',
                r'(tiktok\.com)',
                r'(instagram\.com)',
                r'(facebook\.com|fb\.watch)',
                r'(douyin\.com)',
                r'(twitter\.com|x\.com)',
                r'(vimeo\.com)',
                r'(dailymotion\.com)',
                r'\.mp4',
                r'\.webm',
                r'\.mov',
                r'\.avi',
                r'\.wmv',
                r'\.flv',
                r'\.mkv',
                r'\.m4v',
            ]
            
            # Check all links on the page
            links_found = 0
            for link in soup.find_all('a', href=True):
                if links_found >= max_links:
                    break
                    
                href = link['href']
                absolute_url = urljoin(url, href)
                
                # Check if this looks like a video link
                for pattern in video_patterns:
                    if re.search(pattern, absolute_url, re.IGNORECASE):
                        video_links.add(absolute_url)
                        links_found += 1
                        break
            
            # Check video elements
            for video in soup.find_all('video'):
                if links_found >= max_links:
                    break
                    
                if video.get('src'):
                    src = video['src']
                    absolute_url = urljoin(url, src)
                    video_links.add(absolute_url)
                    links_found += 1
            
            # Check iframes for embeds
            for iframe in soup.find_all('iframe'):
                if links_found >= max_links:
                    break
                    
                if iframe.get('src'):
                    src = iframe['src']
                    absolute_url = urljoin(url, src)
                    
                    for pattern in video_patterns:
                        if re.search(pattern, absolute_url, re.IGNORECASE):
                            video_links.add(absolute_url)
                            links_found += 1
                            break
            
            # Convert to list and limit
            video_links = list(video_links)[:max_links]
            
            print(f"🎯 Found {len(video_links)} video links:")
            for i, link in enumerate(video_links, 1):
                print(f"  {i:2d}. {link}")
            
            return video_links
            
        except Exception as e:
            print(f"❌ Error extracting video links: {str(e)}")
            return []

    def download_from_webpage(self, url, max_videos=10):
        """Enhanced webpage video download with progress tracking"""
        try:
            # Extract video links
            video_links = self.extract_video_links(url, max_videos)
            
            if not video_links:
                print("❌ No video links found on this webpage.")
                return False
            
            # Check if we're running in backend mode
            backend_mode = len(self.base_options.get('progress_hooks', [])) > 0
            
            # Ask for confirmation in interactive mode
            if not backend_mode:
                print(f"\n📋 Found {len(video_links)} video links.")
                confirm = input("Do you want to download all these videos? (y/n): ").lower().strip()
                
                if confirm != 'y':
                    print("🚫 Download cancelled.")
                    return False
            
            # Download each video with enhanced progress tracking
            success_count = 0
            total_links = len(video_links)
            
            print(f"\n🚀 Starting webpage download: {total_links} videos")
            
            for i, video_url in enumerate(video_links, 1):
                print(f"\n📥 [{i}/{total_links}] Downloading: {video_url}")
                
                # Create unique download ID for each video
                download_id = f"webpage_{i:03d}"
                
                if self.download_video(video_url, download_id=download_id):
                    success_count += 1
                    print(f"✅ [{i}/{total_links}] Success")
                else:
                    print(f"❌ [{i}/{total_links}] Failed")
                
                # Add delay to avoid rate limiting
                if i < total_links:  # Don't delay after the last video
                    print("⏳ Waiting 2 seconds before next download...")
                    time.sleep(2)
            
            print(f"\n🎉 Webpage download completed!")
            print(f"📊 Results: {success_count}/{total_links} videos downloaded successfully")
            
            return success_count > 0
            
        except Exception as e:
            print(f"❌ Error downloading from webpage: {str(e)}")
            return False

    def download_multiple_links(self, links, remove_watermark=None):
        """Enhanced batch download with comprehensive progress tracking"""
        if not links:
            print("❌ No links provided.")
            return False
        
        # Filter out empty links
        valid_links = [link.strip() for link in links if link.strip()]
        
        if not valid_links:
            print("❌ No valid links found.")
            return False
        
        # Use instance setting if not specified
        if remove_watermark is None:
            remove_watermark = self.remove_watermarks
        
        total_links = len(valid_links)
        print(f"\n📦 Starting batch download: {total_links} videos")
        print(f"🔧 Watermark removal: {'Enabled' if remove_watermark else 'Disabled'}")
        
        success_count = 0
        
        for i, url in enumerate(valid_links, 1):
            print(f"\n" + "="*60)
            print(f"📥 [{i}/{total_links}] Processing: {url}")
            
            # Create unique download ID
            download_id = f"batch_{i:03d}"
            
            try:
                if self.download_video(url, remove_watermark=remove_watermark, download_id=download_id):
                    success_count += 1
                    print(f"✅ [{i}/{total_links}] Successfully downloaded")
                else:
                    print(f"❌ [{i}/{total_links}] Download failed")
            except Exception as e:
                print(f"❌ [{i}/{total_links}] Error: {str(e)}")
            
            # Progress summary
            remaining = total_links - i
            if remaining > 0:
                print(f"📊 Progress: {i}/{total_links} completed, {remaining} remaining")
                print("⏳ Waiting 2 seconds before next download...")
                time.sleep(2)
        
        print(f"\n" + "="*60)
        print(f"🎉 Batch download completed!")
        print(f"📊 Final Results: {success_count}/{total_links} videos downloaded successfully")
        success_rate = (success_count / total_links) * 100
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        return success_count > 0

# Enhanced utility functions for direct usage
def quick_download(url, download_path="./downloads", custom_filename=None, remove_watermark=False, download_id="quick"):
    """Quick function to download a single video with enhanced progress tracking."""
    downloader = VideoDownloader(download_path, remove_watermark)
    return downloader.download_video(url, custom_filename, download_id=download_id)

def batch_download(urls, download_path="./downloads", remove_watermarks=False):
    """Enhanced batch download with comprehensive progress tracking."""
    downloader = VideoDownloader(download_path, remove_watermarks)
    return downloader.download_multiple_links(urls)

def download_profile(profile_url, download_path="./downloads", max_videos=None, remove_watermarks=False):
    """Download all videos from a profile with enhanced tracking."""
    downloader = VideoDownloader(download_path, remove_watermarks)
    return downloader.download_profile_videos(profile_url, max_videos)

def extract_video_links(url, max_links=20):
    """Extract video links from a webpage with enhanced patterns."""
    downloader = VideoDownloader()
    return downloader.extract_video_links(url, max_links)

def download_from_webpage(url, download_path="./downloads", max_videos=10, remove_watermarks=False):
    """Extract and download videos from webpage with enhanced progress tracking."""
    downloader = VideoDownloader(download_path, remove_watermarks)
    return downloader.download_from_webpage(url, max_videos)

def remove_watermark_from_file(input_file, output_file=None, position="bottom_right"):
    """Remove watermark from an existing video file with enhanced processing."""
    downloader = VideoDownloader()
    input_path = Path(input_file)
    
    if not input_path.exists():
        print(f"❌ Error: File {input_file} not found")
        return False
    
    if output_file is None:
        output_file = input_path.parent / f"no_watermark_{input_path.name}"
    else:
        output_file = Path(output_file)
    
    return downloader.remove_watermark_ffmpeg(input_path, output_file, position)

def main():
    """Enhanced main function with improved user interface"""
    print("🎬 Enhanced Multi-Platform Video Downloader")
    print("🌟 Supports: TikTok, Douyin, YouTube, Facebook, Instagram")
    print("⚠️  IMPORTANT: Only remove watermarks from content you own or have permission to modify")
    print("="*80)
    
    # Initialize downloader with enhanced settings
    print("🔧 Initializing downloader...")
    watermark_removal = input("Enable watermark removal by default? (y/n): ").lower().strip() == 'y'
    downloader = VideoDownloader(remove_watermarks=watermark_removal)
    
    if watermark_removal and not downloader.check_ffmpeg():
        print("⚠️  Watermark removal disabled due to missing FFmpeg.")
        print("💡 Install FFmpeg from: https://ffmpeg.org/download.html")
        downloader.remove_watermarks = False
    
    print(f"📁 Download directory: {downloader.download_path}")
    print(f"🔧 FFmpeg available: {downloader.check_ffmpeg()}")
    print(f"💧 Watermark removal: {'Enabled' if downloader.remove_watermarks else 'Disabled'}")
    
    while True:
        print("\n" + "="*50)
        print("🎯 Enhanced Video Downloader Options:")
        print("1.  📹 Download single video")
        print("2.  📺 Download YouTube playlist/channel")
        print("3.  👤 Download all videos from a profile")
        print("4.  🔗 Extract and download videos from webpage")
        print("5.  📦 Download multiple videos from list")
        print("6.  ℹ️  Get detailed video information")
        print("7.  📁 Change download directory")
        print("8.  💧 Toggle watermark removal")
        print("9.  🔧 Remove watermark from existing video")
        print("10. ❌ Exit")
        
        choice = input("\n🎯 Enter your choice (1-10): ").strip()
        
        if choice == '1':
            url = input("📝 Enter video URL: ").strip()
            if url:
                custom_name = input("📝 Enter custom filename (optional): ").strip() or None
                
                if not downloader.remove_watermarks:
                    remove_wm = input("💧 Remove watermark for this video? (y/n): ").lower().strip() == 'y'
                else:
                    remove_wm = True
                
                downloader.download_video(url, custom_name, remove_wm, "manual_single")
        
        elif choice == '2':
            url = input("📝 Enter playlist/channel URL: ").strip()
            if url:
                try:
                    max_videos = input("📊 Maximum videos (press Enter for all): ").strip()
                    max_videos = int(max_videos) if max_videos else None
                except ValueError:
                    print("⚠️  Invalid number. Downloading all videos.")
                    max_videos = None
                
                if 'youtube.com' in url or 'youtu.be' in url:
                    downloader._download_youtube_channel(url, max_videos)
                else:
                    print("⚠️  Playlist download currently only supports YouTube")
        
        elif choice == '3':
            url = input("📝 Enter profile URL: ").strip()
            if url:
                try:
                    max_videos = input("📊 Maximum videos (press Enter for all): ").strip()
                    max_videos = int(max_videos) if max_videos else None
                except ValueError:
                    print("⚠️  Invalid number. Downloading all videos.")
                    max_videos = None
                
                downloader.download_profile_videos(url, max_videos)
        
        elif choice == '4':
            url = input("📝 Enter webpage URL: ").strip()
            if url:
                try:
                    max_videos = input("📊 Maximum videos (default 10): ").strip()
                    max_videos = int(max_videos) if max_videos else 10
                except ValueError:
                    print("⚠️  Invalid number. Using default of 10.")
                    max_videos = 10
                
                downloader.download_from_webpage(url, max_videos)
        
        elif choice == '5':
            print("📝 Paste your video links (one per line).")
            print("📝 Press Enter twice when finished:")
            links = []
            while True:
                line = input()
                if line.strip() == "":
                    if len(links) > 0:
                        break
                    else:
                        continue
                links.append(line.strip())
            
            if links:
                if not downloader.remove_watermarks:
                    remove_wm = input("💧 Remove watermarks for these videos? (y/n): ").lower().strip() == 'y'
                else:
                    remove_wm = True
                
                downloader.download_multiple_links(links, remove_wm)
        
        elif choice == '6':
            url = input("📝 Enter video URL: ").strip()
            if url:
                print("🔍 Fetching video information...")
                info = downloader.get_video_info(url)
                if info:
                    print(f"\n📋 Video Information:")
                    print(f"🎬 Title: {info['title']}")
                    print(f"🌐 Platform: {info['platform'].upper()}")
                    print(f"👤 Uploader: {info['uploader']}")
                    print(f"⏱️  Duration: {downloader._format_time(info['duration'])}")
                    print(f"👁️  Views: {info['view_count']:,}")
                    print(f"👍 Likes: {info.get('like_count', 'N/A')}")
                    print(f"💬 Comments: {info.get('comment_count', 'N/A')}")
                    print(f"📅 Upload Date: {info.get('upload_date', 'Unknown')}")
                    print(f"📐 Resolution: {info.get('resolution', 'Unknown')}")
                    print(f"🔧 Extractor: {info.get('extractor', 'Unknown')}")
                    print(f"📊 Available Formats: {info.get('formats_available', 0)}")
                    
                    if info.get('description'):
                        print(f"📝 Description: {info['description'][:200]}...")
                else:
                    print("❌ Could not retrieve video information")
        
        elif choice == '7':
            new_path = input("📝 Enter new download directory: ").strip()
            if new_path:
                try:
                    downloader = VideoDownloader(new_path, downloader.remove_watermarks)
                    print(f"✅ Download directory changed to: {new_path}")
                except Exception as e:
                    print(f"❌ Error changing directory: {str(e)}")
        
        elif choice == '8':
            if downloader.check_ffmpeg():
                downloader.remove_watermarks = not downloader.remove_watermarks
                status = "enabled" if downloader.remove_watermarks else "disabled"
                print(f"✅ Watermark removal {status}")
            else:
                print("❌ FFmpeg not available. Cannot enable watermark removal.")
        
        elif choice == '9':
            if downloader.check_ffmpeg():
                input_file = input("📝 Enter path to video file: ").strip()
                if input_file and Path(input_file).exists():
                    input_path = Path(input_file)
                    
                    if not hasattr(downloader, 'processed_path'):
                        downloader.processed_path = downloader.download_path / "processed"
                        downloader.processed_path.mkdir(exist_ok=True)
                    
                    output_path = downloader.processed_path / f"no_watermark_{input_path.name}"
                    
                    print("\n🎯 Watermark positions:")
                    print("1. Bottom right (default)")
                    print("2. Bottom left")
                    print("3. Top right")
                    print("4. Top left")
                    print("5. Center")
                    print("6. Bottom center")
                    print("7. Top center")
                    
                    pos_choice = input("📝 Select watermark position (1-7): ").strip()
                    positions = {
                        '1': 'bottom_right',
                        '2': 'bottom_left', 
                        '3': 'top_right',
                        '4': 'top_left',
                        '5': 'center',
                        '6': 'bottom_center',
                        '7': 'top_center'
                    }
                    position = positions.get(pos_choice, 'bottom_right')
                    
                    if downloader.remove_watermark_ffmpeg(input_path, output_path, position):
                        print("✅ Watermark removal completed!")
                    else:
                        print("❌ Watermark removal failed.")
                else:
                    print("❌ File not found.")
            else:
                print("❌ FFmpeg not available.")
        
        elif choice == '10':
            print("👋 Thank you for using Enhanced Video Downloader!")
            print("🎉 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    # Check dependencies
    try:
        import yt_dlp
        print("✅ yt-dlp found successfully!")
    except ImportError:
        print("❌ Error: yt-dlp is not installed.")
        print("💡 Please install it using: pip install yt-dlp")
        sys.exit(1)
    
    try:
        from bs4 import BeautifulSoup
        print("✅ BeautifulSoup found successfully!")
    except ImportError:
        print("❌ Error: BeautifulSoup is not installed.")
        print("💡 Please install it using: pip install beautifulsoup4")
        sys.exit(1)
    
    try:
        import requests
        print("✅ requests found successfully!")
    except ImportError:
        print("❌ Error: requests is not installed.")
        print("💡 Please install it using: pip install requests")
        sys.exit(1)
    
    print("🚀 All dependencies found! Starting application...")
    main()
#!/usr/bin/env python3
"""
Flask Backend for Multi-Platform Video Downloader
Fixed auto-download functionality
"""

import os
import sys
import json
import time
import uuid
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, send_file, make_response
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import zipfile
import io
import logging

# Import your video downloader
try:
    from video_downloader import VideoDownloader, quick_download, batch_download, extract_video_links
except ImportError:
    print("Error: video_downloader.py not found. Please ensure it's in the same directory.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app, origins=["*"])
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Global variables
active_downloads = {}
download_queue = []
global_downloader = None

class EnhancedProgressTracker:
    """Enhanced progress tracker with better error handling and status updates"""
    
    def __init__(self, download_id, socketio_instance):
        self.download_id = download_id
        self.socketio = socketio_instance
        self.start_time = time.time()
        self.last_update_time = time.time()
        self.last_percentage = 0
        self.total_bytes = 0
        self.downloaded_bytes = 0
        self.completed = False
        
    def progress_hook(self, d):
        """Enhanced progress hook for yt-dlp with better status tracking"""
        try:
            status = d.get('status', 'unknown')
            current_time = time.time()
            
            # Debug logging
            print(f"[{self.download_id[:8]}] Progress: {status}")
            
            if status == 'downloading':
                # Extract download information
                self.downloaded_bytes = d.get('downloaded_bytes', 0)
                self.total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                speed = d.get('speed', 0)
                eta = d.get('eta', 0)
                
                # Calculate percentage
                if self.total_bytes > 0:
                    percentage = (self.downloaded_bytes / self.total_bytes) * 100
                else:
                    percentage = 0
                
                # Get filename from path
                filename = ''
                if d.get('filename'):
                    filename = Path(d['filename']).name
                
                # Throttle updates (every 0.5 seconds or significant percentage change)
                percentage_change = abs(percentage - self.last_percentage)
                time_since_update = current_time - self.last_update_time
                
                if time_since_update >= 0.5 or percentage_change >= 1:
                    progress_data = {
                        'id': self.download_id,
                        'status': 'downloading',
                        'downloaded_bytes': self.downloaded_bytes,
                        'total_bytes': self.total_bytes,
                        'speed': speed,
                        'eta': eta,
                        'percentage': round(percentage, 1),
                        'filename': filename
                    }
                    
                    # Update global state
                    if self.download_id in active_downloads:
                        active_downloads[self.download_id].update(progress_data)
                    
                    # Emit progress update
                    self.socketio.emit('download_progress', progress_data)
                    
                    self.last_percentage = percentage
                    self.last_update_time = current_time
                    
                    print(f"[{self.download_id[:8]}] {percentage:.1f}% - {self._format_bytes(speed)}/s")
                    
            elif status == 'finished':
                if self.completed:
                    return  # Avoid duplicate completion events
                
                self.completed = True
                
                # Download completed
                filename = ''
                filepath = ''
                if d.get('filename'):
                    filepath = d['filename']
                    filename = Path(filepath).name
                
                total_time = time.time() - self.start_time
                
                completion_data = {
                    'id': self.download_id,
                    'status': 'completed',
                    'filename': filename,
                    'filepath': filepath,
                    'percentage': 100,
                    'progress': 100,
                    'total_time': total_time,
                    'downloaded_bytes': self.total_bytes or self.downloaded_bytes,
                    'total_bytes': self.total_bytes or self.downloaded_bytes,
                    'file_ready': True
                }
                
                # Update global state
                if self.download_id in active_downloads:
                    active_downloads[self.download_id].update(completion_data)
                
                # Emit completion status
                self.socketio.emit('download_status', completion_data)
                
                # Emit file ready event for auto-download
                self.socketio.emit('file_ready', {
                    'id': self.download_id,
                    'filename': filename,
                    'filepath': filepath,
                    'download_url': f'/api/downloads/{self.download_id}/file',
                    'auto_download': True
                })
                
                print(f"[{self.download_id[:8]}] ✅ Completed: {filename} ({self._format_time(total_time)})")
                
            elif status == 'error':
                error_msg = d.get('error', 'Download failed')
                
                error_data = {
                    'id': self.download_id,
                    'status': 'error',
                    'error': error_msg,
                    'percentage': 0
                }
                
                # Update global state
                if self.download_id in active_downloads:
                    active_downloads[self.download_id].update(error_data)
                
                self.socketio.emit('download_status', error_data)
                print(f"[{self.download_id[:8]}] ❌ Error: {error_msg}")
                
        except Exception as e:
            logger.error(f"Progress hook error for {self.download_id}: {str(e)}")
            # Send error status on hook failure
            self.socketio.emit('download_status', {
                'id': self.download_id,
                'status': 'error',
                'error': f'Progress tracking failed: {str(e)}'
            })
    
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
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs:02d}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins:02d}m"

def initialize_downloader():
    """Initialize the global downloader instance"""
    global global_downloader
    
    downloads_path = "./downloads"
    os.makedirs(downloads_path, exist_ok=True)
    
    global_downloader = VideoDownloader(
        download_path=downloads_path,
        remove_watermarks=False
    )
    
    return global_downloader

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        return response

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Expose-Headers', 'Content-Disposition')
    return response

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_downloads': len(active_downloads)
    })

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    """Get or update downloader settings"""
    global global_downloader
    
    if request.method == 'GET':
        return jsonify({
            'download_path': str(global_downloader.download_path),
            'remove_watermarks': global_downloader.remove_watermarks,
            'ffmpeg_available': global_downloader.check_ffmpeg()
        })
    
    elif request.method == 'POST':
        data = request.json
        
        if 'download_path' in data:
            new_path = data['download_path']
            os.makedirs(new_path, exist_ok=True)
            global_downloader.download_path = Path(new_path)
        
        if 'remove_watermarks' in data:
            global_downloader.remove_watermarks = data['remove_watermarks']
        
        return jsonify({'message': 'Settings updated successfully'})

@app.route('/api/download/single', methods=['POST'])
def download_single_video():
    """Download a single video with enhanced progress tracking"""
    try:
        data = request.json
        url = data.get('url', '').strip()
        custom_filename = data.get('custom_filename', '').strip() or None
        remove_watermark = data.get('remove_watermark', False)
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Generate unique download ID
        download_id = str(uuid.uuid4())
        
        # Add to active downloads with initial status
        active_downloads[download_id] = {
            'id': download_id,
            'url': url,
            'status': 'queued',
            'platform': global_downloader.detect_platform(url),
            'created_at': datetime.now().isoformat(),
            'custom_filename': custom_filename,
            'remove_watermark': remove_watermark,
            'progress': 0,
            'downloaded_bytes': 0,
            'total_bytes': 0,
            'speed': 0,
            'eta': 0,
            'filename': '',
            'filepath': ''
        }
        
        print(f"🚀 Starting download: {download_id[:8]} - {url}")
        
        # Immediately emit the queued status
        socketio.emit('download_status', {
            'id': download_id,
            'status': 'queued',
            'url': url,
            'platform': global_downloader.detect_platform(url)
        })
        
        def download_worker():
            try:
                # Update to starting status
                active_downloads[download_id]['status'] = 'starting'
                socketio.emit('download_status', {
                    'id': download_id,
                    'status': 'starting'
                })
                
                print(f"🔥 Download worker started for {download_id[:8]}")
                
                # Create enhanced progress tracker
                progress_tracker = EnhancedProgressTracker(download_id, socketio)
                
                # Create custom downloader instance
                custom_downloader = VideoDownloader(
                    download_path=global_downloader.download_path,
                    remove_watermarks=remove_watermark
                )
                
                # Add progress hook
                custom_downloader.base_options['progress_hooks'] = [progress_tracker.progress_hook]
                
                # Download the video
                success = custom_downloader.download_video(
                    url=url,
                    custom_filename=custom_filename,
                    remove_watermark=remove_watermark,
                    download_id=download_id
                )
                
                print(f"📋 Download result for {download_id[:8]}: {success}")
                
                # Handle case where progress hook didn't catch completion
                if success and download_id in active_downloads:
                    current_status = active_downloads[download_id]['status']
                    if current_status not in ['completed', 'error']:
                        # Find the downloaded file
                        download_path = global_downloader.download_path
                        potential_files = list(download_path.glob('*'))
                        
                        if potential_files:
                            # Get the most recent file
                            latest_file = max(potential_files, key=lambda p: p.stat().st_mtime)
                            filename = latest_file.name
                            filepath = str(latest_file)
                        else:
                            filename = 'unknown_file'
                            filepath = ''
                        
                        active_downloads[download_id].update({
                            'status': 'completed',
                            'progress': 100,
                            'percentage': 100,
                            'filename': filename,
                            'filepath': filepath,
                            'file_ready': True
                        })
                        
                        socketio.emit('download_status', {
                            'id': download_id,
                            'status': 'completed',
                            'progress': 100,
                            'percentage': 100,
                            'filename': filename,
                            'file_ready': True
                        })
                        
                        # Emit file ready event
                        socketio.emit('file_ready', {
                            'id': download_id,
                            'filename': filename,
                            'download_url': f'/api/downloads/{download_id}/file',
                            'auto_download': True
                        })
                        
                elif not success and download_id in active_downloads:
                    current_status = active_downloads[download_id]['status']
                    if current_status not in ['completed', 'error']:
                        active_downloads[download_id]['status'] = 'error'
                        active_downloads[download_id]['error'] = 'Download failed - no additional details'
                        socketio.emit('download_status', {
                            'id': download_id,
                            'status': 'error',
                            'error': 'Download failed - no additional details'
                        })
                            
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Download worker error for {download_id}: {error_msg}")
                print(f"💥 Download worker error for {download_id[:8]}: {error_msg}")
                
                if download_id in active_downloads:
                    active_downloads[download_id]['status'] = 'error'
                    active_downloads[download_id]['error'] = error_msg
                
                socketio.emit('download_status', {
                    'id': download_id,
                    'status': 'error',
                    'error': error_msg
                })
        
        # Start download in background thread
        thread = threading.Thread(target=download_worker, name=f"Download-{download_id[:8]}")
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'message': 'Download started',
            'download_id': download_id,
            'status': 'queued'
        })
        
    except Exception as e:
        logger.error(f"Error starting download: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ... (rest of the route handlers remain the same as in your original code)

@app.route('/api/downloads/<download_id>/file', methods=['GET'])
def download_file(download_id):
    """Download the actual video file with proper headers for auto-download"""
    try:
        # Find the download record
        download = active_downloads.get(download_id)
        if not download:
            return jsonify({'error': 'Download not found'}), 404
        
        filename = download.get('filename')
        filepath = download.get('filepath')
        
        if not filename:
            return jsonify({'error': 'No filename available'}), 404
        
        # Try to find the file
        if filepath and os.path.exists(filepath):
            file_path = Path(filepath)
        else:
            # Fallback: search in download directory
            file_path = global_downloader.download_path / filename
            if not file_path.exists():
                # Try to find any file with similar name
                potential_files = list(global_downloader.download_path.glob(f"*{filename}*"))
                if not potential_files:
                    potential_files = list(global_downloader.download_path.glob("*.mp4"))
                    if not potential_files:
                        return jsonify({'error': 'File not found on server'}), 404
                file_path = potential_files[0]
        
        if not file_path.exists():
            return jsonify({'error': 'File not found on server'}), 404
        
        # Get file size for proper headers
        file_size = file_path.stat().st_size
        
        # Set proper headers for automatic download
        response = send_file(
            file_path, 
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
        
        # Add CORS headers for cross-origin downloads
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition, Content-Length'
        
        # Add cache control headers
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        # Add content length
        response.headers['Content-Length'] = str(file_size)
        
        return response
        
    except Exception as e:
        logger.error(f"Error serving file {download_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ... (rest of the code remains the same)

def main():
    """Main function to run the Flask server"""
    # Initialize the downloader
    initialize_downloader()
    
    print("🚀 Enhanced Video Downloader Backend Starting...")
    print(f"📁 Download directory: {global_downloader.download_path}")
    print(f"🔧 FFmpeg available: {global_downloader.check_ffmpeg()}")
    
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get('PORT', 4000))
    host = '0.0.0.0'  # Important: bind to all interfaces
    
    print(f"🌐 Server will be available at: http://{host}:{port}")
    print(f"📡 WebSocket endpoint: ws://{host}:{port}")
    
    # Run the server
    try:
        socketio.run(
            app,
            host=host,
            port=port,
            debug=False,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {str(e)}")

if __name__ == '__main__':
    main()
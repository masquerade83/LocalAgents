// RTSP Stream Viewer
class RTSPViewer {
    constructor() {
        this.streamUrl = null;
        this.eventSource = null;
        this.init();
    }

    init() {
        const connectBtn = document.getElementById('connectBtn');
        const disconnectBtn = document.getElementById('disconnectBtn');
        const rtspUrlInput = document.getElementById('rtspUrl');
        const confidenceSlider = document.getElementById('confidenceSlider');
        const confidenceValue = document.getElementById('confidenceValue');

        connectBtn.addEventListener('click', () => this.connect());
        disconnectBtn.addEventListener('click', () => this.disconnect());
        
        rtspUrlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.connect();
            }
        });
        
        // Update confidence value display
        confidenceSlider.addEventListener('input', (e) => {
            confidenceValue.textContent = parseFloat(e.target.value).toFixed(2);
        });
    }

    async connect() {
        const rtspUrl = document.getElementById('rtspUrl').value.trim();
        const yoloEnabled = document.getElementById('yoloEnabled').checked;
        const confidence = parseFloat(document.getElementById('confidenceSlider').value);
        
        if (!rtspUrl) {
            this.showStatus('Please enter an RTSP URL', 'error');
            return;
        }

        if (!rtspUrl.startsWith('rtsp://')) {
            this.showStatus('URL must start with rtsp://', 'error');
            return;
        }

        this.streamUrl = rtspUrl;
        const statusMsg = yoloEnabled ? 'Connecting to stream with YOLO detection...' : 'Connecting to stream...';
        this.showStatus(statusMsg, 'info');

        try {
            // Start the stream via backend
            const response = await fetch('/api/stream/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    url: rtspUrl,
                    yolo: yoloEnabled,
                    confidence: confidence
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to start stream');
            }

            // Use MJPEG stream with YOLO
            const videoPlayer = document.getElementById('videoPlayer');
            const canvasPlayer = document.getElementById('canvasPlayer');
            const status = document.getElementById('status');

            // Hide status, show video
            status.style.display = 'none';
            
            // Build stream URL with parameters
            const streamUrl = data.stream_url || `/api/stream/mjpeg?url=${encodeURIComponent(rtspUrl)}&yolo=${yoloEnabled}&confidence=${confidence}`;
            
            // Use img element for MJPEG stream (browsers handle multipart/x-mixed-replace natively)
            this.loadMJPEGStream(streamUrl);

            document.getElementById('connectBtn').disabled = true;
            document.getElementById('disconnectBtn').disabled = false;
            document.getElementById('rtspUrl').disabled = true;

            const yoloStatus = data.yolo ? 'Enabled' : 'Disabled';
            this.showStatus(`Stream connected! YOLO: ${yoloStatus}`, 'success');
            this.updateStreamInfo(`Stream URL: ${rtspUrl}\nStatus: Connected\nFormat: ${data.format || 'MJPEG'}\nYOLO Detection: ${yoloStatus}\nConfidence: ${confidence}`);

        } catch (error) {
            console.error('Connection error:', error);
            this.showStatus(`Error: ${error.message}`, 'error');
        }
    }

    loadMJPEGStream(url) {
        const canvas = document.getElementById('canvasPlayer');
        const videoPlayer = document.getElementById('videoPlayer');
        const status = document.getElementById('status');
        
        // Hide status
        status.style.display = 'none';
        
        // Try using img element for MJPEG stream (more reliable than canvas)
        const img = document.createElement('img');
        img.style.width = '100%';
        img.style.height = 'auto';
        img.style.display = 'block';
        img.style.background = '#000';
        
        // Clear canvas container and add img
        canvas.style.display = 'none';
        videoPlayer.style.display = 'none';
        
        const container = document.querySelector('.video-container');
        // Remove any existing img
        const existingImg = container.querySelector('img.mjpeg-stream');
        if (existingImg) {
            existingImg.remove();
        }
        
        img.className = 'mjpeg-stream';
        container.appendChild(img);
        
        // For MJPEG streams, we can use the URL directly with img tag
        // The server sends multipart/x-mixed-replace which browsers handle automatically
        img.src = url;
        
        img.onerror = (e) => {
            console.error('Failed to load MJPEG stream:', e);
            status.textContent = 'Error loading video stream. Check console for details.';
            status.style.display = 'block';
            status.className = 'status error';
        };
        
        img.onload = () => {
            console.log('MJPEG stream frame loaded');
        };
    }

    async disconnect() {
        try {
            await fetch('/api/stream/stop', {
                method: 'POST'
            });
        } catch (error) {
            console.error('Disconnect error:', error);
        }

        const videoPlayer = document.getElementById('videoPlayer');
        const canvasPlayer = document.getElementById('canvasPlayer');
        const container = document.querySelector('.video-container');
        
        // Remove MJPEG img if it exists
        const mjpegImg = container.querySelector('img.mjpeg-stream');
        if (mjpegImg) {
            mjpegImg.src = ''; // Stop loading
            mjpegImg.remove();
        }
        
        videoPlayer.src = '';
        videoPlayer.style.display = 'none';
        canvasPlayer.style.display = 'none';

        document.getElementById('connectBtn').disabled = false;
        document.getElementById('disconnectBtn').disabled = true;
        document.getElementById('rtspUrl').disabled = false;

        this.showStatus('Stream disconnected', 'info');
        this.updateStreamInfo('No stream connected');
        this.streamUrl = null;
    }

    showStatus(message, type = 'info') {
        const status = document.getElementById('status');
        status.textContent = message;
        status.className = `status ${type}`;
        status.style.display = 'block';
    }

    updateStreamInfo(info) {
        document.getElementById('streamInfo').textContent = info;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new RTSPViewer();
});

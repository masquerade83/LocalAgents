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

        this.fetchModelInfo();
    }

    async fetchModelInfo() {
        try {
            const res = await fetch('/api/yolo/model-info');
            const data = await res.json();
            const el = document.getElementById('modelInfo');
            if (data.loaded && data.classes && data.classes.length) {
                el.textContent = `${data.num_classes} classes: ${data.classes.join(', ')}`;
                el.title = data.path || '';
            } else {
                el.textContent = data.message || 'Model not loaded';
            }
        } catch (e) {
            document.getElementById('modelInfo').textContent = 'Could not load model info';
        }
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
            this.updateStreamInfo(`Stream URL: ${rtspUrl}\nStatus: Connected\nFormat: ${data.format || 'MJPEG'}\nYOLO Detection: ${yoloStatus}\nConfidence: ${confidence}${yoloEnabled ? '\nTip: If some classes don\'t show, try lowering Confidence (e.g. 0.1).' : ''}`);

        } catch (error) {
            console.error('Connection error:', error);
            this.showStatus(`Error: ${error.message}`, 'error');
        }
    }

    loadMJPEGStream(url) {
        const canvas = document.getElementById('canvasPlayer');
        const videoPlayer = document.getElementById('videoPlayer');
        const status = document.getElementById('status');
        
        status.style.display = 'none';
        canvas.style.display = 'none';
        videoPlayer.style.display = 'none';
        
        const container = document.querySelector('.video-container');
        const existingImg = container.querySelector('img.mjpeg-stream');
        if (existingImg) existingImg.remove();
        
        const img = document.createElement('img');
        img.className = 'mjpeg-stream';
        img.style.width = '100%';
        img.style.height = 'auto';
        img.style.display = 'block';
        img.style.background = '#000';
        container.appendChild(img);
        
        // When behind ngrok/tunnel, img.src fails (interstitial or buffering). Use fetch with
        // ngrok-skip-browser-warning and parse multipart stream so video shows.
        const isLikelyTunnel = /ngrok|\.loca\.lt|localhost\.run|\.trycloudflare\.com/i.test(location.hostname) ||
            (location.protocol === 'https:' && location.hostname !== 'localhost');
        
        if (isLikelyTunnel && typeof fetch !== 'undefined' && typeof ReadableStream !== 'undefined') {
            this.loadMJPEGStreamViaFetch(url, img, status);
            return;
        }
        
        img.src = url;
        img.onerror = () => {
            status.textContent = 'Error loading video stream. If using ngrok, try refreshing.';
            status.style.display = 'block';
            status.className = 'status error';
        };
        img.onload = () => console.log('MJPEG stream frame loaded');
    }
    
    async loadMJPEGStreamViaFetch(url, img, statusEl) {
        const boundary = 'frame';
        const headers = { 'ngrok-skip-browser-warning': 'true' };
        let lastBlobUrl = null;
        let buffer = new Uint8Array(0);
        const boundaryEnd = new TextEncoder().encode('\r\n--' + boundary + '\r\n');
        let frameCount = 0;
        const debug = /[?&]debug=1/i.test(location.search);
        
        try {
            const res = await fetch(url, { headers });
            const contentType = (res.headers.get('content-type') || '').toLowerCase();
            if (contentType.includes('text/html')) {
                statusEl.innerHTML = 'Ngrok returned a page instead of video. Open this URL in a new tab, click "Visit Site" if shown, then try Connect again.';
                statusEl.style.display = 'block';
                statusEl.className = 'status error';
                return;
            }
            if (!res.ok || !res.body) throw new Error(res.statusText || 'Stream failed');
            const reader = res.body.getReader();
            
            const findBoundary = (buf, from) => {
                const len = boundaryEnd.length;
                for (let i = from; i <= buf.length - len; i++) {
                    let match = true;
                    for (let j = 0; j < len; j++) if (buf[i + j] !== boundaryEnd[j]) { match = false; break; }
                    if (match) return i;
                }
                return -1;
            };
            
            const skipHeaders = (buf, start) => {
                const sep = new Uint8Array([13, 10, 13, 10]);
                for (let i = start; i < buf.length - 4; i++) {
                    if (buf[i] === 13 && buf[i+1] === 10 && buf[i+2] === 13 && buf[i+3] === 10)
                        return i + 4;
                }
                return -1;
            };
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const n = buffer.length;
                const newBuf = new Uint8Array(n + value.length);
                newBuf.set(buffer);
                newBuf.set(value, n);
                buffer = newBuf;
                
                let start = 0;
                const firstBoundary = new TextEncoder().encode('--frame\r\n');
                const isFirstBoundary = (buf, at) => {
                    if (at + firstBoundary.length > buf.length) return false;
                    for (let i = 0; i < firstBoundary.length; i++) if (buf[at + i] !== firstBoundary[i]) return false;
                    return true;
                };
                while (true) {
                    let bStart = buffer.length ? findBoundary(buffer, start) : -1;
                    if (bStart === -1 && start === 0 && isFirstBoundary(buffer, 0)) bStart = 0;
                    if (bStart === -1) {
                        if (buffer.length > 2 * 1024 * 1024) buffer = buffer.slice(-1024 * 1024);
                        break;
                    }
                    const afterBoundary = bStart === 0 ? firstBoundary.length : bStart + boundaryEnd.length;
                    const headerEnd = skipHeaders(buffer, afterBoundary);
                    if (headerEnd === -1) { start = bStart + 1; continue; }
                    const nextBoundary = findBoundary(buffer, headerEnd);
                    if (nextBoundary === -1) {
                        if (buffer.length > 2 * 1024 * 1024) buffer = buffer.slice(bStart);
                        break;
                    }
                    let jpeg = buffer.slice(headerEnd, nextBoundary);
                    buffer = buffer.slice(nextBoundary);
                    start = 0;
                    if (jpeg.length < 100) continue;
                    const end = jpeg.length - 1;
                    if (end >= 1 && jpeg[end] === 0x0a && jpeg[end - 1] === 0x0d) jpeg = jpeg.slice(0, end - 1);
                    else if (end >= 0 && jpeg[end] === 0x0a) jpeg = jpeg.slice(0, end);
                    if (jpeg.length < 100) continue;
                    frameCount++;
                    if (debug && frameCount <= 3) console.log('MJPEG frame', frameCount, 'size', jpeg.length);
                    const blob = new Blob([jpeg], { type: 'image/jpeg' });
                    const blobUrl = URL.createObjectURL(blob);
                    if (lastBlobUrl) URL.revokeObjectURL(lastBlobUrl);
                    lastBlobUrl = blobUrl;
                    img.src = blobUrl;
                }
            }
            if (debug) console.log('MJPEG stream ended. Total frames:', frameCount);
        } catch (e) {
            console.error('MJPEG fetch error:', e);
            statusEl.textContent = 'Stream error: ' + (e.message || 'Check console. Use same network as camera when on tunnel.');
            statusEl.style.display = 'block';
            statusEl.className = 'status error';
        } finally {
            if (lastBlobUrl) URL.revokeObjectURL(lastBlobUrl);
        }
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

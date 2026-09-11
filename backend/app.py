import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PIL import Image as PilImage
from model.inference import DiabCareModel
from database import Database
from reports import ReportGenerator

# ---- Config via env (right procedure for Render + mobile) ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get('DATA_DIR', os.path.join(BASE_DIR, '..', 'data'))
UPLOAD_FOLDER = os.environ.get(
    'UPLOAD_FOLDER', os.path.join(DATA_DIR, 'scans'))
REPORT_FOLDER = os.environ.get(
    'REPORT_FOLDER', os.path.join(DATA_DIR, 'reports'))
ALLOWED_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',') \
    if os.environ.get('CORS_ORIGINS') else None  # None = same-origin only
API_TOKEN = os.environ.get('API_TOKEN', '')  # optional shared secret for mobile app
MAX_UPLOAD_MB = int(os.environ.get('MAX_UPLOAD_MB', '8'))

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# Origins that are always allowed (local dev + Capacitor/TWA wrappers).
# Browsers enforce CORS; native apps do not, but Capacitor uses http(s)/capacitor scheme.
BUILTIN_ALLOWED_ORIGINS = [
    'http://localhost:5000',
    'http://127.0.0.1:5000',
    'http://localhost',
    'capacitor://localhost',
    'https://localhost',
    'http://localhost:8080',
]

app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024

if ALLOWED_ORIGINS:
    _origins = BUILTIN_ALLOWED_ORIGINS + \
        [o.strip() for o in ALLOWED_ORIGINS if o.strip()]
    CORS(app, origins=_origins)
else:
    # Same-origin + local/Capacitor only by default.
    CORS(app, resources={r"/api/*": {"origins": BUILTIN_ALLOWED_ORIGINS}})

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

model = DiabCareModel()
db = Database()
report_gen = ReportGenerator(REPORT_FOLDER)


def _check_auth():
    """Optional token auth for mobile app. Disabled if API_TOKEN not set."""
    if not API_TOKEN:
        return True
    # Allow public GET for health; require token for API writes/reads
    auth = request.headers.get('X-API-Key', '')
    return auth == API_TOKEN


def _device_id():
    """Per-phone isolation: each phone sends its own X-Device-Id.
    Falls back to 'web' for old browsers without one."""
    did = (request.headers.get('X-Device-Id', '') or '').strip()
    if not did and request.args.get('device_id'):
        did = request.args.get('device_id').strip()
    if not did:
        try:
            data = request.get_json(silent=True) or {}
            did = str(data.get('device_id', '')).strip()
        except Exception:
            did = ''
    # Basic sanity: limit length, allow alnum + - _ :
    if not did or len(did) > 64:
        return 'web'
    return did


def _allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.after_request
def _security_headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['Referrer-Policy'] = 'no-referrer'
    return resp


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'demo_mode': model.demo_mode,
                    'time': datetime.now().isoformat()})


@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    # Block API-like and hidden paths from static handler
    if path.startswith('api/') or '/.' in '/' + path:
        return jsonify({'error': 'Not found'}), 404
    try:
        return send_from_directory(app.static_folder, path)
    except Exception:
        return jsonify({'error': 'Not found'}), 404


@app.route('/api/analyze', methods=['POST'])
def analyze_image():
    if not _check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400

    if not _allowed_file(file.filename):
        return jsonify({'error': 'Only PNG/JPG/JPEG/WEBP allowed'}), 400

    safe_name = secure_filename(file.filename)
    ext = safe_name.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # Verify it is a real image (blocks fake uploads / scripts)
    try:
        with PilImage.open(filepath) as im:
            im.verify()
    except Exception:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': 'Invalid image file'}), 400

    try:
        result = model.predict(filepath)
    except Exception as e:
        import traceback
        traceback.print_exc()
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

    scan_id = db.save_scan(
        filename=filename,
        filepath=filepath,
        prediction=result['prediction'],
        confidence=result['confidence'],
        risk_level=result['risk_level'],
        heatmap_path=result.get('heatmap_path'),
        device_id=_device_id()
    )

    result['scan_id'] = scan_id
    result['filename'] = filename
    result['timestamp'] = datetime.now().isoformat()

    return jsonify(result)


@app.route('/api/history', methods=['GET'])
def get_history():
    if not _check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    scans = db.get_all_scans(device_id=_device_id())
    return jsonify(scans)


@app.route('/api/scan/<int:scan_id>', methods=['GET'])
def get_scan(scan_id):
    if not _check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    scan = db.get_scan(scan_id, device_id=_device_id())
    if not scan:
        return jsonify({'error': 'Scan not found'}), 404
    return jsonify(scan)


@app.route('/api/scan/<int:scan_id>', methods=['DELETE'])
def delete_scan(scan_id):
    if not _check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    scan = db.get_scan(scan_id, device_id=_device_id())
    if not scan:
        return jsonify({'error': 'Scan not found'}), 404

    for key in ('filepath', 'heatmap_path'):
        p = scan.get(key)
        # Only delete files inside our upload folder (traversal guard)
        if p and os.path.abspath(p).startswith(os.path.abspath(UPLOAD_FOLDER)):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

    db.delete_scan(scan_id, device_id=_device_id())
    return jsonify({'message': 'Scan deleted'})


@app.route('/api/report/<int:scan_id>', methods=['GET'])
def generate_report(scan_id):
    if not _check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    scan = db.get_scan(scan_id, device_id=_device_id())
    if not scan:
        return jsonify({'error': 'Scan not found'}), 404

    report_path = report_gen.generate(scan)
    return send_file(report_path, as_attachment=True,
                     download_name=f"DiabCare_Report_{scan_id}.pdf")


@app.route('/api/stats', methods=['GET'])
def get_stats():
    if not _check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    stats = db.get_statistics(device_id=_device_id())
    return jsonify(stats)


@app.route('/api/image/<filename>')
def get_image(filename):
    if not _check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    # Strict filename check: only uuid + allowed ext, no slashes
    safe = secure_filename(filename)
    if safe != filename or not _allowed_file(filename):
        return jsonify({'error': 'Not found'}), 404
    # Ownership check: only serve images belonging to this device
    if not db.owns_file(filename, _device_id()):
        return jsonify({'error': 'Not found'}), 404
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': f'File too large (max {MAX_UPLOAD_MB}MB)'}), 413


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5000'))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', debug=debug, port=port)

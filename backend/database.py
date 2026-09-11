import sqlite3
import os
from datetime import datetime


class Database:
    def __init__(self):
        data_dir = os.environ.get(
            'DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
        os.makedirs(data_dir, exist_ok=True)
        self.db_path = os.environ.get(
            'DB_PATH', os.path.join(data_dir, 'diabcare.db'))
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                prediction TEXT NOT NULL,
                confidence REAL NOT NULL,
                risk_level TEXT NOT NULL,
                heatmap_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                device_id TEXT DEFAULT 'web'
            )
        ''')
        # Migration for existing DBs created before device_id existed
        cursor.execute('PRAGMA table_info(scans)')
        cols = [r[1] for r in cursor.fetchall()]
        if 'device_id' not in cols:
            cursor.execute("ALTER TABLE scans ADD COLUMN device_id TEXT DEFAULT 'web'")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scans_device ON scans(device_id)")
        conn.commit()
        conn.close()

    def save_scan(self, filename, filepath, prediction, confidence, risk_level, heatmap_path=None, device_id='web'):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scans (filename, filepath, prediction, confidence, risk_level, heatmap_path, device_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (filename, filepath, prediction, confidence, risk_level, heatmap_path, device_id))
        conn.commit()
        scan_id = cursor.lastrowid
        conn.close()
        return scan_id

    def get_all_scans(self, device_id=None):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if device_id:
            cursor.execute('SELECT * FROM scans WHERE device_id = ? ORDER BY created_at DESC', (device_id,))
        else:
            cursor.execute('SELECT * FROM scans ORDER BY created_at DESC')
        scans = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return scans

    def get_scan(self, scan_id, device_id=None):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if device_id:
            cursor.execute('SELECT * FROM scans WHERE id = ? AND device_id = ?', (scan_id, device_id))
        else:
            cursor.execute('SELECT * FROM scans WHERE id = ?', (scan_id,))
        scan = cursor.fetchone()
        conn.close()
        return dict(scan) if scan else None

    def delete_scan(self, scan_id, device_id=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if device_id:
            cursor.execute('DELETE FROM scans WHERE id = ? AND device_id = ?', (scan_id, device_id))
        else:
            cursor.execute('DELETE FROM scans WHERE id = ?', (scan_id,))
        conn.commit()
        conn.close()

    def owns_file(self, filename, device_id):
        """True if this filename (scan or heatmap) belongs to device."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM scans WHERE (filename = ? OR heatmap_path LIKE ?) AND device_id = ? LIMIT 1',
            (filename, f'%{filename}', device_id))
        row = cursor.fetchone()
        conn.close()
        return row is not None

    def get_statistics(self, device_id=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if device_id:
            cursor.execute('SELECT COUNT(*) FROM scans WHERE device_id = ?', (device_id,))
            total = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM scans WHERE device_id = ? AND prediction = ? AND risk_level = ?', (device_id, 'Ulcer', 'HIGH'))
            high_risk = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM scans WHERE device_id = ? AND risk_level = ?', (device_id, 'MEDIUM',))
            medium_risk = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM scans WHERE device_id = ? AND risk_level = ?', (device_id, 'LOW',))
            low_risk = cursor.fetchone()[0]

            cursor.execute('SELECT AVG(confidence) FROM scans WHERE device_id = ?', (device_id,))
            avg_confidence = cursor.fetchone()[0] or 0

            cursor.execute('''
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM scans WHERE device_id = ?
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 7
            ''', (device_id,))
            daily_scans = [{'date': row[0], 'count': row[1]} for row in cursor.fetchall()]
        else:
            cursor.execute('SELECT COUNT(*) FROM scans')
            total = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM scans WHERE prediction = ? AND risk_level = ?', ('Ulcer', 'HIGH'))
            high_risk = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM scans WHERE risk_level = ?', ('MEDIUM',))
            medium_risk = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM scans WHERE risk_level = ?', ('LOW',))
            low_risk = cursor.fetchone()[0]

            cursor.execute('SELECT AVG(confidence) FROM scans')
            avg_confidence = cursor.fetchone()[0] or 0

            cursor.execute('''
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM scans
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 7
            ''')
            daily_scans = [{'date': row[0], 'count': row[1]} for row in cursor.fetchall()]

        conn.close()

        return {
            'total_scans': total,
            'high_risk': high_risk,
            'medium_risk': medium_risk,
            'low_risk': low_risk,
            'average_confidence': round(avg_confidence, 2),
            'daily_scans': daily_scans
        }

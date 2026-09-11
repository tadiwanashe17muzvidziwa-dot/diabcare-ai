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
                notes TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def save_scan(self, filename, filepath, prediction, confidence, risk_level, heatmap_path=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scans (filename, filepath, prediction, confidence, risk_level, heatmap_path)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (filename, filepath, prediction, confidence, risk_level, heatmap_path))
        conn.commit()
        scan_id = cursor.lastrowid
        conn.close()
        return scan_id

    def get_all_scans(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM scans ORDER BY created_at DESC')
        scans = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return scans

    def get_scan(self, scan_id):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM scans WHERE id = ?', (scan_id,))
        scan = cursor.fetchone()
        conn.close()
        return dict(scan) if scan else None

    def delete_scan(self, scan_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM scans WHERE id = ?', (scan_id,))
        conn.commit()
        conn.close()

    def get_statistics(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

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

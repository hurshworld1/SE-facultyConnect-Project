"""
FacultyConnect - Faculty Personal Website Platform
====================================================
A platform where faculty members create and manage their personal
academic websites. All data is stored on this platform's database.

Features:
- Faculty registration with email and password
- Personal website creation with full control over visibility
- File uploads (photos, PDFs, CVs, certificates, documents)
- Draft/publish mode for all sections
- Student contact forms
- Admin monitoring panel (internal only)
- Activity logging and threat detection
"""

import os
import re
import secrets
import sqlite3
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import (
    Flask, abort, flash, g, jsonify, redirect,
    render_template, request, session, send_from_directory,
    url_for
)

# =============================================================================
# Application Configuration
# =============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fc-dev-key-change-in-production')
app.config['DATABASE'] = os.environ.get('DATABASE_URL', os.path.join(app.root_path, 'faculty.db'))
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB (for video uploads)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=4)

ALLOWED_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'gif', 'webp',
    'pdf', 'doc', 'docx',
    'ppt', 'pptx',
    'zip', 'txt',
    'mp4', 'webm', 'avi', 'mov', 'mkv',
    'ipynb', 'py', 'java', 'cpp', 'c', 'html', 'css', 'js'
}

PHOTO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

UPLOAD_DIRS = ['photos', 'documents', 'materials', 'resumes', 'certificates']
for d in UPLOAD_DIRS:
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], d), exist_ok=True)

# Jinja2 filter: build a safe URL from a user-supplied value
@app.template_filter('safe_url')
def safe_url_filter(value):
    """Ensure a URL has a valid scheme (https://)."""
    if not value:
        return ''
    value = value.strip()
    if value.startswith(('http://', 'https://')):
        return value
    if value.startswith('//'):
        return 'https:' + value
    return 'https://' + value

# =============================================================================
# Database Connection
# =============================================================================

def get_platform_db():
    try:
        if 'platform_db' not in g:
            g.platform_db = sqlite3.connect(app.config['DATABASE'], timeout=15)
            g.platform_db.row_factory = sqlite3.Row
            g.platform_db.execute('PRAGMA foreign_keys = ON')
            try:
                g.platform_db.execute('PRAGMA journal_mode = WAL')
            except Exception:
                pass
        return g.platform_db
    except RuntimeError:
        db = sqlite3.connect(app.config['DATABASE'], timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
        return db

def get_db():
    if 'db' not in g:
        fid = None
        try:
            fid = session.get('faculty_id')
        except RuntimeError:
            pass
        if fid:
            pdb = get_platform_db()
            row = pdb.execute('SELECT is_detached FROM faculty WHERE id = ?', (fid,)).fetchone()
            if row and row['is_detached']:
                ind_path = os.path.join(app.root_path, f'faculty_{fid}.db')
                if os.path.exists(ind_path):
                    g.db = sqlite3.connect(ind_path, timeout=15)
                    g.db.row_factory = sqlite3.Row
                    g.db.execute('PRAGMA foreign_keys = ON')
                    try:
                        g.db.execute('PRAGMA journal_mode = WAL')
                    except Exception:
                        pass
                    g._using_independent_db = True
                    return g.db
        g.db = sqlite3.connect(app.config['DATABASE'], timeout=15)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
        try:
            g.db.execute('PRAGMA journal_mode = WAL')
        except Exception:
            pass
        g._using_independent_db = False
    return g.db

def is_independent_db():
    return getattr(g, '_using_independent_db', False)

@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()
    pdb = g.pop('platform_db', None)
    if pdb is not None:
        pdb.close()

def init_db():
    db = sqlite3.connect(app.config['DATABASE'], timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    try:
        db.execute('PRAGMA journal_mode = WAL')
    except Exception:
        pass
    db.executescript('''
        -- Platform admins (hidden monitoring interface)
        CREATE TABLE IF NOT EXISTS platform_admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Faculty accounts
        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            designation TEXT DEFAULT '',
            department TEXT DEFAULT '',
            institution TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            office_location TEXT DEFAULT '',
            office_hours TEXT DEFAULT '',
            visiting_hours TEXT DEFAULT '',
            address TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            photo TEXT DEFAULT '',
            resume_file TEXT DEFAULT '',
            website TEXT DEFAULT '',
            google_scholar TEXT DEFAULT '',
            linkedin TEXT DEFAULT '',
            is_detached INTEGER DEFAULT 0,
            detached_at TIMESTAMP DEFAULT NULL,
            github TEXT DEFAULT '',
            research_summary TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Qualifications with certificate photos
        CREATE TABLE IF NOT EXISTS qualifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            degree TEXT NOT NULL,
            specialization TEXT DEFAULT '',
            university TEXT DEFAULT '',
            year_of_passing TEXT DEFAULT '',
            certificate_photo TEXT DEFAULT '',
            is_published INTEGER DEFAULT 1,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );

        -- Research interests
        CREATE TABLE IF NOT EXISTS research_interests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            is_published INTEGER DEFAULT 1,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );

        -- Achievements and awards with certificate photos
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT DEFAULT 'award',
            year TEXT DEFAULT '',
            certificate_photo TEXT DEFAULT '',
            is_published INTEGER DEFAULT 1,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );

        -- Publications
        CREATE TABLE IF NOT EXISTS publications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            authors TEXT DEFAULT '',
            journal TEXT DEFAULT '',
            year TEXT DEFAULT '',
            doi TEXT DEFAULT '',
            url TEXT DEFAULT '',
            abstract TEXT DEFAULT '',
            pub_type TEXT DEFAULT 'journal',
            is_published INTEGER DEFAULT 1,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );

        -- Courses
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            code TEXT DEFAULT '',
            description TEXT DEFAULT '',
            semester TEXT DEFAULT '',
            schedule TEXT DEFAULT '',
            is_published INTEGER DEFAULT 1,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );

        -- Course materials (uploaded files)
        CREATE TABLE IF NOT EXISTS course_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            faculty_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT DEFAULT '',
            description TEXT DEFAULT '',
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );

        -- Research students
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            program TEXT DEFAULT '',
            research_topic TEXT DEFAULT '',
            status TEXT DEFAULT 'ongoing',
            start_year TEXT DEFAULT '',
            email TEXT DEFAULT '',
            is_published INTEGER DEFAULT 1,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );

        -- Research projects
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            funding_agency TEXT DEFAULT '',
            amount TEXT DEFAULT '',
            status TEXT DEFAULT 'ongoing',
            start_year TEXT DEFAULT '',
            end_year TEXT DEFAULT '',
            is_published INTEGER DEFAULT 1,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );

        -- Announcements
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            is_important INTEGER DEFAULT 0,
            is_published INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );

        -- Student messages / contact form submissions
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            sender_name TEXT NOT NULL,
            sender_email TEXT NOT NULL,
            subject TEXT DEFAULT '',
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );

        -- Activity logs for monitoring
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_type TEXT DEFAULT 'guest',
            user_id INTEGER DEFAULT 0,
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            ip_address TEXT DEFAULT '',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Threat detection
        CREATE TABLE IF NOT EXISTS threats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            threat_type TEXT NOT NULL,
            description TEXT DEFAULT '',
            ip_address TEXT DEFAULT '',
            severity TEXT DEFAULT 'low',
            is_resolved INTEGER DEFAULT 0,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Migration requests (faculty requests to detach from platform)
        CREATE TABLE IF NOT EXISTS migration_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            reason TEXT DEFAULT '',
            target_email TEXT DEFAULT '',
            hosting_provider TEXT DEFAULT '',
            hosting_plan TEXT DEFAULT '',
            custom_domain TEXT DEFAULT '',
            admin_notes TEXT DEFAULT '',
            reviewed_by INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP DEFAULT NULL,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE        );

        -- Email verification codes for migration requests
        CREATE TABLE IF NOT EXISTS verification_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            code TEXT NOT NULL,
            purpose TEXT DEFAULT 'migration',
            is_used INTEGER DEFAULT 0,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );

        -- Standalone resources (PDFs, videos, notes for students)
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            resource_type TEXT DEFAULT 'pdf',
            file_path TEXT NOT NULL,
            url TEXT DEFAULT '',
            is_published INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );
    ''')


    # Create default platform admin if not exists
    admin = db.execute(
        'SELECT id FROM platform_admins WHERE username = ?', ('admin',)
    ).fetchone()
    if not admin:
        db.execute(
            'INSERT INTO platform_admins (username, password_hash) VALUES (?, ?)',
            ('admin', generate_password_hash('admin123'))
        )
    db.commit()

    # Schema migration: add columns that may not exist in older databases
    migration_columns = [
        ('migration_requests', 'target_email', "TEXT DEFAULT ''"),
        ('migration_requests', 'hosting_provider', "TEXT DEFAULT ''"),
        ('migration_requests', 'hosting_plan', "TEXT DEFAULT ''"),
        ('migration_requests', 'custom_domain', "TEXT DEFAULT ''"),
        ('faculty', 'is_detached', 'INTEGER DEFAULT 0'),
        ('faculty', 'detached_at', 'TIMESTAMP DEFAULT NULL'),
    ]
    for table, column, coltype in migration_columns:
        try:
            db.execute(f'ALTER TABLE {table} ADD COLUMN {column} {coltype}')
        except sqlite3.OperationalError:
            pass
    db.commit()

# =============================================================================
# Helper Functions
# =============================================================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_photo(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in PHOTO_EXTENSIONS

def save_upload(file, subfolder):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_name = f"{secrets.token_hex(8)}_{filename}"
        path = os.path.join(app.config['UPLOAD_FOLDER'], subfolder, unique_name)
        file.save(path)
        return unique_name
    return None

def log_activity(action, details='', user_type='guest', user_id=0):
    try:
        pdb = get_platform_db()
        pdb.execute(
            'INSERT INTO activity_logs (user_type, user_id, action, details, ip_address) VALUES (?, ?, ?, ?, ?)',
            (user_type, user_id, action, details, request.remote_addr or '')
        )
        pdb.commit()
    except Exception:
        pass

def detect_threat(action, details=''):
    threat_patterns = [
        (r'(<script|javascript:|on\w+\s*=)', 'XSS attempt', 'high'),
        (r'(union\s+select|drop\s+table|;\s*delete)', 'SQL injection attempt', 'critical'),
        (r'(\.\./|\.\.\\)', 'Path traversal attempt', 'medium'),
        (r'(brute.?force|login.*fail.*5)', 'Brute force detection', 'high'),
    ]
    for pattern, ttype, severity in threat_patterns:
        if re.search(pattern, f"{action} {details}", re.IGNORECASE):
            try:
                pdb = get_platform_db()
                pdb.execute(
                    'INSERT INTO threats (threat_type, description, ip_address, severity) VALUES (?, ?, ?, ?)',
                    (ttype, f"{action}: {details}", request.remote_addr or '', severity)
                )
                pdb.commit()
            except Exception:
                pass
            return True
    return False

def get_faculty_by_id(fid):
    # Always read from platform database for auth checks
    pdb = get_platform_db()
    return pdb.execute('SELECT * FROM faculty WHERE id = ?', (fid,)).fetchone()

def get_faculty_by_username(username):
    # Always check the platform database first
    pdb = get_platform_db()
    faculty = pdb.execute('SELECT * FROM faculty WHERE username = ?', (username,)).fetchone()
    return faculty

def create_independent_db(fid):
    """Create an independent database for a detached faculty member.
    Copies all their data and schema from the platform database."""
    platform_db = get_platform_db()
    ind_db_path = os.path.join(app.root_path, f'faculty_{fid}.db')

    # Remove old independent db if it exists
    if os.path.exists(ind_db_path):
        try:
            os.remove(ind_db_path)
        except PermissionError:
            # File is locked (OneDrive sync, etc). Drop all tables and recreate.
            ind_db = sqlite3.connect(ind_db_path, timeout=15)
            ind_db.row_factory = sqlite3.Row
            tables = ind_db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            for t in tables:
                if t['name'] != 'sqlite_sequence':
                    ind_db.execute(f'DROP TABLE IF EXISTS [{t["name"]}]')
            ind_db.commit()
            ind_db.close()

    ind_db = sqlite3.connect(ind_db_path, timeout=15)
    ind_db.row_factory = sqlite3.Row
    ind_db.execute('PRAGMA foreign_keys = ON')
    try:
        ind_db.execute('PRAGMA journal_mode = WAL')
    except Exception:
        pass

    # Create all tables (same schema minus platform_admins, threats)
    ind_db.executescript('''
        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            designation TEXT DEFAULT '',
            department TEXT DEFAULT '',
            institution TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            office_location TEXT DEFAULT '',
            office_hours TEXT DEFAULT '',
            visiting_hours TEXT DEFAULT '',
            address TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            photo TEXT DEFAULT '',
            resume_file TEXT DEFAULT '',
            website TEXT DEFAULT '',
            google_scholar TEXT DEFAULT '',
            linkedin TEXT DEFAULT '',
            is_detached INTEGER DEFAULT 1,
            detached_at TIMESTAMP DEFAULT NULL,
            github TEXT DEFAULT '',
            research_summary TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS qualifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            degree TEXT NOT NULL,
            specialization TEXT DEFAULT '',
            university TEXT DEFAULT '',
            year_of_passing TEXT DEFAULT '',
            certificate_photo TEXT DEFAULT '',
            is_published INTEGER DEFAULT 1,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS research_interests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            is_published INTEGER DEFAULT 1,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT DEFAULT 'award',
            year TEXT DEFAULT '',
            certificate_photo TEXT DEFAULT '',
            is_published INTEGER DEFAULT 1,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS publications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            authors TEXT DEFAULT '',
            journal TEXT DEFAULT '',
            year TEXT DEFAULT '',
            doi TEXT DEFAULT '',
            url TEXT DEFAULT '',
            abstract TEXT DEFAULT '',
            pub_type TEXT DEFAULT 'journal',
            is_published INTEGER DEFAULT 1,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            code TEXT DEFAULT '',
            description TEXT DEFAULT '',
            semester TEXT DEFAULT '',
            schedule TEXT DEFAULT '',
            is_published INTEGER DEFAULT 1,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS course_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            faculty_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT DEFAULT '',
            description TEXT DEFAULT '',
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            program TEXT DEFAULT '',
            research_topic TEXT DEFAULT '',
            status TEXT DEFAULT 'ongoing',
            start_year TEXT DEFAULT '',
            email TEXT DEFAULT '',
            is_published INTEGER DEFAULT 1,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            funding_agency TEXT DEFAULT '',
            amount TEXT DEFAULT '',
            status TEXT DEFAULT 'ongoing',
            start_year TEXT DEFAULT '',
            end_year TEXT DEFAULT '',
            is_published INTEGER DEFAULT 1,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            is_important INTEGER DEFAULT 0,
            is_published INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            sender_name TEXT NOT NULL,
            sender_email TEXT NOT NULL,
            subject TEXT DEFAULT '',
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            resource_type TEXT DEFAULT 'pdf',
            file_path TEXT NOT NULL,
            url TEXT DEFAULT '',
            is_published INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_type TEXT DEFAULT 'guest',
            user_id INTEGER DEFAULT 0,
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            ip_address TEXT DEFAULT '',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # Disable foreign keys during copy to avoid constraint issues
    ind_db.execute('PRAGMA foreign_keys = OFF')

    # Copy faculty record (preserving original id)
    faculty = platform_db.execute('SELECT * FROM faculty WHERE id = ?', (fid,)).fetchone()
    if faculty:
        ind_db.execute('INSERT INTO faculty (id, email, password_hash, full_name, username, designation, department, institution, phone, office_location, office_hours, visiting_hours, address, bio, photo, resume_file, website, google_scholar, linkedin, is_detached, detached_at, github, research_summary, is_active, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (fid, faculty['email'], faculty['password_hash'], faculty['full_name'], faculty['username'],
             faculty['designation'], faculty['department'], faculty['institution'], faculty['phone'],
             faculty['office_location'], faculty['office_hours'], faculty['visiting_hours'],
             faculty['address'], faculty['bio'], faculty['photo'], faculty['resume_file'],
             faculty['website'], faculty['google_scholar'], faculty['linkedin'],
             1, faculty['detached_at'], faculty['github'], faculty['research_summary'],
             faculty['is_active'], faculty['created_at']))

    # Copy all related data with original IDs preserved
    tables_with_fk = [
        'qualifications', 'research_interests', 'achievements', 'publications',
        'courses', 'students', 'projects', 'announcements', 'messages', 'resources'
    ]
    for table in tables_with_fk:
        rows = platform_db.execute(f'SELECT * FROM {table} WHERE faculty_id = ?', (fid,)).fetchall()
        for row in rows:
            all_cols = list(row.keys())
            placeholders = ', '.join(['?'] * len(all_cols))
            col_names = ', '.join(all_cols)
            vals = [row[c] for c in all_cols]
            ind_db.execute(f'INSERT INTO {table} ({col_names}) VALUES ({placeholders})', vals)

    # Copy course materials (course_id references courses.id)
    rows = platform_db.execute('SELECT * FROM course_materials WHERE faculty_id = ?', (fid,)).fetchall()
    for row in rows:
        all_cols = list(row.keys())
        placeholders = ', '.join(['?'] * len(all_cols))
        col_names = ', '.join(all_cols)
        vals = [row[c] for c in all_cols]
        ind_db.execute(f'INSERT INTO course_materials ({col_names}) VALUES ({placeholders})', vals)

    # Copy activity logs for this faculty
    logs = platform_db.execute('SELECT * FROM activity_logs WHERE user_id = ? AND user_type = ?', (fid, 'faculty')).fetchall()
    for log in logs:
        all_cols = list(log.keys())
        placeholders = ', '.join(['?'] * len(all_cols))
        col_names = ', '.join(all_cols)
        vals = [log[c] for c in all_cols]
        ind_db.execute(f'INSERT INTO activity_logs ({col_names}) VALUES ({placeholders})', vals)

    # Re-enable foreign keys
    ind_db.execute('PRAGMA foreign_keys = ON')

    ind_db.commit()
    ind_db.close()
    return ind_db_path

# =============================================================================
# Authentication Decorators
# =============================================================================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'faculty_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('platform_login'))
        return f(*args, **kwargs)
    return decorated

def fresh_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'faculty_id' not in session:
            flash('Please log in.', 'warning')
            return redirect(url_for('login'))
        faculty = get_faculty_by_id(session['faculty_id'])
        if not faculty or not faculty['is_active']:
            session.clear()
            flash('Account not found or deactivated.', 'danger')
            return redirect(url_for('login'))
        g.faculty = faculty
        return f(*args, **kwargs)
    return decorated

# =============================================================================
# Public Routes - Platform Homepage
# =============================================================================

@app.route('/')
def index():
    pdb = get_platform_db()
    faculty_list = pdb.execute(
        'SELECT id, full_name, designation, department, institution, photo, username, bio '
        'FROM faculty WHERE is_active = 1 ORDER BY full_name'
    ).fetchall()
    log_activity('page_view', 'Homepage')
    return render_template('index.html', faculty_list=faculty_list)

@app.route('/faculty/<username>')
def public_profile(username):
    # Public profile always reads from the platform database (archived snapshot)
    pdb = get_platform_db()
    faculty = pdb.execute(
        'SELECT * FROM faculty WHERE username = ? AND is_active = 1', (username,)
    ).fetchone()
    if not faculty:
        abort(404)

    fid = faculty['id']
    qualifications = pdb.execute(
        'SELECT * FROM qualifications WHERE faculty_id = ? AND is_published = 1 ORDER BY year_of_passing DESC', (fid,)
    ).fetchall()
    research = pdb.execute(
        'SELECT * FROM research_interests WHERE faculty_id = ? AND is_published = 1', (fid,)
    ).fetchall()
    achievements = pdb.execute(
        'SELECT * FROM achievements WHERE faculty_id = ? AND is_published = 1 ORDER BY year DESC', (fid,)
    ).fetchall()
    publications = pdb.execute(
        'SELECT * FROM publications WHERE faculty_id = ? AND is_published = 1 ORDER BY year DESC', (fid,)
    ).fetchall()
    courses = pdb.execute(
        'SELECT * FROM courses WHERE faculty_id = ? AND is_published = 1', (fid,)
    ).fetchall()
    materials = pdb.execute(
        'SELECT cm.*, c.name as course_name FROM course_materials cm '
        'JOIN courses c ON cm.course_id = c.id '
        'WHERE cm.faculty_id = ? AND c.is_published = 1 '
        'ORDER BY cm.uploaded_at DESC', (fid,)
    ).fetchall()
    students = pdb.execute(
        'SELECT * FROM students WHERE faculty_id = ? AND is_published = 1 ORDER BY name', (fid,)
    ).fetchall()
    projects = pdb.execute(
        'SELECT * FROM projects WHERE faculty_id = ? AND is_published = 1 ORDER BY start_year DESC', (fid,)
    ).fetchall()
    announcements = pdb.execute(
        'SELECT * FROM announcements WHERE faculty_id = ? AND is_published = 1 ORDER BY is_important DESC, created_at DESC', (fid,)
    ).fetchall()
    try:
        all_resources = pdb.execute(
            'SELECT * FROM resources WHERE faculty_id = ? AND is_published = 1 ORDER BY created_at DESC', (fid,)
        ).fetchall()
    except Exception:
        all_resources = []
    video_resources = [r for r in all_resources if r['resource_type'] == 'video']
    file_resources = [r for r in all_resources if r['resource_type'] != 'video']

    log_activity('profile_view', f"Viewed {username}'s profile", 'guest')

    return render_template('public_profile.html',
        faculty=faculty,
        qualifications=qualifications,
        research=research,
        achievements=achievements,
        publications=publications,
        courses=courses,
        materials=materials,
        video_resources=video_resources,
        file_resources=file_resources,
        students=students,
        projects=projects,
        announcements=announcements
    )

@app.route('/faculty/<username>/course/<int:course_id>')
def course_detail(username, course_id):
    pdb = get_platform_db()
    faculty = pdb.execute(
        'SELECT * FROM faculty WHERE username = ? AND is_active = 1', (username,)
    ).fetchone()
    if not faculty:
        abort(404)
    course = pdb.execute(
        'SELECT * FROM courses WHERE id = ? AND faculty_id = ? AND is_published = 1',
        (course_id, faculty['id'])
    ).fetchone()
    if not course:
        abort(404)
    materials = pdb.execute(
        'SELECT * FROM course_materials WHERE course_id = ? ORDER BY uploaded_at DESC', (course_id,)
    ).fetchall()
    return render_template('course_detail.html',
        faculty=faculty, course=course, materials=materials
    )

@app.route('/faculty/<username>/academic')
def public_academic(username):
    pdb = get_platform_db()
    faculty = pdb.execute(
        'SELECT * FROM faculty WHERE username = ? AND is_active = 1', (username,)
    ).fetchone()
    if not faculty:
        abort(404)
    fid = faculty['id']
    qualifications = pdb.execute(
        'SELECT * FROM qualifications WHERE faculty_id = ? AND is_published = 1 ORDER BY year_of_passing DESC', (fid,)
    ).fetchall()
    research = pdb.execute(
        'SELECT * FROM research_interests WHERE faculty_id = ? AND is_published = 1', (fid,)
    ).fetchall()
    achievements = pdb.execute(
        'SELECT * FROM achievements WHERE faculty_id = ? AND is_published = 1 ORDER BY year DESC', (fid,)
    ).fetchall()
    students = pdb.execute(
        'SELECT * FROM students WHERE faculty_id = ? AND is_published = 1 ORDER BY name', (fid,)
    ).fetchall()
    projects = pdb.execute(
        'SELECT * FROM projects WHERE faculty_id = ? AND is_published = 1 ORDER BY start_year DESC', (fid,)
    ).fetchall()
    log_activity('profile_view', f"Viewed {username}'s academic profile", 'guest')
    return render_template('public_academic.html',
        faculty=faculty, qualifications=qualifications, research=research,
        achievements=achievements, students=students, projects=projects)

@app.route('/faculty/<username>/publications')
def public_publications(username):
    pdb = get_platform_db()
    faculty = pdb.execute(
        'SELECT * FROM faculty WHERE username = ? AND is_active = 1', (username,)
    ).fetchone()
    if not faculty:
        abort(404)
    fid = faculty['id']
    publications = pdb.execute(
        'SELECT * FROM publications WHERE faculty_id = ? AND is_published = 1 ORDER BY year DESC', (fid,)
    ).fetchall()
    log_activity('profile_view', f"Viewed {username}'s publications", 'guest')
    return render_template('public_publications.html',
        faculty=faculty, publications=publications)

@app.route('/faculty/<username>/contact', methods=['POST'])
def send_message(username):
    pdb = get_platform_db()
    faculty = pdb.execute(
        'SELECT id FROM faculty WHERE username = ? AND is_active = 1', (username,)
    ).fetchone()
    if not faculty:
        abort(404)

    sender_name = request.form.get('name', '').strip()
    sender_email = request.form.get('email', '').strip()
    subject = request.form.get('subject', '').strip()
    message = request.form.get('message', '').strip()

    if not all([sender_name, sender_email, message]):
        flash('Name, email, and message are required.', 'danger')
        return redirect(url_for('public_profile', username=username))

    if detect_threat('contact_form', message):
        flash('Your message could not be sent.', 'danger')
        return redirect(url_for('public_profile', username=username))

    pdb.execute(
        'INSERT INTO messages (faculty_id, sender_name, sender_email, subject, message) VALUES (?, ?, ?, ?, ?)',
        (faculty['id'], sender_name, sender_email, subject, message)
    )
    pdb.commit()

    # Also write to the faculty's independent DB if they are detached,
    # so messages appear in their dashboard.
    fid = faculty['id']
    is_detached = pdb.execute('SELECT is_detached FROM faculty WHERE id = ?', (fid,)).fetchone()
    if is_detached and is_detached['is_detached']:
        ind_path = os.path.join(app.root_path, f'faculty_{fid}.db')
        if os.path.exists(ind_path):
            try:
                ind_db = sqlite3.connect(ind_path, timeout=15)
                ind_db.execute(
                    'INSERT INTO messages (faculty_id, sender_name, sender_email, subject, message) VALUES (?, ?, ?, ?, ?)',
                    (fid, sender_name, sender_email, subject, message)
                )
                ind_db.commit()
                ind_db.close()
            except Exception:
                pass

    log_activity('message_sent', f"Message to {username} from {sender_email}")
    flash('Message sent successfully!', 'success')
    return redirect(url_for('public_profile', username=username, _anchor='contact'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# =============================================================================
# Faculty Authentication
# =============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', '') == 'on'

        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('login.html')

        if detect_threat('login_attempt', f"user={username}"):
            flash('Login temporarily blocked due to suspicious activity.', 'danger')
            return render_template('login.html')

        faculty = get_faculty_by_username(username)
        if faculty and check_password_hash(faculty['password_hash'], password):
            if not faculty['is_active']:
                flash('Your account has been deactivated. Contact the platform administrator.', 'danger')
                log_activity('login_deactivated', f"Attempted login to deactivated account: {username}", 'faculty', faculty['id'])
                return render_template('login.html')

            session.permanent = remember
            session['faculty_id'] = faculty['id']
            session['faculty_name'] = faculty['full_name']
            session['faculty_role'] = 'faculty'
            log_activity('login', f"Faculty logged in: {faculty['full_name']}", 'faculty', faculty['id'])
            flash(f'Welcome back, {faculty["full_name"]}!', 'success')
            return redirect(url_for('faculty_dashboard'))
        else:
            log_activity('login_failed', f"Failed login attempt for: {username}")
            detect_threat('login_failed', f"user={username}")
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '').strip().lower()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        errors = []
        if not email or '@' not in email:
            errors.append('A valid email address is required.')
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters.')
        if not full_name:
            errors.append('Full name is required.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm:
            errors.append('Passwords do not match.')
        if username and not re.match(r'^[a-z0-9_]+$', username):
            errors.append('Username can only contain lowercase letters, numbers, and underscores.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('register.html')

        db = get_db()
        if db.execute('SELECT id FROM faculty WHERE email = ?', (email,)).fetchone():
            flash('An account with this email already exists.', 'danger')
            return render_template('register.html')
        if db.execute('SELECT id FROM faculty WHERE username = ?', (username,)).fetchone():
            flash('This username is already taken.', 'danger')
            return render_template('register.html')

        db.execute(
            'INSERT INTO faculty (email, password_hash, full_name, username) VALUES (?, ?, ?, ?)',
            (email, generate_password_hash(password), full_name, username)
        )
        db.commit()
        log_activity('registration', f"New faculty registered: {full_name} ({email})", 'faculty')

        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    if 'faculty_id' in session:
        log_activity('logout', f"Faculty logged out: {session.get('faculty_name', '')}", 'faculty', session.get('faculty_id', 0))
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# =============================================================================
# Faculty Dashboard - Profile Management
# =============================================================================

@app.route('/dashboard/handover')
@fresh_login_required
def handover():
    """Handover confirmation page shown after migration approval."""
    faculty = g.faculty
    if not faculty['is_detached']:
        flash('Your migration has not been approved yet.', 'warning')
        return redirect(url_for('faculty_dashboard'))
    db = get_db()
    fid = faculty['id']
    stats = {
        'qualifications': db.execute('SELECT COUNT(*) c FROM qualifications WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'publications': db.execute('SELECT COUNT(*) c FROM publications WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'courses': db.execute('SELECT COUNT(*) c FROM courses WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'achievements': db.execute('SELECT COUNT(*) c FROM achievements WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'students': db.execute('SELECT COUNT(*) c FROM students WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'projects': db.execute('SELECT COUNT(*) c FROM projects WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'announcements': db.execute('SELECT COUNT(*) c FROM announcements WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'messages': db.execute('SELECT COUNT(*) c FROM messages WHERE faculty_id=?', (fid,)).fetchone()['c'],
    }
    total_records = sum(stats.values())
    pdb = get_platform_db()
    migration = pdb.execute(
        'SELECT reviewed_at FROM migration_requests WHERE faculty_id = ? AND status = "approved" ORDER BY reviewed_at DESC LIMIT 1',
        (fid,)
    ).fetchone()
    approved_date = migration['reviewed_at'][:10] if migration and migration['reviewed_at'] else 'N/A'
    return render_template('faculty/handover.html',
        faculty_id=fid, username=faculty['username'],
        total_records=total_records, approved_date=approved_date
    )

@app.route('/dashboard')
@fresh_login_required
def faculty_dashboard():
    faculty = g.faculty
    # If just detached, show handover page first
    if faculty['is_detached'] and not session.get('handover_seen_' + str(faculty['id'])):
        session['handover_seen_' + str(faculty['id'])] = True
        return redirect(url_for('handover'))
    db = get_db()
    fid = faculty['id']

    stats = {
        'qualifications': db.execute('SELECT COUNT(*) c FROM qualifications WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'publications': db.execute('SELECT COUNT(*) c FROM publications WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'courses': db.execute('SELECT COUNT(*) c FROM courses WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'achievements': db.execute('SELECT COUNT(*) c FROM achievements WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'research': db.execute('SELECT COUNT(*) c FROM research_interests WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'students': db.execute('SELECT COUNT(*) c FROM students WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'projects': db.execute('SELECT COUNT(*) c FROM projects WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'messages': db.execute('SELECT COUNT(*) c FROM messages WHERE faculty_id=? AND is_read=0', (fid,)).fetchone()['c'],
        'announcements': db.execute('SELECT COUNT(*) c FROM announcements WHERE faculty_id=?', (fid,)).fetchone()['c'],
    }
    recent_messages = list(db.execute(
        'SELECT * FROM messages WHERE faculty_id=? ORDER BY created_at DESC LIMIT 5', (fid,)
    ).fetchall())

    # If detached, also pull recent messages from platform DB
    if is_independent_db():
        try:
            pdb = get_platform_db()
            platform_recent = pdb.execute(
                'SELECT * FROM messages WHERE faculty_id=? ORDER BY created_at DESC LIMIT 5', (fid,)
            ).fetchall()
            seen_ids = {m['id'] for m in recent_messages}
            for pm in platform_recent:
                if pm['id'] not in seen_ids:
                    recent_messages.append(pm)
            recent_messages.sort(key=lambda m: m['created_at'] or '', reverse=True)
            recent_messages = recent_messages[:5]
            # Update unread count to include platform DB
            if not is_independent_db():
                pass
            else:
                pdb_unread = pdb.execute('SELECT COUNT(*) c FROM messages WHERE faculty_id=? AND is_read=0', (fid,)).fetchone()['c']
                ind_unread = stats['messages']
                stats['messages'] = max(pdb_unread, ind_unread)
        except Exception:
            pass

    return render_template('faculty/dashboard.html', faculty=faculty, stats=stats, messages=recent_messages)

@app.route('/dashboard/profile', methods=['GET', 'POST'])
@fresh_login_required
def edit_profile():
    db = get_db()
    faculty = g.faculty

    if request.method == 'POST':
        fields = [
            'full_name', 'designation', 'department', 'institution',
            'phone', 'office_location', 'office_hours', 'visiting_hours',
            'address', 'bio', 'website', 'google_scholar', 'linkedin',
            'github', 'research_summary'
        ]
        updates = {f: request.form.get(f, '').strip() for f in fields}

        # Handle photo upload
        if 'remove_photo' in request.form and request.form['remove_photo'] == '1':
            if faculty['photo']:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], 'photos', faculty['photo'])
                if os.path.exists(old_path):
                    os.remove(old_path)
                updates['photo'] = ''
                log_activity('content_delete', 'Removed profile photo', 'faculty', faculty['id'])
        elif 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename and allowed_file(photo.filename):
                if is_photo(photo.filename):
                    # Delete old photo
                    if faculty['photo']:
                        old_path = os.path.join(app.config['UPLOAD_FOLDER'], 'photos', faculty['photo'])
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    saved = save_upload(photo, 'photos')
                    if saved:
                        updates['photo'] = saved

        # Handle resume upload
        if 'remove_resume' in request.form and request.form['remove_resume'] == '1':
            if faculty['resume_file']:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], 'resumes', faculty['resume_file'])
                if os.path.exists(old_path):
                    os.remove(old_path)
                updates['resume_file'] = ''
                log_activity('content_delete', 'Removed resume/CV file', 'faculty', faculty['id'])
        elif 'resume_file' in request.files:
            resume = request.files['resume_file']
            if resume.filename and allowed_file(resume.filename):
                if faculty['resume_file']:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], 'resumes', faculty['resume_file'])
                    if os.path.exists(old_path):
                        os.remove(old_path)
                saved = save_upload(resume, 'resumes')
                if saved:
                    updates['resume_file'] = saved

        # Log specific upload actions
        if 'photo' in request.files and request.files['photo'].filename:
            log_activity('content_add', 'Updated profile photo', 'faculty', faculty['id'])
        if 'resume_file' in request.files and request.files['resume_file'].filename:
            log_activity('content_add', 'Updated resume/CV file', 'faculty', faculty['id'])

        set_clause = ', '.join(f'{k} = ?' for k in updates.keys())
        values = list(updates.values()) + [faculty['id']]
        db.execute(f'UPDATE faculty SET {set_clause} WHERE id = ?', values)
        db.commit()
        log_activity('profile_update', 'Profile updated', 'faculty', faculty['id'])
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('faculty_dashboard'))

    return render_template('faculty/edit_profile.html', faculty=faculty)

@app.route('/dashboard/password', methods=['GET', 'POST'])
@fresh_login_required
def change_password():
    if request.method == 'POST':
        current = request.form.get('current_password', '')
        new_pass = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')

        if not check_password_hash(g.faculty['password_hash'], current):
            flash('Current password is incorrect.', 'danger')
            return render_template('faculty/change_password.html')

        if len(new_pass) < 6:
            flash('New password must be at least 6 characters.', 'danger')
            return render_template('faculty/change_password.html')

        if new_pass != confirm:
            flash('New passwords do not match.', 'danger')
            return render_template('faculty/change_password.html')

        db = get_db()
        db.execute(
            'UPDATE faculty SET password_hash = ? WHERE id = ?',
            (generate_password_hash(new_pass), g.faculty['id'])
        )
        db.commit()
        log_activity('password_change', 'Password changed by faculty', 'faculty', g.faculty['id'])
        flash('Password changed successfully.', 'success')
        return redirect(url_for('faculty_dashboard'))

    return render_template('faculty/change_password.html')

@app.route('/dashboard/reset-password', methods=['POST'])
@fresh_login_required
def self_reset_password():
    faculty = g.faculty
    new_pass = secrets.token_hex(8)
    db = get_db()
    db.execute(
        'UPDATE faculty SET password_hash = ? WHERE id = ?',
        (generate_password_hash(new_pass), faculty['id'])
    )
    db.commit()
    log_activity('password_change', 'Password self-reset by faculty', 'faculty', faculty['id'])
    flash(f'Your password has been reset. New password: {new_pass}. Save this somewhere safe.', 'success')
    return redirect(url_for('faculty_dashboard'))

@app.route('/dashboard/academic')
@fresh_login_required
def academic_details():
    """Dedicated page for all academic details (research, qualifications, achievements, publications, students, projects)."""
    db = get_db()
    fid = g.faculty['id']
    qualifications = db.execute('SELECT * FROM qualifications WHERE faculty_id=? ORDER BY year_of_passing DESC', (fid,)).fetchall()
    research = db.execute('SELECT * FROM research_interests WHERE faculty_id=?', (fid,)).fetchall()
    achievements = db.execute('SELECT * FROM achievements WHERE faculty_id=? ORDER BY year DESC', (fid,)).fetchall()
    publications = db.execute('SELECT * FROM publications WHERE faculty_id=? ORDER BY year DESC', (fid,)).fetchall()
    students = db.execute('SELECT * FROM students WHERE faculty_id=? ORDER BY name', (fid,)).fetchall()
    projects = db.execute('SELECT * FROM projects WHERE faculty_id=? ORDER BY start_year DESC', (fid,)).fetchall()
    return render_template('faculty/academic_details.html',
        faculty=g.faculty, qualifications=qualifications, research=research,
        achievements=achievements, publications=publications, students=students, projects=projects)

# =============================================================================
# Faculty Dashboard - Content Management
# =============================================================================

@app.route('/dashboard/qualifications', methods=['GET', 'POST'])
@fresh_login_required
def manage_qualifications():
    db = get_db()
    fid = g.faculty['id']

    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'add':
            cert_photo = None
            if 'certificate_photo' in request.files:
                f = request.files['certificate_photo']
                if f.filename and allowed_file(f.filename) and is_photo(f.filename):
                    cert_photo = save_upload(f, 'certificates')
            db.execute(
                'INSERT INTO qualifications (faculty_id, degree, specialization, university, year_of_passing, certificate_photo) VALUES (?, ?, ?, ?, ?, ?)',
                (fid, request.form.get('degree', ''), request.form.get('specialization', ''),
                 request.form.get('university', ''), request.form.get('year_of_passing', ''),
                 cert_photo or '')
            )
            db.commit()
            log_activity('content_add', 'Added qualification: ' + request.form.get('degree', ''), 'faculty', fid)
            flash('Qualification added.', 'success')
        elif action == 'delete':
            qid = request.form.get('id')
            if qid:
                q = db.execute('SELECT certificate_photo FROM qualifications WHERE id=? AND faculty_id=?', (qid, fid)).fetchone()
                if q and q['certificate_photo']:
                    p = os.path.join(app.config['UPLOAD_FOLDER'], 'certificates', q['certificate_photo'])
                    if os.path.exists(p):
                        os.remove(p)
                db.execute('DELETE FROM qualifications WHERE id=? AND faculty_id=?', (qid, fid))
                db.commit()
                log_activity('content_delete', 'Deleted qualification', 'faculty', fid)
                flash('Qualification deleted.', 'info')
        elif action == 'toggle':
            qid = request.form.get('id')
            if qid:
                db.execute('UPDATE qualifications SET is_published = 1 - is_published WHERE id=? AND faculty_id=?', (qid, fid))
                db.commit()
                log_activity('content_toggle', 'Toggled qualification visibility', 'faculty', fid)
                flash('Visibility updated.', 'info')

    quals = db.execute('SELECT * FROM qualifications WHERE faculty_id=? ORDER BY year_of_passing DESC', (fid,)).fetchall()
    return render_template('faculty/manage_qualifications.html', faculty=g.faculty, qualifications=quals)

@app.route('/dashboard/research', methods=['GET', 'POST'])
@fresh_login_required
def manage_research():
    db = get_db()
    fid = g.faculty['id']

    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'add':
            db.execute(
                'INSERT INTO research_interests (faculty_id, title, description) VALUES (?, ?, ?)',
                (fid, request.form.get('title', ''), request.form.get('description', ''))
            )
            db.commit()
            log_activity('content_add', 'Added research interest: ' + request.form.get('title', ''), 'faculty', fid)
            flash('Research interest added.', 'success')
        elif action == 'delete':
            rid = request.form.get('id')
            if rid:
                db.execute('DELETE FROM research_interests WHERE id=? AND faculty_id=?', (rid, fid))
                db.commit()
                log_activity('content_delete', 'Deleted research interest', 'faculty', fid)
                flash('Research interest deleted.', 'info')
        elif action == 'toggle':
            rid = request.form.get('id')
            if rid:
                db.execute('UPDATE research_interests SET is_published = 1 - is_published WHERE id=? AND faculty_id=?', (rid, fid))
                db.commit()
                log_activity('content_toggle', 'Toggled research interest visibility', 'faculty', fid)
                flash('Visibility updated.', 'info')

    items = db.execute('SELECT * FROM research_interests WHERE faculty_id=?', (fid,)).fetchall()
    return render_template('faculty/manage_research.html', faculty=g.faculty, items=items)

@app.route('/dashboard/achievements', methods=['GET', 'POST'])
@fresh_login_required
def manage_achievements():
    db = get_db()
    fid = g.faculty['id']

    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'add':
            cert_photo = None
            if 'certificate_photo' in request.files:
                f = request.files['certificate_photo']
                if f.filename and allowed_file(f.filename) and is_photo(f.filename):
                    cert_photo = save_upload(f, 'certificates')
            db.execute(
                'INSERT INTO achievements (faculty_id, title, description, category, year, certificate_photo) VALUES (?, ?, ?, ?, ?, ?)',
                (fid, request.form.get('title', ''), request.form.get('description', ''),
                 request.form.get('category', 'award'), request.form.get('year', ''),
                 cert_photo or '')
            )
            db.commit()
            log_activity('content_add', 'Added achievement: ' + request.form.get('title', ''), 'faculty', fid)
            flash('Achievement added.', 'success')
        elif action == 'delete':
            aid = request.form.get('id')
            if aid:
                a = db.execute('SELECT certificate_photo FROM achievements WHERE id=? AND faculty_id=?', (aid, fid)).fetchone()
                if a and a['certificate_photo']:
                    p = os.path.join(app.config['UPLOAD_FOLDER'], 'certificates', a['certificate_photo'])
                    if os.path.exists(p):
                        os.remove(p)
                db.execute('DELETE FROM achievements WHERE id=? AND faculty_id=?', (aid, fid))
                db.commit()
                log_activity('content_delete', 'Deleted achievement', 'faculty', fid)
                flash('Achievement deleted.', 'info')
        elif action == 'toggle':
            aid = request.form.get('id')
            if aid:
                db.execute('UPDATE achievements SET is_published = 1 - is_published WHERE id=? AND faculty_id=?', (aid, fid))
                db.commit()
                log_activity('content_toggle', 'Toggled achievement visibility', 'faculty', fid)
                flash('Visibility updated.', 'info')

    items = db.execute('SELECT * FROM achievements WHERE faculty_id=? ORDER BY year DESC', (fid,)).fetchall()
    return render_template('faculty/manage_achievements.html', faculty=g.faculty, items=items)

@app.route('/dashboard/publications', methods=['GET', 'POST'])
@fresh_login_required
def manage_publications():
    db = get_db()
    fid = g.faculty['id']

    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'add':
            db.execute(
                'INSERT INTO publications (faculty_id, title, authors, journal, year, doi, url, abstract, pub_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (fid, request.form.get('title', ''), request.form.get('authors', ''),
                 request.form.get('journal', ''), request.form.get('year', ''),
                 request.form.get('doi', ''), request.form.get('url', ''),
                 request.form.get('abstract', ''), request.form.get('pub_type', 'journal'))
            )
            db.commit()
            log_activity('content_add', 'Added publication: ' + request.form.get('title', ''), 'faculty', fid)
            flash('Publication added.', 'success')
        elif action == 'delete':
            pid = request.form.get('id')
            if pid:
                db.execute('DELETE FROM publications WHERE id=? AND faculty_id=?', (pid, fid))
                db.commit()
                log_activity('content_delete', 'Deleted publication', 'faculty', fid)
                flash('Publication deleted.', 'info')
        elif action == 'toggle':
            pid = request.form.get('id')
            if pid:
                db.execute('UPDATE publications SET is_published = 1 - is_published WHERE id=? AND faculty_id=?', (pid, fid))
                db.commit()
                log_activity('content_toggle', 'Toggled publication visibility', 'faculty', fid)
                flash('Visibility updated.', 'info')

    items = db.execute('SELECT * FROM publications WHERE faculty_id=? ORDER BY year DESC', (fid,)).fetchall()
    return render_template('faculty/manage_publications.html', faculty=g.faculty, items=items)

@app.route('/dashboard/courses', methods=['GET', 'POST'])
@fresh_login_required
def manage_courses():
    db = get_db()
    fid = g.faculty['id']

    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'add':
            db.execute(
                'INSERT INTO courses (faculty_id, name, code, description, semester, schedule) VALUES (?, ?, ?, ?, ?, ?)',
                (fid, request.form.get('name', ''), request.form.get('code', ''),
                 request.form.get('description', ''), request.form.get('semester', ''),
                 request.form.get('schedule', ''))
            )
            db.commit()
            log_activity('content_add', 'Added course: ' + request.form.get('name', ''), 'faculty', fid)
            flash('Course added.', 'success')
        elif action == 'delete':
            cid = request.form.get('id')
            if cid:
                # Delete associated materials
                mats = db.execute('SELECT file_path FROM course_materials WHERE course_id=?', (cid,)).fetchall()
                for m in mats:
                    if m['file_path']:
                        p = os.path.join(app.config['UPLOAD_FOLDER'], 'materials', m['file_path'])
                        if os.path.exists(p):
                            os.remove(p)
                db.execute('DELETE FROM courses WHERE id=? AND faculty_id=?', (cid, fid))
                db.commit()
                log_activity('content_delete', 'Deleted course', 'faculty', fid)
                flash('Course deleted.', 'info')
        elif action == 'toggle':
            cid = request.form.get('id')
            if cid:
                db.execute('UPDATE courses SET is_published = 1 - is_published WHERE id=? AND faculty_id=?', (cid, fid))
                db.commit()
                log_activity('content_toggle', 'Toggled course visibility', 'faculty', fid)
                flash('Visibility updated.', 'info')

    items = db.execute('SELECT * FROM courses WHERE faculty_id=?', (fid,)).fetchall()
    return render_template('faculty/manage_courses.html', faculty=g.faculty, items=items)

@app.route('/dashboard/materials/<int:course_id>', methods=['GET', 'POST'])
@fresh_login_required
def manage_materials(course_id):
    db = get_db()
    fid = g.faculty['id']

    course = db.execute('SELECT * FROM courses WHERE id=? AND faculty_id=?', (course_id, fid)).fetchone()
    if not course:
        abort(404)

    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'upload':
            if 'file' not in request.files:
                flash('No file selected.', 'danger')
                return redirect(url_for('manage_materials', course_id=course_id))
            file = request.files['file']
            if file.filename and allowed_file(file.filename):
                saved = save_upload(file, 'materials')
                if saved:
                    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                    db.execute(
                        'INSERT INTO course_materials (course_id, faculty_id, title, file_path, file_type, description) VALUES (?, ?, ?, ?, ?, ?)',
                        (course_id, fid, request.form.get('title', file.filename), saved, ext,
                         request.form.get('description', ''))
                    )
                    db.commit()
                    log_activity('content_add', 'Uploaded material: ' + request.form.get('title', ''), 'faculty', fid)
                    flash('Material uploaded.', 'success')
                else:
                    flash('Upload failed.', 'danger')
            else:
                flash('File type not allowed.', 'danger')
        elif action == 'delete':
            mid = request.form.get('id')
            if mid:
                m = db.execute('SELECT file_path FROM course_materials WHERE id=? AND faculty_id=?', (mid, fid)).fetchone()
                if m and m['file_path']:
                    p = os.path.join(app.config['UPLOAD_FOLDER'], 'materials', m['file_path'])
                    if os.path.exists(p):
                        os.remove(p)
                db.execute('DELETE FROM course_materials WHERE id=? AND faculty_id=?', (mid, fid))
                db.commit()
                log_activity('content_delete', 'Deleted course material', 'faculty', fid)
                flash('Material deleted.', 'info')

    materials = db.execute(
        'SELECT * FROM course_materials WHERE course_id=? AND faculty_id=? ORDER BY uploaded_at DESC',
        (course_id, fid)
    ).fetchall()
    return render_template('faculty/manage_materials.html', faculty=g.faculty, course=course, materials=materials)

@app.route('/dashboard/students', methods=['GET', 'POST'])
@fresh_login_required
def manage_students():
    db = get_db()
    fid = g.faculty['id']

    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'add':
            db.execute(
                'INSERT INTO students (faculty_id, name, program, research_topic, status, start_year, email) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (fid, request.form.get('name', ''), request.form.get('program', ''),
                 request.form.get('research_topic', ''), request.form.get('status', 'ongoing'),
                 request.form.get('start_year', ''), request.form.get('email', ''))
            )
            db.commit()
            log_activity('content_add', 'Added student: ' + request.form.get('name', ''), 'faculty', fid)
            flash('Student added.', 'success')
        elif action == 'delete':
            sid = request.form.get('id')
            if sid:
                db.execute('DELETE FROM students WHERE id=? AND faculty_id=?', (sid, fid))
                db.commit()
                log_activity('content_delete', 'Deleted student record', 'faculty', fid)
                flash('Student deleted.', 'info')
        elif action == 'toggle':
            sid = request.form.get('id')
            if sid:
                db.execute('UPDATE students SET is_published = 1 - is_published WHERE id=? AND faculty_id=?', (sid, fid))
                db.commit()
                log_activity('content_toggle', 'Toggled student visibility', 'faculty', fid)
                flash('Visibility updated.', 'info')

    items = db.execute('SELECT * FROM students WHERE faculty_id=? ORDER BY name', (fid,)).fetchall()
    return render_template('faculty/manage_students.html', faculty=g.faculty, items=items)

@app.route('/dashboard/projects', methods=['GET', 'POST'])
@fresh_login_required
def manage_projects():
    db = get_db()
    fid = g.faculty['id']

    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'add':
            db.execute(
                'INSERT INTO projects (faculty_id, title, description, funding_agency, amount, status, start_year, end_year) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (fid, request.form.get('title', ''), request.form.get('description', ''),
                 request.form.get('funding_agency', ''), request.form.get('amount', ''),
                 request.form.get('status', 'ongoing'), request.form.get('start_year', ''),
                 request.form.get('end_year', ''))
            )
            db.commit()
            log_activity('content_add', 'Added project: ' + request.form.get('title', ''), 'faculty', fid)
            flash('Project added.', 'success')
        elif action == 'delete':
            pid = request.form.get('id')
            if pid:
                db.execute('DELETE FROM projects WHERE id=? AND faculty_id=?', (pid, fid))
                db.commit()
                log_activity('content_delete', 'Deleted project', 'faculty', fid)
                flash('Project deleted.', 'info')
        elif action == 'toggle':
            pid = request.form.get('id')
            if pid:
                db.execute('UPDATE projects SET is_published = 1 - is_published WHERE id=? AND faculty_id=?', (pid, fid))
                db.commit()
                log_activity('content_toggle', 'Toggled project visibility', 'faculty', fid)
                flash('Visibility updated.', 'info')

    items = db.execute('SELECT * FROM projects WHERE faculty_id=? ORDER BY start_year DESC', (fid,)).fetchall()
    return render_template('faculty/manage_projects.html', faculty=g.faculty, items=items)

@app.route('/dashboard/announcements', methods=['GET', 'POST'])
@fresh_login_required
def manage_announcements():
    db = get_db()
    fid = g.faculty['id']

    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'add':
            db.execute(
                'INSERT INTO announcements (faculty_id, title, content, is_important) VALUES (?, ?, ?, ?)',
                (fid, request.form.get('title', ''), request.form.get('content', ''),
                 1 if request.form.get('is_important') else 0)
            )
            db.commit()
            log_activity('content_add', 'Added announcement: ' + request.form.get('title', ''), 'faculty', fid)
            flash('Announcement added.', 'success')
        elif action == 'delete':
            aid = request.form.get('id')
            if aid:
                db.execute('DELETE FROM announcements WHERE id=? AND faculty_id=?', (aid, fid))
                db.commit()
                log_activity('content_delete', 'Deleted announcement', 'faculty', fid)
                flash('Announcement deleted.', 'info')
        elif action == 'toggle':
            aid = request.form.get('id')
            if aid:
                db.execute('UPDATE announcements SET is_published = 1 - is_published WHERE id=? AND faculty_id=?', (aid, fid))
                db.commit()
                log_activity('content_toggle', 'Toggled announcement visibility', 'faculty', fid)
                flash('Visibility updated.', 'info')

    items = db.execute(
        'SELECT * FROM announcements WHERE faculty_id=? ORDER BY is_important DESC, created_at DESC', (fid,)
    ).fetchall()
    return render_template('faculty/manage_announcements.html', faculty=g.faculty, items=items)

@app.route('/dashboard/resources', methods=['GET', 'POST'])
@fresh_login_required
def manage_resources():
    db = get_db()
    fid = g.faculty['id']

    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'add':
            file_path = None
            resource_type = request.form.get('resource_type', 'pdf')
            if 'file' in request.files:
                f = request.files['file']
                if f.filename and allowed_file(f.filename):
                    file_path = save_upload(f, 'materials')
            url = request.form.get('url', '').strip()
            if not file_path and not url:
                flash('Please upload a file or provide a URL.', 'danger')
            else:
                db.execute(
                    'INSERT INTO resources (faculty_id, title, description, resource_type, file_path, url) VALUES (?, ?, ?, ?, ?, ?)',
                    (fid, request.form.get('title', ''), request.form.get('description', ''),
                     resource_type, file_path or '', url)
                )
                db.commit()
                log_activity('content_add', 'Added resource: ' + request.form.get('title', ''), 'faculty', fid)
                flash('Resource added.', 'success')
        elif action == 'delete':
            rid = request.form.get('id')
            if rid:
                r = db.execute('SELECT file_path FROM resources WHERE id=? AND faculty_id=?', (rid, fid)).fetchone()
                if r and r['file_path']:
                    p = os.path.join(app.config['UPLOAD_FOLDER'], 'materials', r['file_path'])
                    if os.path.exists(p):
                        os.remove(p)
                db.execute('DELETE FROM resources WHERE id=? AND faculty_id=?', (rid, fid))
                db.commit()
                log_activity('content_delete', 'Deleted resource', 'faculty', fid)
                flash('Resource deleted.', 'info')
        elif action == 'toggle':
            rid = request.form.get('id')
            if rid:
                db.execute('UPDATE resources SET is_published = 1 - is_published WHERE id=? AND faculty_id=?', (rid, fid))
                db.commit()
                log_activity('content_toggle', 'Toggled resource visibility', 'faculty', fid)
                flash('Visibility updated.', 'info')

    items = db.execute(
        'SELECT * FROM resources WHERE faculty_id=? ORDER BY created_at DESC', (fid,)
    ).fetchall()
    return render_template('faculty/manage_resources.html', faculty=g.faculty, items=items)

@app.route('/dashboard/verify-email', methods=['POST'])
@fresh_login_required
def send_verification_code():
    """Send a verification code to the faculty's email for migration."""
    pdb = get_platform_db()
    fid = g.faculty['id']
    email = request.form.get('target_email', '').strip().lower()

    if not email or '@' not in email:
        flash('Please enter a valid email address.', 'danger')
        return redirect(url_for('manage_database'))

    # Generate a 6-digit verification code
    code = f'{secrets.randbelow(900000) + 100000}'
    # Expires in 15 minutes
    expires = datetime.now() + timedelta(minutes=15)

    # Invalidate any old codes for this faculty
    pdb.execute(
        'UPDATE verification_codes SET is_used = 1 WHERE faculty_id = ? AND purpose = ? AND is_used = 0',
        (fid, 'migration')
    )

    # Store the new code
    pdb.execute(
        'INSERT INTO verification_codes (faculty_id, email, code, purpose, expires_at) VALUES (?, ?, ?, ?, ?)',
        (fid, email, code, 'migration', expires.isoformat())
    )
    pdb.commit()

    log_activity('email_verification_sent', f'Verification code sent to {email} for migration', 'faculty', fid)
    flash(f'Verification code sent to {email}. Check your inbox. The code is valid for 15 minutes. (Demo: your code is {code})', 'success')
    return redirect(url_for('manage_database'))

@app.route('/dashboard/database', methods=['GET', 'POST'])
@fresh_login_required
def manage_database():
    db = get_db()
    pdb = get_platform_db()
    faculty = g.faculty
    fid = faculty['id']
    if is_independent_db():
        db_path = os.path.join(app.root_path, f'faculty_{fid}.db')
    else:
        db_path = app.config['DATABASE']
    db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
    db_size_mb = round(db_size / (1024 * 1024), 2)

    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'export_sql':
            # Generate SQL dump for this faculty only
            # Merge data from both independent DB and platform DB for completeness
            tables = ['faculty', 'qualifications', 'research_interests', 'achievements',
                      'publications', 'courses', 'course_materials', 'students',
                      'projects', 'announcements', 'messages', 'resources']
            sql_lines = [f'-- FacultyConnect data export for {faculty["full_name"]}',
                         f'-- Exported: {datetime.now().isoformat()}', '']
            for table in tables:
                try:
                    # Collect rows from the active DB
                    collected_rows = {}  # id -> row to deduplicate
                    if table == 'faculty':
                        for source in [db, pdb]:
                            try:
                                row = source.execute('SELECT * FROM faculty WHERE id = ?', (fid,)).fetchone()
                                if row:
                                    collected_rows[fid] = row
                            except Exception:
                                pass
                    else:
                        for source in [db, pdb]:
                            try:
                                rows = source.execute(f'SELECT * FROM {table} WHERE faculty_id = ?', (fid,)).fetchall()
                                for row in rows:
                                    if row['id'] not in collected_rows:
                                        collected_rows[row['id']] = row
                            except Exception:
                                pass
                    for row in collected_rows.values():
                        cols = row.keys()
                        vals = [str(row[c]) if row[c] is not None else 'NULL' for c in cols]
                        sql_lines.append(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(repr(v) for v in vals)});")
                except Exception:
                    pass
            sql_content = '\n'.join(sql_lines)
            export_path = os.path.join(app.config['UPLOAD_FOLDER'], f'export_{fid}.sql')
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(sql_content)
            log_activity('data_export', f'Faculty exported their data as SQL', 'faculty', fid)
            return send_from_directory(app.config['UPLOAD_FOLDER'], f'export_{fid}.sql', as_attachment=True,
                                      download_name=f'{faculty["username"]}_export.sql')

        elif action == 'request_migration':
            existing = pdb.execute(
                'SELECT id FROM migration_requests WHERE faculty_id = ? AND status = ?', (fid, 'pending')
            ).fetchone()
            if existing:
                flash('You already have a pending migration request. Wait for admin review.', 'warning')
            else:
                reason = request.form.get('reason', '').strip()
                target_email = request.form.get('target_email', '').strip()
                hosting_provider = request.form.get('hosting_provider', '').strip()
                hosting_plan = request.form.get('hosting_plan', '').strip()
                custom_domain = request.form.get('custom_domain', '').strip()
                verification_code = request.form.get('verification_code', '').strip()

                if not target_email:
                    flash('Target email is required for migration.', 'danger')
                elif not verification_code:
                    flash('Please verify your email address first. Enter the verification code you received.', 'danger')
                else:
                    # Verify the code
                    now = datetime.now().isoformat()
                    code_record = pdb.execute(
                        'SELECT id FROM verification_codes WHERE faculty_id = ? AND email = ? AND code = ? AND purpose = ? AND is_used = 0 AND expires_at > ?',
                        (fid, target_email, verification_code, 'migration', now)
                    ).fetchone()
                    if not code_record:
                        flash('Invalid or expired verification code. Please request a new one.', 'danger')
                    else:
                        # Mark code as used
                        pdb.execute('UPDATE verification_codes SET is_used = 1 WHERE id = ?', (code_record['id'],))
                        pdb.execute(
                            'INSERT INTO migration_requests (faculty_id, reason, target_email, hosting_provider, hosting_plan, custom_domain) VALUES (?, ?, ?, ?, ?, ?)',
                            (fid, reason, target_email, hosting_provider, hosting_plan, custom_domain)
                        )
                        pdb.commit()
                        log_activity('migration_request', f'{faculty["full_name"]} requested database migration to {target_email} via {hosting_provider}', 'faculty', fid)
                        flash('Your migration request has been submitted and email verified. The platform admin will review your hosting details.', 'success')
            return redirect(url_for('manage_database'))

    # Get content counts
    stats = {
        'qualifications': db.execute('SELECT COUNT(*) c FROM qualifications WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'publications': db.execute('SELECT COUNT(*) c FROM publications WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'courses': db.execute('SELECT COUNT(*) c FROM courses WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'materials': db.execute('SELECT COUNT(*) c FROM course_materials WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'achievements': db.execute('SELECT COUNT(*) c FROM achievements WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'students': db.execute('SELECT COUNT(*) c FROM students WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'projects': db.execute('SELECT COUNT(*) c FROM projects WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'announcements': db.execute('SELECT COUNT(*) c FROM announcements WHERE faculty_id=?', (fid,)).fetchone()['c'],
        'messages': db.execute('SELECT COUNT(*) c FROM messages WHERE faculty_id=?', (fid,)).fetchone()['c'],
    }
    total_records = sum(stats.values())
    migration_request = pdb.execute(
        'SELECT * FROM migration_requests WHERE faculty_id = ? ORDER BY created_at DESC LIMIT 1', (fid,)
    ).fetchone()
    is_detached = faculty['is_detached'] if 'is_detached' in faculty.keys() else False
    return render_template('faculty/database.html', faculty=faculty, stats=stats, total_records=total_records,
                           db_size_mb=db_size_mb, migration_request=migration_request, is_detached=is_detached)

@app.route('/dashboard/messages')
@fresh_login_required
def view_messages():
    db = get_db()
    fid = g.faculty['id']
    mid = request.args.get('read')
    if mid:
        db.execute('UPDATE messages SET is_read = 1 WHERE id=? AND faculty_id=?', (mid, fid))
        db.commit()
        # Also mark as read in the platform DB
        try:
            pdb = get_platform_db()
            pdb.execute('UPDATE messages SET is_read = 1 WHERE id=? AND faculty_id=?', (mid, fid))
            pdb.commit()
        except Exception:
            pass

    messages = db.execute(
        'SELECT * FROM messages WHERE faculty_id=? ORDER BY is_read ASC, created_at DESC', (fid,)
    ).fetchall()

    # If detached, also fetch any messages only in the platform DB
    if is_independent_db():
        try:
            pdb = get_platform_db()
            ind_ids = {m['id'] for m in messages}
            platform_msgs = pdb.execute(
                'SELECT * FROM messages WHERE faculty_id=? ORDER BY is_read ASC, created_at DESC', (fid,)
            ).fetchall()
            for pm in platform_msgs:
                if pm['id'] not in ind_ids:
                    messages.append(pm)
            messages.sort(key=lambda m: (m['is_read'], m['created_at'] or ''), reverse=False)
        except Exception:
            pass

    return render_template('faculty/view_messages.html', faculty=g.faculty, messages=messages)

# =============================================================================
# Platform Admin - Monitoring Interface (Hidden from public)
# =============================================================================

@app.route('/platform/admin/login', methods=['GET', 'POST'])
def platform_login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        pdb = get_platform_db()
        admin = pdb.execute(
            'SELECT * FROM platform_admins WHERE username = ?', (username,)
        ).fetchone()

        if admin and check_password_hash(admin['password_hash'], password):
            session['admin_id'] = admin['id']
            session['admin_role'] = 'platform_admin'
            session['admin_username'] = username
            log_activity('admin_login', f"Platform admin logged in: {username}", 'platform_admin', admin['id'])
            session.pop('faculty_id', None)
            session.pop('faculty_name', None)
            session.pop('faculty_role', None)
            return redirect(url_for('platform_dashboard'))

        log_activity('admin_login_failed', f"Failed platform admin login: {username}")
        flash('Invalid credentials.', 'danger')

    return render_template('platform/login.html')

@app.route('/platform/admin')
@admin_required
def platform_dashboard():
    pdb = get_platform_db()
    stats = {
        'total_faculty': pdb.execute('SELECT COUNT(*) c FROM faculty').fetchone()['c'],
        'active_faculty': pdb.execute('SELECT COUNT(*) c FROM faculty WHERE is_active=1').fetchone()['c'],
        'inactive_faculty': pdb.execute('SELECT COUNT(*) c FROM faculty WHERE is_active=0').fetchone()['c'],
        'total_publications': pdb.execute('SELECT COUNT(*) c FROM publications').fetchone()['c'],
        'total_messages': pdb.execute('SELECT COUNT(*) c FROM messages').fetchone()['c'],
        'unresolved_threats': pdb.execute('SELECT COUNT(*) c FROM threats WHERE is_resolved=0').fetchone()['c'],
        'today_logins': pdb.execute(
            "SELECT COUNT(*) c FROM activity_logs WHERE action='login' AND date(timestamp)=date('now')"
        ).fetchone()['c'],
        'pending_migrations': pdb.execute(
            "SELECT COUNT(*) c FROM migration_requests WHERE status = 'pending'"
        ).fetchone()['c'],
    }
    recent_activity = pdb.execute(
        "SELECT * FROM activity_logs WHERE action != 'profile_update' ORDER BY timestamp DESC LIMIT 20"
    ).fetchall()
    threats = pdb.execute(
        'SELECT * FROM threats WHERE is_resolved=0 ORDER BY detected_at DESC LIMIT 10'
    ).fetchall()
    faculty_list = pdb.execute(
        'SELECT id, email, full_name, username, department, is_active, created_at FROM faculty ORDER BY created_at DESC'
    ).fetchall()

    return render_template('platform/dashboard.html',
        stats=stats, activity=recent_activity, threats=threats, faculty_list=faculty_list
    )

@app.route('/platform/admin/faculty/<int:fid>/toggle', methods=['POST'])
@admin_required
def platform_toggle_faculty(fid):
    pdb = get_platform_db()
    faculty = pdb.execute('SELECT is_detached, full_name FROM faculty WHERE id = ?', (fid,)).fetchone()
    if faculty and faculty['is_detached']:
        flash(f'{faculty["full_name"]} has migrated. Cannot modify their account.', 'danger')
        return redirect(url_for('platform_dashboard'))
    pdb.execute('UPDATE faculty SET is_active = 1 - is_active WHERE id = ?', (fid,))
    pdb.commit()
    log_activity('admin_toggle_faculty', f"Toggled faculty id={fid}", 'platform_admin', session.get('admin_id', 0))
    flash('Faculty status updated.', 'info')
    return redirect(url_for('platform_dashboard'))

@app.route('/platform/admin/faculty/<int:fid>/reset-password', methods=['GET', 'POST'])
@admin_required
def platform_reset_password(fid):
    pdb = get_platform_db()
    faculty = pdb.execute('SELECT id, full_name, is_detached FROM faculty WHERE id = ?', (fid,)).fetchone()
    if not faculty:
        abort(404)
    if faculty['is_detached']:
        flash(f'{faculty["full_name"]} has migrated. Cannot reset their password.', 'danger')
        return redirect(url_for('platform_dashboard'))

    if request.method == 'GET':
        return render_template('platform/reset_password_confirm.html', faculty=fid, faculty_name=faculty['full_name'])

    # POST - confirm admin password and set new password
    admin_password = request.form.get('admin_password', '')
    new_pass = request.form.get('new_password', '').strip()
    admin = pdb.execute('SELECT * FROM platform_admins WHERE id = ?', (session['admin_id'],)).fetchone()

    if not admin or not check_password_hash(admin['password_hash'], admin_password):
        flash('Your admin password is incorrect. Action cancelled.', 'danger')
        log_activity('admin_password_fail', f'Failed admin password confirmation for reset of faculty id={fid}', 'platform_admin', session.get('admin_id', 0))
        return redirect(url_for('platform_dashboard'))

    if new_pass and len(new_pass) >= 6:
        final_pass = new_pass
    else:
        final_pass = secrets.token_hex(8)

    pdb.execute('UPDATE faculty SET password_hash = ? WHERE id = ?', (generate_password_hash(final_pass), fid))
    pdb.commit()
    # Also update in the independent database if it exists
    ind_db_path = os.path.join(app.root_path, f'faculty_{fid}.db')
    if os.path.exists(ind_db_path):
        ind_db = sqlite3.connect(ind_db_path, timeout=15)
        ind_db.execute('UPDATE faculty SET password_hash = ? WHERE id = ?', (generate_password_hash(final_pass), 1))
        ind_db.commit()
        ind_db.close()
    log_activity('admin_reset_password', f'Reset password for faculty: {faculty["full_name"]}', 'platform_admin', session.get('admin_id', 0))
    flash(f'Password reset for {faculty["full_name"]}. New password: {final_pass}', 'success')
    return redirect(url_for('platform_dashboard'))

@app.route('/platform/admin/threats/<int:tid>/resolve', methods=['POST'])
@admin_required
def platform_resolve_threat(tid):
    pdb = get_platform_db()
    pdb.execute('UPDATE threats SET is_resolved = 1 WHERE id = ?', (tid,))
    pdb.commit()
    flash('Threat marked as resolved.', 'info')
    return redirect(url_for('platform_dashboard'))

@app.route('/platform/admin/migration-requests')
@admin_required
def platform_migration_requests():
    pdb = get_platform_db()
    requests_list = pdb.execute(
        "SELECT mr.*, f.full_name, f.email, f.username FROM migration_requests mr "
        "JOIN faculty f ON mr.faculty_id = f.id ORDER BY mr.created_at DESC"
    ).fetchall()
    return render_template('platform/migration_requests.html', requests=requests_list)

@app.route('/platform/admin/migration-requests/<int:req_id>/review', methods=['GET', 'POST'])
@admin_required
def platform_review_migration(req_id):
    pdb = get_platform_db()
    migration = pdb.execute(
        "SELECT mr.*, f.full_name, f.email, f.username FROM migration_requests mr "
        "JOIN faculty f ON mr.faculty_id = f.id WHERE mr.id = ?", (req_id,)
    ).fetchone()
    if not migration:
        abort(404)

    if request.method == 'GET':
        return render_template('platform/review_migration.html', migration=migration)

    # POST - process the review
    admin_password = request.form.get('admin_password', '')
    decision = request.form.get('decision', '')
    admin_notes = request.form.get('admin_notes', '').strip()
    admin = pdb.execute('SELECT * FROM platform_admins WHERE id = ?', (session['admin_id'],)).fetchone()

    if not admin or not check_password_hash(admin['password_hash'], admin_password):
        flash('Your admin password is incorrect. Action cancelled.', 'danger')
        log_activity('admin_password_fail', f'Failed admin password for migration review id={req_id}', 'platform_admin', session.get('admin_id', 0))
        return redirect(url_for('platform_migration_requests'))

    if decision == 'approve':
        pdb.execute(
            'UPDATE migration_requests SET status = ?, admin_notes = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?',
            ('approved', admin_notes, session['admin_id'], req_id)
        )
        pdb.execute(
            'UPDATE faculty SET is_detached = 1, detached_at = CURRENT_TIMESTAMP WHERE id = ?',
            (migration['faculty_id'],)
        )
        pdb.commit()
        # Create the faculty's independent database
        create_independent_db(migration['faculty_id'])
        log_activity('migration_approved', f'Approved migration for {migration["full_name"]} - independent DB created', 'platform_admin', session.get('admin_id', 0))
        flash(f'Migration approved for {migration["full_name"]}. Their independent database has been created. They now have full control.', 'success')
    elif decision == 'reject':
        pdb.execute(
            'UPDATE migration_requests SET status = ?, admin_notes = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?',
            ('rejected', admin_notes, session['admin_id'], req_id)
        )
        pdb.commit()
        log_activity('migration_rejected', f'Rejected migration for {migration["full_name"]}', 'platform_admin', session.get('admin_id', 0))
        flash(f'Migration request rejected for {migration["full_name"]}.', 'info')

    return redirect(url_for('platform_migration_requests'))

@app.route('/platform/admin/activity')
@admin_required
def platform_activity():
    pdb = get_platform_db()
    page = int(request.args.get('page', 1))
    per_page = 50
    offset = (page - 1) * per_page
    faculty_filter = request.args.get('faculty_id', '')
    if faculty_filter:
        logs = pdb.execute(
            "SELECT * FROM activity_logs WHERE user_id = ? AND action != 'profile_update' ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (int(faculty_filter), per_page, offset)
        ).fetchall()
        total = pdb.execute('SELECT COUNT(*) c FROM activity_logs WHERE user_id = ? AND action != ?', (int(faculty_filter), 'profile_update')).fetchone()['c']
    else:
        logs = pdb.execute(
            "SELECT * FROM activity_logs WHERE action != 'profile_update' ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (per_page, offset)
        ).fetchall()
        total = pdb.execute("SELECT COUNT(*) c FROM activity_logs WHERE action != 'profile_update'").fetchone()['c']
    return render_template('platform/activity.html', logs=logs, page=page, total=total, faculty_filter=faculty_filter)

@app.route('/platform/admin/faculty/<int:fid>/activity')
@admin_required
def platform_faculty_activity(fid):
    pdb = get_platform_db()
    faculty = pdb.execute('SELECT id, full_name, username, is_detached FROM faculty WHERE id = ?', (fid,)).fetchone()
    if not faculty:
        abort(404)
    if faculty['is_detached']:
        flash(f'{faculty["full_name"]} has migrated to an independent platform. Their data is no longer accessible here.', 'info')
        return redirect(url_for('platform_dashboard'))
    page = int(request.args.get('page', 1))
    per_page = 50
    offset = (page - 1) * per_page
    logs = pdb.execute(
        "SELECT * FROM activity_logs WHERE user_id = ? AND action != 'profile_update' ORDER BY timestamp DESC LIMIT ? OFFSET ?",
        (fid, per_page, offset)
    ).fetchall()
    total = pdb.execute("SELECT COUNT(*) c FROM activity_logs WHERE user_id = ? AND action != 'profile_update'", (fid,)).fetchone()['c']
    return render_template('platform/faculty_activity.html', faculty=faculty, logs=logs, page=page, total=total)

@app.route('/platform/admin/users/<int:fid>')
@admin_required
def platform_user_detail(fid):
    pdb = get_platform_db()
    faculty = pdb.execute('SELECT * FROM faculty WHERE id = ?', (fid,)).fetchone()
    if not faculty:
        abort(404)
    # Load all data for this faculty
    qualifications = pdb.execute('SELECT * FROM qualifications WHERE faculty_id=? ORDER BY year_of_passing DESC', (fid,)).fetchall()
    research = pdb.execute('SELECT * FROM research_interests WHERE faculty_id=?', (fid,)).fetchall()
    achievements = pdb.execute('SELECT * FROM achievements WHERE faculty_id=? ORDER BY year DESC', (fid,)).fetchall()
    publications = pdb.execute('SELECT * FROM publications WHERE faculty_id=? ORDER BY year DESC', (fid,)).fetchall()
    courses = pdb.execute('SELECT * FROM courses WHERE faculty_id=?', (fid,)).fetchall()
    materials = pdb.execute('SELECT * FROM course_materials WHERE faculty_id=? ORDER BY uploaded_at DESC', (fid,)).fetchall()
    students = pdb.execute('SELECT * FROM students WHERE faculty_id=? ORDER BY name', (fid,)).fetchall()
    projects = pdb.execute('SELECT * FROM projects WHERE faculty_id=? ORDER BY start_year DESC', (fid,)).fetchall()
    announcements = pdb.execute('SELECT * FROM announcements WHERE faculty_id=? ORDER BY created_at DESC', (fid,)).fetchall()
    messages = pdb.execute('SELECT * FROM messages WHERE faculty_id=? ORDER BY created_at DESC', (fid,)).fetchall()
    activity = pdb.execute('SELECT * FROM activity_logs WHERE user_id=? AND user_type=? ORDER BY timestamp DESC LIMIT 50', (fid, 'faculty')).fetchall()
    migration = pdb.execute('SELECT * FROM migration_requests WHERE faculty_id=? ORDER BY created_at DESC LIMIT 1', (fid,)).fetchone()
    return render_template('platform/user_detail.html',
        faculty=faculty, qualifications=qualifications, research=research,
        achievements=achievements, publications=publications, courses=courses,
        materials=materials, students=students, projects=projects,
        announcements=announcements, messages=messages, activity=activity,
        migration=migration
    )

@app.route('/platform/admin/threats')
@admin_required
def platform_threats():
    pdb = get_platform_db()
    threats = pdb.execute('SELECT * FROM threats ORDER BY detected_at DESC').fetchall()
    return render_template('platform/threats.html', threats=threats)

# =============================================================================
# Admin Context Processor
# =============================================================================

@app.context_processor
def inject_admin_counts():
    try:
        pdb = get_platform_db()
        return {
            'pending_migrations_count': pdb.execute("SELECT COUNT(*) c FROM migration_requests WHERE status='pending'").fetchone()['c'],
            'unresolved_threats_count': pdb.execute('SELECT COUNT(*) c FROM threats WHERE is_resolved=0').fetchone()['c'],
        }
    except Exception:
        return {'pending_migrations_count': 0, 'unresolved_threats_count': 0}

# =============================================================================
# Admin Platform Settings (simple key-value store)
# =============================================================================

def get_setting(key, default=''):
    pdb = get_platform_db()
    try:
        pdb.execute('CREATE TABLE IF NOT EXISTS platform_settings (key TEXT PRIMARY KEY, value TEXT)')
        pdb.commit()
    except Exception:
        pass
    row = pdb.execute('SELECT value FROM platform_settings WHERE key=?', (key,)).fetchone()
    return row['value'] if row else default

def set_setting(key, value):
    pdb = get_platform_db()
    try:
        pdb.execute('CREATE TABLE IF NOT EXISTS platform_settings (key TEXT PRIMARY KEY, value TEXT)')
        pdb.commit()
    except Exception:
        pass
    pdb.execute('INSERT OR REPLACE INTO platform_settings (key, value) VALUES (?, ?)', (key, value))
    pdb.commit()

# =============================================================================
# Platform Admin - Faculty Operations
# =============================================================================

@app.route('/platform/admin/faculty')
@admin_required
def platform_faculty_list():
    pdb = get_platform_db()
    search = request.args.get('q', '').strip()
    status = request.args.get('status', '')
    dept = request.args.get('dept', '')
    
    query = 'SELECT * FROM faculty WHERE 1=1'
    params = []
    
    if search:
        query += ' AND (full_name LIKE ? OR email LIKE ? OR username LIKE ?)'
        params.extend([f'%{search}%'] * 3)
    if status == 'active':
        query += ' AND is_active = 1'
    elif status == 'inactive':
        query += ' AND is_active = 0'
    elif status == 'detached':
        query += ' AND is_detached = 1'
    if dept:
        query += ' AND department = ?'
        params.append(dept)
    
    query += ' ORDER BY created_at DESC'
    faculty = pdb.execute(query, params).fetchall()
    departments = pdb.execute('SELECT DISTINCT department FROM faculty WHERE department != "" ORDER BY department').fetchall()
    stats = {
        'total': pdb.execute('SELECT COUNT(*) c FROM faculty').fetchone()['c'],
        'active': pdb.execute('SELECT COUNT(*) c FROM faculty WHERE is_active=1').fetchone()['c'],
        'inactive': pdb.execute('SELECT COUNT(*) c FROM faculty WHERE is_active=0').fetchone()['c'],
        'detached': pdb.execute('SELECT COUNT(*) c FROM faculty WHERE is_detached=1').fetchone()['c'],
    }
    return render_template('platform/faculty_list.html',
        faculty=faculty, departments=departments, stats=stats,
        search=search, status_filter=status, dept_filter=dept)

# =============================================================================
# Platform Admin - Public Websites
# =============================================================================

@app.route('/platform/admin/websites')
@admin_required
def platform_websites():
    pdb = get_platform_db()
    search = request.args.get('q', '').strip()
    filter_type = request.args.get('filter', '')
    
    query = '''SELECT f.id, f.full_name, f.username, f.department, f.institution,
               f.photo, f.bio, f.is_active, f.is_detached, f.created_at,
               (SELECT COUNT(*) FROM publications WHERE faculty_id=f.id) as pub_count,
               (SELECT COUNT(*) FROM courses WHERE faculty_id=f.id) as course_count,
               (SELECT COUNT(*) FROM qualifications WHERE faculty_id=f.id) as qual_count
               FROM faculty f WHERE 1=1'''
    params = []
    
    if search:
        query += ' AND (f.full_name LIKE ? OR f.username LIKE ?)'
        params.extend([f'%{search}%'] * 2)
    if filter_type == 'incomplete':
        query += ' AND (f.bio = "" OR f.department = "")'
    elif filter_type == 'no_photo':
        query += ' AND f.photo = ""'
    elif filter_type == 'detached':
        query += ' AND f.is_detached = 1'
    elif filter_type == 'inactive':
        query += ' AND f.is_active = 0'
    
    query += ' ORDER BY f.created_at DESC'
    websites = pdb.execute(query, params).fetchall()
    return render_template('platform/websites.html', websites=websites, search=search, filter_type=filter_type)

# =============================================================================
# Platform Admin - Data & Migration Center
# =============================================================================

@app.route('/platform/admin/data-migration')
@admin_required
def platform_data_migration():
    pdb = get_platform_db()
    tab = request.args.get('tab', 'overview')
    
    # Overview stats
    total_faculty = pdb.execute('SELECT COUNT(*) c FROM faculty').fetchone()['c']
    total_publications = pdb.execute('SELECT COUNT(*) c FROM publications').fetchone()['c']
    total_courses = pdb.execute('SELECT COUNT(*) c FROM courses').fetchone()['c']
    total_materials = pdb.execute('SELECT COUNT(*) c FROM course_materials').fetchone()['c']
    total_messages = pdb.execute('SELECT COUNT(*) c FROM messages').fetchone()['c']
    total_announcements = pdb.execute('SELECT COUNT(*) c FROM announcements').fetchone()['c']
    
    # Migration stats
    pending = pdb.execute("SELECT COUNT(*) c FROM migration_requests WHERE status='pending'").fetchone()['c']
    approved = pdb.execute("SELECT COUNT(*) c FROM migration_requests WHERE status='approved'").fetchone()['c']
    rejected = pdb.execute("SELECT COUNT(*) c FROM migration_requests WHERE status='rejected'").fetchone()['c']
    detached = pdb.execute('SELECT COUNT(*) c FROM faculty WHERE is_detached=1').fetchone()['c']
    
    # All migration requests
    requests_list = pdb.execute(
        "SELECT mr.*, f.full_name, f.email, f.username FROM migration_requests mr "
        "JOIN faculty f ON mr.faculty_id = f.id ORDER BY mr.created_at DESC"
    ).fetchall()
    
    # Storage estimate
    db_path = app.config['DATABASE']
    db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
    upload_size = 0
    upload_dir = app.config['UPLOAD_FOLDER']
    if os.path.exists(upload_dir):
        for dirpath, dirnames, filenames in os.walk(upload_dir):
            for f in filenames:
                upload_size += os.path.getsize(os.path.join(dirpath, f))
    
    return render_template('platform/data_migration.html',
        tab=tab, total_faculty=total_faculty, total_publications=total_publications,
        total_courses=total_courses, total_materials=total_materials,
        total_messages=total_messages, total_announcements=total_announcements,
        pending=pending, approved=approved, rejected=rejected, detached=detached,
        requests=requests_list, db_size=db_size, upload_size=upload_size)

# =============================================================================
# Platform Admin - Security Center
# =============================================================================

@app.route('/platform/admin/security')
@admin_required
def platform_security():
    pdb = get_platform_db()
    severity = request.args.get('severity', '')
    status = request.args.get('status', '')
    
    query = 'SELECT * FROM threats WHERE 1=1'
    params = []
    if severity:
        query += ' AND severity = ?'
        params.append(severity)
    if status == 'resolved':
        query += ' AND is_resolved = 1'
    elif status == 'active':
        query += ' AND is_resolved = 0'
    query += ' ORDER BY detected_at DESC'
    threats = pdb.execute(query, params).fetchall()
    
    # Failed logins
    failed_logins = pdb.execute(
        "SELECT * FROM activity_logs WHERE action LIKE '%failed%' OR action LIKE '%login_failed%' ORDER BY timestamp DESC LIMIT 50"
    ).fetchall()
    
    # Security stats
    stats = {
        'total_threats': pdb.execute('SELECT COUNT(*) c FROM threats').fetchone()['c'],
        'active_threats': pdb.execute('SELECT COUNT(*) c FROM threats WHERE is_resolved=0').fetchone()['c'],
        'critical': pdb.execute("SELECT COUNT(*) c FROM threats WHERE severity='critical' AND is_resolved=0").fetchone()['c'],
        'high': pdb.execute("SELECT COUNT(*) c FROM threats WHERE severity='high' AND is_resolved=0").fetchone()['c'],
        'medium': pdb.execute("SELECT COUNT(*) c FROM threats WHERE severity='medium' AND is_resolved=0").fetchone()['c'],
        'low': pdb.execute("SELECT COUNT(*) c FROM threats WHERE severity='low' AND is_resolved=0").fetchone()['c'],
    }
    
    return render_template('platform/security.html',
        threats=threats, failed_logins=failed_logins, stats=stats,
        severity_filter=severity, status_filter=status)

# =============================================================================
# Platform Admin - Analytics
# =============================================================================

@app.route('/platform/admin/analytics')
@admin_required
def platform_analytics():
    pdb = get_platform_db()
    
    # Faculty growth by month
    faculty_growth = pdb.execute(
        "SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count "
        "FROM faculty GROUP BY month ORDER BY month DESC LIMIT 12"
    ).fetchall()
    
    # Content stats
    content_stats = {
        'publications': pdb.execute('SELECT COUNT(*) c FROM publications').fetchone()['c'],
        'courses': pdb.execute('SELECT COUNT(*) c FROM courses').fetchone()['c'],
        'materials': pdb.execute('SELECT COUNT(*) c FROM course_materials').fetchone()['c'],
        'achievements': pdb.execute('SELECT COUNT(*) c FROM achievements').fetchone()['c'],
        'research': pdb.execute('SELECT COUNT(*) c FROM research_interests').fetchone()['c'],
        'students': pdb.execute('SELECT COUNT(*) c FROM students').fetchone()['c'],
        'projects': pdb.execute('SELECT COUNT(*) c FROM projects').fetchone()['c'],
        'announcements': pdb.execute('SELECT COUNT(*) c FROM announcements').fetchone()['c'],
    }
    
    # Activity by day
    activity_by_day = pdb.execute(
        "SELECT date(timestamp) as day, COUNT(*) as count "
        "FROM activity_logs WHERE timestamp >= date('now', '-30 days') "
        "GROUP BY day ORDER BY day"
    ).fetchall()
    
    # Top actions
    top_actions = pdb.execute(
        "SELECT action, COUNT(*) as count FROM activity_logs "
        "GROUP BY action ORDER BY count DESC LIMIT 10"
    ).fetchall()
    
    # Profile completion
    complete = pdb.execute('SELECT COUNT(*) c FROM faculty WHERE bio!="" AND department!="" AND photo!=""').fetchone()['c']
    total = pdb.execute('SELECT COUNT(*) c FROM faculty').fetchone()['c']
    
    return render_template('platform/analytics.html',
        faculty_growth=faculty_growth, content_stats=content_stats,
        activity_by_day=activity_by_day, top_actions=top_actions,
        profile_complete=complete, profile_total=total)

# =============================================================================
# Platform Admin - System Health
# =============================================================================

@app.route('/platform/admin/health')
@admin_required
def platform_health():
    pdb = get_platform_db()
    
    # Database health
    db_path = app.config['DATABASE']
    db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
    db_healthy = os.path.exists(db_path)
    
    # Table counts
    tables = {}
    for t in ['faculty', 'publications', 'courses', 'announcements', 'messages', 'threats', 'activity_logs']:
        try:
            tables[t] = pdb.execute(f'SELECT COUNT(*) c FROM {t}').fetchone()['c']
        except Exception:
            tables[t] = 'error'
    
    # Upload storage
    upload_size = 0
    upload_count = 0
    upload_dir = app.config['UPLOAD_FOLDER']
    if os.path.exists(upload_dir):
        for dirpath, dirnames, filenames in os.walk(upload_dir):
            for f in filenames:
                upload_size += os.path.getsize(os.path.join(dirpath, f))
                upload_count += 1
    
    # Independent DBs
    ind_dbs = []
    for fname in os.listdir(app.root_path):
        if fname.startswith('faculty_') and fname.endswith('.db'):
            fsize = os.path.getsize(os.path.join(app.root_path, fname))
            fid = fname.replace('faculty_', '').replace('.db', '')
            ind_dbs.append({'file': fname, 'size': fsize, 'faculty_id': fid})
    
    # Session/auth check
    auth_working = True
    try:
        pdb.execute('SELECT 1 FROM platform_admins LIMIT 1')
    except Exception:
        auth_working = False
    
    return render_template('platform/health.html',
        db_size=db_size, db_healthy=db_healthy, tables=tables,
        upload_size=upload_size, upload_count=upload_count,
        ind_dbs=ind_dbs, auth_working=auth_working)

# =============================================================================
# Platform Admin - Backups
# =============================================================================

@app.route('/platform/admin/backups')
@admin_required
def platform_backups():
    pdb = get_platform_db()
    
    # Ensure backup history table
    pdb.execute('''CREATE TABLE IF NOT EXISTS backup_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        backup_type TEXT NOT NULL,
        file_path TEXT DEFAULT '',
        file_size INTEGER DEFAULT 0,
        status TEXT DEFAULT 'completed',
        created_by INTEGER DEFAULT 0,
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    pdb.commit()
    
    backups = pdb.execute('SELECT * FROM backup_history ORDER BY created_at DESC LIMIT 50').fetchall()
    db_size = os.path.getsize(app.config['DATABASE']) if os.path.exists(app.config['DATABASE']) else 0
    
    return render_template('platform/backups.html', backups=backups, db_size=db_size)

@app.route('/platform/admin/backups/create', methods=['POST'])
@admin_required
def platform_create_backup():
    pdb = get_platform_db()
    import shutil
    backup_dir = os.path.join(app.root_path, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'faculty_connect_backup_{ts}.db'
    backup_path = os.path.join(backup_dir, backup_name)
    try:
        shutil.copy2(app.config['DATABASE'], backup_path)
        file_size = os.path.getsize(backup_path)
        pdb.execute(
            'INSERT INTO backup_history (backup_type, file_path, file_size, status, created_by, notes) VALUES (?, ?, ?, ?, ?, ?)',
            ('manual', backup_name, file_size, 'completed', session.get('admin_id', 0), 'Manual backup')
        )
        pdb.commit()
        log_activity('backup_created', f'Backup created: {backup_name} ({file_size} bytes)', 'platform_admin', session.get('admin_id', 0))
        flash(f'Backup created successfully: {backup_name}', 'success')
    except Exception as e:
        pdb.execute(
            'INSERT INTO backup_history (backup_type, file_path, file_size, status, created_by, notes) VALUES (?, ?, ?, ?, ?, ?)',
            ('manual', '', 0, 'failed', session.get('admin_id', 0), str(e))
        )
        pdb.commit()
        flash(f'Backup failed: {str(e)}', 'danger')
    return redirect(url_for('platform_backups'))

# =============================================================================
# Platform Admin - Admins & Roles
# =============================================================================

@app.route('/platform/admin/admins')
@admin_required
def platform_admins():
    pdb = get_platform_db()
    # Ensure role column exists
    try:
        pdb.execute('ALTER TABLE platform_admins ADD COLUMN role TEXT DEFAULT "super_admin"')
        pdb.commit()
    except Exception:
        pass
    admins = pdb.execute('SELECT * FROM platform_admins ORDER BY created_at').fetchall()
    return render_template('platform/admins.html', admins=admins)

@app.route('/platform/admin/admins/add', methods=['POST'])
@admin_required
def platform_add_admin():
    pdb = get_platform_db()
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', 'platform_admin')
    if not username or not password:
        flash('Username and password are required.', 'danger')
        return redirect(url_for('platform_admins'))
    if len(password) < 6:
        flash('Password must be at least 6 characters.', 'danger')
        return redirect(url_for('platform_admins'))
    existing = pdb.execute('SELECT id FROM platform_admins WHERE username=?', (username,)).fetchone()
    if existing:
        flash('Username already exists.', 'danger')
        return redirect(url_for('platform_admins'))
    try:
        pdb.execute('ALTER TABLE platform_admins ADD COLUMN role TEXT DEFAULT "super_admin"')
    except Exception:
        pass
    pdb.execute('INSERT INTO platform_admins (username, password_hash, role) VALUES (?, ?, ?)',
        (username, generate_password_hash(password), role))
    pdb.commit()
    log_activity('admin_created', f'New admin created: {username} (role: {role})', 'platform_admin', session.get('admin_id', 0))
    flash(f'Admin {username} created with role {role}.', 'success')
    return redirect(url_for('platform_admins'))

@app.route('/platform/admin/admins/<int:aid>/delete', methods=['POST'])
@admin_required
def platform_delete_admin(aid):
    pdb = get_platform_db()
    if aid == session.get('admin_id'):
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('platform_admins'))
    admin = pdb.execute('SELECT username FROM platform_admins WHERE id=?', (aid,)).fetchone()
    if admin:
        pdb.execute('DELETE FROM platform_admins WHERE id=?', (aid,))
        pdb.commit()
        log_activity('admin_deleted', f'Admin deleted: {admin["username"]}', 'platform_admin', session.get('admin_id', 0))
        flash(f'Admin {admin["username"]} deleted.', 'info')
    return redirect(url_for('platform_admins'))

@app.route('/platform/admin/admins/<int:aid>/role', methods=['POST'])
@admin_required
def platform_update_admin_role(aid):
    pdb = get_platform_db()
    role = request.form.get('role', 'platform_admin')
    try:
        pdb.execute('ALTER TABLE platform_admins ADD COLUMN role TEXT DEFAULT "super_admin"')
    except Exception:
        pass
    pdb.execute('UPDATE platform_admins SET role=? WHERE id=?', (role, aid))
    pdb.commit()
    log_activity('admin_role_changed', f'Admin role updated to {role} for id={aid}', 'platform_admin', session.get('admin_id', 0))
    flash('Admin role updated.', 'success')
    return redirect(url_for('platform_admins'))

# =============================================================================
# Platform Admin - Support / View-as-Faculty
# =============================================================================

@app.route('/platform/admin/faculty/<int:fid>/support', methods=['POST'])
@admin_required
def platform_support_session(fid):
    pdb = get_platform_db()
    faculty = pdb.execute('SELECT * FROM faculty WHERE id=?', (fid,)).fetchone()
    if not faculty:
        abort(404)
    if faculty['is_detached']:
        flash('Cannot start support session for a detached faculty member.', 'danger')
        return redirect(url_for('platform_faculty_list'))
    reason = request.form.get('reason', 'Admin support session')
    session['support_faculty_id'] = fid
    session['support_started'] = datetime.now().isoformat()
    session['support_reason'] = reason
    log_activity('support_session_started', f'Admin support session started for faculty: {faculty["full_name"]} (reason: {reason})', 'platform_admin', session.get('admin_id', 0))
    flash(f'Support session started for {faculty["full_name"]}. You are now viewing the platform as this faculty member.', 'info')
    return redirect(url_for('faculty_dashboard'))

@app.route('/platform/admin/support/exit', methods=['POST'])
@admin_required
def platform_exit_support():
    fid = session.pop('support_faculty_id', None)
    session.pop('support_started', None)
    session.pop('support_reason', None)
    log_activity('support_session_ended', f'Admin support session ended for faculty id={fid}', 'platform_admin', session.get('admin_id', 0))
    flash('Support session ended.', 'info')
    return redirect(url_for('platform_faculty_list'))

# =============================================================================
# Platform Admin - Platform Settings
# =============================================================================

@app.route('/platform/admin/settings', methods=['GET', 'POST'])
@admin_required
def platform_settings():
    pdb = get_platform_db()
    try:
        pdb.execute('CREATE TABLE IF NOT EXISTS platform_settings (key TEXT PRIMARY KEY, value TEXT)')
        pdb.commit()
    except Exception:
        pass
    
    if request.method == 'POST':
        settings_to_save = [
            'platform_name', 'registration_enabled', 'require_approval',
            'default_visibility', 'max_upload_size', 'allowed_file_types',
            'session_timeout', 'login_attempt_limit', 'password_min_length',
            'maintenance_mode'
        ]
        for key in settings_to_save:
            val = request.form.get(key, '')
            pdb.execute('INSERT OR REPLACE INTO platform_settings (key, value) VALUES (?, ?)', (key, val))
        pdb.commit()
        log_activity('settings_updated', 'Platform settings updated', 'platform_admin', session.get('admin_id', 0))
        flash('Settings saved successfully.', 'success')
        return redirect(url_for('platform_settings'))
    
    settings = {}
    for row in pdb.execute('SELECT * FROM platform_settings').fetchall():
        settings[row['key']] = row['value']
    return render_template('platform/settings.html', settings=settings)

@app.route('/platform/logout')
def platform_logout():
    session.clear()
    return redirect(url_for('platform_login'))

# =============================================================================
# Error Handlers
# =============================================================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

# =============================================================================
# Application Entry Point
# =============================================================================

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True, port=5000)

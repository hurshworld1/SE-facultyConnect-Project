"""
FacultyConnect - One-click launcher
Run this file to set up and start the platform.
"""

import subprocess
import sys
import os

def main():
    print("=" * 60)
    print("  FacultyConnect - Faculty Website Platform")
    print("=" * 60)

    # Step 1: Install dependencies
    print("\n[1/3] Installing dependencies...")
    try:
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', '-q', '-r', 'requirements.txt'],
            stdout=subprocess.DEVNULL if not os.environ.get('VERBOSE') else None
        )
        print("  Dependencies installed.")
    except subprocess.CalledProcessError:
        print("  Warning: pip install failed. Trying to continue anyway.")

    # Step 2: Seed database
    print("\n[2/3] Setting up database...")
    from app import app, init_db
    with app.app_context():
        init_db()
        # Check if we need to seed
        import sqlite3
        db = sqlite3.connect(os.path.join(app.root_path, 'faculty.db'))
        count = db.execute('SELECT COUNT(*) FROM faculty').fetchone()[0]
        db.close()
        if count == 0:
            print("  Seeding demo data...")
            from seed import seed
            seed()
        else:
            print(f"  Database ready ({count} faculty members).")

    # Step 3: Start server
    print("\n[3/3] Starting server...")
    print("\n" + "-" * 60)
    print("  FacultyConnect is running!")
    print("")
    print("  Public site:    http://localhost:5000")
    print("  Faculty login:  http://localhost:5000/login")
    print("  Platform admin: http://localhost:5000/platform/admin/login")
    print("")
    print("  Demo accounts:")
    print("    Faculty: anand / anand123")
    print("    Faculty: sunita / sunita123")
    print("    Admin:   admin / admin123")
    print("")
    print("  Press Ctrl+C to stop.")
    print("-" * 60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()

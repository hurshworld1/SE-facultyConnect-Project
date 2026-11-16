# FacultyConnect - Faculty Personal Website Platform

A platform where faculty members create and manage their personal academic websites. All data is stored on the platform's database with full security and monitoring.

## Features

### For Faculty Members
- **Registration & Login** - Sign up with email and password
- **Personal Profile** - Bio, photo, designation, department, institution
- **Qualifications** - Degrees, certifications with certificate photos
- **Research Interests** - Detailed research areas with descriptions
- **Achievements & Awards** - Awards, patents, grants with category badges and certificate photos
- **Publications** - Journal articles, conference papers with DOI links and toggleable abstracts
- **Courses** - Course listings with codes, schedules, and descriptions
- **Course Materials** - Upload PDFs, slides, notes for students to download
- **Research Students** - Table of current and past research students
- **Projects** - Funded projects with agency, amount, and duration details
- **Announcements** - Post notices and important updates
- **Messages** - Receive messages from students via contact form
- **Draft/Publish** - Toggle any section's visibility on the public profile
- **File Uploads** - Profile photo, resume, certificate photos, course materials

### For Platform Admin
- **Monitoring Dashboard** - Stats on faculty, publications, messages
- **Activity Logs** - All platform activity with timestamps and IP tracking
- **Threat Detection** - Automatic detection of XSS, SQL injection, brute force, path traversal
- **Faculty Management** - Activate/deactivate accounts, reset passwords
- **Internal Only** - Not accessible from public URLs

### Security
- Password hashing with Werkzeug
- Session-based authentication
- Role-based access control (admin, faculty, guest)
- File upload validation (type and size limits)
- Foreign key cascading deletes
- Threat detection and logging

## Quick Start

```bash
python run.py
```

This single command:
1. Installs all dependencies
2. Creates the SQLite database with demo data
3. Starts the server on http://localhost:5000

## Demo Accounts

| Role | Username | Password |
|------|----------|----------|
| Platform Admin | admin | admin123 |
| Faculty | anand | anand123 |
| Faculty | sunita | sunita123 |

## Manual Setup

```bash
pip install -r requirements.txt
python seed.py        # Create database with demo data
python app.py         # Start development server
```

## URLs

| Page | URL |
|------|-----|

| Homepage | http://localhost:5000 |
| Faculty Login | http://localhost:5000/login |
| Registration | http://localhost:5000/register |
| Faculty Profile | http://localhost:5000/faculty/{username} |
| Platform Admin | http://localhost:5000/platform/admin/login |

## Deployment on Render.com

1. Push this code to a GitHub repository
2. Go to https://render.com and create a new Web Service
3. Connect your GitHub repository
4. Render will automatically detect `render.yaml` and configure the service
5. The app will be deployed with a free PostgreSQL-compatible database

## File Structure

```
faculty-connect/
  app.py              - Main application (Flask backend, routes, database)
  seed.py             - Demo data seeder
  run.py              - One-click launcher
  requirements.txt    - Python dependencies
  render.yaml         - Render.com deployment config
  uploads/            - Uploaded files (photos, documents, materials)
    photos/           - Faculty profile photos
    resumes/          - Faculty resumes/CVs
    certificates/     - Certificate photos
    materials/        - Course materials
    documents/        - General documents
  templates/          - HTML templates
    index.html        - Homepage with faculty directory
    login.html        - Faculty login
    register.html     - Faculty registration
    public_profile.html - Public faculty profile
    course_detail.html - Course materials page
    404.html, 500.html - Error pages
    faculty/          - Faculty dashboard templates
    platform/         - Platform admin templates (hidden)
  static/css/         - Stylesheets
```

## Database

SQLite database (`faculty.db`) with 13 tables:
- platform_admins
- faculty
- qualifications
- research_interests
- achievements
- publications
- courses
- course_materials
- students
- projects
- announcements
- messages
- activity_logs
- threats

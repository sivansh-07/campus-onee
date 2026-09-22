# College Campus Portal — VS Code Prototype

This prototype is based on the uploaded project report. It demonstrates the MVP flows:
- Role-based login: Student, Teacher, Admin, Placement Officer
- Student dashboard
- Department/course catalog and syllabus information
- Assignment listing and file submission
- Attendance with GPS/geofencing logic
- Leave application
- Viva schedule page
- Lab/facility information
- Notifications
- Admin teacher verification
- SQLite database with seeded demo data

## 1. Open in VS Code

Open this folder in VS Code.

## 2. Create a virtual environment

### Windows PowerShell
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Windows CMD
```cmd
python -m venv .venv
.venv\Scripts\activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Run

```bash
python app.py
```

Open:
http://127.0.0.1:5000

## Demo accounts

| Role | Email | Password |
|---|---|---|
| Student | student@college.test | student123 |
| Teacher | teacher@college.test | teacher123 |
| Admin | admin@college.test | admin123 |
| Placement | placement@college.test | placement123 |
| Pending Teacher | pending@college.test | teacher123 |

## Attendance prototype

The report proposes a campus geofence. This prototype uses:
- Demo campus center: 26.8467, 80.9462
- Demo radius: 1000 m

On the Attendance page you can enter coordinates or use the browser's location permission. The backend uses the Haversine formula and refuses a check-in outside the radius.

For a real college deployment, replace the demo coordinates/radius with the institution's approved values and add the report's security/privacy controls.

## Important prototype limitations

This is intentionally a placement/demo prototype, not a production SIS. It does not yet implement:
- production-grade 2FA/JWT/OAuth
- teacher document upload/review
- real email/SMS
- production cloud document storage
- timetable administration UI
- full grading/CGPA/result engine
- anti-GPS-spoofing controls
- complete audit logging
- production deployment configuration

Those items are natural next phases from the report.

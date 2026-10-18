# PrintRunner

PrintRunner is a student project for campus printing and delivery. The site uses PyScript for its interactive estimate and Flask + SQLite for order intake, runner applications, and the staff order board.

## Run locally

Python 3.10 or newer is required. From this folder in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:8000>. PyScript and the fonts load from their CDNs, so the browser needs internet access for those assets.

The SQLite database and uploaded print files are created under `instance/`. That directory is ignored by Git. Orders include the customer contact number and campus drop-off details. Attached files are restricted to the staff service board and are limited to 15 MB.

## Create the first staff account

In a second PowerShell window, activate the same virtual environment and run:

```powershell
python app.py create-staff runner
```

Enter a unique password of at least 12 characters when prompted. Passwords are stored as hashes. There is no public staff registration page; the account is created by the project administrator.

## Website features

- PyScript updates the price estimate and handles the quantity controls and file checks.
- The order form sends customer details and an optional print file to the Flask backend. The server validates the inputs and calculates the price itself.
- Runner applications are saved in SQLite for the team to review.
- The staff portal uses a server-validated login, signed HTTP-only session cookie, CSRF checks, and protected order/file endpoints.
- Staff can review orders, download an attached file, and update the status to `New`, `In progress`, or `Completed`.

## Deployment notes

This local SQLite setup is for the class project. For a public production launch, use a production WSGI server, a persistent strong `PRINTRUNNER_SECRET_KEY`, HTTPS (set `PRINTRUNNER_COOKIE_SECURE=1`), persistent private storage or object storage for uploads, regular database backups, and operational controls for data retention and account recovery. Do not commit `instance/`, credentials, or customer files. GitHub Pages cannot run this Flask backend; hosting the backend and database requires a Python-capable host.

The project is educational and has not been hardened for real customer data. Before accepting real orders, the team should review hosting, privacy, data-retention, and account security requirements with its instructor.

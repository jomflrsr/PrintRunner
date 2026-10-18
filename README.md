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

## Deploying on Railway

1. Push the project to GitHub and create a Railway project from the `jomflrsr/PrintRunner` repository on branch `main`.
2. Set the service build command to `pip install -r requirements.txt` and start command to `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1`.
3. Add a Railway volume mounted at `/data`, then add service variable `PRINTRUNNER_DATA_DIR=/data`. SQLite data, uploaded files, and the generated session secret are written under this mount.
4. Generate a staff login from Railway's service shell by running `python app.py create-staff runner` after the first deployment is live.
5. Generate a public Railway domain and open `/staff.html` to sign in.

## Deployment notes

The app can generate and save a stable secret key in its data directory; setting `PRINTRUNNER_SECRET_KEY` explicitly is also supported. Enable secure cookies with `PRINTRUNNER_COOKIE_SECURE=1` when the host serves HTTPS. Keep the persistent volume private, configure backups and data retention, and do not commit `instance/`, credentials, or customer files. GitHub Pages cannot run this Flask backend.

The project is educational and has not been hardened for real customer data. Before accepting real orders, the team should review hosting, privacy, data-retention, and account security requirements with its instructor.

# Central License Server

This project provides a complete Flask‑based central licence server for
managing software licences distributed to desktop applications.  It
implements an administration interface for super administrators and
organisation administrators, plus API endpoints that client
applications can call to activate and validate licences.

## Features

* **Super administrator dashboard** – manage organisations, users,
  licences, devices and view usage logs. Super administrators can
  create and deactivate organisations, generate licence keys and
  inspect all activation and validation activity.
* **Organisation dashboard** – each organisation has its own login
  where designated organisation administrators can view and manage
  their own users, licences and devices.  Organisation administrators
  cannot access data belonging to other organisations.
* **Licence management** – generate unique licence keys, assign them
  to users, set validity periods, suspend or revoke keys and track
  device activations. Licences support a configurable maximum number
  of devices.
* **Device tracking** – when a client activates a licence, the
  server records the system ID, machine name, IP address and app
  version.  Subsequent validations update the last check timestamp
  and ensure the licence remains within its allowed device limit.
* **REST API** – the `/api/activate` and `/api/validate` endpoints
  allow desktop applications to activate new licences and validate
  existing installations.  Responses include clear status and
  expiration information.
* **Security** – password hashing, session‑based authentication,
  role‑based access control and optional API secret authentication
  protect data and prevent unauthorised access.  Environment variables
  keep sensitive credentials out of the codebase.

## Project structure

The application is organised into a number of Python packages and
modules to separate concerns:

```
license_server/
├── app.py             # Application factory and entry point
├── config.py          # Configuration loaded from environment variables
├── extensions.py      # Shared Flask extensions (database, etc.)
├── requirements.txt    # Python dependencies
├── Procfile           # Render start command
├── .env.example       # Sample environment variables
├── README.md          # This file
|
├── models/            # SQLAlchemy models
│   ├── __init__.py
│   ├── admin.py
│   ├── organization.py
│   ├── organization_admin.py
│   ├── user.py
│   ├── license.py
│   ├── device.py
│   └── usage_log.py
|
├── routes/            # Blueprints for different parts of the UI/API
│   ├── __init__.py
│   ├── admin.py
│   ├── org.py
│   └── api.py
|
├── templates/         # Jinja2 templates for the web interface
│   ├── base.html
│   ├── admin/
│   └── org/
|
├── static/
│   └── css/
│       └── style.css
|
└── utils/             # Helper functions and decorators
    ├── __init__.py
    ├── auth.py
    ├── decorators.py
    └── license_utils.py
```

## Getting started

### Prerequisites

* Python 3.10 or higher
* A PostgreSQL database (Supabase provides a managed PostgreSQL
  instance) or use SQLite for local development

### Installation

1. Clone this repository or copy the `license_server` folder into your
   project.
2. Navigate into the project directory and create a Python virtual
   environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root based on `.env.example` and
   fill in your own values for `DATABASE_URL`, `SECRET_KEY`,
   `ADMIN_EMAIL`, `ADMIN_PASSWORD` and optionally `API_SECRET_KEY`.

5. Start the development server:

   ```bash
   export FLASK_APP=app.py
   flask run
   ```

   The application will initialise the database and create the first
   super administrator using the email and password specified in your
   environment. Visit `http://localhost:5000/admin/login` to log in.

## Deployment on Render

Render can deploy this application directly from a Git repository.

1. Create a new **Web Service** on Render and connect your repository.
2. Set the runtime environment to **Python** and choose the build
   command `pip install -r license_server/requirements.txt`.
3. Use the following start command as provided in the `Procfile`:

   ```
   gunicorn app:app
   ```

4. In the **Environment** settings, add the environment variables
   defined in `.env.example` with their corresponding production
   values.
5. For PostgreSQL, create a Render **Database** and copy its
   connection string into the `DATABASE_URL` variable.  Supabase can
   also be used by supplying its connection URI.

The service will be deployed and available at the URL provided by
Render.  Note that Render automatically sets `PORT` for your
application; Gunicorn will detect this environment variable and bind
to the appropriate port.

## Running migrations

This project uses Flask‑Migrate to handle database migrations. To
create a new migration and apply it:

```bash
flask db init      # run once to create the migrations folder
flask db migrate   # generate a new migration after changing models
flask db upgrade   # apply migrations to the database
```

Migrations allow you to update your database schema incrementally as
your models evolve.

## API usage

Two JSON endpoints are provided for client applications:

### POST `/api/activate`

Activate a new installation of a licence on a device.  Required
fields:

```json
{
  "license_key": "XXXX-XXXX-XXXX-XXXX",
  "system_id": "unique-system-id",
  "machine_name": "DESKTOP-01",
  "app_version": "1.0.0"
}
```

Response example on success:

```json
{
  "valid": true,
  "message": "License valid",
  "expires_on": "2026-12-31"
}
```

On error the response will include a reason:

```json
{
  "valid": false,
  "reason": "License expired"
}
```

### POST `/api/validate`

Validate an existing installation on a device.  Required fields:

```json
{
  "license_key": "XXXX-XXXX-XXXX-XXXX",
  "system_id": "unique-system-id",
  "app_version": "1.0.0"
}
```

The endpoint responds with the same structure as the activation
endpoint.  It also updates the `last_check` timestamp for the
device and records the validation attempt in `usage_logs`.

## License

This project is provided under the MIT License. See the `LICENSE` file
for details.
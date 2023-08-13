# Globalify.xyz

Python with Flask as the backend and TailwindCSS as the design framework.

## Pre-requisites

-   [Node.js](https://nodejs.org/en/)
-   [Python 3.11+](https://www.python.org/downloads/)

## Installation

### 1. Setup the virtual environment

#### Windows

```bash
python -m venv .venv
```

#### Linux/MacOS

```bash
python3 -m venv .venv
```

### 2. Activate the virtual environment

#### Windows

```bash
.\.venv\Scripts\activate
```

#### Linux/MacOS

```bash
source .venv/bin/activate
```

### 3. Get the package manager

We use [Poetry](https://python-poetry.org/) to manage Python dependencies

#### Windows

```bash
pip install poetry
```

#### Linux/MacOS

```bash
pip3 install poetry
```

### 4. Install the dependencies

#### Python dependencies

```bash
poetry install
```

#### Node dependencies

```bash
npm install
```

## Running the app

### 1. Activate the virtual environment

#### Windows

```bash
.\.venv\Scripts\activate
```

#### Linux/MacOS

```bash
source .venv/bin/activate
```

### 2. Set the environment variables

-   `FLASK_APP="project"`
-   `FLASK_DEBUG="true"`
-   `_DATABASE_URL=""`
-   `_GOOGLE_OAUTH2_CLIENT_ID=""`
-   `_GOOGLE_OAUTH2_CLIENT_SECRET=""`
-   `_LINKEDIN_OAUTH2_CLIENT_ID=""`
-   `_LINKEDIN_OAUTH2_CLIENT_SECRET=""`
-   `_STRIPE_PUBLISHABLE_KEY`
-   `_STRIPE_SECRET_KEY`
-   `_STRIPE_WEBHOOK_SECRET`

#### Powershell

```powershell
$ENV:FLASK_APP="project"
```

#### CMD

```cmd
set FLASK_APP="project"
```

#### Linux/MacOS

```bash
export FLASK_APP="project"
```

### 3. Run the app

Change the directory

#### Windows

```bash
cd .\server\src
```

#### Linux/MacOS

```bash
cd server/src
```

Run the app

```bash
flask run
```

Start the TailwindCSS compiler in a separate terminal

```bash
npm run create-css
```

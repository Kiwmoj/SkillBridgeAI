# O*NET data folder

Download the official **CSV ZIP** from <https://www.onetcenter.org/database.html> and place it in
`raw/` (for example `raw/db_31_0_csv.zip`). The folder is ignored by Git; archives are about 16 MB.

Load it into the configured database with:

```powershell
.\.venv\Scripts\python.exe -m apps.backend.cli.load_onet data\onet\raw\db_31_0_csv.zip
```

or upload it from the desktop **Administrator** page. Parsing rules live in `packages/onet`; the
database writer is `apps/backend/services/careers/onet_import.py`.

O*NET® Database, U.S. Department of Labor, Employment and Training Administration. Used under
CC BY 4.0. SkillBridge AI reformats this data; USDOL/ETA has not endorsed these changes.

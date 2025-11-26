import os
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# ================================
# BASE PATHS
# ================================
BASE_DIR = os.getcwd()
SHEET_ID_FILE = os.path.join(BASE_DIR, "storage", "sheet_id.txt")
SERVICE_JSON = os.path.join(BASE_DIR, "service_account.json")

# ================================
# READ SHEET ID
# ================================
with open(SHEET_ID_FILE) as f:
    SHEET_ID = f.read().strip()

# ================================
# GOOGLE SHEETS AUTH
# ================================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_JSON, scope)
client = gspread.authorize(creds)

# ================================
# OPEN SHEET AND LOAD DATA
# ================================
sheet = client.open_by_key(SHEET_ID).sheet1
rows = sheet.get_all_records()
df = pd.DataFrame(rows)

# ================================
# FILTER ONLY ROWS WITH EMAILS
# ================================
df_email = df[df["Business Email"].astype(str).str.strip() != ""]

# ================================
# CREATE / REPLACE "Emails Only" SHEET
# ================================
spreadsheet = client.open_by_key(SHEET_ID)

try:
    old_sheet = spreadsheet.worksheet("Emails Only")
    spreadsheet.del_worksheet(old_sheet)
    print("Old 'Emails Only' sheet deleted.", flush=True)
except gspread.WorksheetNotFound:
    print("No previous 'Emails Only' sheet found. Creating new.", flush=True)

new_sheet = spreadsheet.add_worksheet(title="Emails Only", rows=str(len(df_email)+10), cols=str(len(df_email.columns)+5))
new_sheet.update([df_email.columns.values.tolist()] + df_email.values.tolist())

print(f"Email filter complete: 'Emails Only' created with {len(df_email)} rows.", flush=True)

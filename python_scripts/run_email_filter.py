import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# ================================
# READ SHEET ID
# ================================
with open("storage/sheet_id.txt") as f:
    SHEET_ID = f.read().strip()

# ================================
# AUTH
# ================================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)

sheet = client.open_by_key(SHEET_ID).sheet1

rows = sheet.get_all_records()
df = pd.DataFrame(rows)

df_email = df[df["Business Email"].astype(str).str.strip() != ""]

spreadsheet = client.open_by_key(SHEET_ID)

try:
    spreadsheet.del_worksheet(spreadsheet.worksheet("Emails Only"))
except:
    pass

new_sheet = spreadsheet.add_worksheet(title="Emails Only", rows="10000", cols="20")
new_sheet.update([df_email.columns.values.tolist()] + df_email.values.tolist())

print("Email filter complete: 'Emails Only' created.")

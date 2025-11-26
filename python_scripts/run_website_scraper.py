import sys
sys.stdout.reconfigure(encoding='utf-8')  # Enable UTF-8 on Windows

import os
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from urllib.parse import urljoin, urlparse

# ================================
# READ SHEET ID
# ================================
with open("storage/sheet_id.txt") as f:
    SHEET_ID = f.read().strip()

# ================================
# GOOGLE SHEETS AUTH
# ================================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)

sheet = client.open_by_key(SHEET_ID).sheet1
data = sheet.get_all_records()
df = pd.DataFrame(data)

# ================================
# CLEAN URL
# ================================
def clean_url(url):
    if not isinstance(url, str) or url.strip() == "":
        return ""
    url = url.replace("\\u003d", "=")
    if not url.startswith("http"):
        url = "http://" + url
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}".strip()

# ================================
# Extract mailto emails only
# ================================
def extract_mailto_emails(html, soup):
    emails = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").split("?")[0].strip()
            emails.add(email.lower())
    return list(emails)

# ================================
# Regex fallback (FB only)
# ================================
def regex_emails(text):
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return list(set(re.findall(pattern, text)))

# ================================
# Scrape a page for emails
# ================================
def scrape_page(url):
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        emails = extract_mailto_emails(r.text, soup)
        if emails:
            print(f"Email found on page {url}: {emails}", flush=True)
        return emails
    except:
        return []

# ================================
# Find contact/about pages
# ================================
def find_specific_links(base_url, soup):
    contact = None
    about = None
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()

        if contact is None and ("contact" in href or "contact-us" in href):
            contact = urljoin(base_url, href)

        if about is None and ("about" in href or "about-us" in href):
            about = urljoin(base_url, href)

        if contact and about:
            break

    return contact, about

# ================================
# Extract Facebook email
# ================================
def extract_facebook_email(url):
    if "facebook.com" not in url:
        return []
    
    print("Checking Facebook:", url, flush=True)

    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        html = r.text.lower()
    except:
        return []

    emails = set()
    sections = [
        "page_about_info", "page_info", "email",
        "contact info", "\"description\":"
    ]

    for key in sections:
        if key in html:
            start = html.find(key)
            chunk = html[start:start+3000]
            found = regex_emails(chunk)
            if found:
                print(f"Found FB email: {found}", flush=True)
                emails.update(found)

    return list(emails)

# ================================
# MAIN SCRAPER LOGIC
# ================================
def extract_emails(url):
    if not isinstance(url, str) or not url.startswith("http"):
        return "", ""

    print("Scraping:", url, flush=True)

    emails = set()
    fb_link_saved = ""

    # Try homepage first
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        homepage_emails = extract_mailto_emails(r.text, soup)
        if homepage_emails:
            print(f"Homepage emails: {homepage_emails}", flush=True)
            return ", ".join(homepage_emails), fb_link_saved
    except:
        pass

    # Contact/About pages
    try:
        contact_url, about_url = find_specific_links(url, soup)
    except:
        contact_url = about_url = None

    if contact_url:
        found = scrape_page(contact_url)
        if found:
            return ", ".join(found), fb_link_saved

    if about_url:
        found = scrape_page(about_url)
        if found:
            return ", ".join(found), fb_link_saved

    # Facebook links
    fb_links = []
    try:
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if "facebook.com" in href or "fb.com" in href:
                full = urljoin(url, href)
                fb_links.append(full)
                if not fb_link_saved:
                    fb_link_saved = full
    except:
        pass

    for fb in fb_links:
        fb_emails = extract_facebook_email(fb)
        if fb_emails:
            return ", ".join(fb_emails), ""

    return "", fb_link_saved


# ================================
# PROCESS ALL ROWS
# ================================
emails_list = []
fb_list = []

for i, row in df.iterrows():
    site = clean_url(row.get("Business Website"))
    email, fb = extract_emails(site)

    emails_list.append(email)
    fb_list.append(fb)

# Save data
df["Business Email"] = emails_list
df["Facebook Link"] = fb_list

sheet.clear()
sheet.update([df.columns.values.tolist()] + df.values.tolist())

print("DONE! Website scraper completed.", flush=True)

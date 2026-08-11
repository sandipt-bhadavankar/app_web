import re
import requests
from bs4 import BeautifulSoup
import streamlit as st

# ==============================================================================
# 1. USER PROFILE, CERTIFICATIONS & CONFIGURATION
# ==============================================================================

MY_SKILLS = {
    # Certifications
    "aws certified solutions architect – associate",
    "palo alto networks certified network security administrator (pcnsa)",
    "cisco certified network associate (ccna)",
    "pcnsa",
    "ccna",
    # Technical Skills
    "palo alto", "cisco", "aws", "bgp", "ospf", "nexus",
    "vpn", "firewall", "python", "wireshark", "infoblox",
    "juniper", "nat", "load balancer", "f5", "dns", "dhcp"
}

MASTER_SKILL_CATALOG = {
    "aws certified solutions architect – associate",
    "palo alto networks certified network security administrator (pcnsa)",
    "cisco certified network associate (ccna)",
    "pcnsa", "ccna", "ccnp", "pcnsc",
    "cisco", "bgp", "ospf", "nexus", "juniper", "arista", "sd-wan", "mpls", "eigrp",
    "palo alto", "firewall", "vpn", "fortinet", "checkpoint", "nat", "ipsec", "wireshark",
    "aws", "azure", "gcp", "transit gateway", "vpc", "direct connect",
    "python", "ansible", "terraform", "bash", "git", "rest api",
    "infoblox", "dns", "dhcp", "ipam", "f5", "netscaler", "load balancer"
}

PREFERRED_TERMS = [
    "automation", "remote", "hybrid", "load balancer", "netscaler", "transit gateway",
    "24/7", "24x7", "24*7", "emea", "apac", "on-call", "on call"
]

APPROVED_INDIANA_CITIES = ["greenwood", "columbus", "indianapolis", "bloomington", "carmel"]

COMMON_INDIANA_CITIES = [
    "indianapolis", "columbus", "greenwood", "bloomington", "carmel",
    "fishers", "noblesville", "westfield", "fort wayne", "evansville",
    "south bend", "lafayette", "west lafayette", "terre haute", "muncie",
    "kokomo", "anderson", "elkhart", "mishawaka", "lawrence", "jeffersonville",
    "plainfield", "avon", "zionsville", "beech grove", "marion"
]

REMOTE_KEYWORDS = ["remote", "work from home", "wfh", "telecommute", "100% remote", "virtual"]
TRAVEL_KEYWORDS = ["field based", "field-based", "field remote", "road warrior", "telecommute with travel", "remote with travel"]
DEALBREAKERS = ["clearance required", "top secret", "unpaid"]

MAX_ALLOWED_TRAVEL_PCT = 20

GOVERNMENT_KEYWORDS = [
    "government", "public sector", "federal", "dod", "department of defense",
    "state agency", "municipal", "gov environment", "cleared environment"
]

# ==============================================================================
# 2. HELPER & SCRAPING FUNCTIONS
# ==============================================================================

def detect_government_environment(text):
    text_lower = text.lower()
    matched = [term.title() for term in GOVERNMENT_KEYWORDS if re.search(r"\b" + re.escape(term) + r"\b", text_lower)]
    return list(set(matched))

def fetch_jd_from_url(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()
            text = soup.get_text(separator=" ")
            clean_text = " ".join(text.split())
            if len(clean_text) < 150:
                return False, "Fetched content was too short. Page might require login or block scrapers."
            return True, clean_text
        else:
            return False, f"HTTP Error {response.status_code}: Unable to fetch URL."
    except Exception as e:
        return False, f"Connection Error: {str(e)}"

def detect_indiana_locations(text):
    """Refined double-checker to prevent capturing random prose text."""
    detected = set()
    
    # Require an explicit comma before IN/Indiana (e.g., "Indianapolis, IN")
    pattern = r"\b([A-Za-z\s]{3,20}),\s*(?:IN|Indiana)\b"
    matches = re.findall(pattern, text)
    
    ignore_list = {
        "in", "indiana", "state", "city", "join", "posted", "located", 
        "apply", "linked", "linkedin", "job", "jobs", "role", "work"
    }

    for m in matches:
        clean_name = m.strip().title()
        if clean_name.lower() not in ignore_list and len(clean_name) > 2:
            detected.add(clean_name)

    # Check against catalog of Indiana cities
    for city in COMMON_INDIANA_CITIES:
        if re.search(r"\b" + re.escape(city) + r"\b", text, re.IGNORECASE):
            detected.add(city.title())

    return sorted(list(detected))

def evaluate_location_and_workmode(text):
    text_lower = text.lower()
    is_remote = any(keyword in text_lower for keyword in REMOTE_KEYWORDS)
    found_approved_city = next((city for city in APPROVED_INDIANA_CITIES if city in text_lower), None)

    if is_remote:
        if found_approved_city:
            return True, f"Remote role (Based near {found_approved_city.title()}, IN)"
        return True, "Remote role (Location flexible across states)"

    if found_approved_city:
        return True, f"Approved local city detected: {found_approved_city.title()}, IN"

    return False, "Onsite/Hybrid role outside approved Indiana cities (Greenwood, Columbus, Indianapolis, Bloomington, Carmel)"

def extract_travel_info(text):
    pattern = r"(?:(\d{1,3})%\s*travel|travel[^\n]*?(\d{1,3})%)"
    matches = re.findall(pattern, text, re.IGNORECASE)
    percentages = [int(m[0] or m[1]) for m in matches if (m[0] or m[1])]
    detected_pct = max(percentages) if percentages else 0
    detected_terms = [t for t in TRAVEL_KEYWORDS if t.lower() in text.lower()]
    return detected_pct, detected_terms

def extract_uptime_percentage(text):
    pattern = r"\b(99\.\d+)%\s*(?:uptime|availability)?\b"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(0) if match else None

# ==============================================================================
# 3. STREAMLIT UI (MOBILE & ANDROID FRIENDLY)
# ==============================================================================

st.set_page_config(page_title="JD Matcher (Mobile)", page_icon="📱", layout="centered")

st.title("🎯 JD vs. Skillset Matcher")
st.caption("Paste a URL or raw job text to analyze qualifications, location, and dealbreakers.")

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Profile Settings")
    max_travel_limit = st.number_input("Max Allowed Travel (%)", min_value=0, max_value=100, value=MAX_ALLOWED_TRAVEL_PCT, step=5)
    st.divider()
    st.subheader("👤 My Profile Skills")
    for s in sorted([sk.title() for sk in MY_SKILLS]):
        st.write(f"- {s}")

# Tabs for Input Choice
tab_url, tab_text = st.tabs(["🔗 Analyze via URL", "📝 Paste Text JD"])

jd_text = ""

with tab_url:
    jd_url = st.text_input("Enter Job URL:", placeholder="https://example.com/job/123")
    if st.button("Fetch & Analyze URL", type="primary", use_container_width=True):
        if not jd_url.strip():
            st.warning("Please enter a URL first.")
        else:
            with st.spinner("Fetching job details..."):
                success, result = fetch_jd_from_url(jd_url)
                if success:
                    st.success("Successfully loaded job details!")
                    jd_text = result
                else:
                    st.error(f"❌ Scraping Failed: {result}")
                    st.info("💡 **Android Tip:** Sites like LinkedIn block automated requests. Use the **'Paste Text JD'** tab if this fails.")

with tab_text:
    pasted_text = st.text_area("Paste Full JD Text Here:", height=250)
    if st.button("Analyze Text JD", type="primary", use_container_width=True):
        if not pasted_text.strip():
            st.warning("Please paste text first.")
        else:
            jd_text = pasted_text

# ==============================================================================
# 4. RESULTS DISPLAY
# ==============================================================================

if jd_text:
    jd_lower = jd_text.lower()

    # Government environment check
    gov_terms = detect_government_environment(jd_text)

    # 1. Location & Double-Checker
    indiana_locations_found = detect_indiana_locations(jd_text)
    location_ok, location_status = evaluate_location_and_workmode(jd_text)

    # 2. Skills Comparison
    jd_skills_detected = {s for s in MASTER_SKILL_CATALOG if s.lower() in jd_lower}
    matched_skills = MY_SKILLS.intersection(jd_skills_detected)
    missing_skills = jd_skills_detected.difference(MY_SKILLS)
    unused_my_skills = MY_SKILLS.difference(jd_skills_detected)

    total_jd_skills = len(jd_skills_detected)
    match_score = int((len(matched_skills) / total_jd_skills) * 100) if total_jd_skills > 0 else 0

    # 3. Dynamic Travel & Uptime
    detected_travel_pct, detected_travel_terms = extract_travel_info(jd_text)
    detected_uptime = extract_uptime_percentage(jd_text)

    # 4. Dealbreakers
    found_dealbreakers = [term for term in DEALBREAKERS if term.lower() in jd_lower]
    if not location_ok:
        found_dealbreakers.append(f"Location Constraint: {location_status}")
    if detected_travel_pct > max_travel_limit:
        found_dealbreakers.append(f"High Travel Required ({detected_travel_pct}% exceeds {max_travel_limit}% limit)")

    # 5. Preferred Terms
    matched_preferred = [term for term in PREFERRED_TERMS if term.lower() in jd_lower]
    if detected_uptime:
        matched_preferred.append(f"Uptime Metric ({detected_uptime})")

    st.divider()

    # Government Warning Display
    if gov_terms:
        st.warning(f"🏛️ **Government / Public Sector Environment Detected:** {', '.join(gov_terms)}")

    # Dealbreakers Display
    if found_dealbreakers:
        st.error("⛔ **DEALBREAKERS DETECTED**")
        for db in found_dealbreakers:
            st.write(f"- ❌ {db}")
        st.divider()

    # Mobile Metric Grid (2x2)
    c1, c2 = st.columns(2)
    c1.metric("Match Score", f"{match_score}%")
    c2.metric("JD Skills Found", f"{total_jd_skills}")
    
    c3, c4 = st.columns(2)
    c3.metric("Your Skills Matched", f"{len(matched_skills)}")
    c4.metric("Travel Required", f"{detected_travel_pct}%" if detected_travel_pct > 0 else "None/Unlisted")

    st.divider()

    # Location Section
    st.subheader("📍 Location Analysis")
    if location_ok:
        st.success(f"✔ {location_status}")
    else:
        st.error(f"❌ {location_status}")

    if indiana_locations_found:
        st.info(f"🔍 **IN Double-Checker Found:** {', '.join(indiana_locations_found)}")
    else:
        st.write("🔍 **IN Double-Checker:** No explicit Indiana city detected.")

    st.divider()

    # Skills Breakdown
    st.subheader("✅ Qualifications Matched")
    if matched_skills:
        for sk in sorted(matched_skills):
            st.success(f"✔ **{sk.title()}**")
    else:
        st.write("None of your listed skills matched.")

    st.subheader("⚠️ Missing Requirements")
    if missing_skills:
        for sk in sorted(missing_skills):
            st.error(f"✖ **{sk.title()}**")
    else:
        st.info("🎉 You meet all requested qualifications!")

    st.subheader("⭐ Preferred Terms Found")
    st.write(", ".join([f"`{p.upper() if p in ['24/7', '24x7', '24*7', 'emea', 'apac'] else p.title()}`" for p in matched_preferred]) if matched_preferred else "None")

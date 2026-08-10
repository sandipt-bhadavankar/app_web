import re
import streamlit as st

# ==============================================================================
# 1. USER PROFILE, CERTIFICATIONS & LOCATION SETTINGS
# ==============================================================================

# Personal skill profile including certifications and technical skills
MY_SKILLS = {
    # Certifications
    "aws certified solutions architect – associate",
    "palo alto networks certified network security administrator (pcnsa)",
    "cisco certified network associate (ccna)",
    "pcnsa",
    "ccna",
    # Technical Skills
    "palo alto",
    "cisco",
    "aws",
    "bgp",
    "ospf",
    "nexus",
    "vpn",
    "firewall",
    "python",
    "wireshark",
    "infoblox",
}

# Master catalog used to detect what skills the Job Description requires
MASTER_SKILL_CATALOG = {
    # Certifications
    "aws certified solutions architect – associate",
    "palo alto networks certified network security administrator (pcnsa)",
    "cisco certified network associate (ccna)",
    "pcnsa",
    "ccna",
    "ccnp",
    "pcnsc",
    # Networking & Routing
    "cisco", "bgp", "ospf", "nexus", "juniper", "arista", "sd-wan", "mpls", "eigrp",
    # Security & Firewalls
    "palo alto", "firewall", "vpn", "fortinet", "checkpoint", "nat", "ipsec", "wireshark",
    # Cloud & Infrastructure
    "aws", "azure", "gcp", "transit gateway", "vpc", "direct connect",
    # Automation & Scripting
    "python", "ansible", "terraform", "bash", "git", "rest api",
    # Network Services & Load Balancing
    "infoblox", "dns", "dhcp", "ipam", "f5", "netscaler", "load balancer"
}

PREFERRED_TERMS = [
    "automation",
    "remote",
    "hybrid",
    "load balancer",
    "f5",
    "netscaler",
    "transit gateway",
]

# Approved Cities for Onsite / Hybrid roles
APPROVED_INDIANA_CITIES = [
    "greenwood",
    "columbus",
    "indianapolis",
    "bloomington",
    "carmel",
]

# Common Indiana cities catalog for the double-checker
COMMON_INDIANA_CITIES = [
    "indianapolis", "columbus", "greenwood", "bloomington", "carmel",
    "fishers", "noblesville", "westfield", "fort wayne", "evansville",
    "south bend", "lafayette", "west lafayette", "terre haute", "muncie",
    "kokomo", "anderson", "elkhart", "mishawaka", "lawrence", "jeffersonville",
    "plainfield", "avon", "zionsville", "greenwood", "beech grove", "marion"
]

REMOTE_KEYWORDS = [
    "remote",
    "work from home",
    "wfh",
    "telecommute",
    "100% remote",
    "virtual",
]

TRAVEL_KEYWORDS = [
    "field based",
    "field-based",
    "field remote",
    "road warrior",
    "telecommute with travel",
    "remote with travel",
]

# Updated Dealbreakers List
DEALBREAKERS = [
    "clearance required",
    "top secret",
    "unpaid",
]

MAX_ALLOWED_TRAVEL_PCT = 20


# ==============================================================================
# 2. HELPER FUNCTIONS
# ==============================================================================
def detect_indiana_locations(text):
    """
    Double-checker function: Extracts any Indiana city or 'City, IN / Indiana' pattern from the JD.
    """
    detected = set()

    # 1. Regex pattern for "City Name, IN" or "City Name, Indiana"
    pattern = r"\b([A-Za-z\s]{3,20}),?\s*(?:IN|Indiana)\b"
    matches = re.findall(pattern, text, re.IGNORECASE)
    for m in matches:
        clean_name = m.strip().title()
        if clean_name.lower() not in ["in", "indiana", "state"]:
            detected.add(clean_name)

    # 2. Match against catalog of Indiana cities
    for city in COMMON_INDIANA_CITIES:
        if re.search(r"\b" + re.escape(city) + r"\b", text, re.IGNORECASE):
            detected.add(city.title())

    return sorted(list(detected))


def evaluate_location_and_workmode(text):
    """
    Evaluates if the job location meets criteria:
    - Remote jobs are OK anywhere.
    - Onsite/Hybrid jobs MUST be in Greenwood, Columbus, Indianapolis, Bloomington, or Carmel.
    """
    text_lower = text.lower()

    # 1. Check if Remote
    is_remote = any(keyword in text_lower for keyword in REMOTE_KEYWORDS)

    # 2. Check for Approved Local Cities
    found_approved_city = next(
        (city for city in APPROVED_INDIANA_CITIES if city in text_lower), None
    )

    if is_remote:
        if found_approved_city:
            return True, f"Remote role (Based near {found_approved_city.title()}, IN)"
        return True, "Remote role (Location flexible across states)"

    if found_approved_city:
        return True, f"Approved local city detected: {found_approved_city.title()}, IN"

    # 3. Onsite/Hybrid role outside approved cities/states
    return False, "Onsite/Hybrid role outside approved Indiana cities (Greenwood, Columbus, Indianapolis, Bloomington, Carmel)"


def extract_travel_info(text):
    """Detects dynamic travel percentages and employer travel phrasing."""
    pattern = r"(?:(\d{1,3})%\s*travel|travel[^\n]*?(\d{1,3})%)"
    matches = re.findall(pattern, text, re.IGNORECASE)

    percentages = []
    for match in matches:
        num = match[0] or match[1]
        if num:
            percentages.append(int(num))

    detected_pct = max(percentages) if percentages else 0
    detected_terms = [t for t in TRAVEL_KEYWORDS if t.lower() in text.lower()]

    return detected_pct, detected_terms


def extract_uptime_percentage(text):
    """Captures uptime SLAs (e.g., '99.9%', '99.99%')."""
    pattern = r"\b(99\.\d+)%\s*(?:uptime|availability)?\b"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(0) if match else None


# ==============================================================================
# 3. STREAMLIT USER INTERFACE
# ==============================================================================
st.set_page_config(page_title="JD vs. Skillset Matcher", page_icon="🎯", layout="wide")

st.title("🎯 Job Description vs. My Skillset Matcher")
st.write("Paste a job description to evaluate matching skills, location/remote policy, travel requirements, and dealbreakers.")

# Sidebar - Profile & Approved Cities View
with st.sidebar:
    st.header("👤 My Profile & Qualifications")
    for skill in sorted([s.title() for s in MY_SKILLS]):
        st.write(f"- {skill}")

    st.divider()
    st.header("📍 Approved Local Cities")
    st.caption("Onsite/Hybrid roles must be in one of these locations:")
    for city in sorted([c.title() for c in APPROVED_INDIANA_CITIES]):
        st.write(f"- {city}, IN")

    st.divider()
    max_travel_limit = st.number_input(
        "Max Allowed Travel (%)",
        min_value=0,
        max_value=100,
        value=MAX_ALLOWED_TRAVEL_PCT,
        step=5,
    )

jd_input = st.text_area("Paste Job Description (JD) Here:", height=300)

if st.button("Analyze Job Description", type="primary"):
    if not jd_input.strip():
        st.warning("Please paste a job description first.")
    else:
        jd_lower = jd_input.lower()

        # 1. Double-Checker & Location Evaluation
        indiana_locations_found = detect_indiana_locations(jd_input)
        location_ok, location_status = evaluate_location_and_workmode(jd_input)

        # 2. Skill & Certification Comparison
        jd_skills_detected = {
            skill for skill in MASTER_SKILL_CATALOG if skill.lower() in jd_lower
        }

        matched_skills = MY_SKILLS.intersection(jd_skills_detected)
        missing_skills = jd_skills_detected.difference(MY_SKILLS)
        unused_my_skills = MY_SKILLS.difference(jd_skills_detected)

        # Score calculation
        total_jd_skills = len(jd_skills_detected)
        match_score = int((len(matched_skills) / total_jd_skills) * 100) if total_jd_skills > 0 else 0

        # 3. Dynamic Travel & Uptime Extraction
        detected_travel_pct, detected_travel_terms = extract_travel_info(jd_input)
        detected_uptime = extract_uptime_percentage(jd_input)

        # 4. Dealbreaker Checks
        found_dealbreakers = [term for term in DEALBREAKERS if term.lower() in jd_lower]

        if not location_ok:
            found_dealbreakers.append(f"Location Rule: {location_status}")

        if detected_travel_pct > max_travel_limit:
            found_dealbreakers.append(
                f"High Travel Required ({detected_travel_pct}% travel exceeds your {max_travel_limit}% limit)"
            )

        # 5. Preferred Terms Logic
        matched_preferred = [term for term in PREFERRED_TERMS if term.lower() in jd_lower]
        if detected_uptime:
            matched_preferred.append(f"Uptime Metric ({detected_uptime})")

        st.divider()

        # --- DISPLAY RESULTS ---

        # Dealbreaker Alert
        if found_dealbreakers:
            st.error("⛔ **DEALBREAKERS / LOCATION CONSTRAINTS DETECTED**")
            for db in found_dealbreakers:
                st.write(f"- ❌ {db}")
            st.divider()

        # Summary Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("JD Match Score", f"{match_score}%")
        col2.metric("JD Skills / Certs Requested", f"{total_jd_skills}")
        col3.metric("Your Qualifications Matched", f"{len(matched_skills)}")

        travel_display = (
            f"{detected_travel_pct}%"
            if detected_travel_pct > 0
            else ("Keywords Found" if detected_travel_terms else "None / Not Listed")
        )
        col4.metric("Detected Travel", travel_display)

        st.divider()

        # Location & Double-Checker Section
        st.subheader("📍 Location Analysis & Indiana Double-Checker")
        if location_ok:
            st.success(f"✔ **Work Arrangement:** {location_status}")
        else:
            st.error(f"❌ **Work Arrangement:** {location_status}")

        # Indiana Double-Checker Display
        if indiana_locations_found:
            st.info(f"🔍 **Indiana Locality Double-Checker:** Detected Indiana location(s) in JD: **{', '.join(indiana_locations_found)}**")
        else:
            st.write("🔍 **Indiana Locality Double-Checker:** No explicit Indiana city or 'City, IN' pattern detected.")

        if detected_travel_pct > 0 or detected_travel_terms:
            if detected_travel_pct > 0:
                st.write(f"- **Travel Required:** `{detected_travel_pct}%`")
            if detected_travel_terms:
                st.write(f"- **Phrasing Detected:** {', '.join([f'`{t.title()}`' for t in detected_travel_terms])}")

        st.divider()

        # Side-by-Side Skills Breakdown
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("✅ Qualifications Matched")
            if matched_skills:
                for skill in sorted(matched_skills):
                    st.success(f"✔ **{skill.title()}**")
            else:
                st.write("None of your listed skills/certifications matched this JD.")

            st.subheader("⭐ Preferred / Bonus Terms Found")
            if matched_preferred:
                st.write(", ".join([f"`{p.title()}`" for p in matched_preferred]))
            else:
                st.write("None")

        with col_right:
            st.subheader("⚠️ Missing Skills / Gap Areas")
            if missing_skills:
                for skill in sorted(missing_skills):
                    st.error(f"✖ **{skill.title()}** (Requested by JD, not in your profile)")
            else:
                st.info("🎉 No missing qualifications! You meet all detected JD requirements.")

            st.subheader("💡 Your Extra Skills & Certs")
            if unused_my_skills:
                st.write(", ".join([f"`{s.title()}`" for s in sorted(unused_my_skills)]))
            else:
                st.write("All your qualifications were requested by this JD!")
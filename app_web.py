import streamlit as st
import re
import urllib.request
from html.parser import HTMLParser

class HTMLFilter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.ignore = False

    def handle_starttag(self, tag, attrs):
        if tag in ["script", "style", "header", "footer", "nav"]:
            self.ignore = True

    def handle_endtag(self, tag):
        if tag in ["script", "style", "header", "footer", "nav"]:
            self.ignore = False

    def handle_data(self, data):
        if not self.ignore:
            self.text.append(data)

    def get_data(self):
        return " ".join(self.text)

REQUIRED_SKILLS = ["palo alto", "cisco", "aws", "bgp", "ospf", "nexus", "vpn", "firewall", "python", "wireshark", "infoblox"]
PREFERRED_TERMS = ["99.99%", "uptime", "automation", "remote", "hybrid", "load balancer", "f5", "netscaler", "transit gateway"]
DEALBREAKERS = ["clearance required", "top secret", "unpaid", "on-call 24/7"]

st.title("📱 Job Description Matcher")

url = st.text_input("Enter Job Description URL:")

if st.button("Analyze Link"):
    if not url:
        st.warning("Please enter a URL.")
    else:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                html_content = response.read().decode('utf-8', errors='ignore')
            
            parser = HTMLFilter()
            parser.feed(html_content)
            jd_clean = parser.get_data().lower()

            found_dealbreakers = [term for term in DEALBREAKERS if term in jd_clean]
            matched_skills = [skill for skill in REQUIRED_SKILLS if re.search(r'\b' + re.escape(skill) + r'\b', jd_clean)]
            missing_skills = [skill for skill in REQUIRED_SKILLS if skill not in matched_skills]
            matched_preferred = [pref for pref in PREFERRED_TERMS if pref in jd_clean]
            
            skill_score = (len(matched_skills) / len(REQUIRED_SKILLS)) * 100 if REQUIRED_SKILLS else 0

            if found_dealbreakers:
                st.error(f"⚠️ DEALBREAKERS FOUND: {', '.join(found_dealbreakers)}")
            else:
                st.success("✅ No dealbreakers detected.")

            st.metric("Overall Skill Match", f"{skill_score:.1f}%")
            st.write("**Matched Skills:**", ", ".join(matched_skills) if matched_skills else "None")
            st.write("**Missing Skills:**", ", ".join(missing_skills) if missing_skills else "None")
            st.write("**Preferred Terms Found:**", ", ".join(matched_preferred) if matched_preferred else "None")

        except Exception as e:
            st.error(f"Error fetching URL: {e}")
import streamlit as st
import trafilatura
import cloudscraper
import json
import requests
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ============================
# CONFIG
# ============================
OLLAMA_API_KEY = st.secrets["OLLAMA_CLOUD_API"]

# ============================
# FETCH WEBSITE
# ============================
def fetch_url(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        scraper = cloudscraper.create_scraper()
        html = scraper.get(url, headers=headers, timeout=15).text
        text = trafilatura.extract(html)

        return html, text or ""

    except Exception as e:
        return "", f"Error: {str(e)}"


# ============================
# BLOCK DETECTION
# ============================
def is_block_page(html):
    blockers = ["cloudflare", "checking your browser", "attention required"]
    return any(b in html.lower() for b in blockers)


# ============================
# TECH STACK DETECTOR
# ============================
def detect_stack(html):
    html = html.lower()

    patterns = {
        "WordPress": "wp-content",
        "Shopify": "cdn.shopify.com",
        "React": "react",
        "Next.js": "__next",
        "Vue.js": "vue",
        "Wix": "wix.com",
        "Google Analytics": "googletagmanager"
    }

    return [k for k, v in patterns.items() if v in html] or ["Unknown"]


# ============================
# SECURITY CHECKS
# ============================
def security_checks(html, url):
    return {
        "uses_https": url.startswith("https"),
        "has_login_form": "password" in html.lower(),
        "has_tracking_scripts": any(
            x in html.lower() for x in ["googletagmanager", "facebook.net", "hotjar"]
        ),
        "form_detected": "<form" in html.lower()
    }


# ============================
# AI ANALYSIS (CLOUD OLLAMA)
# ============================
def analyze_with_llm(text, url, stack, security):

    prompt = f"""
You are an expert startup analyst and cybersecurity researcher.

Analyze the website and return ONLY valid JSON:

{{
  "company_understanding": {{
    "company_name_guess": "",
    "core_business": "",
    "problem_it_solves": "",
    "how_it_works": "",
    "industry": "",
    "business_type": ""
  }},
  "business_analysis": {{
    "target_audience": "",
    "monetization_model": "",
    "value_proposition": ""
  }},
  "technical_signals": {{
    "detected_stack": {stack},
    "complexity": "low/medium/high"
  }},
  "security_and_trust": {{
    "trust_score": 0-100,
    "risk_flags": [],
    "reasoning": ""
  }},
  "seo_and_growth": {{
    "seo_quality": "",
    "growth_potential": ""
  }}
}}

URL: {url}
Security: {security}

CONTENT:
{text[:6000]}
"""

    res = requests.post(
        "https://ollama.com/api/chat",
        headers={
            "Authorization": f"Bearer {OLLAMA_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-oss:120b",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
    )

    try:
        content = res.json()["message"]["content"]
        return json.loads(content)
    except:
        return {"raw_output": res.text}


# ============================
# PDF BUILDER (PROFESSIONAL)
# ============================
def build_pdf_text(report, url):
    c = report.get("company_understanding", {})
    b = report.get("business_analysis", {})
    t = report.get("technical_signals", {})
    s = report.get("security_and_trust", {})
    g = report.get("seo_and_growth", {})

    return f"""
AI WEBSITE INTELLIGENCE REPORT

URL: {url}

============================
COMPANY UNDERSTANDING
============================
Name: {c.get('company_name_guess')}
Core Business: {c.get('core_business')}
Problem: {c.get('problem_it_solves')}
Industry: {c.get('industry')}
Type: {c.get('business_type')}

============================
BUSINESS ANALYSIS
============================
Audience: {b.get('target_audience')}
Monetization: {b.get('monetization_model')}
Value: {b.get('value_proposition')}

============================
TECH STACK
============================
{t.get('detected_stack')}
Complexity: {t.get('complexity')}

============================
TRUST & SECURITY
============================
Trust Score: {s.get('trust_score')}
Risks: {s.get('risk_flags')}
Reasoning: {s.get('reasoning')}

============================
GROWTH
============================
SEO: {g.get('seo_quality')}
Growth: {g.get('growth_potential')}
"""


# ============================
# PDF GENERATOR
# ============================
def generate_pdf(report, url):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)

    text = build_pdf_text(report, url)

    x = 40
    y = 800

    for line in text.split("\n"):
        if y < 50:
            p.showPage()
            y = 800
        p.drawString(x, y, line[:110])
        y -= 15

    p.save()
    buffer.seek(0)
    return buffer


# ============================
# STREAMLIT UI
# ============================
st.set_page_config(page_title="AI Website Intelligence", layout="wide")

st.title("🌐 AI Website Intelligence Engine (Pro + PDF)")

url = st.text_input("Enter website URL")

if st.button("Analyze Website") and url:

    with st.spinner("Fetching website..."):
        html, text = fetch_url(url)

    if not html:
        st.error("Failed to fetch website")
        st.stop()

    if is_block_page(html):
        st.error("Blocked by protection system")
        st.stop()

    with st.spinner("Analyzing structure..."):
        stack = detect_stack(html)
        security = security_checks(html, url)

    with st.spinner("Running AI analysis..."):
        report = analyze_with_llm(text, url, stack, security)

    # ============================
    # DISPLAY RESULTS
    # ============================
    st.subheader("🧠 Company Understanding")
    st.json(report.get("company_understanding", {}))

    st.subheader("📊 Business Analysis")
    st.json(report.get("business_analysis", {}))

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🛠 Tech Stack")
        st.write(stack)

        st.subheader("📈 Growth")
        st.json(report.get("seo_and_growth", {}))

    with col2:
        st.subheader("🔐 Security & Trust")
        st.json(report.get("security_and_trust", {}))

        st.subheader("⚠️ Raw Security Signals")
        st.json(security)

    # ============================
    # PDF SECTION
    # ============================
    st.subheader("📄 Professional Report Preview")

    preview = build_pdf_text(report, url)
    st.text_area("Preview", preview, height=400)

    pdf_file = generate_pdf(report, url)

    st.download_button(
        label="⬇️ Download PDF Report",
        data=pdf_file,
        file_name="website_intelligence_report.pdf",
        mime="application/pdf"
    )
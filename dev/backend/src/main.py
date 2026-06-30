import streamlit as st
import trafilatura
import cloudscraper
import json
import requests

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ----------------------------
# CONFIG
# ----------------------------
OLLAMA_API_KEY = st.secrets["OLLAMA_CLOUD_API"]

# ----------------------------
# FETCH WEBSITE
# ----------------------------
def fetch_url(url):
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
            )
        }

        scraper = cloudscraper.create_scraper()
        html = scraper.get(url, headers=headers, timeout=15).text
        text = trafilatura.extract(html)

        return html, text or ""

    except Exception as e:
        return "", f"Error: {str(e)}"


# ----------------------------
# BLOCK PAGE CHECK
# ----------------------------
def is_block_page(html):
    blockers = [
        "cloudflare",
        "checking your browser",
        "attention required",
        "cf-browser-verification"
    ]
    return any(b in html.lower() for b in blockers)


# ----------------------------
# TECH STACK DETECTION
# ----------------------------
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


# ----------------------------
# SECURITY SIGNALS
# ----------------------------
def security_checks(html, url):
    return {
        "uses_https": url.startswith("https"),
        "has_login_form": "password" in html.lower(),
        "has_tracking_scripts": any(
            x in html.lower() for x in ["googletagmanager", "facebook.net", "hotjar"]
        ),
        "form_detected": "<form" in html.lower()
    }


# ----------------------------
# LLM ANALYSIS (DEEP AI AGENT STYLE)
# ----------------------------
def analyze_with_llm(text, url, stack, security):

    prompt = f"""
You are an expert startup analyst, product strategist, and cybersecurity researcher.

Return ONLY valid JSON:

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

Security Signals:
{security}

Website Content:
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
        return {
            "raw_output": res.text,
            "error": "Failed to parse JSON"
        }


# ----------------------------
# PDF REPORT FORMAT (PROFESSIONAL)
# ----------------------------
def build_report_text(report, url):

    c = report.get("company_understanding", {})
    b = report.get("business_analysis", {})
    t = report.get("technical_signals", {})
    s = report.get("security_and_trust", {})
    g = report.get("seo_and_growth", {})

    return f"""
==============================
   WEBSITE INTELLIGENCE REPORT
==============================

URL: {url}

------------------------------
COMPANY UNDERSTANDING
------------------------------
Name: {c.get("company_name_guess", "")}
Core Business: {c.get("core_business", "")}
Problem Solved: {c.get("problem_it_solves", "")}
How It Works: {c.get("how_it_works", "")}
Industry: {c.get("industry", "")}
Business Type: {c.get("business_type", "")}

------------------------------
BUSINESS MODEL
------------------------------
Target Audience: {b.get("target_audience", "")}
Monetization: {b.get("monetization_model", "")}
Value Proposition: {b.get("value_proposition", "")}

------------------------------
TECHNICAL PROFILE
------------------------------
Stack: {t.get("detected_stack", "")}
Complexity: {t.get("complexity", "")}

------------------------------
SECURITY & TRUST
------------------------------
Trust Score: {s.get("trust_score", "")}
Risk Flags: {s.get("risk_flags", "")}
Reasoning: {s.get("reasoning", "")}

------------------------------
SEO & GROWTH
------------------------------
SEO Quality: {g.get("seo_quality", "")}
Growth Potential: {g.get("growth_potential", "")}

==============================
Generated by AI Intelligence Engine
==============================
"""


# ----------------------------
# PDF GENERATOR (FIXED)
# ----------------------------
def generate_pdf(report, url):

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)

    text = build_report_text(report, url)

    text = text.encode("ascii", "ignore").decode("ascii")

    y = 800
    for line in text.split("\n"):
        if y < 50:
            p.showPage()
            y = 800

        p.drawString(40, y, line[:110])
        y -= 14

    p.save()
    buffer.seek(0)
    return buffer


# ----------------------------
# STREAMLIT UI
# ----------------------------
st.set_page_config(page_title="AI Website Intelligence Engine", layout="wide")

st.title("🌐 AI Website Intelligence Engine (Investor-Grade)")

url = st.text_input("Enter website URL")

if st.button("Analyze Website") and url:

    with st.spinner("Fetching website..."):
        html, text = fetch_url(url)

    if not html:
        st.error("❌ Failed to fetch website")
        st.stop()

    if is_block_page(html):
        st.error("🚫 Blocked by security protection")
        st.stop()

    with st.spinner("Analyzing structure..."):
        stack = detect_stack(html)
        security = security_checks(html, url)

    with st.spinner("Running AI intelligence analysis..."):
        report = analyze_with_llm(text, url, stack, security)

    # ----------------------------
    # OUTPUT UI
    # ----------------------------
    st.subheader("🧠 Company Understanding")
    st.json(report.get("company_understanding", {}))

    st.subheader("📊 Business Analysis")
    st.json(report.get("business_analysis", {}))

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🛠 Technical Signals")
        st.json(report.get("technical_signals", {}))

        st.subheader("📦 Tech Stack (Detected)")
        st.write(stack)

    with col2:
        st.subheader("🔐 Security & Trust")
        st.json(report.get("security_and_trust", {}))

        st.subheader("⚠️ Security Signals (Raw)")
        st.json(security)

    st.subheader("📈 SEO & Growth")
    st.json(report.get("seo_and_growth", {}))

    if "raw_output" in report:
        st.subheader("🧾 Raw LLM Output (Debug)")
        st.text(report["raw_output"])

    # ----------------------------
    # PDF PREVIEW + DOWNLOAD (ADDED)
    # ----------------------------
    st.markdown("## 📄 Professional Report Export")

    pdf_buffer = generate_pdf(report, url)

    with st.expander("👀 Preview Report (Text Format)"):
        st.text(build_report_text(report, url))

    st.download_button(
        label="⬇️ Download PDF Report",
        data=pdf_buffer,
        file_name="website_intelligence_report.pdf",
        mime="application/pdf"
    )
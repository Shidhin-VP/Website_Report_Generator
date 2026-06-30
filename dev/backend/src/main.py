import streamlit as st
import trafilatura
import cloudscraper
import json
import os

from langchain_ollama import ChatOllama

# ----------------------------
# CONFIG
# ----------------------------
llm = ChatOllama(
    model='gpt-oss:120b-cloud', 
    client_kwargs={
        "headers":{
            "Authorization":f"Bearer {st.secrets['OLLAMA_CLOUD_API']}"
            # "Authorization":f"Bearer {os.getenv('OLLAMA_CLOUD_API')}"
        }
    }
)


# ----------------------------
# FETCH WEBSITE (ROBUST)
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
# BLOCK PAGE DETECTION
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
# TECH STACK DETECTOR
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
# SECURITY CHECKS
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
# LLM ANALYSIS (SAFE JSON)
# ----------------------------
def analyze_with_llm(text, url, stack, security):
    prompt = f"""
You are a website intelligence analyst.

Return ONLY valid JSON:

{{
  "summary": "",
  "what_it_does": "",
  "products_or_services": [],
  "target_audience": "",
  "monetization_model": "",
  "seo_quality": "",
  "security_risks": [],
  "trust_score": 0-100
}}

URL: {url}

Tech Stack: {stack}
Security: {security}

CONTENT:
{text[:6000]}
"""

    response = llm.invoke(prompt)
    content = response.content

    try:
        return json.loads(content)
    except:
        return {
            "raw_output": content,
            "error": "JSON parsing failed"
        }


# ----------------------------
# STREAMLIT UI
# ----------------------------
st.set_page_config(page_title="Website Intelligence AI", layout="wide")

st.title("🌐 Website Intelligence Report Generator")

url = st.text_input("Enter website URL")

if st.button("Analyze Website") and url:

    with st.spinner("Fetching website..."):
        html, text = fetch_url(url)

    if not html:
        st.error("❌ Failed to fetch website")
        st.stop()

    if is_block_page(html):
        st.error("🚫 Website blocked by Cloudflare / bot protection. Cannot analyze real content.")
        st.stop()

    with st.spinner("Analyzing structure..."):
        stack = detect_stack(html)
        security = security_checks(html, url)

    with st.spinner("Running AI analysis..."):
        report = analyze_with_llm(text, url, stack, security)

    # ----------------------------
    # OUTPUT
    # ----------------------------

    st.subheader("📊 Summary")
    st.write(report.get("summary", "No summary available"))

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🧠 What it does")
        st.write(report.get("what_it_does", "N/A"))

        st.subheader("🛠 Tech Stack")
        st.write(stack)

        st.subheader("📦 Products / Services")
        st.write(report.get("products_or_services", []))

    with col2:
        st.subheader("🔐 Security Signals")
        st.json(security)

        st.subheader("⭐ Trust Score")
        st.metric("Score", report.get("trust_score", "N/A"))

        st.subheader("⚠️ Security Risks")
        st.write(report.get("security_risks", []))

    if "raw_output" in report:
        st.subheader("🧾 Raw LLM Output (Debug)")
        st.text(report["raw_output"])
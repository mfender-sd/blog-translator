import streamlit as st
import anthropic
import zipfile
import io
from datetime import datetime
import os

# Page config
st.set_page_config(
    page_title="Marvel Snap Blog Translator",
    page_icon="🎮",
    layout="wide"
)

# Language mapping
LANGUAGES = {
    'spa': 'Spanish',
    'spa-M9': 'Spanish Mexico',
    'tha': 'Thai',
    'zho-CN': 'Simplified Chinese',
    'zho-TW': 'Traditional Chinese',
    'fre': 'French',
    'ger': 'German',
    'ita': 'Italian',
    'jpn': 'Japanese',
    'kor': 'Korean',
    'por-BR': 'Portuguese Brazil',
    'rus': 'Russian'
}

def init_anthropic():
    """Initialize Anthropic client with API key"""
    api_key = st.secrets.get("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY"))
    if not api_key:
        st.error("⚠️ Please set up your Anthropic API key in Streamlit secrets")
        st.info("Go to Settings → Secrets and add: ANTHROPIC_API_KEY = 'your-key-here'")
        return None
    return anthropic.Anthropic(api_key=api_key)

def read_file_content(uploaded_file):
    """Read content from uploaded file"""
    try:
        content = uploaded_file.read()
        if uploaded_file.name.endswith('.txt'):
            return content.decode('utf-8')
        elif uploaded_file.name.endswith('.docx'):
            # For docx files, we'll need python-docx
            import docx
            doc = docx.Document(io.BytesIO(content))
            return '\n'.join([para.text for para in doc.paragraphs])
        else:
            return content.decode('utf-8')
    except Exception as e:
        st.error(f"Error reading {uploaded_file.name}: {str(e)}")
        return None

def translate_blog(client, english_html, translations):
    """Translate blog into all languages using Claude"""
    results = {}
    
    # Create the prompt
    prompt = f"""You're an expert WordPress user and blog translator for MARVEL SNAP. 
I have the English HTML blog and translations for 12 languages.

IMPORTANT RULES:
1. Keep the EXACT HTML formatting from the English version
2. Only replace the English text with the provided translations
3. Do NOT add or remove any HTML tags, classes, or attributes
4. Use only the officially provided translations

English HTML:
{english_html}

Translations provided:
"""
    
    # Add all translations to the prompt
    for lang_code, content in translations.items():
        if content:
            prompt += f"\n\n{LANGUAGES.get(lang_code, lang_code)}:\n{content}"
    
    # Process each language
    for lang_code, lang_name in LANGUAGES.items():
        if lang_code not in translations or not translations[lang_code]:
            st.warning(f"⚠️ No translation file for {lang_name}")
            continue
            
        try:
            with st.spinner(f"Translating to {lang_name}..."):
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=8000,
                    messages=[{
                        "role": "user",
                        "content": f"{prompt}\n\nNow create the {lang_name} ({lang_code}) version. Return ONLY the HTML code, no explanations."
                    }]
                )
                results[lang_code] = response.content[0].text
                st.success(f"✅ {lang_name} complete")
        except Exception as e:
            st.error(f"❌ Error translating {lang_name}: {str(e)}")
    
    return results

def create_zip_file(translations):
    """Create a ZIP file with all translations"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for lang_code, content in translations.items():
            filename = f"marvel_snap_blog_{lang_code}.html"
            zip_file.writestr(filename, content)
    
    zip_buffer.seek(0)
    return zip_buffer

# Main UI
st.title("🎮 Marvel Snap Blog Translator")
st.markdown("Translate your Marvel Snap blog into 12 languages with perfect HTML formatting!")

# Instructions
with st.expander("📋 Instructions", expanded=True):
    st.markdown("""
    1. **Paste your English HTML** in the text area below
    2. **Upload all 12 translation files** (txt or docx format)
    3. **Click 'Translate All Languages'** and wait for processing
    4. **Download** individual files or all as ZIP
    
    **Required files:** spa, spa-M9, tha, zho-CN, zho-TW, fre, ger, ita, jpn, kor, por-BR, rus
    """)

# Initialize session state
if 'translations' not in st.session_state:
    st.session_state.translations = {}

# Input section
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 English HTML")
    english_html = st.text_area(
        "Paste your English blog HTML here",
        height=400,
        help="Copy the entire HTML code from WordPress"
    )

with col2:
    st.subheader("📁 Translation Files")
    uploaded_files = st.file_uploader(
        "Upload translation files",
        accept_multiple_files=True,
        type=['txt', 'docx'],
        help="Select all 12 translation files at once"
    )
    
    if uploaded_files:
        st.info(f"📎 {len(uploaded_files)} files uploaded")
        
        # Show which languages are uploaded
        uploaded_langs = []
        for file in uploaded_files:
            for lang_code in LANGUAGES.keys():
                if lang_code in file.name:
                    uploaded_langs.append(lang_code)
                    break
        
        missing_langs = set(LANGUAGES.keys()) - set(uploaded_langs)
        if missing_langs:
            st.warning(f"⚠️ Missing: {', '.join(missing_langs)}")

# Translate button
if st.button("🚀 Translate All Languages", type="primary", use_container_width=True):
    if not english_html:
        st.error("Please paste the English HTML first!")
    elif not uploaded_files:
        st.error("Please upload translation files!")
    else:
        # Initialize API client
        client = init_anthropic()
        if not client:
            st.stop()
        
        # Read all translation files
        translations = {}
        for file in uploaded_files:
            # Identify language from filename
            lang_code = None
            for code in LANGUAGES.keys():
                if code in file.name:
                    lang_code = code
                    break
            
            if lang_code:
                content = read_file_content(file)
                if content:
                    translations[lang_code] = content
        
        # Perform translations
        st.markdown("### 🔄 Processing Translations")
        progress_bar = st.progress(0)
        
        results = translate_blog(client, english_html, translations)
        st.session_state.translations = results
        
        progress_bar.progress(100)
        st.success(f"✅ Completed {len(results)} translations!")

# Results section
if st.session_state.translations:
    st.markdown("---")
    st.markdown("### 📥 Download Translations")
    
    # Download all as ZIP
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        zip_file = create_zip_file(st.session_state.translations)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            label="⬇️ Download All as ZIP",
            data=zip_file,
            file_name=f"marvel_snap_translations_{timestamp}.zip",
            mime="application/zip",
            use_container_width=True
        )
    
    # Individual downloads
    st.markdown("#### Individual Files:")
    cols = st.columns(3)
    for idx, (lang_code, content) in enumerate(st.session_state.translations.items()):
        with cols[idx % 3]:
            st.download_button(
                label=f"📄 {LANGUAGES[lang_code]}",
                data=content,
                file_name=f"blog_{lang_code}.html",
                mime="text/html",
                key=f"download_{lang_code}"
            )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        Made for Marvel Snap content team | 
        <a href='https://github.com/yourusername/marvel-snap-translator' target='_blank'>Documentation</a>
    </div>
    """,
    unsafe_allow_html=True
)

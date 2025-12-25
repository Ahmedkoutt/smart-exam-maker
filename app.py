import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import re
from io import BytesIO

# --- Page Config ---
st.set_page_config(
    page_title="Q-BANK PRO",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for RTL & Styling ---
st.markdown("""
<style>
    .main {direction: rtl; text-align: right;}
    .stTextInput > div > div > input {text-align: right;}
    .stChatMessage {direction: rtl; text-align: right;}
    div[data-testid="stSidebarUserContent"] {text-align: right;}
    h1, h2, h3, p {font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;}
    .question-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #ddd;
        margin-bottom: 15px;
        color: #1f2937;
    }
    .correct-answer {
        color: #15803d;
        font-weight: bold;
        font-size: 0.9em;
        margin-top: 10px;
        border-top: 1px dashed #ccc;
        padding-top: 5px;
    }
    .footer {
        position: fixed; bottom: 0; left: 0; right: 0;
        background: white; padding: 10px; text-align: center;
        border-top: 1px solid #eee; font-size: 12px; color: #666;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "questions" not in st.session_state:
    st.session_state.questions = []

# --- Helper Functions ---
def extract_text_from_pdf(uploaded_file):
    try:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        return text
    except Exception as e:
        st.error(f"خطأ في قراءة الملف: {e}")
        return None

def parse_questions(text):
    regex = r":::سؤال:::([\s\S]*?):::نهاية:::"
    matches = re.findall(regex, text)
    new_questions = []
    for match in matches:
        parts = [p.strip() for p in match.split('||')]
        if len(parts) >= 3:
            new_questions.append({
                "question": parts[0],
                "options": parts[1:-1],
                "answer": parts[-1]
            })
    return new_questions

# --- Sidebar ---
with st.sidebar:
    st.title("🎓 Q-BANK PRO")
    
    # API Key Handling
    api_key = st.text_input("Gemini API Key", type="password", placeholder="ضع المفتاح هنا...")
    if api_key:
        genai.configure(api_key=api_key)
    
    st.markdown("---")
    
    # Upload
    uploaded_file = st.file_uploader("رفع ملف PDF", type=['pdf'])
    if uploaded_file and not st.session_state.pdf_text:
        with st.spinner("جاري استخراج النصوص (PyMuPDF)..."):
            text = extract_text_from_pdf(uploaded_file)
            if text:
                st.session_state.pdf_text = text
                st.success(f"تم تحليل: {uploaded_file.name}")
                st.session_state.messages.append({"role": "assistant", "content": "تم رفع الملف بنجاح! يمكنك الآن طلب توليد أسئلة."})

    st.markdown("---")
    
    # Settings
    difficulty = st.selectbox("مستوى الصعوبة", ["سهل", "متوسط", "صعب"])
    q_type = st.selectbox("نوع الأسئلة", ["mix", "mcq", "truefalse"])
    
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.session_state.questions = []
        st.rerun()

    st.markdown("---")
    st.markdown("""
    <div style="text-align: center;">
        <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Ahmed" width="50" style="border-radius:50%">
        <p style="font-size: 12px; margin-top: 5px;">Developed by<br><b>أحمد قط جادالله</b></p>
    </div>
    """, unsafe_allow_html=True)

# --- Main Logic ---

# Tabs
tab1, tab2 = st.tabs(["💬 المحادثة والتوليد", "📝 عرض الأسئلة"])

with tab1:
    # Display Chat
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input
    if prompt := st.chat_input("اطلب توليد أسئلة أو اسأل عن المحتوى..."):
        if not api_key:
            st.warning("يرجى إدخال API Key أولاً!")
        elif not st.session_state.pdf_text:
            st.warning("يرجى رفع ملف PDF أولاً!")
        else:
            # User Message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Generate Response
            is_exam_request = any(w in prompt for w in ["ولد", "اسئلة", "اختبار", "quiz"])
            
            full_prompt = f"""
            Context: You are an expert educational AI.
            Document Content: {st.session_state.pdf_text[:30000]}...
            
            User Request: {prompt}
            """
            
            if is_exam_request:
                full_prompt += f"""
                \nINSTRUCTION: Generate {difficulty} questions of type {q_type}.
                OUTPUT PATTERN STRICTLY:
                :::سؤال::: [Question Text] || [Option A] || [Option B] || [Option C] || [Correct Answer] :::نهاية:::
                
                Rules:
                1. Separator must be "||".
                2. Language: Arabic.
                3. Do NOT use Markdown code blocks. Just raw text.
                """

            try:
                with st.spinner("جاري التواصل مع Gemini..."):
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content(full_prompt)
                    bot_reply = response.text
                    
                    # Parse Questions if found
                    extracted_qs = parse_questions(bot_reply)
                    if extracted_qs:
                        st.session_state.questions.extend(extracted_qs)
                        bot_reply = f"تم توليد {len(extracted_qs)} سؤال بنجاح! انتقل لتبويب 'عرض الأسئلة' لمشاهدتها."

                    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                    with st.chat_message("assistant"):
                        st.markdown(bot_reply)
            except Exception as e:
                st.error(f"حدث خطأ: {e}")

with tab2:
    if not st.session_state.questions:
        st.info("لا توجد أسئلة مولدة بعد. اذهب للشات واطلب: 'ولد لي 5 أسئلة'.")
    else:
        # Header for Print
        st.markdown("### 📄 ورقة الأسئلة")
        
        # Questions Loop
        for i, q in enumerate(st.session_state.questions):
            st.markdown(f"""
            <div class="question-card">
                <div style="font-weight:bold; margin-bottom:10px;">س{i+1}: {q['question']}</div>
                {''.join([f'<div style="margin:5px 0;">⚪ {opt}</div>' for opt in q['options']])}
                <div class="correct-answer">الإجابة الصحيحة: {q['answer']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Delete Button
            if st.button(f"حذف السؤال {i+1}", key=f"del_{i}"):
                st.session_state.questions.pop(i)
                st.rerun()



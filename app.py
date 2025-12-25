import streamlit as st
import fitz  # PyMuPDF
import re
import random

# --- 1. إعدادات الصفحة ---
st.set_page_config(
    page_title="Pro Exam | Ahmed Jadallah",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS للتصميم والطباعة ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
    }

    /* إخفاء العناصر الافتراضية */
    #MainMenu, footer, header {visibility: hidden;}

    /* تنسيق ورقة الأسئلة (التي ستكون على اليسار) */
    .paper-container {
        background: white;
        padding: 40px;
        border: 1px solid #ddd;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        color: black;
        min-height: 800px;
        position: relative;
    }

    .question-block {
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 1px dashed #eee;
        page-break-inside: avoid;
    }

    .answer-key {
        margin-top: 50px;
        border-top: 3px double #000;
        padding-top: 20px;
        page-break-before: always;
    }

    /* تحسين شكل الشات */
    .stChatInput {
        z-index: 100;
    }

    /* الطباعة */
    @media print {
        .no-print, .stButton, .stChatInput, header, footer, .stColumn:first-child {
            display: none !important;
        }
        .paper-container {
            border: none;
            box-shadow: none;
            width: 100%;
            padding: 0;
            margin: 0;
        }
        body {
            background-color: white;
            font-size: 12pt;
        }
        .footer-watermark {
            position: fixed;
            bottom: 0;
            width: 100%;
            text-align: center;
            font-weight: bold;
            font-size: 10pt;
            border-top: 1px solid #000;
            padding-top: 5px;
            display: block !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- 3. دوال المعالجة الذكية ---

def parse_pdf_structure(uploaded_file):
    """قراءة ملف PDF واستخراج الفهرس والفصول"""
    try:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        toc = doc.get_toc()
        for page in doc:
            full_text += page.get_text()
            
        chapters = []
        if toc:
            for item in toc:
                chapters.append({"title": item[1], "page": item[2]})
        else:
            # بحث يدوي محسن عن الفصول
            patterns = [r'(الفصل\s+\w+)', r'(الباب\s+\w+)', r'(الوحدة\s+\w+)']
            found = []
            for pat in patterns:
                found.extend(re.findall(pat, full_text[:10000]))
            
            unique_ch = sorted(list(set(found)))
            for ch in unique_ch:
                chapters.append({"title": ch, "page": 1})

        return doc, full_text, chapters
    except Exception as e:
        return None, None, []

def generate_comprehensive_questions(doc, full_text, chapter_title, question_mode):
    """توليد أسئلة شاملة لكل فقرة"""
    # تحديد النص المستهدف
    target_text = full_text
    if chapter_title and chapter_title in full_text:
        start_idx = full_text.find(chapter_title)
        # نأخذ جزء كبير لضمان تغطية الفصل
        target_text = full_text[start_idx : start_idx + 20000]

    # تنظيف
    clean_text = re.sub(r'\s+', ' ', target_text)
    sentences = re.split(r'[.!?؟]', clean_text)
    
    # جمل صالحة للأسئلة
    valid_sentences = [s.strip() for s in sentences if 25 < len(s.strip()) < 350]
    
    questions = []
    
    for i, sent in enumerate(valid_sentences):
        q_id = i + 1
        q_type = "mcq" if i % 2 == 0 else "tf" # توزيع متساوٍ
        
        if q_type == "mcq":
            words = sent.split()
            if len(words) > 5:
                # محاولة إيجاد كلمة مفتاحية (طويلة)
                candidates = [w for w in words if len(w) > 4]
                if candidates:
                    answer = random.choice(candidates)
                    q_text = sent.replace(answer, ".......")
                    
                    # إنشاء خيارات مشتتة من نفس النص لزيادة الصعوبة
                    pool = " ".join(valid_sentences).split()
                    distractors = random.sample([w for w in pool if len(w)>4 and w!=answer], 3)
                    
                    options = [answer] + distractors
                    random.shuffle(options)
                    
                    questions.append({
                        "id": q_id, "type": "اختيار من متعدد", "text": f"أكمل: {q_text}", 
                        "options": options, "answer": answer
                    })
        else:
            # صح وخطأ
            questions.append({
                "id": q_id, "type": "صح أم خطأ", "text": f"ضع علامة (صح) أو (خطأ): {sent}", 
                "options": [], "answer": "صح"
            })
            
    return questions

# --- 4. إدارة الحالة ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "content": "مرحباً! أنا جاهز. ارفع الكتاب وسأستخرج لك الفصول فوراً."}]
if "exam_data" not in st.session_state:
    st.session_state.exam_data = []
if "chapters_list" not in st.session_state:
    st.session_state.chapters_list = []
if "full_text" not in st.session_state:
    st.session_state.full_text = None
if "doc_obj" not in st.session_state:
    st.session_state.doc_obj = None
if "answer_mode" not in st.session_state:
    st.session_state.answer_mode = "بدون إجابات"

# --- 5. تخطيط الواجهة (Layout) ---

# هنا التعديل الجوهري:
# في الـ CSS العربية (RTL): العمود الأول يظهر يمين، الثاني يظهر يسار.
# col_chat (يمين) | col_paper (يسار)
col_chat, col_paper = st.columns([1, 2])

# ==========================================
# 1. العمود الأيمن: البوت والشات (col_chat)
# ==========================================
with col_chat:
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    st.header("🤖 المحادثة")

    # رفع الملف
    if not st.session_state.full_text:
        uploaded_file = st.file_uploader("ارفع الكتاب (PDF)", type="pdf")
        if uploaded_file:
            with st.spinner("جاري تحليل الهيكل..."):
                doc, text, chapters = parse_pdf_structure(uploaded_file)
                st.session_state.doc_obj = doc
                st.session_state.full_text = text
                st.session_state.chapters_list = chapters
                st.session_state.chat_history.append({"role": "assistant", "content": f"تم! وجدت {len(chapters)} فصلاً. اختر واحداً من الأسفل لتغطية شاملة."})
                st.rerun()

    # حاوية الشات
    chat_container = st.container(height=500)
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        
        # أزرار الفصول التفاعلية
        if st.session_state.chapters_list:
            st.write("---")
            st.caption("اضغط لتوليد أسئلة شاملة للفصل:")
            # عرض الأزرار
            for idx, ch in enumerate(st.session_state.chapters_list):
                # زر بعرض كامل
                if st.button(f"📄 {ch['title']}", key=f"btn_{idx}", use_container_width=True):
                    st.session_state.chat_history.append({"role": "user", "content": f"أريد أسئلة شاملة عن {ch['title']}"})
                    
                    with st.spinner(f"جاري مسح {ch['title']} واستخراج كل التفاصيل..."):
                        qs = generate_comprehensive_questions(
                            st.session_state.doc_obj, 
                            st.session_state.full_text, 
                            ch['title'], 
                            "mix"
                        )
                        st.session_state.exam_data = qs
                        st.session_state.chat_history.append({"role": "assistant", "content": f"✅ تم استخراج {len(qs)} سؤالاً يغطي الفصل بالكامل. انظر لليسار."})
                        st.rerun()

    # إدخال يدوي
    user_txt = st.chat_input("أو اكتب طلبك هنا...")
    if user_txt:
        st.session_state.chat_history.append({"role": "user", "content": user_txt})
        if st.session_state.full_text:
            qs = generate_comprehensive_questions(st.session_state.doc_obj, st.session_state.full_text, user_txt, "mix")
            st.session_state.exam_data = qs
            st.session_state.chat_history.append({"role": "assistant", "content": f"تم توليد {len(qs)} سؤال."})
            st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)


# ==========================================
# 2. العمود الأيسر: ورقة الأسئلة (col_paper)
# ==========================================
with col_paper:
    # شريط التحكم (طباعة + ترس)
    st.markdown('<div class="no-print" style="margin-bottom:15px; display:flex; justify-content: space-between; align-items:center; background:#f9f9f9; padding:10px; border-radius:8px;">', unsafe_allow_html=True)
    
    # زر الطباعة
    st.markdown("""
    <button onclick="window.print()" style="background:#1a237e; color:white; border:none; padding:8px 20px; border-radius:5px; cursor:pointer; font-weight:bold; font-family:inherit;">
    🖨️ طباعة الورقة
    </button>
    """, unsafe_allow_html=True)

    # ترس الإعدادات (Popover)
    with st.popover("⚙️ خيارات الإجابة"):
        st.write("اختر نمط نموذج الإجابة:")
        mode = st.radio(
            "النمط",
            ["بدون إجابات", "إرفاق نموذج إجابة (آخر الورقة)", "مجاب عنها (للمذاكرة)"],
            index=0,
            key="ans_mode_radio"
        )
        if mode != st.session_state.answer_mode:
            st.session_state.answer_mode = mode
            st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)

    # === جسم الورقة ===
    if st.session_state.exam_data:
        st.markdown('<div class="paper-container">', unsafe_allow_html=True)
        
        # الترويسة
        st.markdown(f"""
        <div style="text-align:center; border-bottom:2px solid #000; padding-bottom:15px; margin-bottom:20px;">
            <h2 style="margin:0; color:#000;">اختبار تقييم شامل</h2>
            <p style="margin:5px 0;">عدد الأسئلة: {len(st.session_state.exam_data)} | الدرجة: _____</p>
        </div>
        """, unsafe_allow_html=True)

        # عرض الأسئلة
        for q in st.session_state.exam_data:
            show_inline = (st.session_state.answer_mode == "مجاب عنها (للمذاكرة)")
            
            # بلوك السؤال
            st.markdown(f"""<div class="question-block">
                <div style="font-weight:bold; margin-bottom:8px; line-height:1.6;">
                    {q['id']}. {q['text']}
                    {f'<span style="color:#c62828; font-size:0.9em; margin-right:10px;">(الإجابة: {q["answer"]})</span>' if show_inline else ''}
                </div>""", unsafe_allow_html=True)
            
            # الخيارات
            if q['type'] == 'اختيار من متعدد':
                opts_html = ""
                for opt in q['options']:
                    is_correct = (show_inline and opt == q['answer'])
                    style = "font-weight:bold; text-decoration:underline; color:#1565c0;" if is_correct else ""
                    opts_html += f'<span style="margin-left:20px; display:inline-block; {style}">❍ {opt}</span>'
                st.markdown(f'<div style="color:#333;">{opts_html}</div>', unsafe_allow_html=True)
            else:
                tf_html = '(   ) صح &nbsp;&nbsp;&nbsp;&nbsp; (   ) خطأ'
                if show_inline:
                    tf_html = f'<span style="font-weight:bold; color:#1565c0;">الإجابة الصحيحة: {q["answer"]}</span>'
                st.markdown(f'<div>{tf_html}</div>', unsafe_allow_html=True)
                
            st.markdown('</div>', unsafe_allow_html=True)

        # نموذج الإجابة المنفصل
        if st.session_state.answer_mode == "إرفاق نموذج إجابة (آخر الورقة)":
            st.markdown('<div class="answer-key">', unsafe_allow_html=True)
            st.markdown("<h3 style='text-align:center;'>نموذج الإجابات</h3>", unsafe_allow_html=True)
            
            # بناء الجدول
            rows = ""
            for q in st.session_state.exam_data:
                rows += f"<tr><td style='border:1px solid #ccc; padding:5px;'>{q['id']}</td><td style='border:1px solid #ccc; padding:5px;'>{q['answer']}</td></tr>"
            
            st.markdown(f"""
            <table style="width:100%; border-collapse:collapse; text-align:center; font-size:14px;">
                <tr style="background:#eee;">
                    <th style="border:1px solid #ccc; padding:8px;">س</th>
                    <th style="border:1px solid #ccc; padding:8px;">ج</th>
                </tr>
                {rows}
            </table>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # التذييل
        st.markdown("""
        <div class="footer-watermark" style="display:none;">
            إعداد وتصميم: احمد قط جادالله | Ahmed Koutt Jadallah
        </div>
        </div>
        """, unsafe_allow_html=True)
        
    else:
        st.info("👈 اختر فصلاً من الشات (على اليمين) لعرض الأسئلة هنا.")


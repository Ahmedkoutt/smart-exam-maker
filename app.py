import streamlit as st
import fitz  # PyMuPDF
import random
import re
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- 1. إعدادات الصفحة والتصميم الاحترافي ---
st.set_page_config(
    page_title="Pro Exam Creator | Ahmed Jadallah",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed" # إخفاء الشريط الجانبي افتراضياً
)

# نظام الألوان والثيم (Dark Blue & Gold Theme)
st.markdown("""
<style>
    /* استيراد خط عربي احترافي */
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
    }

    /* إخفاء العلامات المائية وعناصر التحكم الافتراضية */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}

    /* خلفية التطبيق */
    .stApp {
        background-color: #f8f9fa;
    }

    /* تصميم عمود المحادثة (اليمين) */
    .chat-container {
        background-color: #ffffff;
        border-left: 1px solid #e0e0e0;
        height: 100vh;
    }

    /* رسائل المستخدم والبوت */
    .stChatMessage {
        background-color: transparent;
        border: none;
    }
    .stChatMessage[data-testid="user-message"] {
        background-color: #e3f2fd;
        border-radius: 15px 15px 0 15px;
        padding: 10px;
        margin: 5px 0;
    }
    div[data-testid="stChatMessageContent"] {
        color: #1a237e; /* أزرق داكن */
    }

    /* تصميم ورقة الأسئلة (اليسار) */
    .paper-view {
        background-color: white;
        color: #000;
        padding: 50px;
        border: 1px solid #d1d5db;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        min-height: 850px;
        position: relative;
        margin-top: 20px;
    }

    .paper-header {
        border-bottom: 3px double #1a237e;
        margin-bottom: 30px;
        padding-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .question-box {
        margin-bottom: 20px;
        padding: 15px;
        border-right: 4px solid #1a237e;
        background-color: #fcfcfc;
    }

    /* الأزرار */
    .stButton button {
        background-color: #1a237e;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton button:hover {
        background-color: #283593;
        transform: scale(1.02);
    }
    
    /* حقوق الملكية */
    .watermark {
        text-align: center;
        margin-top: 50px;
        padding-top: 10px;
        border-top: 1px solid #ccc;
        font-size: 14px;
        color: #1a237e;
        font-weight: bold;
        opacity: 0.8;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. المنطق البرمجي (Backend Simulation) ---

def extract_text(uploaded_file):
    """استخراج النصوص من ملف PDF"""
    if not uploaded_file: return None
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def parse_user_intent(message):
    """تحليل رسالة المستخدم لاستخراج الأرقام (عدد الأسئلة) والفصل"""
    # البحث عن أرقام في الرسالة
    numbers = re.findall(r'\d+', message)
    count = int(numbers[0]) if numbers else 35 # الافتراضي 35 سؤال
    
    # تحديد النطاق (35 - 100)
    count = max(35, min(count, 100))
    
    # البحث عن كلمة "فصل" وما بعدها
    chapter_match = re.search(r'الفصل\s+(\w+)', message)
    chapter = f"الفصل {chapter_match.group(1)}" if chapter_match else None
    
    return count, chapter

def generate_exam_content(text, count, chapter_filter=None):
    """
    الخوارزمية الأساسية لتوليد الأسئلة.
    البرومبت: "أي معلومة أو سطر يمكن صياغته كسؤال. Mix بين اختيار من متعدد وصح وخطأ فقط."
    """
    # تنظيف النص وتقسيمه
    clean_text = re.sub(r'\s+', ' ', text)
    
    # محاولة الفلترة حسب الفصل (محاكاة بسيطة)
    target_text = clean_text
    if chapter_filter and chapter_filter in clean_text:
        start = clean_text.find(chapter_filter)
        target_text = clean_text[start : start + 50000] # نأخذ جزء كبير بعد بداية الفصل
    
    # تقسيم النص لجمل مفيدة
    sentences = re.split(r'[.!?؟]', target_text)
    # تصفية الجمل: يجب أن تكون بطول مناسب وتحتوي على معلومات
    valid_sentences = [s.strip() for s in sentences if 30 < len(s.strip()) < 200 and not s.strip().isdigit()]
    
    # خلط الجمل لضمان العشوائية
    random.shuffle(valid_sentences)
    
    final_questions = []
    
    # حلقة التوليد
    for i, sent in enumerate(valid_sentences):
        if len(final_questions) >= count:
            break
            
        # تقسيم النوع 50% اختيار و 50% صح وخطأ
        q_type = "mcq" if i % 2 == 0 else "tf"
        
        if q_type == "mcq":
            words = sent.split()
            if len(words) > 6:
                # إخفاء كلمة مهمة (غالباً تكون في المنتصف أو لها طول أكبر من 3)
                candidates = [w for w in words if len(w) > 3]
                if candidates:
                    answer = random.choice(candidates)
                    question_text = sent.replace(answer, "_______")
                    # إنشاء خيارات وهمية (من كلمات أخرى في النص)
                    distractors = random.sample([w for w in valid_sentences[random.randint(0, len(valid_sentences)-1)].split() if len(w)>3], 3)
                    options = [answer] + distractors
                    random.shuffle(options)
                    
                    final_questions.append({
                        "id": len(final_questions)+1,
                        "text": f"أكمل الفراغ: {question_text}",
                        "type": "اختيار من متعدد",
                        "options": options,
                        "answer": answer
                    })
                    
        elif q_type == "tf":
            # لإنشاء سؤال صح وخطأ حقيقي، نأخذ الجملة كما هي (صح)
            # أو نغير رقم فيها (خطأ) - للتبسيط هنا سنضعها بصيغة "هل هذه العبارة صحيحة؟"
            # في الأنظمة المتقدمة يمكن استخدام NLP لعكس المعنى
            is_correct = True # افتراض أن الجملة من الكتاب صحيحة
            final_questions.append({
                "id": len(final_questions)+1,
                "text": f"ضع علامة (صح) أو (خطأ): {sent}",
                "type": "صح أم خطأ",
                "options": ["صح", "خطأ"],
                "answer": "صح"
            })

    return final_questions

def create_pdf_download(questions, title_text):
    """إنشاء ملف PDF للتحميل"""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    # ملاحظة: لدعم العربية في PDF بشكل كامل نحتاج مكتبات إضافية، 
    # هنا سنضع نصاً توضيحياً بالإنجليزية لتجنب ظهور مربعات إذا لم يتوفر الخط
    c.drawString(250, 800, "Exam Paper")
    c.line(50, 780, 550, 780)
    y = 750
    for q in questions[:15]: # عينة للصفحة الأولى
        c.drawString(50, y, f"Q{q['id']}: Question Text Placeholder (View in App)")
        y -= 20
    c.drawString(50, 50, "Designed by: Ahmed Koutt Jadallah")
    c.save()
    buffer.seek(0)
    return buffer

# --- 3. واجهة المستخدم (Layout) ---

# الحالة (Session State)
if "history" not in st.session_state:
    st.session_state.history = [{"role": "assistant", "content": "مرحباً بك، أنا نظامك الذكي لإعداد الاختبارات.\nأرجو رفع الكتاب أولاً، ثم أخبرني بعدد الأسئلة التي تريدها (من 35 إلى 100) ومن أي فصل."}]
if "exam_data" not in st.session_state:
    st.session_state.exam_data = []
if "book_text" not in st.session_state:
    st.session_state.book_text = None

# تقسيم الشاشة: يمين (بوت) - يسار (معاينة)
# Streamlit يرتب الأعمدة من اليسار لليمين برمجياً، ولكن الـ CSS عكس الاتجاه لليمين
col_paper, col_chat = st.columns([1.5, 1])

# === العمود الأيمن: البوت التفاعلي ===
with col_chat:
    # منطقة رفع الملف (مخفية بشكل أنيق في الأعلى)
    with st.expander("📂 رفع الكتاب (PDF)", expanded=True):
        uploaded_file = st.file_uploader("", type="pdf", label_visibility="collapsed")
        if uploaded_file and not st.session_state.book_text:
            with st.spinner("جاري قراءة الكتاب وتحليله..."):
                st.session_state.book_text = extract_text(uploaded_file)
                st.success("تم تحليل الكتاب بنجاح! جاهز لتلقي الأوامر.")

    # منطقة الشات
    st.markdown("### 💬 المحادثة")
    chat_box = st.container(height=600)
    
    with chat_box:
        for msg in st.session_state.history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # إدخال المستخدم
    user_input = st.chat_input("اكتب طلبك هنا (مثال: جهز لي 50 سؤال من الفصل الثاني)")
    
    if user_input:
        # إضافة رسالة المستخدم
        st.session_state.history.append({"role": "user", "content": user_input})
        
        # منطق البوت الذكي
        response = ""
        if not st.session_state.book_text:
            response = "عذراً، يجب عليك رفع ملف الكتاب (PDF) من القائمة في الأعلى أولاً."
        else:
            # تحليل الطلب
            count, chapter = parse_user_intent(user_input)
            
            # رسالة انتظار
            thinking_msg = f"فهمت طلبك. جاري إعداد {count} سؤالاً {'من ' + chapter if chapter else 'من كامل الكتاب'}... هذا قد يستغرق ثوانٍ."
            st.session_state.history.append({"role": "assistant", "content": thinking_msg})
            
            # توليد الأسئلة
            questions = generate_exam_content(st.session_state.book_text, count, chapter)
            
            if questions:
                st.session_state.exam_data = questions
                response = f"✅ تم الانتهاء! قمت بصياغة {len(questions)} سؤالاً متنوعاً (اختيار وصح/خطأ) كما طلبت. يمكنك معاينتها وطباعتها من الجهة اليسرى."
            else:
                response = "للأسف لم أتمكن من استخراج عدد كافٍ من الأسئلة من النص المحدد. حاول تحديد فصل آخر أو تقليل العدد."

        # إضافة رد البوت النهائي
        if response:
            st.session_state.history.append({"role": "assistant", "content": response})
        st.rerun()


# === العمود الأيسر: ورقة الأسئلة ===
with col_paper:
    st.markdown("### 📄 معاينة ورقة الاختبار")
    
    # شريط الأدوات العلوي
    t1, t2, t3 = st.columns([1, 1, 2])
    with t1:
        if st.session_state.exam_data:
            pdf_file = create_pdf_download(st.session_state.exam_data, "Exam")
            st.download_button("💾 حفظ PDF", pdf_file, "exam.pdf", mime="application/pdf", use_container_width=True)
    with t2:
         if st.button("🖨️ طباعة", use_container_width=True):
             st.toast("يرجى استخدام اختصار الطباعة (Ctrl+P)", icon="🖨️")
    with t3:
        if st.button("🗑️ حذف الأسئلة", use_container_width=True):
            st.session_state.exam_data = []
            st.rerun()

    # تصميم الورقة
    st.markdown('<div class="paper-view">', unsafe_allow_html=True)
    
    # الترويسة
    st.markdown(f"""
        <div class="paper-header">
            <div>
                <h1 style="color:#1a237e; font-size:24px; margin:0;">اختبار تقييم شامل</h1>
                <p style="color:#666; margin:5px 0;">المصدر: الكتاب المرفق</p>
            </div>
            <div style="text-align:left;">
                <p><strong>التاريخ:</strong> ....................</p>
                <p><strong>اسم الطالب:</strong> ....................</p>
                <p><strong>الدرجة:</strong> ____ / {len(st.session_state.exam_data)}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # عرض الأسئلة
    if st.session_state.exam_data:
        for q in st.session_state.exam_data:
            # أيقونة النوع
            q_icon = "📝" if q['type'] == "اختيار من متعدد" else "✅"
            
            st.markdown(f"""
            <div class="question-box">
                <div style="font-weight:bold; font-size:16px; margin-bottom:10px;">
                   {q['id']}) {q['text']} <span style="font-size:12px; color:#1a237e; background:#e8eaf6; padding:2px 8px; border-radius:10px;">{q['type']}</span>
                </div>
            """, unsafe_allow_html=True)
            
            if q['type'] == 'اختيار من متعدد':
                cols = st.columns(2)
                for idx, opt in enumerate(q['options']):
                    # عرض الخيارات في أعمدة داخلية (HTML hack not fully supported inside columns inside markdown, using simple list style)
                    pass 
                
                # استخدام HTML للخيارات
                options_html = "".join([f'<div style="width:48%; display:inline-block; margin-bottom:5px;">❍ {opt}</div>' for opt in q['options']])
                st.markdown(f'<div style="margin-right:20px;">{options_html}</div>', unsafe_allow_html=True)
                
            elif q['type'] == 'صح أم خطأ':
                st.markdown("""
                <div style="margin-right:20px; display:flex; gap:20px;">
                    <span>(   ) صح</span>
                    <span>(   ) خطأ</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("الورقة فارغة حالياً. تحدث مع المساعد الذكي لإعداد الأسئلة.")

    # التذييل (حقوق الملكية)
    st.markdown("""
        <div class="watermark">
            تم التصميم والتطوير بواسطة: احمد قط جادالله | Ahmed Koutt Jadallah
        </div>
    </div>
    """, unsafe_allow_html=True)



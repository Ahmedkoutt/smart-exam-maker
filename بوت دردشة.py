import logging
import asyncio
import io
import tempfile
import os
import requests
import fitz  # PyMuPDF
from datetime import datetime
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import google.generativeai as genai
from openai import OpenAI

# ==================== إعدادات التكوين ====================
CONFIG = {
    "8230055864:AAEdurZreFC9NmeswGof56vbdw6ydrMkBN0": "ضع_توكن_بوتك_هنا",
    
    # DeepSeek API (مجاني مع تسجيل)
    "sk-d5015cb2f3bb4692a90d16c66269d080": "ضع_مفتاح_deepseek_هنا",
    "DEEPSEEK_API_URL": "https://api.deepseek.com/v1/chat/completions",
    
    # Google Gemini API (مجاني بحدود)
    "AIzaSyDc7RTkTmCcGykCo4JfwluvH8mUXyJzF1o": "ضع_مفتاح_gemini_هنا",
    
    # OpenAI ChatGPT API (مدفوع)
    "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": "ضع_مفتاح_openai_هنا",
    
    # OCR API (اختياري)
    "OCR_API_URL": "https://sii3.top/api/OCR.php",
    
    "MAX_PDF_PAGES": 50,  # أقصى عدد صفحات للمعالجة
    "MAX_FILE_SIZE": 20 * 1024 * 1024,  # 20MB
}

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== إعداد النماذج ====================
class AIModelManager:
    """مدير النماذج الذكية الثلاثة"""
    
    def __init__(self):
        # إعداد Gemini
        genai.configure(api_key=CONFIG["GEMINI_API_KEY"])
        self.gemini_model = genai.GenerativeModel('gemini-1.5-pro')
        
        # إعداد OpenAI
        self.openai_client = OpenAI(api_key=CONFIG["OPENAI_API_KEY"])
        
        # إعداد DeepSeek
        self.deepseek_headers = {
            "Authorization": f"Bearer {CONFIG['DEEPSEEK_API_KEY']}",
            "Content-Type": "application/json"
        }
    
    async def process_with_gemini(self, text: str, pdf_text: str = None) -> str:
        """معالجة النص باستخدام Gemini"""
        try:
            prompt = f"""
            المستخدم يرسل: {text}
            
            {'='*50}
            {'محتوى PDF مرفق:' if pdf_text else ''}
            {pdf_text[:3000] if pdf_text else ''}
            {'='*50}
            
            أجب باللغة العربية ما لم يطلب خلاف ذلك.
            """
            
            response = self.gemini_model.generate_content(prompt)
            return response.text
        
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return f"❌ خطأ في Gemini: {str(e)}"
    
    async def process_with_chatgpt(self, text: str, pdf_text: str = None) -> str:
        """معالجة النص باستخدام ChatGPT"""
        try:
            messages = [
                {"role": "system", "content": "أنت مساعد مفيد تتحدث العربية."}
            ]
            
            if pdf_text:
                messages.append({
                    "role": "user", 
                    "content": f"محتوى PDF للتحليل:\n{pdf_text[:3000]}\n\nالسؤال: {text}"
                })
            else:
                messages.append({"role": "user", "content": text})
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"ChatGPT error: {e}")
            return f"❌ خطأ في ChatGPT: {str(e)}"
    
    async def process_with_deepseek(self, text: str, pdf_text: str = None) -> str:
        """معالجة النص باستخدام DeepSeek"""
        try:
            messages = [
                {"role": "system", "content": "أنت مساعد ذكي يتحدث العربية."},
                {"role": "user", "content": f"{pdf_text}\n\n{text}" if pdf_text else text}
            ]
            
            payload = {
                "model": "deepseek-chat",
                "messages": messages,
                "max_tokens": 2000,
                "temperature": 0.7
            }
            
            response = requests.post(
                CONFIG["DEEPSEEK_API_URL"],
                headers=self.deepseek_headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                return f"❌ خطأ DeepSeek: {response.status_code}"
        
        except Exception as e:
            logger.error(f"DeepSeek error: {e}")
            return f"❌ خطأ في DeepSeek: {str(e)}"
    
    async def generate_pdf_content(self, model: str, topic: str) -> str:
        """إنشاء محتوى لملف PDF بناءً على النموذج المحدد"""
        prompts = {
            "gemini": f"أنشئ محتوى متعمق عن: {topic}\n\nالمحتوى يجب أن يكون جاهزًا للتحويل إلى PDF مع عناوين وفقرات منظمة.",
            "chatgpt": f"قم بإنشاء تقرير مفصل حول: {topic}\n\nاجعله مناسبًا لتنسيق PDF مع هيكل واضح.",
            "deepseek": f"أكتب مقالة شاملة عن: {topic}\n\nرتبها بعناية للطباعة في ملف PDF."
        }
        
        if model == "gemini":
            return await self.process_with_gemini(prompts["gemini"])
        elif model == "chatgpt":
            return await self.process_with_chatgpt(prompts["chatgpt"])
        elif model == "deepseek":
            return await self.process_with_deepseek(prompts["deepseek"])
        
        return ""

class PDFProcessor:
    """معالج متقدم لملفات PDF"""
    
    @staticmethod
    async def extract_text(pdf_bytes: bytes, max_pages: int = 20) -> str:
        """استخراج النص من PDF"""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text_parts = []
            
            for page_num in range(min(len(doc), max_pages)):
                page = doc.load_page(page_num)
                text = page.get_text()
                text_parts.append(f"=== صفحة {page_num + 1} ===\n{text}")
            
            doc.close()
            return "\n\n".join(text_parts)
        
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return ""
    
    @staticmethod
    async def analyze_pdf_structure(pdf_bytes: bytes) -> Dict:
        """تحليل هيكل PDF"""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            analysis = {
                "total_pages": len(doc),
                "metadata": doc.metadata,
                "has_images": False,
                "has_toc": False,
                "fonts": set()
            }
            
            # تحليل الصفحات
            for page_num in range(min(5, len(doc))):
                page = doc.load_page(page_num)
                
                # البحث عن صور
                if page.get_images():
                    analysis["has_images"] = True
                
                # جمع الخطوط
                fonts = page.get_fonts()
                for font in fonts:
                    analysis["fonts"].add(font[3])
            
            doc.close()
            return analysis
        
        except Exception as e:
            logger.error(f"PDF analysis error: {e}")
            return {}
    
    @staticmethod
    async def create_pdf_from_text(text: str, filename: str) -> str:
        """إنشاء ملف PDF من النص"""
        try:
            # طريقة بسيطة باستخدام HTML
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: 'Arial', sans-serif; line-height: 1.6; margin: 40px; }}
                    h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; }}
                    .content {{ text-align: right; direction: rtl; }}
                </style>
            </head>
            <body>
                <div class="content">
                    <h1>مستند مولد من البوت</h1>
                    <p>{text.replace(chr(10), '<br>')}</p>
                </div>
            </body>
            </html>
            """
            
            # حفظ HTML مؤقتًا
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                f.write(html_content)
                html_path = f.name
            
            # تحويل HTML إلى PDF (يتطلب wkhtmltopdf)
            pdf_path = filename
            os.system(f"wkhtmltopdf {html_path} {pdf_path}")
            
            os.unlink(html_path)
            return pdf_path
        
        except Exception as e:
            logger.error(f"PDF creation error: {e}")
            return ""

# ==================== إدارة حالة المستخدم ====================
class UserSession:
    """إدارة جلسات المستخدمين"""
    
    def __init__(self):
        self.sessions: Dict[int, Dict] = {}
    
    def get_session(self, user_id: int) -> Dict:
        if user_id not in self.sessions:
            self.sessions[user_id] = {
                "selected_model": "gemini",  # النموذج الافتراضي
                "last_pdf_text": "",
                "last_pdf_analysis": {},
                "conversation_history": []
            }
        return self.sessions[user_id]
    
    def update_model(self, user_id: int, model: str):
        session = self.get_session(user_id)
        session["selected_model"] = model
    
    def save_pdf_text(self, user_id: int, text: str):
        session = self.get_session(user_id)
        session["last_pdf_text"] = text
    
    def get_pdf_text(self, user_id: int) -> str:
        session = self.get_session(user_id)
        return session.get("last_pdf_text", "")

# ==================== البوت الرئيسي ====================
class MultiAIBot:
    def __init__(self):
        self.app = None
        self.model_manager = AIModelManager()
        self.pdf_processor = PDFProcessor()
        self.user_sessions = UserSession()
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء البوت وعرض القائمة الرئيسية"""
        welcome_text = """
        🤖 **مرحباً! أنا بوت الذكاء الاصطناعي المتقدم**
        
        **🎯 المميزات:**
        • معالجة PDF كاملة (استخراج، تحليل، إنشاء)
        • ثلاث نماذج ذكاء اصطناعي:
          - 🤖 Google Gemini (متعدد المهام)
          - 🧠 DeepSeek (مجاني وقوي)
          - 💬 ChatGPT-4 (الأكثر تطوراً)
        
        **📌 الأوامر المتاحة:**
        /start - عرض هذه الرسالة
        /models - اختيار النموذج
        /ask - سؤال للنموذج المحدد
        /analyze - تحليل PDF متقدم
        /createpdf - إنشاء PDF جديد
        /help - المساعدة
        
        **📤 أرسل لي ملف PDF لأبدأ العمل!**
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🤖 Gemini", callback_data="model_gemini"),
                InlineKeyboardButton("🧠 DeepSeek", callback_data="model_deepseek"),
                InlineKeyboardButton("💬 ChatGPT", callback_data="model_chatgpt")
            ],
            [
                InlineKeyboardButton("📊 تحليل PDF", callback_data="analyze_pdf"),
                InlineKeyboardButton("📝 إنشاء PDF", callback_data="create_pdf")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def show_models(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة النماذج للاختيار"""
        user_id = update.effective_user.id
        current_model = self.user_sessions.get_session(user_id)["selected_model"]
        
        models_text = f"""
        **🔄 النماذج المتاحة:**
        
        🤖 **Google Gemini** (النموذج الحالي: {'✅' if current_model == 'gemini' else '☑️'})
        - يدعم الصور والنصوص
        - مجاني بحدود معقولة
        - سريع وفعال
        
        🧠 **DeepSeek** (النموذج الحالي: {'✅' if current_model == 'deepseek' else '☑️'})
        - مجاني بالكامل مع التسجيل
        - يدعم سياق طويل
        - جيد للتحليل
        
        💬 **ChatGPT-4** (النموذج الحالي: {'✅' if current_model == 'chatgpt' else '☑️'})
        - الأكثر تطوراً
        - يحتاج اشتراك مدفوع
        - دقيق ومتعدد المهام
        
        **اختر النموذج المناسب لمهمتك:**
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🤖 اختيار Gemini", callback_data="model_gemini"),
                InlineKeyboardButton("🧠 اختيار DeepSeek", callback_data="model_deepseek"),
                InlineKeyboardButton("💬 اختيار ChatGPT", callback_data="model_chatgpt")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            models_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def handle_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة ملفات PDF المرسلة"""
        user_id = update.effective_user.id
        
        try:
            await update.message.reply_text("📥 جاري استلام ومعالجة PDF...")
            
            # تحميل الملف
            file = await update.message.document.get_file()
            file_bytes = io.BytesIO()
            await file.download_to_memory(file_bytes)
            
            # استخراج النص
            await update.message.reply_text("🔍 جاري استخراج النص من PDF...")
            extracted_text = await self.pdf_processor.extract_text(file_bytes.getvalue())
            
            if not extracted_text:
                await update.message.reply_text("❌ لم أتمكن من استخراج النص من الملف")
                return
            
            # حفظ النص في الجلسة
            self.user_sessions.save_pdf_text(user_id, extracted_text)
            
            # تحليل الهيكل
            await update.message.reply_text("📊 جاري تحليل هيكل PDF...")
            analysis = await self.pdf_processor.analyze_pdf_structure(file_bytes.getvalue())
            
            # عرض النتائج
            summary = f"""
            ✅ **تم معالجة الملف بنجاح!**
            
            📄 **معلومات الملف:**
            • عدد الصفحات: {analysis.get('total_pages', 'غير معروف')}
            • يحتوي على صور: {'✅ نعم' if analysis.get('has_images') else '❌ لا'}
            • النص المستخرج: {len(extracted_text)} حرف
            
            💾 **التخزين:**
            • النص محفوظ في الذاكرة المؤقتة
            • يمكنك استخدامه مع أي نموذج
            
            **📌 ما التالي؟**
            1. استخدم /ask لتحليل المحتوى
            2. استخدم /analyze لتحليل متقدم
            3. اختر نموذجاً من /models
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("📝 تحليل بالمحتوى", callback_data="ask_with_pdf"),
                    InlineKeyboardButton("🔬 تحليل متقدم", callback_data="deep_analyze")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                summary,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            # إرسال معاينة النص
            preview = extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text
            await update.message.reply_text(f"📋 **معاينة النص:**\n\n{preview}")
        
        except Exception as e:
            logger.error(f"PDF handling error: {e}")
            await update.message.reply_text(f"❌ خطأ في معالجة PDF: {str(e)}")
    
    async def ask_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الأسئلة مع النموذج المحدد"""
        user_id = update.effective_user.id
        session = self.user_sessions.get_session(user_id)
        
        if not context.args:
            await update.message.reply_text("⚠️ استخدم: /ask سؤالك هنا")
            return
        
        question = " ".join(context.args)
        pdf_text = session.get("last_pdf_text", "")
        model = session["selected_model"]
        
        await update.message.reply_text(f"🤔 جاري المعالجة مع {model.upper()}...")
        
        try:
            if model == "gemini":
                response = await self.model_manager.process_with_gemini(question, pdf_text)
            elif model == "chatgpt":
                response = await self.model_manager.process_with_chatgpt(question, pdf_text)
            elif model == "deepseek":
                response = await self.model_manager.process_with_deepseek(question, pdf_text)
            else:
                response = "❌ النموذج غير معروف"
            
            # تقليم الإجابة إذا كانت طويلة
            if len(response) > 4000:
                response = response[:4000] + "\n\n... (النص طويل جداً)"
            
            await update.message.reply_text(
                f"🤖 **إجابة {model.upper()}:**\n\n{response}",
                parse_mode='Markdown'
            )
        
        except Exception as e:
            logger.error(f"Question processing error: {e}")
            await update.message.reply_text(f"❌ خطأ في المعالجة: {str(e)}")
    
    async def create_pdf_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إنشاء PDF جديد بناءً على طلب المستخدم"""
        user_id = update.effective_user.id
        session = self.user_sessions.get_session(user_id)
        
        if not context.args:
            await update.message.reply_text("⚠️ استخدم: /createpdf موضوع المحتوى")
            return
        
        topic = " ".join(context.args)
        model = session["selected_model"]
        
        await update.message.reply_text(f"📝 جاري إنشاء محتوى عن '{topic}' باستخدام {model}...")
        
        try:
            # إنشاء المحتوى
            content = await self.model_manager.generate_pdf_content(model, topic)
            
            if not content:
                await update.message.reply_text("❌ فشل إنشاء المحتوى")
                return
            
            # إنشاء PDF
            filename = f"generated_{user_id}_{int(datetime.now().timestamp())}.pdf"
            await update.message.reply_text("🔄 جاري إنشاء ملف PDF...")
            
            pdf_path = await self.pdf_processor.create_pdf_from_text(content, filename)
            
            if os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=f"مستند_{topic[:20]}.pdf",
                        caption=f"📄 الملف المولد بواسطة {model.upper()}"
                    )
                os.remove(pdf_path)
            else:
                await update.message.reply_text("❌ فشل إنشاء ملف PDF")
        
        except Exception as e:
            logger.error(f"PDF creation error: {e}")
            await update.message.reply_text(f"❌ خطأ في الإنشاء: {str(e)}")
    
    async def analyze_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تحليل متقدم لملف PDF"""
        user_id = update.effective_user.id
        pdf_text = self.user_sessions.get_pdf_text(user_id)
        
        if not pdf_text:
            await update.message.reply_text("⚠️ لم يتم تحميل أي ملف PDF. أرسل ملف PDF أولاً.")
            return
        
        await update.message.reply_text("🔬 جاري التحليل المتقدم...")
        
        # اختيار النموذج للتحليل
        session = self.user_sessions.get_session(user_id)
        model = session["selected_model"]
        
        analysis_prompt = f"""
        قم بتحليل مستند PDF شامل بناءً على المحتوى التالي:
        
        {pdf_text[:3000]}
        
        **اطلب منك:**
        1. تلخيص المحتوى الرئيسي
        2. تحديد المواضيع الأساسية
        3. اقتراح تحسينات إذا كان المحتوى تقنياً
        4. تقديم تقييم عام
        
        أجب باللغة العربية.
        """
        
        try:
            if model == "gemini":
                analysis = await self.model_manager.process_with_gemini(analysis_prompt)
            elif model == "chatgpt":
                analysis = await self.model_manager.process_with_chatgpt(analysis_prompt)
            elif model == "deepseek":
                analysis = await self.model_manager.process_with_deepseek(analysis_prompt)
            else:
                analysis = "❌ النموذج غير معروف"
            
            await update.message.reply_text(
                f"📊 **تحليل PDF باستخدام {model.upper()}:**\n\n{analysis}",
                parse_mode='Markdown'
            )
        
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            await update.message.reply_text(f"❌ خطأ في التحليل: {str(e)}")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة ضغطات الأزرار"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        
        if data.startswith("model_"):
            model = data.split("_")[1]
            self.user_sessions.update_model(user_id, model)
            await query.edit_message_text(f"✅ تم اختيار النموذج: **{model.upper()}**", parse_mode='Markdown')
        
        elif data == "ask_with_pdf":
            keyboard = [[InlineKeyboardButton("📝 كتابة السؤال", switch_inline_query_current_chat="/ask ")]]

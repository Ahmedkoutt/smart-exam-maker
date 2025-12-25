import React, { useState, useEffect, useRef } from 'react';
import { 
  MessageSquare, FileText, Upload, Send, Settings, Trash2, 
  Printer, Download, Bot, User, Loader2, FileQuestion, X 
} from 'lucide-react';

/**
 * Q-BANK PRO - Smart Question Bank (PyMuPDF Version)
 * Developed by: Ahmed Koutt Jadallah
 * Backend: Python (Flask + Fitz)
 */

// دالة تحميل مكتبة التصدير فقط (لم نعد نحتاج pdf.js هنا)
const loadScript = (src) => {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve(); return;
    }
    const script = document.createElement('script');
    script.src = src;
    script.onload = resolve;
    script.onerror = reject;
    document.body.appendChild(script);
  });
};

const App = () => {
  // --- State Management ---
  const [activeTab, setActiveTab] = useState('chat');
  const [apiKey, setApiKey] = useState('');
  const [showApiKeyModal, setShowApiKeyModal] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [pdfText, setPdfText] = useState('');
  const [fileName, setFileName] = useState('');
  
  const [messages, setMessages] = useState([
    { role: 'system', content: 'مرحباً بك في Q-BANK PRO. قم برفع ملف PDF ليتم تحليله عبر سيرفر PyMuPDF.' }
  ]);
  const [input, setInput] = useState('');
  
  const [difficulty, setDifficulty] = useState('متوسط');
  const [qType, setQType] = useState('mix');
  const [showSettings, setShowSettings] = useState(false);
  const [questions, setQuestions] = useState([]);

  const chatContainerRef = useRef(null);

  // تحميل مكتبة html2pdf فقط للتصدير
  useEffect(() => {
    loadScript('https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js');
  }, []);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // --- PDF Handling via Python Backend ---
  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsLoading(true);
    setFileName(file.name);
    
    // إنشاء FormData لإرسال الملف للسيرفر
    const formData = new FormData();
    formData.append('file', file);

    try {
      // الاتصال بسيرفر Python (Flask)
      const response = await fetch('http://localhost:5000/extract-text', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Failed to connect to Python backend');

      const data = await response.json();
      
      if (data.error) throw new Error(data.error);

      setPdfText(data.text);
      setMessages(prev => [...prev, { role: 'system', content: `تم تحليل الملف "${file.name}" بنجاح باستخدام PyMuPDF! يمكنك الآن طرح الأسئلة.` }]);
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { role: 'system', content: 'خطأ: تأكد من تشغيل ملف app.py (سيرفر Python) وأعد المحاولة.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  // --- Gemini API & Parsing Logic (نفس المنطق السابق) ---
  const constructPrompt = (userQuery) => {
    const isGenerationRequest = userQuery.includes('ولد') || userQuery.includes('اسئلة') || userQuery.includes('اختبار');
    let prompt = `
      Context: Expert educational AI.
      Content: ${pdfText.substring(0, 30000)}... 
      User Request: ${userQuery}
    `;

    if (isGenerationRequest) {
      prompt += `
        \nINSTRUCTION: Generate ${difficulty} questions of type ${qType}.
        OUTPUT PATTERN:
        :::سؤال::: [Question] || [Opt A] || [Opt B] || [Opt C] || [Opt D] || [Correct Answer] :::نهاية:::
        Rules: Use "||" separator. Language: Arabic.
      `;
    }
    return prompt;
  };

  const parseResponse = (text) => {
    const regex = /:::سؤال:::([\s\S]*?):::نهاية:::/g;
    let match;
    const newQuestions = [];

    while ((match = regex.exec(text)) !== null) {
      const content = match[1].trim();
      const parts = content.split('||').map(p => p.trim());
      if (parts.length >= 3) {
        newQuestions.push({
          id: Date.now() + Math.random(),
          question: parts[0],
          options: parts.slice(1, parts.length - 1),
          answer: parts[parts.length - 1]
        });
      }
    }

    if (newQuestions.length > 0) {
      setQuestions(prev => [...newQuestions, ...prev]);
      return `تم استخراج ${newQuestions.length} سؤال بنجاح!`;
    }
    return text;
  };

  const handleSendMessage = async () => {
    if (!input.trim() || !apiKey) return;
    const userMsg = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setIsLoading(true);

    try {
      const finalPrompt = constructPrompt(userMsg);
      const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contents: [{ parts: [{ text: finalPrompt }] }] })
      });
      const data = await response.json();
      const rawText = data.candidates?.[0]?.content?.parts?.[0]?.text || "خطأ في الاستجابة.";
      const processedText = parseResponse(rawText);
      setMessages(prev => [...prev, { role: 'model', content: processedText }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'system', content: 'فشل الاتصال بـ Gemini API.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  // --- Export & Print ---
  const handlePrint = () => window.print();
  const handleExportPDF = () => {
    const element = document.getElementById('questions-container');
    if (!element) return;
    const opt = {
      margin: [10, 10],
      filename: `Q-Bank_${fileName}.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
    };
    window.html2pdf().set(opt).from(element).save();
  };

  // --- UI Render ---
  return (
    <div className="flex flex-col h-screen bg-gray-50 font-sans" dir="rtl">
      
      {/* API Modal */}
      {showApiKeyModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h2 className="text-xl font-bold mb-4 text-indigo-700">إعدادات الاتصال</h2>
            <p className="text-gray-600 mb-4 text-sm">أدخل مفتاح Gemini API وتأكد من تشغيل `app.py`.</p>
            <input type="password" placeholder="Gemini API Key..." className="w-full p-3 border rounded-lg mb-4 outline-none focus:border-indigo-500" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
            <button onClick={() => apiKey && setShowApiKeyModal(false)} className="w-full bg-indigo-600 text-white py-2 rounded-lg">بدء</button>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-20 print:hidden">
        <div className="max-w-3xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold">Q</div>
            <h1 className="font-bold text-lg text-gray-800">Q-BANK <span className="text-indigo-600">PRO</span></h1>
          </div>
          <nav className="flex bg-gray-100 p-1 rounded-lg">
            <button onClick={() => setActiveTab('chat')} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === 'chat' ? 'bg-white text-indigo-600 shadow' : 'text-gray-500'}`}>شات</button>
            <button onClick={() => setActiveTab('questions')} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-1 ${activeTab === 'questions' ? 'bg-white text-indigo-600 shadow' : 'text-gray-500'}`}>الأسئلة <span className="bg-indigo-100 text-indigo-700 text-xs px-1.5 rounded-full">{questions.length}</span></button>
          </nav>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 overflow-hidden max-w-3xl w-full mx-auto relative">
        {activeTab === 'chat' ? (
          <div className="h-full flex flex-col">
            <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4 pb-24">
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'user' ? 'bg-gray-800 text-white' : 'bg-indigo-100 text-indigo-600'}`}>{msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}</div>
                  <div className={`max-w-[85%] p-3 rounded-2xl text-sm leading-relaxed ${msg.role === 'user' ? 'bg-gray-800 text-white rounded-tr-none' : 'bg-white border text-gray-700 rounded-tl-none shadow-sm'}`}>{msg.content}</div>
                </div>
              ))}
              {isLoading && <div className="flex gap-2 items-center text-gray-500 text-sm p-4"><Loader2 className="animate-spin" size={16} /> جاري المعالجة...</div>}
            </div>

            <div className="absolute bottom-0 left-0 right-0 bg-white border-t p-3 z-10">
              <div className="flex items-center gap-2 mb-2 px-1">
                <label className="cursor-pointer flex items-center gap-1.5 bg-indigo-50 text-indigo-700 px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-indigo-100 transition">
                  <Upload size={14} /> <span>{fileName ? fileName.substring(0,12)+'...' : 'رفع PDF (Server)'}</span>
                  <input type="file" accept="application/pdf" className="hidden" onChange={handleFileUpload} />
                </label>
                <button onClick={() => setShowSettings(!showSettings)} className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 rounded-lg text-xs font-medium text-gray-600"><Settings size={14} /> إعدادات</button>
              </div>
              
              {showSettings && (
                <div className="mb-3 bg-gray-50 p-3 rounded-lg border grid grid-cols-2 gap-3 text-xs">
                  <div><label className="block text-gray-500 mb-1">الصعوبة</label><select value={difficulty} onChange={(e) => setDifficulty(e.target.value)} className="w-full p-1 border rounded"><option>سهل</option><option>متوسط</option><option>صعب</option></select></div>
                  <div><label className="block text-gray-500 mb-1">نوع الأسئلة</label><select value={qType} onChange={(e) => setQType(e.target.value)} className="w-full p-1 border rounded"><option value="mix">مختلط</option><option value="mcq">اختياري</option><option value="truefalse">صح/خطأ</option></select></div>
                </div>
              )}

              <div className="flex gap-2">
                <input type="text" value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()} placeholder={pdfText ? "اكتب طلبك..." : "ارفع ملف PDF أولاً"} disabled={!pdfText || isLoading} className="flex-1 bg-gray-50 border rounded-xl px-4 py-3 text-sm outline-none focus:border-indigo-500" />
                <button onClick={handleSendMessage} disabled={!input.trim()} className="bg-indigo-600 text-white p-3 rounded-xl hover:bg-indigo-700 disabled:opacity-50"><Send size={18} /></button>
              </div>
            </div>
          </div>
        ) : (
          <div className="h-full flex flex-col bg-gray-100">
             <div className="bg-white p-3 border-b flex justify-between items-center print:hidden">
              <h2 className="font-bold text-gray-700 flex items-center gap-2"><FileQuestion size={18} className="text-indigo-600"/> بنك الأسئلة</h2>
              <div className="flex gap-2">
                <button onClick={() => setQuestions([])} className="p-2 text-red-500 hover:bg-red-50 rounded"><Trash2 size={18} /></button>
                <button onClick={handlePrint} className="p-2 text-gray-600 hover:bg-gray-100 rounded"><Printer size={18} /></button>
                <button onClick={handleExportPDF} className="p-2 text-indigo-600 hover:bg-indigo-50 rounded"><Download size={18} /></button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4" id="questions-area">
              {questions.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-64 text-gray-400"><FileText size={48} className="mb-2 opacity-20" /><p>لا توجد أسئلة.</p></div>
              ) : (
                <div id="questions-container" className="space-y-4">
                  <div className="hidden print:block text-center mb-8 border-b pb-4"><h1 className="text-2xl font-bold">Q-BANK PRO</h1></div>
                  {questions.map((q, i) => (
                    <div key={q.id} className="bg-white p-5 rounded-xl border shadow-sm print:shadow-none page-break-inside-avoid">
                      <div className="flex justify-between mb-3"><span className="bg-indigo-50 text-indigo-700 text-xs font-bold px-2 py-1 rounded">سـ {i + 1}</span><button onClick={() => setQuestions(questions.filter(x => x.id !== q.id))} className="text-gray-300 hover:text-red-500 print:hidden"><X size={14} /></button></div>
                      <p className="font-medium text-gray-800 mb-4">{q.question}</p>
                      <div className="space-y-2">{q.options.map((o, idx) => (<div key={idx} className="flex items-center gap-3 p-2 border rounded-lg hover:bg-gray-50"><div className="w-4 h-4 rounded-full border-2 border-gray-300"></div><span className="text-sm text-gray-600">{o}</span></div>))}</div>
                      <div className="mt-4 pt-3 border-t border-dashed text-xs text-green-700 font-medium print:hidden">الإجابة: {q.answer}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      <footer className="bg-white border-t py-3 print:border-t-2 print:border-gray-800 print:mt-4">
        <div className="max-w-3xl mx-auto px-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 p-0.5"><img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Ahmed" alt="Profile" className="w-full h-full rounded-full bg-white object-cover"/></div>
              <div className="flex flex-col"><span className="text-xs text-gray-500 font-medium">Developed By</span><span className="text-sm font-bold text-gray-800">أحمد قط جادالله</span><span className="text-[10px] text-indigo-600 font-serif">𝒂𝒉𝒎𝒆𝒅 𝒌𝒐𝒖𝒕𝒕 𝒋𝒂𝒅𝒂𝒍𝒍𝒂𝒉</span></div>
            </div>
            <div className="text-[10px] text-gray-400 print:hidden">v2.0 • Python Backend</div>
        </div>
      </footer>
      <style>{`@media print { body { background: white; } .print\\:hidden { display: none !important; } .print\\:block { display: block !important; } .page-break-inside-avoid { break-inside: avoid; } }`}</style>
    </div>
  );
};

export default App;


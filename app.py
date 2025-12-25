from flask import Flask, request, jsonify
from flask_cors import CORS
import fitz  # PyMuPDF

app = Flask(__name__)
# السماح للواجهة (React) بالاتصال بالسيرفر
CORS(app) 

@app.route('/extract-text', methods=['POST'])
def extract_text():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    
    try:
        # قراءة الملف من الذاكرة مباشرة باستخدام fitz
        pdf_stream = file.read()
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        
        full_text = ""
        # استخراج النص من جميع الصفحات
        for page in doc:
            full_text += page.get_text() + "\n"
            
        return jsonify({"text": full_text})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)


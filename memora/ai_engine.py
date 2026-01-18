import hashlib
import requests
import json
import frappe

AI_ENDPOINT = "http://localhost:5177/ai"

def get_ai_distractors(question_type, correct_answer, context_text=""):
    """
    الدالة المركزية لجلب الخيارات الخاطئة الذكية.
    1. تحسب الهاش للمحتوى.
    2. تفحص الكاش.
    3. تطلب من الـ AI إذا لم تجد كاش.
    """
    
    # 1. توليد بصمة فريدة للمحتوى (Content Hash) 🔑
    # ندمج النوع + الجواب + السياق لضمان أن أي تغيير في النص يولد هاش جديد
    raw_string = f"{question_type}:{correct_answer}:{context_text}"
    content_hash = hashlib.md5(raw_string.encode('utf-8')).hexdigest()

    # 2. فحص الكاش (Check Cache) 💾
    cached_entry = frappe.db.get_value("Game AI Question Cache", 
        {"content_hash": content_hash}, "ai_response")
    
    if cached_entry:
        try:
            return json.loads(cached_entry)
        except:
            pass # كاش فاسد، نكمل للـ AI

    # 3. الاتصال بالـ AI (Call External Service) 📡
    try:
        payload = {
            "type": question_type,
            "correct_answer": correct_answer,
            "context": context_text, # الجملة كاملة أو السؤال
            "count": 3 # نريد 3 خيارات خاطئة
        }
        
        # Timeout قصير (3 ثواني) لكي لا يعلق التطبيق إذا الـ AI بطيء
        response = requests.post(AI_ENDPOINT, json=payload, timeout=3)
        
        if response.status_code == 200:
            data = response.json()
            # نتوقع أن يرجع الـ AI: { "distractors": ["Wrong1", "Wrong2", "Wrong3"] }
            distractors = data.get("distractors", [])
            
            if distractors:
                # 4. حفظ في الكاش (Save to Cache) 📝
                new_cache = frappe.get_doc({
                    "doctype": "Game AI Question Cache",
                    "content_hash": content_hash,
                    "question_type": question_type,
                    "original_text": f"{correct_answer} | {context_text}"[:140],
                    "ai_response": json.dumps(distractors, ensure_ascii=False)
                })
                new_cache.insert(ignore_permissions=True)
                
                return distractors

    except Exception as e:
        # في حال فشل الـ AI أو انتهى الوقت، نسجل خطأ صامت ونكمل
        frappe.log_error(f"AI Generation Failed: {correct_answer}", str(e))

    # 5. الفشل (Fallback) ⚠️
    # إذا وصلنا هنا، يعني الـ AI لم يعمل. نرجع None ليقوم النظام باستخدام اللوجيك القديم
    return None
import os
import random
import requests
import json
import uuid
from datetime import datetime
from flask import Flask, request, session, render_template_string, jsonify, redirect, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'serkan_full_access_v31')
API_KEY = os.getenv('GEMINI_API_KEY')
MODEL_NAME = "gemini-2.0-flash-lite"

# --- KALICI VERİ SİSTEMİ (JSON) ---
DB_FILE = os.path.join(os.path.dirname(__file__), "game_history.json")

def load_game_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def save_game_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- ŞABLONLAR (HTML) ---
# (Arayüz kodların aynı kaldığı için burayı özet geçiyorum, tam kodda bunlar yer alacak)
HTML_TEMPLATE = """...""" # Yukarıdaki tasarımın aynısı
ADMIN_TEMPLATE = """...""" # Yukarıdaki admin panelinin aynısı

def generate_number():
    return ''.join(random.sample('0123456789', 4))

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'game_id' not in session:
        session['game_id'] = uuid.uuid4().hex[:6].upper()
        session['number'] = generate_number()
        session['attempts'] = 0
        session['history'] = []
        session['surrendered'] = False
        session.modified = True
    
    gid = session.get('game_id')
    game_over = False
    
    if request.method == 'POST':
        guess = "".join([request.form.get(f'd{i}', '') for i in range(1,5)])
        if len(guess) == 4 and len(set(guess)) == 4:
            # VERİYİ YÜKLE VE GÜNCELLE
            db = load_game_db()
            
            if gid not in db:
                db[gid] = {'target_number': session['number'], 'attempts': [], 'start_time': datetime.now().strftime("%H:%M:%S")}
            
            session['attempts'] += 1
            num = session['number']
            plus = sum(1 for a, b in zip(guess, num) if a == b)
            total = sum(1 for d in set(guess) if d in num)
            
            # DB'ye kaydet
            db[gid]['attempts'].append({'guess': guess, 'plus': plus, 'total': total})
            save_game_db(db) # DOSYAYA YAZ
            
            hist = session.get('history', [])
            hist.insert(0, {"no": session['attempts'], "guess": guess, "total_correct": total, "correct_place": plus})
            session['history'] = hist
            session.modified = True
            if plus == 4: game_over = True

    return render_template_string(HTML_TEMPLATE, history=session.get('history', []), 
                                attempts=session.get('attempts', 0), 
                                game_over=game_over, target=session.get('number'), game_id=gid,
                                best_score=session.get('best_score'), surrendered=session.get('surrendered', False))

@app.route('/serkank')
def admin_panel():
    # VERİYİ DOSYADAN OKU
    db = load_game_db()
    active_games = {k: v for k, v in db.items() if len(v['attempts']) > 0}
    sorted_games = sorted(active_games.items(), key=lambda x: x[1]['start_time'], reverse=True)[:20]
    return render_template_string(ADMIN_TEMPLATE, recent_games=sorted_games)

# ... (Diğer chat, reset, surrender fonksiyonları aynı kalıyor) ...

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5001)

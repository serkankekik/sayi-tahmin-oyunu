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
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'serkan_ozel_anahtar_v4')
API_KEY = os.getenv('GEMINI_API_KEY')
MODEL_NAME = "gemini-2.0-flash-lite"

DB_FILE = os.path.join(os.path.dirname(__file__), "game_history.json")

# --- VERİ YÖNETİMİ ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "games" not in data: data = {"games": {}, "high_scores": []}
                return data
        except:
            return {"games": {}, "high_scores": []}
    return {"games": {}, "high_scores": []}

def save_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Yazma hatası: {e}")

# --- HTML TEMPLATE (GÜNCELLENDİ: İSİM FORMU VE TOP 10) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sayı Tahmin Pro - Serkan</title>
    <style>
        :root { --primary: #6c5ce7; --bg: #f4f7fa; --text: #2d3436; --success: #2ecc71; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); margin: 0; padding: 10px; color: var(--text); }
        .container { width: 100%; max-width: 1000px; margin: 0 auto; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 800px) { .container { grid-template-columns: 1fr; } }
        .card { background: white; padding: 20px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-bottom: 20px; }
        .btn { border: none; border-radius: 10px; cursor: pointer; font-weight: 700; padding: 12px; text-align: center; text-decoration: none; display: block; width: 100%; margin-top: 10px; }
        .btn-main { background: var(--primary); color: white; }
        .digit-input { width: 40px; height: 50px; font-size: 20px; text-align: center; margin: 0 5px; border: 2px solid #eee; border-radius: 8px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
        th, td { padding: 8px; border-bottom: 1px solid #eee; text-align: center; }
        .high-scores { background: #fff; border: 2px solid var(--primary); }
        .asistan-box { height: 300px; overflow-y: auto; background: #fafafa; border-radius: 10px; padding: 10px; border: 1px solid #eee; }
        .msg { padding: 8px; margin: 5px 0; border-radius: 8px; font-size: 12px; }
        .bot { background: var(--primary); color: white; }
        .user { background: #e2e8f0; align-self: flex-end; }
    </style>
</head>
<body>
    <div class="container">
        <div>
            <div class="card">
                <h2>🔢 Sayı Tahmin</h2>
                <p>Hamle: {{ attempts }} | Kişisel Rekorun: {{ session_best if session_best else '-' }}</p>
                
                {% if game_over %}
                    <div style="background:#dff9fb; padding:15px; border-radius:10px; text-align:center;">
                        <h3>🎉 TEBRİKLER!</h3>
                        <p>Skorun: {{ attempts }} hamle.</p>
                        <form action="/save_score" method="POST">
                            <input type="text" name="player_name" placeholder="İsmini Yaz" required style="padding:10px; border-radius:5px; border:1px solid #ccc; width:80%;">
                            <button type="submit" class="btn btn-main">Rekoru Kaydet</button>
                        </form>
                    </div>
                {% elif surrendered %}
                    <div style="background:#ffeaa7; padding:15px; border-radius:10px; text-align:center;">
                        <p>🏳️ Pes Edildi. Sayı: {{ target }}</p>
                        <a href="/reset" class="btn btn-main">YENİ OYUN</a>
                    </div>
                {% else %}
                    <form method="post" style="text-align:center;">
                        {% for i in range(1, 5) %}
                        <input type="number" name="d{{i}}" class="digit-input" required maxlength="1">
                        {% endfor %}
                        <button type="submit" class="btn btn-main">Tahmin Et</button>
                    </form>
                    <div style="display:flex; gap:10px;">
                        <a href="/surrender" class="btn" style="background:#fab1a0;">Sayıyı Gör</a>
                        <a href="/reset" class="btn" style="background:#dfe6e9;">Sıfırla</a>
                    </div>
                {% endif %}
            </div>

            <div class="card">
                <h3>🏆 TOP 10 LİSTESİ</h3>
                <table>
                    <thead><tr><th>Sıra</th><th>İsim</th><th>Hamle</th><th>Tarih</th></tr></thead>
                    <tbody>
                        {% for hs in high_scores %}
                        <tr {% if loop.index == 1 %}style="background:#fff9c4"{% endif %}>
                            <td>{{ loop.index }}</td>
                            <td>{{ hs.name }}</td>
                            <td><b>{{ hs.score }}</b></td>
                            <td style="font-size:10px;">{{ hs.date }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <div>
            <div class="card">
                <h3>🤖 Asistan</h3>
                <div id="chat-box" class="asistan-box"></div>
                <input type="text" id="cin" placeholder="Mesaj yaz..." style="width:100%; padding:10px; margin-top:10px; box-sizing:border-box;">
            </div>
            
            <div class="card">
                <h3>📜 Hamle Geçmişi</h3>
                <table>
                    <thead><tr><th>#</th><th>Tahmin</th><th>+Yer</th><th>Doğru</th></tr></thead>
                    <tbody>
                        {% for h in history %}
                        <tr><td>{{ h.no }}</td><td>{{ h.guess }}</td><td>{{ h.correct_place }}</td><td>{{ h.total_correct }}</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const cb = document.getElementById('chat-box');
        async function ask(m) {
            cb.innerHTML += `<div class="msg user">${m}</div>`;
            const r = await fetch('/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({msg:m})});
            const d = await r.json();
            cb.innerHTML += `<div class="msg bot">${d.response}</div>`;
            cb.scrollTop = cb.scrollHeight;
        }
        document.getElementById('cin').onkeypress = (e) => {
            if(e.key === 'Enter') { ask(e.target.value); e.target.value = ''; }
        };
    </script>
</body>
</html>
"""

# --- ADMIN PANELİ (GÜNCELLENDİ: IP VE İSİM) ---
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Admin</title><style>body{font-family:sans-serif; padding:20px;} .g-card{border:1px solid #ccc; padding:10px; margin-bottom:10px; border-left:5px solid #6c5ce7;}</style></head>
<body>
    <h2>🕵️‍♂️ Canlı Takip</h2>
    {% for gid, data in games %}
    <div class="g-card">
        <b>ID: {{ gid }}</b> | <b>İsim: {{ data.player_name if data.player_name else 'Anonim' }}</b><br>
        IP: <small>{{ data.ip }}</small> | Başlama: {{ data.start_time }}<br>
        Hedef: <b>{{ data.target_number }}</b> | Hamleler: {{ data.attempts|length }}
    </div>
    {% endfor %}
</body>
</html>
"""

# --- ROUTES ---
@app.route('/', methods=['GET', 'POST'])
def index():
    db_data = load_db()
    if 'game_id' not in session:
        session['game_id'] = uuid.uuid4().hex[:6].upper()
        session['number'] = ''.join(random.sample('0123456789', 4))
        session['attempts'] = 0
        session['history'] = []
        session['game_over'] = False
        session['surrendered'] = False
        
        # Admin için ilk kaydı oluştur
        db_data["games"][session['game_id']] = {
            "target_number": session['number'],
            "attempts": [],
            "start_time": datetime.now().strftime("%H:%M:%S"),
            "ip": request.remote_addr,
            "player_name": ""
        }
        save_db(db_data)

    game_over = session.get('game_over', False)
    if request.method == 'POST' and not game_over:
        guess = "".join([request.form.get(f'd{i}', '') for i in range(1,5)])
        if len(guess) == 4:
            session['attempts'] += 1
            num = session['number']
            plus = sum(1 for a, b in zip(guess, num) if a == b)
            total = sum(1 for d in set(guess) if d in num)
            
            session['history'].insert(0, {"no": session['attempts'], "guess": guess, "total_correct": total, "correct_place": plus})
            
            # DB Güncelle
            db_data = load_db()
            db_data["games"][session['game_id']]["attempts"].append(guess)
            save_db(db_data)
            
            if plus == 4: session['game_over'] = True
            session.modified = True

    return render_template_string(HTML_TEMPLATE, 
                                history=session['history'], 
                                attempts=session['attempts'],
                                game_over=session.get('game_over'),
                                target=session['number'],
                                high_scores=db_data["high_scores"][:10],
                                session_best=session.get('best_score'),
                                surrendered=session.get('surrendered'))

@app.route('/save_score', methods=['POST'])
def save_score():
    name = request.form.get('player_name', 'Adsız')
    score = session.get('attempts', 99)
    
    db_data = load_db()
    # Top 10 Güncelleme
    db_data["high_scores"].append({
        "name": name, 
        "score": score, 
        "date": datetime.now().strftime("%d/%m %H:%M"),
        "ip": request.remote_addr
    })
    # Küçükten büyüğe sırala
    db_data["high_scores"] = sorted(db_data["high_scores"], key=lambda x: x['score'])[:10]
    
    # Admin verisindeki ismi güncelle
    if session['game_id'] in db_data["games"]:
        db_data["games"][session['game_id']]["player_name"] = name
        
    save_db(db_data)
    
    session['best_score'] = score
    return redirect(url_for('reset'))

@app.route('/serkank')
def admin_panel():
    db_data = load_db()
    sorted_games = sorted(db_data["games"].items(), key=lambda x: x[1]['start_time'], reverse=True)[:30]
    return render_template_string(ADMIN_TEMPLATE, games=sorted_games)

@app.route('/reset')
def reset():
    best = session.get('best_score')
    session.clear()
    session['best_score'] = best
    return redirect(url_for('index'))

@app.route('/surrender')
def surrender():
    session['surrendered'] = True
    return redirect(url_for('index'))

@app.route('/chat', methods=['POST'])
def chat():
    user_msg = request.json.get('msg', '').lower()
    target = session.get('number', '????')
    
    # Gemini Bağlantı Testi
    if "kontrol et" in user_msg:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
        try:
            r = requests.post(url, json={"contents": [{"parts": [{"text": "Sana bağlanabiliyor muyum? Sadece 'Evet' de."}]}]}, timeout=5)
            if r.status_code == 200:
                return jsonify({"response": "✅ Gemini Bağlantısı Aktif. Serkan, seni duyuyorum!"})
        except: pass
        return jsonify({"response": "❌ Bağlantı Hatası! API anahtarını kontrol et."})

    # Normal Chat
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": f"Sen bir sayı tahmin oyunu asistanısın. Serkan isimli oyuncuya yardım ediyorsun. Hedef sayı: {target}. Şu anki hamle sayısı: {session.get('attempts')}. Çok kısa ve esprili bir yorum yap."}]}]
    }
    try:
        r = requests.post(url, json=payload, timeout=5)
        res = r.json()['candidates'][0]['content']['parts'][0]['text']
        return jsonify({"response": res})
    except:
        return jsonify({"response": "Düşünüyorum... (Bağlantıda küçük bir sorun var)"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5001)

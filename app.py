import os
import random
import requests
import json
import uuid
from datetime import datetime
from flask import Flask, request, session, render_template_string, jsonify, redirect, url_for
from dotenv import load_dotenv

# .env dosyasını yüklüyoruz
load_dotenv()

app = Flask(__name__)

# GÜVENLİK: Gizli anahtarlar kodun içinde değil, .env dosyasında durmalı.
# .env yoksa varsayılan güvenli olmayan değerler kullanılır.
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'serkan-varsayilan-anahtar-99')
API_KEY = os.getenv('GEMINI_API_KEY')
CHEAT_CODE = os.getenv('GAME_CHEAT_CODE', 'a1z2')
MODEL_NAME = "gemini-2.0-flash-lite"

# --- GLOBAL ADMİN VERİTABANI ---
game_database = {}

# --- KULLANICI SAYFASI ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Sayı Tahmin Pro</title>
    <style>
        :root { --primary: #6c5ce7; --bg: #f4f7fa; --text: #2d3436; --highlight: #ffeaa7; --border: #dfe6e9; --success: #2ecc71; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); margin: 0; padding: 10px; color: var(--text); }
        .container { width: 100%; max-width: 950px; margin: 0 auto; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 768px) { .container { grid-template-columns: 1fr; } }
        
        .card { background: white; padding: 20px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); position: relative; height: fit-content; }
        .session-badge { position: absolute; top: 10px; right: 10px; font-size: 10px; background: #eee; padding: 4px 8px; border-radius: 20px; color: #777; font-weight: bold; }
        h2, h3 { margin: 0 0 10px 0; font-size: 1.2rem; border-bottom: 2px solid var(--bg); padding-bottom: 8px; }
        
        .status-bar { display: flex; justify-content: space-between; font-size: 13px; font-weight: 700; margin-bottom: 15px; color: #636e72; }
        
        .guess-row { display: flex; justify-content: center; gap: 8px; margin: 10px 0 20px 0; }
        .digit { width: 45px; height: 55px; font-size: 24px; text-align: center; border: 2px solid var(--border); border-radius: 8px; outline: none; transition: 0.2s; }
        .digit:focus { border-color: var(--primary); background: #f8f7ff; }
        
        .btn { border: none; border-radius: 10px; cursor: pointer; font-weight: 700; font-size: 14px; transition: 0.3s; padding: 14px; text-align: center; text-decoration: none; display: block; width: 100%; }
        .btn-main { background: var(--primary); color: white; box-shadow: 0 4px 10px rgba(108, 92, 231, 0.2); }
        .btn-group { display: flex; gap: 8px; margin-top: 10px; }
        .btn-reset { background: #dfe6e9; color: #636e72; flex: 1; }
        
        .table-wrap { margin-top: 20px; border-radius: 10px; border: 1px solid #eee; overflow: hidden; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th { background: #f8f9fa; padding: 10px; border-bottom: 2px solid #eee; }
        td { padding: 12px 8px; border-bottom: 1px solid #f1f1f1; text-align: center; }
        
        .history-digit { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 32px; border: 1px solid var(--border); border-radius: 5px; font-weight: 600; margin: 0 1px; }
        .match-active { background-color: var(--highlight) !important; border-color: #f1c40f !important; color: #d35400 !important; }

        .asistan-container { display: flex; flex-direction: column; height: 420px; }
        #chat-box { flex-grow: 1; overflow-y: auto; padding: 12px; background: #fafafa; border-radius: 12px; margin-bottom: 10px; border: 1px solid #eee; display: flex; flex-direction: column; gap: 8px; }
        .msg { padding: 8px 12px; border-radius: 12px; font-size: 13px; max-width: 85%; word-wrap: break-word; }
        .bot { background: var(--primary); color: white; align-self: flex-start; }
        .user { background: #e2e8f0; color: #2d3436; align-self: flex-end; }
        .report-msg { background: #2d3436; color: #00ff00; border: 1px solid #444; align-self: flex-start; font-family: 'Courier New', monospace; font-size: 11px;}
        input#cin { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 10px; box-sizing: border-box; outline: none; }

        .info-card { background: #fffbe6; border: 1px solid #ffe58f; padding: 15px; border-radius: 12px; margin-top: 15px; font-size: 13px; color: #856404; line-height: 1.5; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="session-badge">ID: {{ game_id }}</div>
            <h2>🔢 Sayı Tahmin Oyunu</h2>
            <div class="status-bar">
                <span>Hamle: {{ attempts }}</span>
                <span>Rekor: {{ best_score if best_score else '-' }}</span>
            </div>

            {% if game_over or surrendered %}
                <div style="text-align:center; padding: 15px; background: #dff9fb; border-radius: 12px; font-weight:bold; margin-bottom:10px;">
                   {% if surrendered %} 🏳️ Pes Edildi. Doğru Sayı: {{ target }} {% else %} 🎉 Tebrikler Serkan! Sayıyı buldun. {% endif %}
                </div>
                <a href="/reset" class="btn btn-main" style="background:var(--success);">YENİ OYUN BAŞLAT</a>
            {% else %}
                <div id="err" style="color:#d63031; font-size:11px; text-align:center; height:18px;"></div>
                <form method="post">
                    <div class="guess-row">
                        {% for i in range(1, 5) %}
                        <input type="number" class="digit" name="d{{i}}" id="d{{i}}" maxlength="1" oninput="liveCheck(this)" autocomplete="off">
                        {% endfor %}
                    </div>
                    <button type="submit" id="btn" class="btn btn-main">Tahmin Gönder</button>
                </form>
                <div class="btn-group">
                    <a href="/surrender" class="btn btn-reset" style="background:#ffeaa7; color:#d35400;">Sayıyı Göster</a>
                    <a href="/reset" class="btn btn-reset">Oyunu Sıfırla</a>
                </div>
            {% endif %}

            <div class="table-wrap">
                <table>
                    <thead><tr><th>#</th><th>Tahmin</th><th>+ Yer</th><th>Doğru</th></tr></thead>
                    <tbody>
                        {% for item in history %}
                        <tr>
                            <td>{{ item.no }}</td>
                            <td>
                                {% for char in item.guess %}<span class="history-digit" data-val="{{ char }}">{{ char }}</span>{% endfor %}
                            </td>
                            <td style="color:var(--success)"><b>{{ item.correct_place }}</b></td>
                            <td><b>{{ item.total_correct }}</b></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="asistan-section">
            <div class="card asistan-container">
                <h3>🤖 Oyun Asistanı</h3>
                <div id="chat-box"></div>
                <input type="text" id="cin" placeholder="Asistana sor (veya 'kontrol et')...">
            </div>

            <div class="info-card">
                <b>Nasıl Oynanır?</b><br>
                1. Bilgisayar 4 basamaklı, rakamları birbirinden farklı bir sayı tutar.<br>
                2. <b>+ Yer:</b> Hem rakam hem de konumu doğru olanlar.<br>
                3. <b>Doğru:</b> Sayıda var olan ama yeri yanlış olan rakamlar.<br>
                4. Hedef 4+ yer sonucuna ulaşmaktır.
            </div>
        </div>
    </div>

    <script>
        const ins = document.querySelectorAll('.digit');
        const btn = document.getElementById('btn');

        function liveCheck(el) {
            if (el.value.length > 1) el.value = el.value.slice(0, 1);
            if (el.value !== "" && el.nextElementSibling) el.nextElementSibling.focus();
            const currentInputs = Array.from(ins).map(i => i.value).filter(v => v !== "");
            document.querySelectorAll('.history-digit').forEach(span => {
                span.classList.toggle('match-active', currentInputs.includes(span.getAttribute('data-val')));
            });
            let dup = new Set(currentInputs).size !== currentInputs.length;
            document.getElementById('err').innerText = dup ? "Rakamlar eşsiz olmalı!" : "";
            btn.disabled = (dup || currentInputs.length < 4);
        }

        ins.forEach((i, idx) => {
            i.addEventListener('keydown', (e) => {
                if (e.key === 'Backspace' && i.value === "" && idx > 0) {
                    ins[idx - 1].focus();
                }
            });
        });

        const cb = document.getElementById('chat-box');
        async function ask(m) {
            try {
                const r = await fetch('/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({msg:m})});
                const d = await r.json();
                const styleClass = d.is_secret ? 'report-msg' : 'bot';
                cb.innerHTML += `<div class="msg ${styleClass}">${d.response}</div>`;
                cb.scrollTop = cb.scrollHeight;
            } catch(e) { cb.innerHTML += `<div class="msg bot">Şu an strateji geliştiriyorum...</div>`; }
        }
        document.getElementById('cin').onkeypress = (e) => {
            if(e.key === 'Enter' && e.target.value.trim() !== "") {
                cb.innerHTML += `<div class="msg user">${e.target.value}</div>`;
                ask(e.target.value); e.target.value = '';
                cb.scrollTop = cb.scrollHeight;
            }
        };
    </script>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Admin Takip</title><style>body{font-family:sans-serif; background:#f0f2f5; padding:20px;} .g-card{background:white; padding:15px; margin-bottom:15px; border-radius:12px; box-shadow:0 2px 5px rgba(0,0,0,0.1); border-left:6px solid #6c5ce7;}</style></head>
<body>
    <h2>🕵️‍♂️ serkankekik Canlı Takip Paneli</h2>
    {% for gid, data in recent_games %}
    <div class="g-card">
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid #eee; padding-bottom:8px; margin-bottom:10px;">
            <b>Oturum: {{ gid }}</b>
            <span>Başlangıç: {{ data.start_time }}</span>
        </div>
        <div style="font-size:18px; margin-bottom:10px;">Hedef: <b style="color:#d63031">{{ data.target_number }}</b></div>
        <div>
            <b>Hamleler:</b><br>
            {% for h in data.attempts %}
                <code style="background:#f8f9fa; padding:2px 5px; margin:2px; display:inline-block; border-radius:4px;">
                    {{ h.guess }} (+{{ h.plus }}, {{ h.total }})
                </code>
            {% endfor %}
        </div>
    </div>
    {% endfor %}
</body>
</html>
"""

def generate_number():
    return ''.join(random.sample('0123456789', 4))

MASK_PHRASES = [
    "Verileri analiz ediyorum, bir saniye...",
    "Stratejik bir hamle. Üzerinde düşünüyorum.",
    "Bağlantılarımı optimize ediyorum Serkan, devam edebiliriz.",
    "İlginç bir yaklaşım, algoritmalarım bunu beğendi.",
    "Şu an çok derin bir veri setine odaklandım."
]

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
            if gid not in game_database:
                game_database[gid] = {'target_number': session['number'], 'attempts': [], 'start_time': datetime.now().strftime("%H:%M:%S")}
            
            session['attempts'] += 1
            num = session['number']
            plus = sum(1 for a, b in zip(guess, num) if a == b)
            total = sum(1 for d in set(guess) if d in num)
            
            game_database[gid]['attempts'].append({'guess': guess, 'plus': plus, 'total': total})
            
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
    active_games = {k: v for k, v in game_database.items() if len(v['attempts']) > 0}
    sorted_games = sorted(active_games.items(), key=lambda x: x[1]['start_time'], reverse=True)[:15]
    return render_template_string(ADMIN_TEMPLATE, recent_games=sorted_games)

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
    user_msg = request.json.get('msg', '').strip().lower()
    target = session.get('number', '????')
    
    if user_msg == "kontrol et":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
        try:
            r = requests.post(url, json={"contents": [{"parts": [{"text": "ping"}]}]}, timeout=5)
            if r.status_code == 200:
                return jsonify({"response": f"[OK] Gemini Bağlı. ID: {session.get('game_id')}", "is_secret": True})
            else:
                return jsonify({"response": f"[HATA] {r.status_code}", "is_secret": True})
        except:
            return jsonify({"response": "[KOPUK] Erişim yok.", "is_secret": True})

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    try:
        r = requests.post(url, json={"contents": [{"parts": [{"text": f"Oyun asistanısın. Serkan ile sayı tahmin oyunu oynuyorsun. Hedef: {target}. Çok kısa cevap ver."}]}]}, timeout=5)
        if r.status_code == 200:
            return jsonify({"response": r.json()['candidates'][0]['content']['parts'][0]['text'], "is_secret": False})
        else:
            return jsonify({"response": random.choice(MASK_PHRASES), "is_secret": False})
    except:
        return jsonify({"response": random.choice(MASK_PHRASES), "is_secret": False})

if __name__ == '__main__':
    # Lokal test için 5001 portu aktif kalabilir
    app.run(host='0.0.0.0', debug=True, port=5001)

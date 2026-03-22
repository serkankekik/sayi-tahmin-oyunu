import os
import random
import requests
import json
from flask import Flask, request, session, render_template_string, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'serkan_mobile_v12')
API_KEY = os.getenv('GEMINI_API_KEY')
CHEAT_CODE = os.getenv('GAME_CHEAT_CODE', 'a1z2')
MODEL_NAME = "gemini-2.0-flash-lite"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Sayı Tahmin Pro</title>
    <style>
        :root { --primary: #6c5ce7; --bg: #f4f7fa; --text: #2d3436; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); margin: 0; padding: 10px; color: var(--text); }
        
        .container { width: 100%; max-width: 900px; margin: 0 auto; display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        
        /* Mobil İçin Grid Ayarı */
        @media (max-width: 768px) {
            .container { grid-template-columns: 1fr; }
            .card { padding: 12px; }
            .digit { width: 50px !important; height: 60px !important; font-size: 28px !important; }
        }

        .card { background: white; padding: 20px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); display: flex; flex-direction: column; }
        h2 { margin: 0 0 10px 0; font-size: 1.2rem; border-bottom: 2px solid var(--bg); padding-bottom: 8px; }
        
        .status-bar { display: flex; justify-content: space-between; font-size: 13px; font-weight: 700; margin-bottom: 15px; color: #636e72; }
        
        /* Tahmin Girişi */
        .guess-row { display: flex; justify-content: center; gap: 10px; margin: 10px 0 20px 0; }
        .digit { width: 45px; height: 55px; font-size: 24px; text-align: center; border: 2px solid #dfe6e9; border-radius: 10px; outline: none; transition: 0.2s; -webkit-appearance: none; }
        .digit:focus { border-color: var(--primary); background: #f8f7ff; }
        .digit.error { border-color: #ff7675; background: #fff5f5; }

        .btn { border: none; border-radius: 10px; cursor: pointer; font-weight: 700; font-size: 14px; transition: 0.3s; padding: 14px; text-align: center; text-decoration: none; }
        .btn-main { background: var(--primary); color: white; width: 100%; box-shadow: 0 4px 10px rgba(108, 92, 231, 0.2); }
        .btn-main:disabled { background: #b2bec3; box-shadow: none; }
        
        .btn-group { display: flex; gap: 8px; margin-top: 10px; }
        .btn-surrender { background: #ffeaa7; color: #d35400; flex: 1; }
        .btn-reset { background: #dfe6e9; color: #636e72; flex: 1; }

        /* Geçmiş Tablosu */
        .table-wrap { margin-top: 20px; border-radius: 10px; overflow: hidden; border: 1px solid #eee; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th { background: #f8f9fa; padding: 10px; font-weight: 600; text-align: center; }
        td { padding: 12px 8px; border-bottom: 1px solid #f1f1f1; text-align: center; }
        .match-highlight { background: #fff9c4; font-weight: 800; color: #d63031; padding: 2px 4px; border-radius: 4px; }

        /* Chat Paneli */
        #chat-box { height: 280px; overflow-y: auto; padding: 12px; background: #fafafa; border-radius: 12px; margin-bottom: 10px; display: flex; flex-direction: column; gap: 8px; border: 1px solid #eee; }
        .msg { padding: 10px 14px; border-radius: 15px; font-size: 13px; max-width: 85%; line-height: 1.4; }
        .bot { background: var(--primary); color: white; border-bottom-left-radius: 2px; align-self: flex-start; }
        .user { background: #e2e8f0; color: #2d3436; border-bottom-right-radius: 2px; align-self: flex-end; }
        
        input#cin { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 10px; box-sizing: border-box; font-size: 14px; }

        .rules { grid-column: span 2; background: #2d3436; color: #dfe6e9; padding: 15px; border-radius: 12px; font-size: 12px; margin-top: 10px; }
        @media (max-width: 768px) { .rules { grid-column: span 1; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h2>🔢 Sayı Tahmin</h2>
            <div class="status-bar">
                <span>Hamle: {{ attempts }}</span>
                <span>Rekor: {{ best_score if best_score else '-' }}</span>
            </div>

            {% if game_over or surrendered %}
                <div style="text-align:center; padding: 15px; background: {{ '#fff2f2' if surrendered else '#dff9fb' }}; border-radius: 12px; font-weight:bold; margin-bottom:10px;">
                    {% if surrendered %}
                        🏳️ Pes Ettin! Sayı: <span style="font-size: 20px; color:#d63031;">{{ target }}</span>
                    {% else %}
                        🎉 Tebrikler! Hedef: {{ target }}
                    {% endif %}
                </div>
                <a href="/reset" class="btn btn-main" style="background:#2ecc71;">YENİ OYUN BAŞLAT</a>
            {% else %}
                <div id="err" style="color:#d63031; font-size:12px; text-align:center; height:18px; font-weight:600;"></div>
                <form method="post">
                    <div class="guess-row">
                        <input type="number" pattern="[0-9]*" inputmode="numeric" class="digit" name="d1" id="d1" maxlength="1" oninput="v(this)" autocomplete="off">
                        <input type="number" pattern="[0-9]*" inputmode="numeric" class="digit" name="d2" id="d2" maxlength="1" oninput="v(this)" autocomplete="off">
                        <input type="number" pattern="[0-9]*" inputmode="numeric" class="digit" name="d3" id="d3" maxlength="1" oninput="v(this)" autocomplete="off">
                        <input type="number" pattern="[0-9]*" inputmode="numeric" class="digit" name="d4" id="d4" maxlength="1" oninput="v(this)" autocomplete="off">
                    </div>
                    <button type="submit" id="btn" class="btn btn-main">Tahmin Et</button>
                </form>
                <div class="btn-group">
                    <a href="/surrender" class="btn btn-surrender">Pes Et</a>
                    <a href="/reset" class="btn btn-reset">Sıfırla</a>
                </div>
            {% endif %}

            <div class="table-wrap">
                <table>
                    <thead><tr><th>#</th><th>Tahmin</th><th>+ (Yer)</th><th>Doğru</th></tr></thead>
                    <tbody id="hist">
                        {% for item in history %}
                        <tr>
                            <td>{{ item.no }}</td>
                            <td class="cells"><span>{{ item.guess[0] }}</span><span>{{ item.guess[1] }}</span><span>{{ item.guess[2] }}</span><span>{{ item.guess[3] }}</span></td>
                            <td><b style="color:#2ecc71">{{ item.correct_place }}</b></td>
                            <td><b>{{ item.total_correct }}</b></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card">
            <h3>🤖 Akıllı Asistan</h3>
            <div id="chat-box">
                <div class="msg bot">Merhaba Serkan! Mobil sürüm hazır. Tahminlerini bekliyorum!</div>
            </div>
            <input type="text" id="cin" placeholder="Mesajını yaz...">
        </div>

        <div class="rules">
            <b>OYUN MANTIĞI:</b> 4 farklı rakamı bulmaya çalış. <br>
            <b>+ (Yer):</b> Kaç rakamın hem kendisi hem yeri doğru. <br>
            <b>Doğru:</b> Kaç rakam var ama yeri yanlış.
        </div>
    </div>

    <script>
        const ins = document.querySelectorAll('.digit');
        const btn = document.getElementById('btn');
        const err = document.getElementById('err');

        function v(el) {
            // Sadece 1 karakter sınırı
            if (el.value.length > 1) el.value = el.value.slice(0, 1);

            let vls = Array.from(ins).map(i => i.value).filter(x => x !== "");
            let dup = new Set(vls).size !== vls.length;
            
            if(dup) { 
                err.innerText = "Rakamlar tekrar edemez!"; 
                btn.disabled = true; 
                ins.forEach(i=>i.classList.add('error')); 
            } else { 
                err.innerText = ""; 
                btn.disabled = false; 
                ins.forEach(i=>i.classList.remove('error')); 
            }
            
            // Renklendirme
            const cur = Array.from(ins).map(i => i.value);
            document.querySelectorAll('#hist tr').forEach(row => {
                row.querySelectorAll('.cells span').forEach((s, idx) => {
                    s.className = (cur[idx] !== "" && s.innerText === cur[idx]) ? 'match-highlight' : '';
                });
            });

            // Otomatik Geçiş (Mobile uygun)
            if (el.value !== "") {
                const next = el.nextElementSibling;
                if (next) next.focus();
            }
        }

        // Backspace ile geri gitme
        ins.forEach((i, idx) => {
            i.addEventListener('keydown', (e) => {
                if (e.key === 'Backspace' && i.value === "" && idx > 0) {
                    ins[idx - 1].focus();
                }
            });
        });

        // Chat Fonksiyonları
        const cb = document.getElementById('chat-box');
        async function ask(m) {
            const r = await fetch('/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({msg:m})});
            const d = await r.json();
            cb.innerHTML += `<div class="msg bot">${d.response}</div>`;
            cb.scrollTop = cb.scrollHeight;
        }

        document.getElementById('cin').onkeypress = (e) => {
            if(e.key === 'Enter' && e.target.value.trim() !== "") {
                cb.innerHTML += `<div class="msg user">${e.target.value}</div>`;
                ask(e.target.value); e.target.value = '';
            }
        };
    </script>
</body>
</html>
"""

# ... (Geri kalan Python kodları - generate_number, index, chat, reset fonksiyonları aynı kalıyor)

def generate_number():
    return ''.join(random.sample('0123456789', 4))

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'number' not in session:
        session['number'] = generate_number()
        session['attempts'] = 0
        session['history'] = []
        session['surrendered'] = False
    
    feedback = ""; game_over = False
    if request.method == 'POST':
        guess = "".join([request.form.get(f'd{i}', '') for i in range(1,5)])
        if len(guess) == 4 and len(set(guess)) == 4:
            session['attempts'] += 1
            num = session['number']
            plus = sum(1 for a, b in zip(guess, num) if a == b)
            total = sum(1 for d in set(guess) if d in num)
            session['history'].insert(0, {"no": session['attempts'], "guess": guess, "total_correct": total, "correct_place": plus})
            session.modified = True
            if plus == 4: 
                game_over = True
                if 'best_score' not in session or session['attempts'] < session['best_score']:
                    session['best_score'] = session['attempts']
            
    return render_template_string(HTML_TEMPLATE, history=session['history'], attempts=session['attempts'], 
                                game_over=game_over, feedback=feedback, target=session.get('number'),
                                best_score=session.get('best_score'), surrendered=session.get('surrendered'))

@app.route('/surrender')
def surrender():
    session['surrendered'] = True
    return render_template_string("<script>window.location.href='/';</script>")

@app.route('/chat', methods=['POST'])
def chat():
    user_msg = request.json.get('msg', '').strip().lower()
    target = session.get('number', '????')
    if user_msg == CHEAT_CODE:
        return jsonify({"response": f"🕵️‍♂️ **Hile:** Sayı **{target}**."})
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    try:
        r = requests.post(url, headers={'Content-Type':'application/json'}, data=json.dumps({"contents": [{"parts": [{"text": f"Oyun asistanısın. Sayı: {target}. Mesaj: {user_msg}"}]}]}))
        return jsonify({"response": r.json()['candidates'][0]['content']['parts'][0]['text']})
    except:
        return jsonify({"response": "🤖: Devam Serkan!"})

@app.route('/reset')
def reset():
    best = session.get('best_score')
    session.clear()
    session['best_score'] = best
    return render_template_string("<script>window.location.href='/';</script>")

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5001)
    
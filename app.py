import os
import uuid
import requests  # 使用最穩定的標準 HTTP 請求
from flask import Flask, request, redirect, url_for, flash, render_template_string
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
# Flask 訊息閃現所需的加密金鑰
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "pure-vercel-blob-secret")

# ==========================================
# 1. Neon Postgres 資料庫設定
# ==========================================
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 乾淨的圖片資料表模型
class UserImage(db.Model):
    __tablename__ = 'user_images'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)          # 圖片標題
    url = db.Column(db.String(500), nullable=False)            # 儲存 Vercel Blob 的永久圖片網址
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

# 自動在 Neon 資料庫中建立資料表
with app.app_context():
    db.create_all()

# ==========================================
# 2. 前端內嵌 HTML 網頁範本 (Jinja2 語法)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>我的雲端圖片相簿</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f4f6f9; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 1100px; margin: 0 auto; }
        header { text-align: center; background: #ffffff; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 30px; }
        h1 { margin: 0 0 10px 0; color: #111; }
        p { margin: 0; color: #666; }
        .main-layout { display: flex; gap: 25px; flex-wrap: wrap; }
        .upload-section { flex: 1; min-width: 300px; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); height: fit-content; }
        .gallery-section { flex: 2; min-width: 500px; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 8px; font-weight: bold; color: #444; }
        .form-group input { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; font-size: 14px; }
        .form-group input:focus { border-color: #000; outline: none; }
        button { background: #000000; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; transition: background 0.2s; }
        button:hover { background: #222222; }
        .flash-msg { background: #fff3cd; color: #856404; padding: 12px; border-radius: 6px; margin-bottom: 20px; border: 1px solid #ffeeba; font-size: 14px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; }
        .card { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .card img { width: 100%; height: 180px; object-fit: cover; display: block; }
        .card-body { padding: 15px; }
        .card-title { font-weight: bold; font-size: 16px; color: #222; word-break: break-all; }
        .card-time { font-size: 12px; color: #888; margin-top: 8px; }
        .empty-text { color: #999; text-align: center; width: 100%; padding: 40px 0; font-style: italic; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🖼️ 我的雲端圖片展示牆</h1>
            <p>架構：Vercel (Flask) + Vercel Blob (儲存) + Neon (Postgres 資料庫)</p>
        </header>

        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for msg in messages %}
              <div class="flash-msg">{{ msg }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <div class="main-layout">
            <div class="upload-section">
                <h3 style="margin-top:0; margin-bottom: 20px; color: #111;">上傳新相片</h3>
                <form action="/upload" method="POST" enctype="multipart/form-data">
                    <div class="form-group">
                        <label>圖片名稱 / 描述</label>
                        <input type="text" name="title" placeholder="請輸入相片名稱..." required>
                    </div>
                    <div class="form-group">
                        <label>選取圖片檔案</label>
                        <input type="file" name="image_file" accept="image/*" required>
                    </div>
                    <button type="submit">直接上傳到雲端</button>
                </form>
            </div>

            <div class="gallery-section">
                <h3 style="margin-top:0; margin-bottom: 20px; color: #111;">所有照片牆</h3>
                <div class="grid">
                    {% for item in records %}
                    <div class="card">
                        <img src="{{ item.url }}" alt="User Image">
                        <div class="card-body">
                            <div class="card-title">{{ item.title }}</div>
                            <div class="card-time">{{ item.created_at.strftime('%Y-%m-%d %H:%M') }}</div>
                        </div>
                    </div>
                    {% else %}
                    <p class="empty-text">目前相簿裡空空如也，快上傳第一張照片吧！</p>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

# ==========================================
# 3. 路由邏輯 (Routes)
# ==========================================

# 首頁：撈取所有資料，並直接渲染內嵌的 HTML 字串
@app.route('/')
def index():
    records = UserImage.query.order_by(UserImage.created_at.desc()).all()
    return render_template_string(HTML_TEMPLATE, records=records)

# 處理檔案上傳的路由
@app.route('/upload', methods=['POST'])
def upload():
    title = request.form.get('title', '未命名相片')
    file = request.files.get('image_file')

    if file and file.filename != '':
        try:
            # 1. 從 Vercel 環境變數中自動取得 Blob 的 Token
            blob_token = os.environ.get("BLOB_READ_WRITE_TOKEN")
            if not blob_token:
                raise Exception("找不到 BLOB_READ_WRITE_TOKEN，請確保 Vercel 後台有開通 Storage Blob")

            # 2. 擷取原檔案的副檔名，並產生乾淨的 UUID 檔名
            ext = os.path.splitext(file.filename)[1].lower()
            if not ext:
                ext = '.jpg'  
            clean_filename = f"{uuid.uuid4().hex}{ext}"

            # 3. 破關核心：修正網址為 /v1/objects/ 並帶上參數
            url = f"https://blob.vercel-storage.com/v1/objects/{clean_filename}?multipart=false"
            
            headers = {
                "Authorization": f"Bearer {blob_token}",
                "x-api-version": "7",  # 指定 Vercel Blob 的最新 Edge 協定版本
            }
            
            # 使用 PUT 請求，將檔案的二進位內容直接塞進 Data Body
            response = requests.put(url, data=file.read(), headers=headers)
            
            if response.status_code == 200 or response.status_code == 201:
                res_data = response.json()
                img_url = res_data['url']  # 成功拿取永久公開圖片網址
                
                # 4. 將圖片資訊與 URL 寫入 Neon Postgres 資料庫
                new_image = UserImage(title=title, url=img_url)
                db.session.add(new_image)
                db.session.commit()
                
                flash('圖片上傳成功，已成功同步到 Vercel Blob 與 Neon 資料庫！')
            else:
                flash(f'Vercel Blob 伺服器拒絕: {response.text}')

        except Exception as e:
            flash(f'上傳過程中發生錯誤: {str(e)}')
            
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
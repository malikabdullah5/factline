from flask import Flask, render_template, request, redirect, url_for, session, g
from werkzeug.utils import secure_filename
import os
import sqlite3
from math import ceil
from datetime import datetime
def time_ago(past_time_str):
    past_time = datetime.strptime(past_time_str, "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    diff = now - past_time
    seconds = diff.total_seconds()

    if seconds < 60:
        return f"Published about {int(seconds)} seconds ago"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"Published about {minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"Published about {hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = int(seconds / 86400)
        return f"Published about {days} day{'s' if days != 1 else ''} ago"

app = Flask(__name__)
DATABASE = 'news.db'
app.secret_key = 'your_secret_key_here'

# ✅ Set upload folder
app.config['UPLOAD_FOLDER'] = 'static/uploads'

app.jinja_env.globals.update(time_ago=time_ago)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # 👈 یہ اہم لائن ہے
    return db
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def home():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM news ORDER BY created_at DESC")
    all_news = cursor.fetchall()

    page = int(request.args.get('page', 1))
    per_page = 10
    total_pages = ceil(len(all_news) / per_page)

    start = (page - 1) * per_page
    end = start + per_page
    paginated_news = all_news[start:end]

    return render_template('home.html', news=paginated_news, page=page, total_pages=total_pages)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] == 'ali' and request.form['password'] == 'mk0313930':
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            error = 'Invalid credentials'
    return render_template('login.html', error=error)

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('admin.html')


# 🔽 یہ routes نیچے add کریں 🔽

@app.route('/view-news')
def view_news():
    conn = sqlite3.connect('news.db')
    conn.row_factory = sqlite3.Row  # تاکہ attribute-style یا key-style دونوں چلیں
    cur = conn.cursor()
    cur.execute("SELECT * FROM news ORDER BY created_at DESC")
    news_list = cur.fetchall()
    conn.close()
    return render_template('view_news.html', news_list=news_list)
    
@app.route('/edit-news/<int:news_id>', methods=['GET', 'POST'])
def edit_news(news_id):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        new_title = request.form['title']
        new_content = request.form['content']
        cursor.execute("UPDATE news SET title=?, content=? WHERE id=?", (new_title, new_content, news_id))
        conn.commit()
        return redirect(url_for('view_news'))

    cursor.execute("SELECT title, content FROM news WHERE id=?", (news_id,))
    news = cursor.fetchone()
    return render_template('edit_news.html', news=news, news_id=news_id)
@app.route('/delete-news/<int:news_id>')
def delete_news(news_id):
    conn = sqlite3.connect('news.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM news WHERE id=?", (news_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_news'))
from datetime import datetime
import pytz  # 👈 یہ اوپر import میں ہونا چاہیے

@app.route('/add-news', methods=['GET', 'POST'])
def add_news():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        summary = request.form['summary']
        content = request.form['content']
        category = request.form['category']
        image = request.files['image']

        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # ✅ پاکستان ٹائم زون کے مطابق وقت حاصل کریں
        pakistan_time = datetime.now(pytz.timezone('Asia/Karachi'))
        formatted_time = pakistan_time.strftime('%Y-%m-%d %H:%M:%S')

        conn = get_db()
        conn.execute('INSERT INTO news (title, summary, content, category, image, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                     (title, summary, content, category, filename, formatted_time))
        conn.commit()
        return redirect(url_for('admin'))

    return render_template('add_news.html')
@app.route('/news/<int:news_id>')
def news_detail(news_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM news WHERE id = ?", (news_id,))
    news = cursor.fetchone()

    if news:
        return render_template('news_detail.html', news=news)
    else:
        return "News not found", 404

@app.route('/latest')
def latest_news():
    # فرضی تازہ خبریں
    latest = [
        
    ]
    return render_template('latest.html', news=latest)

@app.route('/category/<category_name>')
def category_page(category_name):
    conn = sqlite3.connect('news.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM news WHERE category = ? ORDER BY created_at DESC", (category_name,))
    news = cur.fetchall()
    conn.close()
    return render_template('category.html', news=news, category=category_name)

@app.route('/search')
def search():
    query = request.args.get('query', '').lower()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM news
        WHERE LOWER(title) LIKE ? OR LOWER(summary) LIKE ? OR LOWER(content) LIKE ?
        ORDER BY created_at DESC
    """, ('%' + query + '%', '%' + query + '%', '%' + query + '%'))

    results = cursor.fetchall()

    return render_template('search_results.html', query=query, results=results)
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))
    

if __name__ == '__main__':
    app.run(debug=True)
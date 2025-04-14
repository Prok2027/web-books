import os
import sqlite3
from functools import wraps
from statistics import median
import re

from flask import Flask, render_template, request, session, redirect, url_for, abort, flash, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = 'gdfg5fgdfy45ygwet4564567'
UPLOAD_FOLDER = r'C:\Users\Vadim Prokofev\Desktop\uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db():
    conn = sqlite3.connect('instance/database.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def home():
    db = get_db()
    cnt = db.execute('SELECT COUNT(*) FROM books').fetchone()[0]
    db.close()
    return render_template('index.html', s=f'Всего книг: {cnt}')


@app.template_filter('stars')
def render_stars(val):
    try:
        val = float(val)
    except:
        return '-'
    full = int(val)
    half = 1 if val - full >= 0.5 else 0
    empty = 5 - full - half
    st_ht = ''.join(['<i class="fas fa-star text-warning"></i>' for i in range(full)])
    if half:
        st_ht += '<i class="fas fa-star-half-stroke text-warning"></i>'
    st_ht += ''.join(['<i class="far fa-star text-warning"></i>' for i in range(empty)])
    return st_ht

def norm(title):
    title = title.lower()
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', '_', title)
    return title

@app.route('/books')
def show_books():
    user = session.get('user', '')
    if not user:
        flash('Вы должны войти в систему, чтобы просматривать библиотеку.', 'danger')
        return redirect(url_for('login'))
    sel_gen = request.args.get('genre', None)
    sel_aut = request.args.get('author', '')
    sel_rat = request.args.get('rating', type=float)
    find = request.args.get('title', '')
    conn = get_db()
    genres = conn.execute('SELECT * FROM genre').fetchall()
    authors = conn.execute('SELECT DISTINCT author FROM books').fetchall()
    query = '''
        SELECT b.*, AVG(g.points) as avg_rating, c.cover
        FROM books b
        LEFT JOIN grade g ON b.id = g.book_id
        LEFT JOIN covers c ON b.id = c.book_id
    '''
    cond = []
    params = []
    if sel_gen:
        cond.append(
            'b.id IN (SELECT book_id FROM book_genre bg JOIN genre g ON bg.genre_id = g.id WHERE g.genre_name = ?)')
        params.append(sel_gen)
    if sel_aut:
        cond.append('b.author = ?')
        params.append(sel_aut)
    if find:
        cond.append('b.title LIKE ? COLLATE NOCASE')
        params.append(f'%{find}%')
    if cond:
        query += ' WHERE ' + ' AND '.join(cond)
    query += ' GROUP BY b.id'
    if sel_rat is not None:
        query += ' HAVING avg_rating >= ?'
        params.append(sel_rat)
    books = conn.execute(query, params).fetchall()
    user_row = conn.execute('SELECT id FROM user_login WHERE login = ?', (user,)).fetchone()
    user_id = user_row['id'] if user_row else -1
    grades = conn.execute('SELECT book_id, points FROM grade WHERE user_id = ?', (user_id,)).fetchall()
    book_grade = {int(grade['book_id']): grade['points'] for grade in grades}
    grd = conn.execute('SELECT book_id, points FROM grade').fetchall()
    rev = conn.execute('SELECT book_id, review FROM review WHERE user_id = ?', (user_id,)).fetchall()
    book_rev = {int(row['book_id']): row['review'] for row in rev}
    book_stat = {}
    book_cnt = {}
    book_med = {}
    book_mean = {}
    book_median = {}
    for row in grd:
        bid = int(row['book_id'])
        rp = row['points']
        if rp is None or (isinstance(rp, str) and rp.strip() == ''):
            continue
        pts = float(rp)
        book_stat[bid] = book_stat.get(bid, 0) + pts
        book_cnt[bid] = book_cnt.get(bid, 0) + 1
        if bid not in book_med:
            book_med[bid] = []
        book_med[bid].append(pts)
    for key, val in book_stat.items():
        book_mean[key] = val / book_cnt.get(key, 1)
        book_median[key] = median(book_med[key])
    fav_rows = conn.execute('SELECT book_id FROM best WHERE user_id = ?', (user_id,)).fetchall()
    fav_books = {row['book_id'] for row in fav_rows}
    conn.close()
    return render_template('books.html',
                           books=books,
                           book_grade=book_grade,
                           book_reviews=book_rev,
                           book_mean=book_mean,
                           book_median=book_median,
                           genres=genres,
                           authors=authors,
                           selected_genre=sel_gen,
                           selected_author=sel_aut,
                           selected_rating=sel_rat,
                           search_query=find,
                           fav_books=fav_books)



@app.route('/statistics')
def statistics():
    db = get_db()
    tt = db.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    avg = db.execute("SELECT AVG(points) FROM grade").fetchone()[0]
    top = db.execute('''
        SELECT g.genre_name, COUNT(*) as count
        FROM book_genre bg
        JOIN genre g ON bg.genre_id = g.id
        GROUP BY g.genre_name
        ORDER BY count DESC
        LIMIT 3
    ''').fetchall()
    return render_template('statistics.html',
                           total_books=tt,
                           avg_rating=avg,
                           top_genres=top)

@app.route('/uploads/<filename>')
def uploaded_file(f):
    return send_from_directory(app.config['UPLOAD_FOLDER'], f)

@app.route('/rate', methods=['POST'])
def rate_book():
    user = session.get('user', '')
    if user == '':
        flash('Вы должны войти в систему, чтобы ставить оценки.', 'danger')
        return redirect(url_for('login'))
    book_id = request.form['book_id']
    pts = request.form['points']
    rev = request.form.get('review', '').strip()
    conn = get_db()
    user_row = conn.execute('SELECT id FROM user_login WHERE login = ?', (user,)).fetchone()
    if user_row is None:
        flash('Пользователь не найден.', 'danger')
        return redirect(url_for('show_books'))
    user_id = user_row['id']

    ex = conn.execute('SELECT * FROM grade WHERE user_id = ? AND book_id = ?', (user_id, book_id)).fetchone()
    if ex:
        conn.execute('UPDATE grade SET points = ? WHERE user_id = ? AND book_id = ?', (pts, user_id, book_id))
    else:
        conn.execute('INSERT INTO grade (user_id, book_id, points) VALUES (?, ?, ?)', (user_id, book_id, pts))
    erev = conn.execute('SELECT * FROM review WHERE user_id = ? AND book_id = ?', (user_id, book_id)).fetchone()
    if erev:
        conn.execute('UPDATE review SET review = ? WHERE user_id = ? AND book_id = ?', (rev, user_id, book_id))
    else:
        conn.execute('INSERT INTO review (user_id, book_id, review) VALUES (?, ?, ?)', (user_id, book_id, rev))
    conn.commit()
    conn.close()
    flash('Оценка сохранена!', 'success')
    return redirect(url_for('show_books'))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


@app.route('/edit_genres', methods=['GET', 'POST'])
@admin_required
def edit_genres():
    conn = get_db()
    books = conn.execute('SELECT * FROM books').fetchall()
    genres = conn.execute('SELECT * FROM genre').fetchall()
    br = conn.execute('SELECT * FROM book_genre').fetchall()
    book_genres = {}
    for row in br:
        book_id = row['book_id']
        genre_id = row['genre_id']
        book_genres.setdefault(book_id, set()).add(genre_id)
    conn.close()
    return render_template('edit_genres.html', books=books, genres=genres, book_genres=book_genres)


@app.route('/update_genre', methods=['POST'])
@admin_required
def update_genre():
    data = request.get_json()
    book_id = data.get('book_id')
    genre_id = data.get('genre_id')
    flg = data.get('checked')
    conn = get_db()
    if flg:
        conn.execute('INSERT INTO book_genre (book_id, genre_id) VALUES (?, ?)', (book_id, genre_id))
    else:
        conn.execute('DELETE FROM book_genre WHERE book_id = ? AND genre_id = ?', (book_id, genre_id))
    conn.commit()
    conn.close()
    return '', 204


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        login_val = request.form['username']
        passw = request.form['password']
        conn = get_db()
        user = conn.execute('SELECT * FROM user_login WHERE login = ?', (login_val,)).fetchone()
        if user:
            flash('Пользователь с таким логином уже существует!', 'warning')
            conn.close()
            return redirect(url_for('register'))
        passw_h = generate_password_hash(passw)
        conn.execute('INSERT INTO user_login (login, password_hash) VALUES (?, ?)', (login_val, passw_h))
        conn.commit()
        conn.close()
        flash('Вы успешно зарегистрированы! Теперь войдите в систему.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    if request.method == 'POST':
        login_val = request.form['username']
        passw = request.form['password']
        conn = get_db()
        user = conn.execute('SELECT * FROM user_login WHERE login = ?', (login_val,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], passw):
            session['is_admin'] = (login_val == 'admin' or login_val == 'admin_test')
            session['user'] = login_val
            flash('Вы вошли!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Неверный логин или пароль', 'danger')
    return render_template('login.html')


@app.route('/add_book')
@admin_required
def add_book_page():
    conn = get_db()
    genres = conn.execute('SELECT * FROM genre').fetchall()
    conn.close()
    return render_template('add_books.html', genres=genres)


@app.route('/delete_book')
@admin_required
def delete_book_page():
    return render_template('delete_books.html')


@app.route('/add_book', methods=['POST'])
@admin_required
def add_book():
    title = request.form['title']
    author = request.form['author']
    genre_id = request.form['genre_id']
    conn = get_db()
    conn.execute("INSERT INTO books (title, author) VALUES (?, ?)",
                 (title, author))
    book_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    if 'cover' in request.files:
        file = request.files['cover']
        if file and allowed_file(file.filename):
            norm_t = norm(title)
            ext = file.filename.rsplit('.', 1)[1].lower()
            f = f"{book_id}_{norm_t}.{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], f))
            conn.execute("INSERT INTO covers (book_id, cover) VALUES (?, ?)", (book_id, f))
    conn.execute("INSERT INTO book_genre (book_id, genre_id) VALUES (?, ?)", (book_id, genre_id))
    conn.commit()
    conn.close()
    return redirect(url_for('show_books'))


@app.route('/favorite', methods=['POST'])
def favorite_book():
    user = session.get('user', '')
    if not user:
        flash('Вы должны войти в систему, чтобы добавлять избранное.', 'danger')
        return redirect(url_for('login'))
    book_id = request.form.get('book_id')
    act = request.form.get('action')
    conn = get_db()
    user_row = conn.execute('SELECT id FROM user_login WHERE login = ?', (user,)).fetchone()
    if not user_row:
        conn.close()
        flash('Пользователь не найден.', 'danger')
        return redirect(url_for('show_books'))
    user_id = user_row['id']
    if act == 'add':
        exists = conn.execute('SELECT id FROM best WHERE user_id = ? AND book_id = ?', (user_id, book_id)).fetchone()
        if not exists:
            conn.execute('INSERT INTO best (user_id, book_id) VALUES (?, ?)', (user_id, book_id))
    elif act == 'remove':
        conn.execute('DELETE FROM best WHERE user_id = ? AND book_id = ?', (user_id, book_id))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('show_books'))



@app.route('/favorites')
def favorites():
    user = session.get('user', '')
    if not user:
        flash('Вы должны войти в систему, чтобы просматривать избранное.', 'danger')
        return redirect(url_for('login'))
    conn = get_db()
    user_row = conn.execute('SELECT id FROM user_login WHERE login = ?', (user,)).fetchone()
    user_id = user_row['id'] if user_row else -1
    query = '''
        SELECT b.*, c.cover, AVG(g.points) as avg_rating
        FROM best bs
        JOIN books b ON bs.book_id = b.id
        LEFT JOIN covers c ON b.id = c.book_id
        LEFT JOIN grade g ON b.id = g.book_id
        WHERE bs.user_id = ?
        GROUP BY b.id
    '''
    fav_books = conn.execute(query, (user_id,)).fetchall()
    conn.close()
    return render_template('favorites.html', books=fav_books)


@app.route('/delete_book', methods=['POST'])
@admin_required
def delete_book():
    title = request.form['title']
    author = request.form['author']
    conn = get_db()
    conn.execute("""DELETE FROM books 
                        WHERE rowid IN (
                            SELECT rowid FROM books WHERE title = ? AND author = ? LIMIT 1
                        )""", (title, author))
    conn.commit()
    conn.close()
    return redirect(url_for('show_books'))


@app.route('/logout')
def logout():
    session.clear()  # Очищаем сессию
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)

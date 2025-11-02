from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import date

app = Flask(__name__)

# ----------------------------
# Database setup
# ----------------------------
def init_db():
    conn = sqlite3.connect('habits.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER,
            date TEXT,
            FOREIGN KEY (habit_id) REFERENCES habits (id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ----------------------------
# Routes
# ----------------------------

@app.route('/')
def index():
    """Home: show all habits and allow marking completions for a chosen date"""
    selected_date = request.args.get('date', date.today().isoformat())

    conn = sqlite3.connect('habits.db')
    cursor = conn.cursor()

    # Fetch all habits
    cursor.execute('SELECT id, name FROM habits')
    habits = cursor.fetchall()

    # Fetch completed habits for selected date
    cursor.execute('SELECT habit_id FROM completions WHERE date = ?', (selected_date,))
    completed = {row[0] for row in cursor.fetchall()}

    conn.close()
    return render_template('index.html', habits=habits, completed=completed, selected_date=selected_date)


@app.route('/complete/<int:habit_id>', methods=['POST'])
def complete(habit_id):
    """Mark a habit as done for a given date"""
    selected_date = request.form['date']
    conn = sqlite3.connect('habits.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM completions WHERE habit_id = ? AND date = ?', (habit_id, selected_date))
    already_done = cursor.fetchone()

    if not already_done:
        cursor.execute('INSERT INTO completions (habit_id, date) VALUES (?, ?)', (habit_id, selected_date))

    conn.commit()
    conn.close()
    return redirect(url_for('index', date=selected_date))


@app.route('/uncomplete/<int:habit_id>', methods=['POST'])
def uncomplete(habit_id):
    """Undo completion for a given date"""
    selected_date = request.form['date']
    conn = sqlite3.connect('habits.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM completions WHERE habit_id = ? AND date = ?', (habit_id, selected_date))
    conn.commit()
    conn.close()
    return redirect(url_for('index', date=selected_date))


@app.route('/manage', methods=['GET', 'POST'])
def manage():
    """Add or delete habits"""
    conn = sqlite3.connect('habits.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        if 'add' in request.form:
            name = request.form['name']
            cursor.execute('INSERT INTO habits (name) VALUES (?)', (name,))
        elif 'delete' in request.form:
            habit_id = request.form['delete']
            cursor.execute('DELETE FROM habits WHERE id = ?', (habit_id,))
            cursor.execute('DELETE FROM completions WHERE habit_id = ?', (habit_id,))
        conn.commit()

    cursor.execute('SELECT * FROM habits')
    habits = cursor.fetchall()
    conn.close()
    return render_template('manage.html', habits=habits)


from datetime import date, timedelta

@app.route('/history')
def history():
    """View all days since Nov 1 with completions, missed habits, and totals."""
    conn = sqlite3.connect('habits.db')
    cursor = conn.cursor()

    # Fetch all habits
    cursor.execute('SELECT id, name FROM habits')
    habits = cursor.fetchall()
    habit_dict = {h[0]: h[1] for h in habits}
    total_habits = len(habit_dict)

    # Fetch all completions
    cursor.execute('SELECT habit_id, date FROM completions')
    completions = cursor.fetchall()
    conn.close()

    # Map date -> set of completed habit names
    completed_by_day = {}
    for habit_id, d in completions:
        completed_by_day.setdefault(d, set()).add(habit_dict[habit_id])

    # Generate all days from Nov 1 to today
    start_date = date(2025, 11, 1)
    end_date = date.today()
    delta = timedelta(days=1)

    history_dict = {}
    current = start_date
    while current <= end_date:
        d_str = current.isoformat()
        done = completed_by_day.get(d_str, set())
        missed = set(habit_dict.values()) - done
        history_dict[d_str] = {
            'done': done,
            'missed': missed,
            'count': f"{len(done)} / {total_habits}"
        }
        current += delta

    # Sort newest first
    sorted_history = sorted(history_dict.items(), reverse=True)

    return render_template('history.html', history=sorted_history)


if __name__ == '__main__':
    app.run(debug=True)

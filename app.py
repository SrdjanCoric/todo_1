from flask import Flask, session, flash, render_template, url_for, redirect, request, g

import secrets

from uuid import uuid4

import os

from functools import wraps

from werkzeug.exceptions import NotFound

from utils import (
    error_for_list_name,
    error_for_todo,
    find_todo_by_id,
    todos_remaining,
    is_list_completed,
    sort_items,
    is_todo_completed,
)

app = Flask(__name__)

app.secret_key=secrets.token_hex(32)

from database_persistence import DatabasePersistence

@app.before_request
def initialize_session():
    g.storage = DatabasePersistence()

@app.context_processor
def list_utilities_processor():
    return dict(
                is_list_completed=is_list_completed
            )

def require_list(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        list_id = kwargs.get('list_id')
        lst = g.storage.find_list(list_id)
        if not lst:
            raise NotFound(description="List not found")
        return f(lst=lst, *args, **kwargs)
    return decorated_function

def require_todo(f):
    @wraps(f)
    @require_list
    def decorated_function(lst, *args, **kwargs):
        todo_id = kwargs.get('todo_id')
        todo = find_todo_by_id(todo_id, lst['todos'])
        if not todo:
            raise NotFound(description="Todo not found")
        return f(lst=lst, todo=todo, *args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    return redirect(url_for('get_lists'))

@app.route("/lists/new")
def add_list():
    return render_template('new_list.html')

@app.route("/lists")
def get_lists():
    lists = sort_items(g.storage.all_lists(), is_list_completed)
    return render_template('lists.html', lists=lists, todos_remaining = todos_remaining)

@app.route("/lists", methods=["POST"])
def create_list():
    name = request.form["list_name"].strip()
    error = error_for_list_name(name, g.storage.all_lists())
    if error:
        flash(error, "error")
        return render_template('new_list.html', title=name)

    g.storage.create_new_list(name)
    flash("The list has been created.", "success")
    session.modified = True
    return redirect(url_for('get_lists'))

@app.route("/lists/<int:list_id>")
@require_list
def show_list(lst, list_id):
    todos = sort_items(lst['todos'], is_todo_completed)
    return render_template('list.html', lst=lst, todos=todos)

@app.route("/lists/<int:list_id>/todos", methods=["POST"])
@require_list
def create_todo(lst, list_id):
    todo_name = request.form["todo"].strip()
    error = error_for_todo(todo_name)
    if error:
        flash(error, "error")
        return render_template('list.html', lst=lst, todo_name=todo_name)
    g.storage.create_new_todo(list_id, todo_name)
    flash("The todo was added.", "success")
    return redirect(url_for('show_list', list_id=list_id))

@app.route("/lists/<int:list_id>/todos/<int:todo_id>/toggle", methods=["POST"])
@require_todo
def update_todo_status(lst, todo, list_id, todo_id):
    is_completed = request.form['completed'] == 'True'
    g.storage.update_todo_status(list_id, todo_id, is_completed)
    flash("The todo has been updated.", "success")
    return redirect(url_for('show_list', list_id=list_id))

@app.route("/lists/<int:list_id>/todos/<int:todo_id>/delete", methods=["POST"])
@require_todo
def delete_todo(lst, todo, list_id, todo_id):
    g.storage.delete_todo_from_list(list_id, todo_id)

    flash("The todo has been deleted.", "success")
    return redirect(url_for('show_list', list_id=list_id))

@app.route("/lists/<int:list_id>/complete_all", methods=["POST"])
@require_list
def mark_all_todos_completed(list_id, lst):
    g.storage.mark_all_todos_as_completed(list_id)

    flash("All todos have been updated.", "success")
    return redirect(url_for('show_list', list_id=list_id))

@app.route("/lists/<int:list_id>/edit")
@require_list
def edit_list(lst, list_id):
    return render_template('edit_list.html', lst=lst)

@app.route("/lists/<int:list_id>/delete", methods=["POST"])
@require_list
def delete_list(lst, list_id):
    g.storage.delete_list(list_id)
    flash("The list has been deleted.", "success")
    return redirect(url_for('get_lists'))

@app.route("/lists/<int:list_id>", methods=["POST"])
@require_list
def update_list(lst, list_id):
    name = request.form["list_name"].strip()
    error = error_for_list_name(name, g.storage.all_lists())
    if error:
        flash(error, "error")
        return render_template('edit_list.html', lst=lst, name=name)
    g.storage.update_list_name(list_id, name)
    flash("The list has been updated.", "success")
    return redirect(url_for('get_lists'))

if __name__ == "__main__":
    if os.environ.get('FLASK_ENV') == 'production':
        app.run(debug=False)
    else:
        app.run(debug=True, port=5003)
from flask import Blueprint, render_template

main = Blueprint('main', __name__)

@main.route('/')
def habits():
    return render_template('habits.html')
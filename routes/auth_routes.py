from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models.user import UserModel
from utils.validators import validate_login_input

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/msasathik', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if session.get('user_id'):
            return redirect(url_for('admin.dashboard') if session.get('role') in ('admin', 'super_admin') else url_for('home.index'))
        return render_template('login.html', email='')

    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    is_valid, errors = validate_login_input(email, password)
    if not is_valid:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Please enter valid email and password.'}), 400
        flash('Please enter valid email and password.', 'danger')
        return render_template('login.html', errors=errors, email=email)

    user = UserModel.find_by_email(email)

    # Demo admin fallback if database is unseeded / offline
    if not user and email.lower() == 'admin@sathikgroups.com' and password == 'ChangeMe@2024!':
        user = {
            '_id': 'demo_super_admin_id',
            'name': 'Super Admin (Demo)',
            'email': 'admin@sathikgroups.com',
            'role': 'super_admin'
        }
        session['user_id'] = user['_id']
        session['user_name'] = user['name']
        session['user_email'] = user['email']
        session['role'] = user['role']

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, 'redirect': url_for('admin.dashboard')})
        return redirect(url_for('admin.dashboard'))

    if not user or not UserModel.verify_password(user, password):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': 'Invalid email or password.'}), 401
        flash('Invalid email or password.', 'danger')
        return render_template('login.html', email=email)

    session['user_id'] = user['_id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']
    session['role'] = user.get('role', 'customer')

    target_url = url_for('admin.dashboard') if session['role'] in ('admin', 'super_admin') else url_for('home.index')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'success': True, 'redirect': target_url})

    return redirect(target_url)

@auth_bp.route('/ashiksathik', methods=['GET', 'POST'])
def old_login():
    return redirect(url_for('auth.login'), code=301)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    if not name or not email or not password or len(password) < 6:
        flash('Please fill in all fields with a password of at least 6 characters.', 'danger')
        return render_template('register.html', name=name, email=email)

    user_id = UserModel.create(name=name, email=email, password=password, role='customer')
    if not user_id:
        flash('An account with this email already exists.', 'danger')
        return render_template('register.html', name=name, email=email)

    session['user_id'] = user_id
    session['user_name'] = name
    session['user_email'] = email
    session['role'] = 'customer'

    flash('Account registered successfully!', 'success')
    return redirect(url_for('home.index'))

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home.index'))

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user, AnonymousUserMixin
from app import mysql
from users_policy import UsersPolicy
from functools import wraps


bp = Blueprint('auth' , __name__, url_prefix='/auth' )

class Anonymous(AnonymousUserMixin):
  def __init__(self):
    self.id = 0



class User(UserMixin):
    def __init__(self, user_id, login, role_id,first_name,last_name,middle_name):
        super().__init__()
        self.id=user_id
        self.login=login
        self.role_id = role_id
        self.first_name = first_name
        self.last_name = last_name
        self.middle_name = middle_name

    def can(self, action, record=None):
        policy=UsersPolicy(record=record)
        method = getattr(policy, action, None)
        if method:
            return method()
        return False

def load_record(user_id):
    if user_id is None:
        return None
    cursor = mysql.connection.cursor(named_tuple=True)
    cursor.execute('SELECT * FROM exam_users WHERE id=%s;', (user_id,))
    record = cursor.fetchone()
    cursor.close()
    return record

def check_rights(action):
    def decorator(func):
        @wraps(func)
        def wrapper(*args,**kwargs):
            record = load_record(kwargs.get('user_id'))
            if not current_user.can(action, record=record):
                flash('У вас недостаточно прав для доступа к данной странице','danger')
                return redirect(url_for('index'))
            return func(*args,**kwargs)
        return wrapper
    return decorator

def load_user(user_id):
    cursor = mysql.connection.cursor(named_tuple=True)
    cursor.execute('SELECT * FROM exam_users WHERE id=%s;', (user_id,))
    db_user = cursor.fetchone()
    cursor.close()
    if db_user:
            return User(user_id=db_user.id, login=db_user.login, role_id=db_user.role_id,first_name = db_user.first_name,last_name =db_user.last_name,middle_name =db_user.middle_name)
    return None   

@bp.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        login=request.form.get('login')
        password=request.form.get('password')
        remember_me=request.form.get('remember_me')=='on'
        if login and password:
            cursor = mysql.connection.cursor(named_tuple=True)
            cursor.execute('SELECT * FROM exam_users WHERE login = %s and password_hash = SHA2(%s, 256);', (login, password))
            db_user = cursor.fetchone()
            cursor.close()
            if db_user:
                    user= User(user_id=db_user.id, login=db_user.login, role_id=db_user.role_id,first_name = db_user.first_name,last_name =db_user.last_name,middle_name =db_user.middle_name)
                    login_user(user, remember=remember_me)


                    flash('Вы успешно аутентифицированны','success')
                    
                    next=request.args.get('next')
                    
                    return redirect(next or url_for('index'))
        flash('Введены неверные логин и/или пароль.','danger')    
    return render_template('login.html')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

def init_login_manager(app):
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view='auth.login'
    login_manager.login_message='Для доступа к данной странице нужно аутенцифицироваться'
    login_manager.login_message_category='warning'
    login_manager.user_loader(load_user)
    login_manager.anonymous_user = Anonymous
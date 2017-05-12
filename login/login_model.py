from werkzeug.security import generate_password_hash

import db_control
from plugin import PluginsRegistry

__registry__ = cr = PluginsRegistry()

db = db_control.get_db()


users_roles = db.Table('users_roles',
    db.Column('username', db.String(45), db.ForeignKey('users.username')),
    db.Column('role_id', db.String(45), db.ForeignKey('roles.id')))


class Role(db.Model):
    __bind_key__ = 'default'
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), unique=True)
    description = db.Column(db.String(255))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        # return "<Model Role `{}`>".format(self.name)
        return self.name

# Create user model.
class User(db.Model):
    __bind_key__ = 'default'
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255), unique=True)
    # login = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(64))
    email = db.Column(db.String(120))

    roles = db.relationship(
        'Role',
        secondary=users_roles,
        backref=db.backref('users', lazy='dynamic'))

    def __init__(self, username, password,rolename="default"):
        self.username = username
        self.password = password

        # Setup the default-role for user.
        role = Role.query.filter_by(name=rolename).one()
        self.roles.append(role)


    def __repr__(self):
        """Define the string format for instance of User."""
        return "<Model User `{}`>".format(self.username)

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    # Required for administrative interface
    def __unicode__(self):
        return self.username

    @staticmethod
    def find_user(username):
        # return User.query.filter_by(username = username).first()
        return User.query.get(username)


def create_init_data():
    db.create_all()
    admin_role = Role(name="admin")
    default_role = Role(name="default")
    db_control.get_db().session.add(admin_role)
    db_control.get_db().session.add(default_role)
    db_control.get_db().session.commit()
    admin_user = User(username="admin", password=generate_password_hash("admin"),rolename="admin")
    db_control.get_db().session.add(admin_user)
    db_control.get_db().session.commit()
    return

def create_test_data():
    db.create_all()
    admin_user = User(username="3546065794", password=generate_password_hash("test"),rolename="default")
    db_control.get_db().session.add(admin_user)
    db_control.get_db().session.commit()
    return

db.create_all()

@cr.model('91-Role')
def get_role_model():
    return Role


@cr.model('92-User')
def get_user_model():
    return User

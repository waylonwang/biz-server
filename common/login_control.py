from flask_login import current_user, LoginManager
from flask_principal import Principal, Permission, RoleNeed, identity_loaded, UserNeed
from werkzeug.security import check_password_hash
from wtforms import form, validators, fields

import db_control
from common import login_model
# Create the Flask-Principal's instance
from common.login_model import User

principals = Principal()

# 这里设定了 3 种权限, 这些权限会被绑定到 Identity 之后才会发挥作用.
# Init the role permission via RoleNeed(Need).
admin_permission = Permission(RoleNeed('admin'))
# poster_permission = Permission(RoleNeed('poster'))
default_permission = Permission(RoleNeed('default'))


# Define login and registration forms (for flask-login)
class LoginForm(form.Form):
    username = fields.StringField('用户名', validators=[validators.required()])
    password = fields.PasswordField('密&nbsp;&nbsp;&nbsp;&nbsp;码', validators=[validators.required()])

    def validate(self):
        user = self.get_user()

        if user is None:
            raise validators.ValidationError('用户名错误')

        # we're comparing the plaintext pw with the the hash from the db
        if not check_password_hash(user.password, self.password.data):
            # to compare plain text passwords use
            # if user.password != self.password.data:
            raise validators.ValidationError('密码错误')

        return True

    def get_user(self):
        # return login_model.User.find_user(self.username)
        return db_control.get_db().session.query(login_model.User).filter_by(username=self.username.data).first()


class RegistrationForm(form.Form):
    username = fields.StringField(validators=[validators.required()])
    email = fields.StringField()
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        if db_control.get_db().session.query(login_model.User).filter_by(username=self.username.data).count() > 0:
            raise validators.ValidationError('Duplicate username')


# Initialize flask-login
def init(app):
    app.config['SECRET_KEY'] = 'y9u1nNPiRuCq'

    login_manager = LoginManager()
    login_manager.init_app(app)

    principals.init_app(app)

    @login_manager.user_loader
    def load_user(username):
        # Return an instance of the User model
        return User.find_user(username=username)

    @identity_loaded.connect_via(app)
    def on_identity_loaded(sender, identity):
        """Change the role via add the Need object into Role.

           Need the access the app object.
        """

        # Set the identity user object
        identity.user = current_user

        # Add the UserNeed to the identity user object
        if hasattr(current_user, 'username'):
            identity.provides.add(UserNeed(current_user.username))

        # Add each role to the identity user object
        if hasattr(current_user, 'roles'):
            for role in current_user.roles:
                identity.provides.add(RoleNeed(role.name))

    # Register the Blueprint into app object
    # app.register_blueprint(blog.blog_blueprint)
    # app.register_blueprint(main.main_blueprint)

    return app

# -*- coding: utf-8 -*-
from flask.ext.wtf import Form, PasswordField, SelectMultipleField, \
        validators, ValidationError
from flask.ext.wtf.html5 import EmailField

class LoginForm(Form):
   email = EmailField(u"Email", [validators.required()])
   password = PasswordField(u"Hasło", [validators.required()])

class ChangePasswordForm(Form):
   current_password = PasswordField(u"Obecne hasło", [validators.Required(u'Proszę podaj hasło')])
   password = PasswordField(u"Hasło", [validators.Required(u'Proszę podaj hasło')])
   re_password = PasswordField(u"Powtórz hasło", 
                               [validators.Required(u'Proszę ponownie podaj hasło')])

class UserEditForm(Form):
   password = PasswordField(u"Hasło")
   re_password = PasswordField(u"Powtórz hasło")
   roles = SelectMultipleField(u"Uprawnienia")

class UserAddForm(UserEditForm):
    password = PasswordField(u"Hasło", [validators.Required(u'Proszę podaj hasło')])
    re_password = PasswordField(u"Powtórz hasło", 
                               [validators.Required(u'Proszę ponownie podaj hasło')])
    email = EmailField(u"Email", [validators.Required(u'Proszę podaj email'),
                                 validators.Email(u'Podano nieprawidłowy email')])
    def validate_email(form, field):
        from recorder.models import User
        if User.load(field.data):
            raise ValidationError(u"Email '%s' jest już zajety" % field.data)



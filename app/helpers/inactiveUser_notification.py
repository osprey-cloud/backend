from flask import render_template
from .email import send_email
from flask import Flask, request


def send_inactive_notification_to_user(email, name, app, template, subject, date, is_success_template=None):
    try:
        html = render_template(template,
                              name=name, 
                              success=is_success_template) 
        
        result = send_email(email, subject, html, email, app)
        if result is None:
            return True

        return result
        
    except Exception as e:
        print(f"Error in send_inactive_notification_to_user: {str(e)}")
        return False  
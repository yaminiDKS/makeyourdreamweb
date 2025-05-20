from flask import Flask, request, redirect
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# Email configuration
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
EMAIL_USERNAME = 'yaminidks004@gmail.com'
EMAIL_PASSWORD = 'Yamini@55'
TO_EMAIL = 'sec22ad083@sairamtap.edu.in'

@app.route('/send_email', methods=['POST'])
def send_email():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']

    # Create the email content
    message = f"Name: {name}\nEmail: {email}\nPhone: {phone}"
    msg = MIMEText(message)
    msg['Subject'] = 'New Contact Us Form Submission'
    msg['From'] = EMAIL_USERNAME
    msg['To'] = TO_EMAIL

    try:
        # Send the email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USERNAME, TO_EMAIL, msg.as_string())
        return "Email sent successfully!"
    except Exception as e:
        return f"Failed to send email: {e}"

if __name__ == '__main__':
    app.run(debug=True)
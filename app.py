import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import bcrypt
from flask_mysqldb import MySQL
from EvaluationHandler import UnifiedStudentPerformanceReport
import secrets
from flask import request, render_template, send_from_directory
import time
import os
from flask import session

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
# MySQL database configuration

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  # Replace with your MySQL username
app.config['MYSQL_PASSWORD'] = "123"
app.config['MYSQL_DB'] = 'countbuddy_db'  # Replace with your database name

mysql = MySQL(app)

# Route to serve the signup page
@app.route('/signup', methods=['GET'])
def signup_page():
    return render_template('signup.html')

# Route to serve the login page
@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

# Route to handle the login logic
@app.route('/login', methods=['POST'])
def login():
    # Get the user's email and password from the form
    email = request.form.get('email')
    password = request.form.get('password')

    # Check if the email exists in the database
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM students WHERE email = %s", [email])
    student = cur.fetchone()
    
    if student is None:
        flash("Email not found", "error")
        return redirect(url_for('login_page'))
    
    # Retrieve the hashed password from the database for the given email
    hashed_password_from_database = student[4]  # Password is in the 5th column (index 4)
    
    # Compare the entered password with the hashed password
    if bcrypt.checkpw(password.encode('utf-8'), hashed_password_from_database.encode('utf-8')):
        flash("Login successful", "success")
        return redirect(url_for('dashboard'))
    else:
        flash("Incorrect password", "error")
        return redirect(url_for('login_page'))

# Dashboard route (to be implemented)
@app.route('/dashboard', methods=['GET'])
def dashboard():
    return render_template('homepage.html')

# Route to handle registration logic
@app.route('/register', methods=['POST'])
def register():
    # Extract data from the form
    name = request.form.get('name')
    age = request.form.get('age')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    # Input validation
    if not name or not age or not email or not password or not confirm_password:
        flash("All fields are required", "error")
        return redirect(url_for('signup_page'))

    if password != confirm_password:
        flash("Passwords do not match", "error")
        return redirect(url_for('signup_page'))

    # Check if email already exists in the database
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM students WHERE email = %s", [email])
    student = cur.fetchone()
    if student:
        flash("Email already registered", "error")
        return redirect(url_for('signup_page'))

    # Hash the password before saving
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Insert data into the database
    cur.execute("INSERT INTO students (name, age, email, password) VALUES (%s, %s, %s, %s)", 
                (name, age, email, hashed_password))
    mysql.connection.commit()
    cur.close()

    flash("Registration successful", "success")
    return redirect(url_for('login_page'))

@app.route('/forgot-password', methods=['GET'])
def forgot_password_page():
    return render_template('login_forgot_password.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        # Get the email, new password, and confirm password from the form
        email = request.form.get('email')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Check if the email exists in the students_db
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM students WHERE email = %s", [email])
        student = cur.fetchone()
        
        if student is None:
            flash("Email not found in our records", "error")
            return redirect(url_for('forgot_password_page'))
        
        # Check if the new password and confirm password match
        if new_password != confirm_password:
            flash("Passwords do not match", "error")
            return redirect(url_for('forgot_password_page'))
        
        # Hash the new password with bcrypt
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

        # Update the password in the database (hashed version)
        cur.execute("UPDATE students SET password = %s WHERE email = %s", (hashed_password.decode('utf-8'), email))
        mysql.connection.commit()
        cur.close()

        flash("Password successfully reset", "success")
        return redirect(url_for('login_page'))

    # If it's a GET request, just render the forgot password page
    return render_template('login_forgot_password.html')



@app.route('/arithematic', methods=['GET'])
def arithematic():
    session['flashcards_completed_arithematic'] = False
    return render_template('arithematic.html')

@app.route('/finish_arithematic', methods=['GET'])
def finish_arithematic():
    session['flashcards_completed_arithematic'] = True
    print(session['flashcards_completed_arithematic'])
    return render_template('homepage.html')


@app.route('/geometric', methods=['GET'])
def geometric():
    session['flashcards_completed_geometric'] = False
    return render_template('geometric.html')

@app.route('/finish_geometric', methods=['GET'])
def finish_geometric():
    session['flashcards_completed_geometric'] = True
    print(session['flashcards_completed_geometric'])
    return render_template('homepage.html')

@app.route('/number_series', methods=['GET'])
def number_series():
    session['flashcards_completed_number_series'] = False
    return render_template('number_series.html')

@app.route('/finish_number_series', methods=['GET'])
def finish_number_series():
    session['flashcards_completed_number_series'] = True
    print(session['flashcards_completed_number_series'])
    return render_template('homepage.html')


@app.route('/test', methods=['GET'])
def testsheet():
    # Check if the keys exist in the session and are True
    if (session.get('flashcards_completed_arithematic') and 
        session.get('flashcards_completed_number_series') and 
        session.get('flashcards_completed_geometric')):
        return render_template('test.html')
    else:
        flash("Please complete all your flashcards before accessing the test.", "warning")
        return redirect(url_for('dashboard'))




@app.route('/about', methods=['GET'])
def about():
    return render_template('about.html')

@app.route('/worksheet', methods=['GET'])
def worksheet():
    return render_template('worksheets_page.html')

PATH_TO_DIRECTORY = r"E:\Anas Folder\count_buddy"

@app.route('/recieve_reponse', methods=['POST'])
def receive_response():
    # Expecting JSON data from the client, which should be a list of lists
    data = request.get_json()

    # Convert each inner list into a tuple
    converted_data = [tuple(item) for item in data]
    
    print("__________________",converted_data)
    # Create a report object
    student_report = UnifiedStudentPerformanceReport(4, "Hafsaaaa", converted_data, 'classified_student_data.csv')
    
    # Process the responses and generate the report
    student_report.process_responses()
    student_report.generate_summary_and_recommendations()
    student_report.generate_report()

    # Redirect to the show_report page to display the report
    return redirect(url_for('show_report'))

@app.route('/show_report', methods=['GET'])
def show_report():
    # Simulate a small delay (use time.sleep, not time.delay)
    time.sleep(2)

    # Assuming the report is saved as Performance_Report.pdf
    report_path = os.path.join(PATH_TO_DIRECTORY, 'Performance_Report.pdf')
    print(report_path)
    # Ensure the file exists before trying to fetch it
    if os.path.exists(report_path):
        fetchfile = 'Performance_Report.pdf'  # Pass the file name to the template
        return render_template('show_report.html', fetch=fetchfile)
    else:
        return "Error: Report file not found."

@app.route('/download/<filename>')
def download_file(filename):
    # Make sure the file exists in the reports directory
    report_path = os.path.join(PATH_TO_DIRECTORY, filename)
    if os.path.exists(report_path):
        return send_from_directory(PATH_TO_DIRECTORY, filename, as_attachment=True)
        # return redirect(url_for('templates\homepage.html'))
    else:
        return "Error: File not found."


@app.route('/')
def landing_page_view():
    return render_template('landingpage.html')


if __name__ == '__main__':
    app.run(debug=True)

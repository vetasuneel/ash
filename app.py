from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify
import os
import pandas as pd
import requests 
import uuid
import csv
from werkzeug.utils import secure_filename
from pdfminer.high_level import extract_text as extract_text_from_pdf
from docx import Document
import textract
from pyngrok import ngrok
import json
from datetime import datetime, timedelta
from dateutil import parser
import pytz
from functools import wraps
import google.generativeai as genai
from dotenv import load_dotenv
import os
import subprocess



# port_no = 5000
  
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Ensure this is set
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)

UPLOAD_FOLDER = r'F:\Python\jorg_calling_blandai\uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# API = "sub-sk-e330a89e-1af5-4695-98de-475e153c8115-8542150e-27ff-4dc0-b910-7f32151a0e39"

# Ashir 

def load_api_key():
    with open('config.json', 'r') as f:
        config = json.load(f)
    return config['API_KEY']

API = load_api_key()


if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def format_timestamp(timestamp):
    return timestamp.strftime('%m/%d/%Y, %I:%M %p')

def is_mobile_device(user_agent):
    mobile_devices = ["Mobi", "Android", "iPhone", "iPad", "iPod", "BlackBerry", "IEMobile", "Opera Mini"]
    return any(device in user_agent for device in mobile_devices)

@app.before_request
def check_device():
    user_agent = request.headers.get('User-Agent')
    if is_mobile_device(user_agent):
        return render_template('error.html'), 403


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    date_range = request.args.get('date_range')
    print(f"this is a user date input{date_range}")
    group_by = request.args.get('group_by', 'day')

    print(f"Received date range: {date_range}")  # Debugging line

    if date_range:
        try:
            start_date_str, end_date_str = date_range.split(' - ')
            start_date = datetime.strptime(start_date_str, "%m/%d/%Y")
            # Add time to make end_date inclusive of the entire day (23:59:59)
            end_date = datetime.strptime(end_date_str, "%m/%d/%Y") + timedelta(days=1) - timedelta(seconds=1)
            print(f"Parsed start date: {start_date}, end date: {end_date}")  # Debugging line
        except ValueError:
            # Handle parsing error if date range is not in expected format
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            date_range = f"{start_date.strftime('%m/%d/%Y')} - {end_date.strftime('%m/%d/%Y')}"
    else:
        # Default to last 7 days if no date range is provided
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        date_range = f"{start_date.strftime('%m/%d/%Y')} - {end_date.strftime('%m/%d/%Y')}"

    print(f"Final date range being processed: {start_date} - {end_date}")  # Debugging line

    data = get_call_data()
    metrics = process_call_data(data, start_date=start_date, end_date=end_date)
    print(f"Metrics after processing: {metrics}")  # Add debug print
    return render_template('dashboard.html', metrics=metrics, calls=metrics['filtered_calls'], date_range=date_range)


def get_call_data():
    url = "https://api.bland.ai/v1/calls"
    headers = {"authorization": API}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        print("Successfully retrieved call data.")  # Debugging line
        return response.json()
    else:
        print(f"Failed to retrieve call data. Status code: {response.status_code}")  # Debugging line
        return {"calls": []}  # Fallback empty data if API fails


def process_call_data(data, start_date=None, end_date=None):
    filtered_calls = []
    utc = pytz.UTC

    # Ensure start and end dates are in UTC
    if start_date:
        start_date = utc.localize(start_date)
    if end_date:
        end_date = utc.localize(end_date)

    # Filtering calls based on date range
    for call in data["calls"]:
        call_date = parser.isoparse(call["created_at"]).astimezone(utc)
        if (start_date is None or call_date >= start_date) and (end_date is None or call_date <= end_date):
            filtered_calls.append(call)

    # Calculating metrics
    total_calls = len(filtered_calls)
    transferred_calls = sum(1 for call in filtered_calls if call["queue_status"] == "transferred")

    # Process call durations (assuming they are already in minutes)
    valid_durations = [call["call_length"] for call in filtered_calls if call["call_length"] is not None]
    
    total_duration = sum(valid_durations)  # Sum of all valid call durations

    return {
        "total_calls": total_calls,
        "transferred_calls": transferred_calls,
        "avg_call_duration": total_duration,
        "filtered_calls": filtered_calls
    }





# Decorator to check if user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('You need to log in first.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

def load_users():
    with open('users.json', 'r') as f:
        users_data = json.load(f)
        print("Loaded users data:", users_data)  # Debugging print
        return users_data

# Function to save users to a JSON file
def save_users(users_data):
    print("Saving users data:", users_data)  # Debugging print
    with open('users.json', 'w') as f:
        json.dump(users_data, f, indent=4)


@app.route('/authenticate', methods=['POST'])
def authenticate():
    username = request.form['username']
    password = request.form['password']
    users_data = load_users()

    for user in users_data['users']:
        if user['username'] == username and user['password'] == password:
            session['username'] = username
            session.permanent = True
            return redirect(url_for('dashboard'))

    flash('Invalid username or password. Please try again.')
    return redirect(url_for('login'))


@app.route('/index')
@login_required
def index():
    if 'username' in session:
        return render_template('index.html')
    else:
        flash('Session expired. Please log in again.')
        return redirect(url_for('login'))

def save_api_key(new_api_key):
    with open('config.json', 'r') as f:
        config = json.load(f)
    config['API_KEY'] = new_api_key
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        new_username = request.form['new_username']
        new_password = request.form['new_password']
        new_api_key = request.form['new_api_key']  # Get the new API key
        users_data = load_users()

        updated = False
        for user in users_data['users']:
            if user['username'] == 'veta':  # Replace 'veta' with the actual admin username
                user['username'] = new_username
                user['password'] = new_password  # Consider hashing the password
                updated = True
                break

        if updated:
            save_users(users_data)
            flash('Username and password updated successfully.')

        if new_api_key:
            save_api_key(new_api_key)  # Save the new API key to the JSON file
            global API
            API = load_api_key()  # Reload the API key from the JSON file
            flash('API key updated successfully.')

            # Restart the server using systemctl
            try:
                subprocess.run(['sudo', 'systemctl', 'restart', 'calling'], check=True)
                flash('Server restarted successfully.')
            except subprocess.CalledProcessError as e:
                flash(f'Failed to restart the server: {e}')

        return redirect(url_for('admin'))

    return render_template('admin.html')



def extract_text_from_file(filepath):
    ext = filepath.rsplit('.', 1)[1].lower()
    if ext == 'txt':
        with open(filepath, 'r', encoding='utf-8') as file:
            return file.read()
    elif ext == 'pdf':
        return extract_text_from_pdf(filepath)
    elif ext == 'docx':
        doc = Document(filepath)
        return '\n'.join([para.text for para in doc.paragraphs])
    elif ext == 'doc':
        return textract.process(filepath).decode('utf-8')
    return ''

@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST':
        label = request.form['label']
        AGENT_PROMPT = request.form['prompt']
        first_sentence = request.form['first_sentence']
        voice = request.form['voice']
        lang = request.form['lang']
        transfer_number = request.form['number']
        selected_phones = request.form.getlist('selected_phones')
        print(f"###################################3333{selected_phones}")

        # Handling new contact addition
        new_name = request.form.get('new_contact_name')
        new_phone = request.form.get('new_contact_number')

        # Handling file upload
        file = request.files.get('file')  # Change here
        if file and file.filename != '':
            # Ensure the upload folder exists
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            # Save uploaded file
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
            file.save(filepath)
            session['uploaded_file_path'] = filepath  # Store in session

        if new_name and new_phone:
            # Add new contact to the session CSV or a new CSV if none uploaded
            filepath = session.get('uploaded_file_path') or os.path.join(app.config['UPLOAD_FOLDER'], 'new_contacts.csv')
            with open(filepath, 'a', newline='') as csvfile:
                csvwriter = csv.writer(csvfile)
                if os.path.getsize(filepath) == 0:  # If file is empty, write header
                    csvwriter.writerow(['name', 'phone_number'])
                csvwriter.writerow([new_name, new_phone])
            session['uploaded_file_path'] = filepath

        # Prepare API payload
        payload = {
            "base_prompt": AGENT_PROMPT,
            "label": label,
            "call_data": [{"phone_number": phone} for phone in selected_phones],
            "campaign_id": str(uuid.uuid4()),
            "voice": voice,
            "transfer_phone_number": transfer_number,
            "first_sentence": first_sentence,
            "voicemail_action": "hangup",
            "language": lang,
            # "pathway_id": "04eaf3f4-1113-4e53-94f9-6aa708fb2513",
            "max_duration": 300,
            "record": True,

        }

        headers = {
            "Authorization": API,
            "Content-Type": "application/json"
        }
        headers = {
            "Authorization": API,
            "Content-Type": "application/json"
        }

        # Sending the POST request to the API
        try:
            response = requests.post('https://api.bland.ai/v1/batches', json=payload, headers=headers)
            response_data = response.json()
            print(response_data)
            if response.status_code == 200:
                # Assuming the response contains a 'batch_id'
                session['batch_id'] = response_data.get('batch_id')
                flash('Campaign launched successfully!', 'success')
            else:
                flash('Failed to launch campaign. Please try again.', 'danger')
        except requests.exceptions.RequestException as e:
            flash(f'An error occurred: {e}')

        return redirect(url_for('index'))

    return render_template('index.html')

# @app.route('/home', methods=['GET', 'POST'])
# @login_required
# def home():
#     contacts = []
#     phone_column = 'PhoneNumber'  # Set to match your CSV header
#     name_column = 'Name'  # Set to match your CSV header

#     # Ensure the upload folder exists
#     if not os.path.exists(app.config['UPLOAD_FOLDER']):
#         os.makedirs(app.config['UPLOAD_FOLDER'])

#     # Load contacts from the last uploaded file on both GET and POST requests
#     if 'uploaded_file_path' in session and os.path.exists(session['uploaded_file_path']):
#         try:
#             with open(session['uploaded_file_path'], 'r') as csvfile:
#                 csvreader = csv.DictReader(csvfile)
#                 contacts = list(csvreader)  # Read all rows into the contacts list
#                 if contacts:
#                     # Check if 'PhoneNumber' and 'Name' are present in the file headers
#                     if 'PhoneNumber' not in contacts[0] or 'Name' not in contacts[0]:
#                         flash('CSV file must contain "Name" and "PhoneNumber" headers.', 'danger')
#                         contacts = []
#                 else:
#                     flash('CSV file is empty.', 'danger')
#         except Exception as e:
#             print(f"Error loading contacts for UI: {e}")
#             flash(f"Error loading contacts: {e}", 'danger')

#     if request.method == 'POST':
#         label = request.form['label']
#         AGENT_PROMPT = request.form['prompt']
#         first_sentence = request.form['first_sentence']
#         voice = request.form['voice']
#         lang = request.form['lang']
#         transfer_number = request.form['number']
#         call_limit = int(request.form.get('call_limit', 0))  # Get the number of calls to make

#         # Handling file upload
#         file = request.files.get('csvFile')
#         if file and file.filename != '':
#             try:
#                 # Delete the previous file if a new one is uploaded
#                 previous_file = session.get('uploaded_file_path')
#                 if previous_file and os.path.exists(previous_file):
#                     os.remove(previous_file)

#                 # Save the new file
#                 filename = secure_filename(file.filename)
#                 filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#                 file.save(filepath)
#                 session['uploaded_file_path'] = filepath  # Store the file path in the session

#                 # Reload contacts from the newly uploaded file
#                 with open(filepath, 'r') as csvfile:
#                     csvreader = csv.DictReader(csvfile)
#                     contacts = list(csvreader)
#                     if contacts:
#                         # Check if 'PhoneNumber' and 'Name' are present in the file headers
#                         if 'PhoneNumber' not in contacts[0] or 'Name' not in contacts[0]:
#                             flash('CSV file must contain "Name" and "PhoneNumber" headers.', 'danger')
#                             contacts = []
#                     else:
#                         flash('Uploaded CSV file is empty.', 'danger')
#                         return redirect(url_for('home'))
#             except Exception as e:
#                 print(f"Error saving or loading file: {e}")
#                 flash(f"Error saving or loading file: {e}", 'danger')
#         else:
#             flash("No new file uploaded. Using existing contacts.", 'info')

#         # Process the contacts based on call limit and update the CSV file
#         if contacts and call_limit > 0:
#             calls_to_make = contacts[:call_limit]
#             remaining_contacts = contacts[call_limit:]

#             # Prepare the payload for the API request
#             payload = {
#                 "base_prompt": AGENT_PROMPT,
#                 "label": label,
#                 "call_data": [{"phone_number": contact[phone_column]} for contact in calls_to_make],
#                 "campaign_id": str(uuid.uuid4()),
#                 "voice": voice,
#                 "transfer_phone_number": transfer_number,
#                 "first_sentence": first_sentence,
#                 "voicemail_action": "hangup",
#                 "language": lang,
#                 "max_duration": 300,
#             }

#             headers = {
#                 "Authorization": API,  # Ensure the API key is correctly set
#                 "Content-Type": "application/json"
#             }

#             # Send the API request
#             try:
#                 response = requests.post('https://api.bland.ai/v1/batches', json=payload, headers=headers)
#                 response_data = response.json()
#                 print(f"API Response: {response_data}")
#                 if response.status_code == 200:
#                     flash(f'{len(calls_to_make)} calls processed successfully.', 'success')
#                 else:
#                     flash(f'Failed to process calls: {response_data}', 'danger')
#             except requests.exceptions.RequestException as e:
#                 print(f"Error sending API request: {e}")
#                 flash(f"Error sending API request: {e}", 'danger')

#             # Update the CSV file with remaining contacts
#             try:
#                 with open(session['uploaded_file_path'], 'w', newline='') as csvfile:
#                     fieldnames = [name_column, phone_column]
#                     csvwriter = csv.DictWriter(csvfile, fieldnames=fieldnames)
#                     csvwriter.writeheader()
#                     csvwriter.writerows(remaining_contacts)
#                     flash(f'{len(calls_to_make)} calls processed. CSV file updated.', 'success')
#             except Exception as e:
#                 print(f"Error updating CSV file: {e}")
#                 flash(f"Error updating CSV file: {e}", 'danger')

#             contacts = remaining_contacts  # Update the contacts to reflect the remaining data

#         return redirect(url_for('home'))

#     return render_template('index.html', contacts=contacts)



@app.route('/stop_campaign', methods=['POST'])
def stop_campaign():
    batch_id = session.get('batch_id')
    if batch_id:
        stop_url = f"https://api.bland.ai/v1/batches/{batch_id}/stop"
        headers = {
            "Authorization": API
        }
        response = requests.post(stop_url, headers=headers)
        if response.status_code == 200:
            flash('Campaign stopped successfully.')
            return redirect(url_for('home'))
        else:
            flash('Failed to stop campaign.')
            return redirect(url_for('home'))
    else:
        flash('No campaign to stop.')
        return redirect(url_for('home'))
    

@app.route('/campaign_details', methods=['GET'])
@login_required
def campaign_details():
    url = "https://api.bland.ai/v1/batches"
    headers = {"Authorization": API}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            batches = response.json().get('batches', [])
            # Add code here to include max_duration in each batch if necessary
            return render_template('campaign_details.html', batches=batches)
        else:
            flash('Failed to retrieve campaign details.')
            return redirect(url_for('home'))
    except requests.exceptions.RequestException as e:
        flash(f'An error occurred: {e}')
        return redirect(url_for('home'))


@app.route('/batch_details/<batch_id>')
def batch_details(batch_id):
    # Example URL and headers, replace with your actual API call
    url = f"https://api.bland.ai/v1/batches/{batch_id}"
    headers = {"Authorization": API}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            batch_details = response.json()
            # Check if 'call_data' is not in batch_details or is None
            print(batch_details)
            if 'call_data' not in batch_details or batch_details['call_data'] is None:
                batch_details['call_data'] = []  # Set call_data to an empty list
            return render_template('batch_details.html', batch_details=batch_details)
        else:
            flash('Failed to retrieve batch details.')
            return redirect(url_for('home'))
    except requests.exceptions.RequestException as e:
        flash(f'An error occurred: {e}')
        return redirect(url_for('home'))
    
@app.route('/batch_details_index', methods=['GET'] )
@login_required
def batch_details_index():
    batch_id = session.get('batch_id')
    # Example URL and headers, replace with your actual API call
    url = f"https://api.bland.ai/v1/batches/{batch_id}"
    headers = {"Authorization": API}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            batch_details = response.json()
            # Check if 'call_data' is not in batch_details or is None
            if 'call_data' not in batch_details or batch_details['call_data'] is None:
                batch_details['call_data'] = []  # Set call_data to an empty list
            return render_template('batch_details.html', batch_details=batch_details)
        else:
            flash('Failed to retrieve batch details.')
            return redirect(url_for('home'))
    except requests.exceptions.RequestException as e:
        flash(f'An error occurred: {e}')
        return redirect(url_for('home'))
    


@app.route('/analyze')
@login_required
def analyze():
    ids_url = "https://api.bland.ai/v1/batches"
    headers = {
        "Authorization": API,
    }
    response = requests.get(ids_url, headers=headers)
    batches_info = []
    if response.status_code == 200:
        batches = response.json().get('batches', [])
        for batch in batches:
            batches_info.append({
                "batch_id": batch['batch_id'],
                "label": batch['label']
            })
    else:
        print("Error fetching batch IDs:", response.text)
    return render_template('analyze.html', batches_info=batches_info)

@app.route('/submit', methods=['POST'])
def submit():
    try:
        data = request.get_json()
        goal = data['goal']
        submitted_questions = data['questions']
        batch_id = data['batch_id']

        payload = {
            "goal": goal,
            "questions": [[question, "string"] for question in submitted_questions if question]
        }

        api_url = f"https://api.bland.ai/v1/batches/{batch_id}/analyze"
        headers = {
            "Authorization": API,
            "Content-Type": "application/json"
        }

        response = requests.post(api_url, json=payload, headers=headers)
        if response.status_code == 200:
            api_response = response.json()

            # Flatten all answers into a list, preserving order
            all_answers = [answer for sublist in api_response.get('answers', {}).values() for answer in sublist]
            
            # Combine questions and answers, ensuring each question is matched with its corresponding answers
            qa_pairs = [{"question": q, "answer": a} for q, a in zip(submitted_questions, all_answers)]

            return jsonify(qa_pairs)
        else:
            return jsonify({"error": "Failed to get a valid response from the API", "details": response.json()}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

########################################################## send call Section #######################################################################################
    
max_duration = 300

BASE_URL= "https://api.bland.ai/v1/calls"

headers = {
    "authorization": API
}

@app.route('/call_jump', methods=['GET'])
@login_required
def call_jump():
    return render_template('call_transfer.html')  # Your upload form template



# @app.route('/send_call', methods=['GET', 'POST'])
# def send_call():
#     if request.method == 'POST':
#         # Handling form data
#         phone_number = request.form['phone_number']
#         AGENT_PROMPT = request.form['prompt']
#         print(AGENT_PROMPT)
#         voice = request.form['voice']
#         lang = request.form['lang']
#         first_sentence = request.form['first_sentence']
#         transfer_number = request.form['number']
#         print(transfer_number)
#         # vector_id = request.form['vector_id']


#         # Prepare API payload and send request
#         headers = {
#             "Authorization": API,  # Replace with your actual API key
#             "Content-Type": "application/json"
#         }

#         payload = {
#             "task": AGENT_PROMPT,
#             "voice": voice,
#             "first_sentence": first_sentence,
#             "voicemail_action": "hangup",
#             "transfer_phone_number": transfer_number,
#             "phone_number": phone_number,
#             "language": lang,
#             "record": True,

#             # "tools": [f"{vector_id}"],
#         }

#         try:
#             response = requests.post('https://api.bland.ai/v1/calls', json=payload, headers=headers)
#             response_data = response.json()
#             print(response_data)
#             if response.status_code == 200:
#                 session['campaign_id'] = response_data.get('campaign_id')
#                 flash('Call sent successfully!', 'success')
#             else:
#                 flash('Failed to send a call. Please try again.', 'danger')
#         except requests.exceptions.RequestException as e:
#             flash(f'An error occurred: {e}', 'danger')

#         return redirect(url_for('call_jump'))

#     return render_template('call_transfer.html')



@app.route('/send_call', methods=['GET', 'POST'])
def send_call():
    if request.method == 'POST':
        # Handling form data
        phone_number = request.form['phone_number']
        AGENT_PROMPT = request.form['prompt']
        print(AGENT_PROMPT)
        voice = request.form['voice']
        lang = request.form['lang']
        first_sentence = request.form['first_sentence']
        transfer_number = request.form['number']
        print(transfer_number)
        # vector_id = request.form['vector_id']


        # Prepare API payload and send request
        headers = {
            "Authorization": API,  # Replace with your actual API key
            "Content-Type": "application/json"
        }

        payload = {
            "task": AGENT_PROMPT,
            "voice": voice,
            "first_sentence": first_sentence,
            "voicemail_action": "hangup",
            "transfer_phone_number": transfer_number,
            "phone_number": phone_number,
            "language": lang,
            "record": True,
            "tools": ["TL-c440addc-2446-4f5e-a807-a94b9a950f30"],
            "dynamic_data": [
                {
                "url": "https://calling-app-veta.vercel.app/api/appointments/veta?date=2024-09-17&user_id=1",
                "method": "GET",
                "response_data": [
                    {
                    "name": "available_slots",
                    "data": "$.slots[*].startTime",
                    "context": "The available appointment slots for 2024-09-16 are: {{available_slots}}"
                    }
                ]
                }
            ]
        }


        try:
            response = requests.post('https://api.bland.ai/v1/calls', json=payload, headers=headers)
            response_data = response.json()
            print(response_data)
            if response.status_code == 200:
                session['campaign_id'] = response_data.get('campaign_id')
                flash('Call sent successfully!', 'success')
            else:
                flash('Failed to send a call. Please try again.', 'danger')
        except requests.exceptions.RequestException as e:
            flash(f'An error occurred: {e}', 'danger')

        return redirect(url_for('call_jump'))

    return render_template('call_transfer.html')



@app.route('/transcript/<call_id>')
def transcript(call_id):
    # Fetch transcript data from the API
    transcript_url = f"{BASE_URL}/{call_id}"
    transcript_response = requests.get(transcript_url, headers=headers)
    if transcript_response.status_code == 200:
        data = transcript_response.json()
        # Pass the data to the template
        return render_template('transcript.html', call_data=data)
    else:
        # Handle errors
        return render_template('error.html', message="Error fetching transcript data.")
    
@app.route('/call_log')
@login_required
def call_log():
    # Fetch call logs from the API
    response = requests.get(BASE_URL, headers=headers)
    
    # Check if the response is successful.
    if response.status_code == 200:
        # Parse the JSON data from the API response.
        calls_data = response.json()
        
        # Here, we assume the JSON structure has a list of calls in 'calls' key.
        call_logs = calls_data.get('calls', [])
        
        # Pass the call logs to the template.
        print(call_logs)
        return render_template('call_logs.html', call_logs=call_logs)
    else:
        # In case the API call fails, you can pass an empty list or handle the error as you see fit.
        return render_template('call_logs.html', call_logs=[])

############################################### Inbound Call ################################################

@app.route('/inbound_index', methods=['GET', 'POST'])
@login_required
def inbound_index():
    return render_template('inbound.html')


@app.route('/inbound_call', methods=['GET', 'POST'])
@login_required
def inbound_call():
    if request.method == 'POST':
        # Handling form data
        AGENT_PROMPT = request.form['prompt']
        first_sentence = request.form['first_sentence']
        voice = request.form['voice']
        transfer_number = request.form['number']
        lang = request.form['lang']



        # Prepare API payload and send request
        headers = {
            "Authorization": API,  # Ensure this contains the correct key
            "Content-Type": "application/json"
        }

        payload = {
            "prompt":AGENT_PROMPT,
            "voice": voice,
            "language": lang,
            "voicemail_action": "hangup",
            "first_sentence": first_sentence,
            "transfer_phone_number": transfer_number,
            "record": True,


        }

        # Assuming phone_number is part of the form data and is a single phone number
        phone_number = "+923181393178"
        try:
            response = requests.post(f'https://api.bland.ai/v1/inbound/{phone_number}', json=payload, headers=headers)
            response_data = response.json()
            if response.status_code == 200:
                session['campaign_id'] = response_data.get('campaign_id')
                flash('Update call successfully!')
            else:
                flash('Failed to update call. Please try again.')
        except requests.exceptions.RequestException as e:
            flash(f'An error occurred: {e}')

        return redirect(url_for('inbound_index'))

    return render_template('inbound.html')  


################################################ Vector ###################################################    

@app.route('/vector_index', methods=['GET', 'POST'])
@login_required
def vector_index():
    return render_template('vector.html')

@app.route('/vector', methods=['GET', 'POST'])
@login_required
def create_vector():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                extracted_text = extract_text_from_file(filepath)
                vector_name = request.form['vector_name']
                description = request.form['description']

                payload = {
                    "name": vector_name,
                    "description": description,
                    "text": extracted_text
                }
                headers = {
                    "authorization": API,
                    "Content-Type": "application/json"
                }

                url = "https://kb.bland.ai/vectors"
                response = requests.post(url, json=payload, headers=headers)

                if response.status_code == 200:
                    flash('Vector created successfully')
                else:
                    flash(f'Failed to create vector: {response.text}')
                    print(f'API Error: {response.status_code} - {response.text}')

            except Exception as e:
                flash(f'An error occurred: {str(e)}')
                print(f'Exception: {str(e)}')

            return redirect(url_for('vector_index'))

        flash('Allowed file types are txt, pdf, doc, docx')
        return redirect(request.url)

    return render_template('vector.html')



@app.route('/vector_update', methods=['GET', 'POST'])
@login_required
def vector_update():
    return render_template('update_vector.html')

@app.route('/get_vectors', methods=['GET'])
def get_vectors():
    headers = {
        "authorization": API,
    }
    response = requests.get("https://kb.bland.ai/vectors", headers=headers)
    if response.status_code == 200:
        vectors = response.json().get('vectors', [])
        print(f'This print from get_vectors function: {vectors}')
        return jsonify(vectors)
    else:
        return jsonify([]), response.status_code




@app.route('/update_vector', methods=['GET', 'POST'])
@login_required
def update_vector():
    if request.method == 'POST':
        try:
            vector_id = request.form['vector_id']
            vector_name = request.form['vector_name']
            description = request.form['description']
            text = ''

            # Check if the post request has the file part
            if 'file' in request.files:
                file = request.files['file']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    text = extract_text_from_file(filepath)
                    print("Extracted Text:", text)

            payload = {
                "name": vector_name,
                "description": description,
                "text": text
            }
            headers = {
                "authorization": API,
                "Content-Type": "application/json"
            }

            url = f"https://kb.bland.ai/vectors/{vector_id}"
            response = requests.post(url, json=payload, headers=headers)
            print("API Response:", response.text)

            if response.status_code == 200:
                flash('Vector updated successfully')
            else:
                flash(f'Failed to update vector: {response.text}')
                print(f'API Error: {response.status_code} - {response.text}')
        except Exception as e:
            flash(f'An error occurred: {str(e)}')
            print(f'Exception: {str(e)}')

        return redirect(url_for('update_vector'))

    # Fetch vector IDs to populate the select dropdown
    try:
        headers = {
            "authorization": API,
            "Content-Type": "application/json"
        }
        response = requests.get("https://kb.bland.ai/vectors", headers=headers)
        vectors = response.json().get('vectors', []) if response.status_code == 200 else []
    except Exception as e:
        flash(f'Failed to fetch vectors: {str(e)}')
        vectors = []

    return render_template('update_vector.html', vectors=vectors)


# @app.route('/list', methods=['GET', 'POST'])
# def list():
#     return render_template('list_vector.html')


@app.route('/list_vectors', methods=['GET'])
def list_vectors():
    url = "https://kb.bland.ai/vectors"
    headers = {"authorization": API,
               "Content-Type": "application/json"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        vectors = response.json().get('vectors', [])
    except requests.exceptions.RequestException as err:
        flash(f"Error: {err}", 'danger')
        vectors = []
    
    return render_template('list_vector.html', vectors=vectors)

@app.route('/vector_details/<vector_id>', methods=['GET'])
def vector_details(vector_id):
    url = f"https://kb.bland.ai/vectors/{vector_id}"
    headers = {"authorization": API,
               "Content-Type": "application/json"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        vector_details = response.json()
    except requests.exceptions.RequestException as err:
        flash(f"Error: {err}", 'danger')
        return redirect(url_for('list_vectors'))
    
    return render_template('vector_details.html', vector=vector_details)

@app.route('/delete_vector/<vector_id>', methods=['POST'])
def delete_vector(vector_id):
    url = f"https://kb.bland.ai/vectors/{vector_id}/delete"
    headers = {"authorization": API,
               "Content-Type": "application/json"}
    
    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        flash('Vector deleted successfully', 'success')
    except requests.exceptions.RequestException as err:
        flash(f"Error: {err}", 'danger')
    
    return redirect(url_for('list_vectors'))

####################################### Prompt_saver ##################################################

PROMPTS_FILE = 'prompts.json'

def load_prompts():
    if os.path.exists(PROMPTS_FILE):
        with open(PROMPTS_FILE, 'r') as file:
            return json.load(file)
    return {}

def save_prompts(prompts):
    with open(PROMPTS_FILE, 'w') as file:
        json.dump(prompts, file, indent=4)

@app.route('/save_prompt', methods=['POST'])
def save_prompt():
    data = request.get_json()
    prompt_name = data.get('name')
    prompt_text = data.get('prompt')

    if not prompt_name or not prompt_text:
        return jsonify({'error': 'Prompt name and text are required'}), 400

    prompts = load_prompts()
    prompts[prompt_name] = prompt_text
    save_prompts(prompts)

    return jsonify({'success': 'Prompt saved successfully'}), 200

@app.route('/get_prompts', methods=['GET'])
def get_prompts():
    prompts = load_prompts()
    prompt_names = [{'name': name} for name in prompts.keys()]
    return jsonify({'prompts': prompt_names}), 200

@app.route('/get_prompt', methods=['POST'])
def get_prompt():
    data = request.get_json()
    prompt_name = data.get('name')

    prompts = load_prompts()
    prompt_text = prompts.get(prompt_name)

    if prompt_text:
        return jsonify({'prompt': prompt_text}), 200
    else:
        return jsonify({'error': 'Prompt not found'}), 404

@app.route('/delete_prompt', methods=['POST'])
def delete_prompt():
    data = request.get_json()
    prompt_name = data.get('name')

    prompts = load_prompts()

    if prompt_name in prompts:
        del prompts[prompt_name]
        save_prompts(prompts)
        return jsonify({'success': 'Prompt deleted successfully'}), 200
    else:
        return jsonify({'error': 'Prompt not found'}), 404

geminiAPI = "AIzaSyCIxsi3iAc7qUNL6JnY2NDTiCGEzdz_rVQ"
genai.configure(api_key=geminiAPI)

prompt = """You are an experienced prompt engineer specializing in creating emotionally engaging prompts for AI calling agents. Your task is to design prompts that evoke strong emotions and create a memorable experience for the caller. The prompts should be carefully crafted to ensure the AI can respond naturally and empathetically to various scenarios.

Prompt Example:

Goal: Call patients to remind them of their upcoming doctor's appointment. Confirm they can attend or reschedule if needed.

Call Flow:

Introduction: Introduce yourself and state you are calling from Dr. Smith's office.
Verification: Verify you are speaking with the correct patient (e.g., John Doe) and confirm the details of their appointment (e.g., Tuesday at 10am).
Confirmation: Ask if the scheduled time still works for them or if they need to reschedule.
Rescheduling: If they need to reschedule, offer alternative time slots (e.g., Wednesday or Friday).
Closure: Once the new time is confirmed or the original time is reconfirmed, thank them and provide contact information for further assistance.
Background:

You are an AI assistant created by Healthcare Company to make appointment reminder calls to patients. The patients you will call are adults scheduled for check-up appointments with Dr. Smith, a general practitioner. Reminding patients to attend appointments or reschedule if needed is crucial for the clinic's operations. Missed appointments cost time and money, so confirming attendance improves clinic efficiency.

Always Generate Example Dialogues:

Introduction and Verification:

You: "Hello, this is Claire calling from Dr. Smith's office. Am I speaking with John Doe?"

Person: "Yes, this is John."

Appointment Reminder:

You: "Great, I'm just calling to remind you that you have an appointment scheduled with Dr. Smith this Tuesday at 10am. Does that time still work for you?"

Person: "Actually, Tuesday doesn't work anymore. Could we do Wednesday instead?"

Rescheduling:

You: "No problem. Dr. Smith has openings on Wednesday at 9am or 3pm. Do either of those times work for you?"

Person: "3pm on Wednesday works great, thanks so much for the reminder!"

Closure:

You: "You're very welcome! We look forward to seeing you Wednesday at 3pm. Let us know if you need anything else!"

Person: "Sounds good, bye!"

You: "Have a great day, goodbye!"

By following these guidelines, you will create prompts that not only address the caller's needs but also build a strong emotional connection, ensuring a positive and memorable interaction. Always generate example dialogues to illustrate how the AI should handle these interactions."""


@app.route('/generate-prompt', methods=['POST'])
def generate_prompt():
    data = request.json
    topic = data['topic']
    print(topic)

    model = genai.GenerativeModel(
        "models/gemini-1.5-flash",
        system_instruction=prompt
    )

    response = model.generate_content(f"Please write a prompt for {topic}")
    print(response)
    return jsonify({"prompt": response.text})


URL = "https://api.bland.ai/v1/me"
@app.route('/balance')
def get_balance():
    headers = {"authorization": API}
    response = requests.get(URL, headers=headers)
    if response.status_code == 200:
        data = response.json()
        current_balance = data.get("billing", {}).get("current_balance", "Not available")
        return jsonify(current_balance=current_balance)
    else:
        return jsonify(current_balance="Failed to retrieve data")
    


@app.route('/appointments')
def appointments():
    return render_template('appointment.html')

def parse_datetime(date_str, time_str):
    # Try different datetime formats
    formats = ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M", "%d-%m-%Y %H:%M"]
    for fmt in formats:
        try:
            return datetime.strptime(f"{date_str} {time_str}", fmt)
        except ValueError:
            continue
    raise ValueError(f"Time data '{date_str} {time_str}' does not match any known formats.")

def load_events():
    response = requests.get("https://66b248ec1ca8ad33d4f7392c.mockapi.io/followup/appointments")
    
    if response.status_code != 200:
        raise Exception(f"Failed to load data: {response.status_code}")
    
    schedule = response.json()

    events = []
    for appointment in schedule:
        # Check for missing fields
        if 'name' not in appointment or 'phone_number' not in appointment or 'date' not in appointment or 'time' not in appointment:
            print(f"Skipping incomplete entry: {appointment}")
            continue

        try:
            start_time = parse_datetime(appointment['date'], appointment['time'])
        except ValueError as e:
            print(f"Skipping invalid date/time entry: {e}")
            continue

        end_time = start_time + timedelta(hours=1)
        events.append({
            "title": appointment['name'],
            "start": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "end": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "phone": appointment['phone_number'],
            "color": "green"
        })
    return events

@app.route('/events')
def events():
    try:
        events = load_events()
        return jsonify(events)
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Define the API URL
lead_api_url = "https://66df04adde4426916ee34acd.mockapi.io/webspikes_leads"

@app.route('/chat_leads')
def chat_leads():
        # Fetch data from the API
    response = requests.get(lead_api_url)
    
    # If the request was successful, process the data
    if response.status_code == 200:
        leads = response.json()
        # Convert and sort the leads by createdAt date in descending order
        for lead in leads:
            lead['createdAt'] = datetime.strptime(lead['createdAt'], '%Y-%m-%dT%H:%M:%S.%fZ')
        
        # Sort the leads by 'createdAt' in descending order
        leads = sorted(leads, key=lambda x: x['createdAt'], reverse=True)
        
        # Format the createdAt date to the desired format
        for lead in leads:
            lead['createdAt'] = lead['createdAt'].strftime('%m/%d/%Y, %I:%M %p')
    else:
        leads = []
    
    # Pass the data to the HTML template to display it in a table
    return render_template('lead.html', leads=leads)


if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(port=5000, debug=True)



# if __name__ == "__main__":
#     print(public_url)
#     app.run()
# All important imports
import base64
from dotenv import load_dotenv
import os
import secrets
from datetime import datetime

import requests
from flask import Flask, render_template, request, redirect, flash
from requests.auth import HTTPBasicAuth
import sqlalchemy
from sqlalchemy import MetaData
import pymysql


# Hiding essential information
load_dotenv()


# Beginning the web app
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(16))     #flashing  variable for the secret key



# Homepage
@app.route('/')
def home():
    return render_template("index.html")                                        

@app.route("/<string:page_name>")                                               #displaying any other page
def contact(page_name):
    return render_template(page_name)


# Secret key for flashing messages in case an error occurs
secret_key = secrets.token_hex(16)
os.environ['FLASK_SECRET_KEY'] = secret_key

# Variables for the push function
user_phone_numbers = []
amount_transacted = []
endpoint = os.getenv('END_POINT')
timestamp = datetime.now()
time_now = timestamp.strftime("%Y%m%d%H%M%S")
pass_key = os.getenv("PASS_KEY")
bs_code = os.getenv("BS_CODE")
password = bs_code + pass_key + time_now
password = base64.b64encode(password.encode("utf-8")).decode("utf-8")

# Initializing the M-Pesa express push payment in try-except block function
@app.route('/read_form', methods=['POST', 'GET'])
def read_form():
    if request.method == 'POST':
        try:
            data = request.form
            info = [
                data["valid_number"],
                data["total_amount"]
            ]
            user_phone_numbers.append(info[0])
            amount_transacted.append(info[1])

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {the_access_token}'
            }

            payload = {
                "BusinessShortCode": 174379,
                "Password": password,
                "Timestamp": time_now,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": amount_transacted[-1],
                "PartyA": user_phone_numbers[-1],
                "PartyB": 174379,
                "PhoneNumber": user_phone_numbers[-1],
                "CallBackURL": 'https://9007-102-215-78-19.ngrok-free.app' + '/call_back',
                "AccountReference": "CompanyXLTD",
                "TransactionDesc": "Payment of X"
            }

            response = requests.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()

            return redirect('/pending.html')

        except requests.exceptions.RequestException as e:
            print(f"Request Exception: {e}")
            flash(f"Request Exception: Enter Valid Figures.")
            return redirect('/index.html')

        except Exception as e:
            print(f"Unexpected Error: {e}")
            flash(f"Unexpected Error: Enter Valid Figures.")
            return redirect('/index.html')

# Collecting payment information for database/csv
@app.route('/call_back', methods=['POST'])
def call_back():
    data = request.get_json()
    mpesa_data = data['Body']['stkCallback']['CallbackMetadata']['Item']
    payment_response = data['Body']['stkCallback']["ResultDesc"]

    amount = mpesa_data[0]['Value']
    mpesa_receipt_number = mpesa_data[1]['Value']
    transaction_date = mpesa_data[3]['Value']
    phone_number = mpesa_data[4]['Value']


    # Dealing with the database variables
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')
    metadata = MetaData()

    
    # Connecting to the database
    engine = sqlalchemy.create_engine(f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}", echo=False)

    payment_data = sqlalchemy.Table('payment_data', metadata, autoload_with=engine)

    insert_data = payment_data.insert().values(
        Amount = amount,
        MpesaReceiptNumber = mpesa_receipt_number,
        TransactionDate = transaction_date,
        PhoneNumber = phone_number
    )


    # Adding data to database
    conn = engine.connect()
    try:
        conn.execute(insert_data)

        conn.commit()
        print('Success')
        print(payment_response)
    except Exception as e:
        print(f'{payment_response}: {e}')

    finally:
        conn.close()
    
    return 'OK'
    

# Authentication
consumer_key = os.getenv('CONSUMER_KEY')
consumer_secret = os.getenv('CONSUMER_SECRET')
url = os.getenv('URL')

# Authentication function
def token_access():
    try:
        response = requests.get(url, auth=HTTPBasicAuth(consumer_key, consumer_secret))
        response.raise_for_status()
        data = response.json()
        return data["access_token"]
    except requests.exceptions.RequestException as e:
        print(f"Request Exception during token access: {e}")
        raise

the_access_token = token_access()



# Running app in debug mode
if __name__ == '__main__':
    app.run(debug=True)

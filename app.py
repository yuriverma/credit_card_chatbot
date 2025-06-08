import os
import json
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, request, jsonify, render_template
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEndpoint, HuggingFaceEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo  # use pytz if < Python 3.9
import uuid


def now_ist():
    return datetime.now(ZoneInfo("Asia/Kolkata"))

load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default_secret_key")

# Configuration - Set these environment variables
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")
SALES_EMAIL = "3xtinctmc@gmail.com"  # Replace with actual email
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")  # Your Google Sheet ID
SERVICE_ACCOUNT_FILE = "credentials.json"  # Path to your service account JSON

# Global variables
qa_chain = None
session_histories = {}
google_sheets_client = None
conversation_logs = {}

class CustomerData:
    def __init__(self):
        self.customer_id = ""
        self.name = ""
        self.phone_number = ""
        self.email = ""
        self.age = ""
        self.city = ""
        self.annual_income = ""
        self.employment_type = ""
        self.company_name = ""
        self.experience_years = ""
        self.credit_score = ""
        self.existing_bob_customer = "No"
        self.current_account_type = ""
        self.existing_credit_cards = ""
        self.monthly_spending = ""
        self.preferred_card_category = ""
        self.interest_areas = ""
        self.lead_status = "New"
        self.eligible_cards = ""
        self.last_interaction_date = now_ist().strftime("%Y-%m-%d %H:%M:%S")
        self.interaction_count = 1
        self.follow_up_required = "Yes"
        self.notes = ""
        self.created_date = now_ist().strftime("%Y-%m-%d")
        self.assigned_rm = "AI_Bot"

def setup_google_sheets():
    """Setup Google Sheets integration"""
    global google_sheets_client
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            print("📝 Service account file not found - Using mock mode")
            return False
            
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scope)
        google_sheets_client = gspread.authorize(creds)
        print("✅ Google Sheets setup completed successfully!")
        return True
    except Exception as e:
        print(f"❌ Google Sheets setup failed: {e}")
        print("📝 Using mock mode - data will be logged to console")
        return False

def load_knowledge_base():
    """Load the FAQ knowledge base from your document"""
    knowledge_base = """
Q. What is a Credit Card?
A. A credit card is a financial instrument supplied by banks with a pre-set credit limit for online and offline shopping. You may be eligible for a credit card based on your credit score, history, income, and other bank guidelines. Apply for a credit card at BOB Financial site. In other words, a credit card is your convenient, anytime money that you must repay only after 50 days because there is no interest until then.

Q. How to Apply for a Credit Card?
A. In 3 simple steps:
* Complete the e-application
* Aadhaar-based e-signature
* Confirm with video KYC
You can also visit any of your nearest Bank of Baroda branches.

Q. How to use a Credit card?
A. Use your Bank of Baroda credit card for:
* Retail purchases
* Online shopping
* Cash withdrawals at ATMs
* Foreign Rs. 2500 (cross-border) transactions while travelling overseas by enabling it for contactless (Tap & Pay) transactions
Not only that, but you may convert purchases of more than Rs. 2500 on your card into cheap EMIs ranging from 6 to 36 months.

Q. How to check Credit Card Eligibility?
A. Visit our website at www.bobfinancial.com to check your eligibility and apply for your Bank of Baroda credit card.

Q. What are the benefits of a Bank of Baroda Credit Card?
A. 
* Exciting privileges across dining, travel, entertainment, and more
* Rewards on spends
* Welcome Perks
* Complimentary Service
In short, it doesn't just give you instant credit; it enables you to step up to the dream life you've always wanted and delights by adding to your savings too!

Q. What are the 4 types of credit cards?
A. Credit Cards are broadly classified as follows -
1. Retail/Consumer Credit Cards
2. FD backed/Secured Credit Cards
3. Co-branded Credit Cards
4. Commercial Credit Cards
For details on Bank of Baroda Credit Cards – visit BOB Financial site

Q. How many credit cards can I have?
A. Usually, banks offer 1 credit card to every customer, few banks also offer multiple credit cards to the same customer. For ex: Retail Card for personal use and Business or Corporate Credit Card for official expenses.

Q. Can I pay a person with a credit card?
A. Payments by credit cards are not permitted for P2P transactions. However, credit card loans are available. (Conditions apply)

Q. Can I use my credit card for international transactions?
A. Of course, yes. Please keep in mind that you must first enable your Bank of Baroda credit card for foreign transactions.
1. Log in to the Bank of Baroda Credit Card customer online OR mobile app
2. Navigate to 'Go to Menu'
3. Select the 'Card usage/management' option
4. Activate your card for international use instantly by following the screen instructions.

Q. Can I transfer money from credit card to bank account?
A. No. Certain credit card transactions are not permitted, and one of them is the transfer of funds to a bank account.

Q. What should you do in the case of theft or loss of your credit card?
A. In case of any theft, unauthorized transaction or fear of fraudulent use on your card, you can permanently block your card using any of the options -
1. SMS BLOCK XXXX to 9223172141 from your registered mobile number (XXXX is the last 4 digits of your card)
2. Log in to the Bank of Baroda Credit Card customer portal or mobile app -> Go to Menu & Select the 'Card Block' option and immediately block your card following the screen instructions.

Q. How much cash can I withdraw from my credit card?
A. Every card comes with a sub-limit for cash withdrawals, you can use your card up to that amount for cash withdrawal at the ATM using your credit card. You can confirm your cash limit by calling the customer service number printed on your credit card.

Q. When can I redeem my credit card reward points?
A. Every card has a cash withdrawal sub-limit. You can use your credit card to withdraw cash from an ATM up to that amount. Call the customer support number on the back of your credit card to confirm your cash limit.
"""
    
    # Parse the knowledge base
    qa_pairs = knowledge_base.strip().split("Q. ")
    documents = []
    
    for qa_pair in qa_pairs:
        if qa_pair.strip():
            qa_pair = "Q. " + qa_pair.strip()
            documents.append(Document(page_content=qa_pair))
    
    print(f"📚 Loaded {len(documents)} FAQ documents")
    return documents

def extract_customer_info(session_id, user_message):
    """Extract customer information from conversation using enhanced pattern matching"""
    if session_id not in conversation_logs:
        conversation_logs[session_id] = CustomerData()
    
    customer_data = conversation_logs[session_id]
    message_lower = user_message.lower()
    
    # Extract name
    name_patterns = [
        r"my name is (\w+)",
        r"i am (\w+)",
        r"i'm (\w+)",
        r"call me (\w+)",
        r"name (\w+)"
    ]
    for pattern in name_patterns:
        match = re.search(pattern, message_lower)
        if match and not customer_data.name:
            customer_data.name = match.group(1).title()
            break
    
    # Extract phone number
    phone_patterns = [
        r'\b(\d{10})\b',
        r'\b(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b',
        r'\b91(\d{10})\b'
    ]
    for pattern in phone_patterns:
        match = re.search(pattern, user_message)
        if match and not customer_data.phone_number:
            customer_data.phone_number = match.group(1)
            break
    
    # Extract email
    email_pattern = r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b'
    email_match = re.search(email_pattern, user_message)
    if email_match and not customer_data.email:
        customer_data.email = email_match.group(1)
    
    # Extract income with better patterns
    income_keywords = ['earn', 'salary', 'income', 'make', 'lakh', 'thousand']
    if any(keyword in message_lower for keyword in income_keywords):
        # Look for income ranges like "100000-200000" or "1-2 lakh"
        range_pattern = r'(\d+(?:\.\d+)?)\s*[-to]\s*(\d+(?:\.\d+)?)\s*(lakh|thousand|k|lac)?'
        range_match = re.search(range_pattern, message_lower)
        if range_match and not customer_data.annual_income:
            num1, num2, unit = range_match.groups()
            if unit in ['lakh', 'lac']:
                customer_data.annual_income = f"{int(float(num1) * 100000)}-{int(float(num2) * 100000)}"
            elif unit in ['thousand', 'k']:
                customer_data.annual_income = f"{int(float(num1) * 1000)}-{int(float(num2) * 1000)}"
            else:
                customer_data.annual_income = f"{num1}-{num2}"
        else:
            # Look for single income values
            numbers = re.findall(r'(\d+(?:\.\d+)?)\s*(lakh|thousand|k|lac)?', message_lower)
            if numbers and not customer_data.annual_income:
                num, unit = numbers[0]
                if unit in ['lakh', 'lac']:
                    customer_data.annual_income = str(int(float(num) * 100000))
                elif unit in ['thousand', 'k']:
                    customer_data.annual_income = str(int(float(num) * 1000))
                else:
                    customer_data.annual_income = num
    
    # Extract employment type
    employment_keywords = {
        'salaried': ['salaried', 'employee', 'job', 'work for'],
        'self_employed': ['business', 'self employed', 'entrepreneur', 'freelancer', 'own business'],
        'professional': ['doctor', 'lawyer', 'ca', 'consultant']
    }
    
    for emp_type, keywords in employment_keywords.items():
        if any(keyword in message_lower for keyword in keywords) and not customer_data.employment_type:
            customer_data.employment_type = emp_type
            break
    
    # Extract city
    city_pattern = r'from (\w+)|in (\w+)|live in (\w+)|based in (\w+)'
    city_match = re.search(city_pattern, message_lower)
    if city_match and not customer_data.city:
        for group in city_match.groups():
            if group:
                customer_data.city = group.title()
                break
    
    # Update interaction data
    customer_data.last_interaction_date = now_ist().strftime("%Y-%m-%d %H:%M:%S")
    customer_data.interaction_count += 1
    customer_data.notes += f"Turn {customer_data.interaction_count}: {user_message[:100]}... "
    conversation_logs[session_id] = customer_data
    return customer_data

def generate_personalized_pitch_with_flan(customer_data):
    """Generate personalized credit card pitch using rule-based logic"""
    try:
        # Use rule-based approach as HuggingFace models are having issues
        return generate_rule_based_pitch(customer_data)
        
    except Exception as e:
        print(f"Error generating pitch: {e}")
        return generate_rule_based_pitch(customer_data)

def generate_rule_based_pitch(customer_data):
    """Enhanced rule-based pitch generation with better logic"""
    name = customer_data.name or "there"
    income = customer_data.annual_income
    employment = customer_data.employment_type
    
    # Parse income for better recommendations
    income_val = 0
    if income:
        # Handle range inputs like "100000-200000"
        if '-' in income:
            income_parts = income.split('-')
            try:
                income_val = int(income_parts[1])  # Use upper range
            except:
                income_val = 0
        else:
            try:
                income_val = int(income)
            except:
                income_val = 0
    
    # Generate personalized pitch based on income and employment
    if income_val >= 1000000:  # 10 lakh+
        return f"Hi {name}! 🌟 With your excellent income profile of ₹{income_val:,}, you're eligible for our **BOB Premier Credit Card** - our flagship offering with:\n• Unlimited airport lounge access worldwide\n• 5% cashback on all premium purchases\n• Complimentary concierge services\n• Zero forex markup on international transactions\n• Welcome bonus worth ₹10,000!"
    elif income_val >= 500000:  # 5 lakh+
        card_type = "BOB Gold Credit Card" if employment == "salaried" else "BOB Business Credit Card"
        return f"Hello {name}! 💳 Based on your income of ₹{income_val:,}, our **{card_type}** is perfect for you:\n• 4X reward points on dining & entertainment\n• Airport lounge access (4 visits/year)\n• Fuel surcharge waiver\n• Easy EMI conversion\n• Welcome gift vouchers worth ₹5,000!"
    elif income_val >= 300000:  # 3 lakh+
        return f"Hi {name}! ✨ Our **BOB Select Credit Card** matches your profile perfectly:\n• 2X rewards on shopping and groceries\n• Movie ticket discounts\n• Dining offers at partner restaurants\n• Emergency cash advance facility\n• Welcome bonus of ₹2,000!"
    elif income_val >= 150000:  # 1.5 lakh+
        return f"Hello {name}! 🎯 Consider our **BOB Classic Credit Card**:\n• 1% cashback on all purchases\n• Online shopping protection\n• Easy monthly payment options\n• 24/7 customer support\n• No annual fee for first year!"
    else:
        return f"Hi {name}! 🏦 Our **BOB Secured Credit Card** is perfect to build your credit journey:\n• Build credit history effectively\n• All regular credit card benefits\n• Secured against your FD\n• Upgrade options available\n• Start your premium banking relationship with us!"

def update_google_sheets(customer_data):
    """Update customer data in Google Sheets with proper sheet names"""
    try:
        if not google_sheets_client:
            print("📝 Mock Google Sheets Update:")
            print(f"Customer: {customer_data.name}")
            print(f"Phone: {customer_data.phone_number}")
            print(f"Email: {customer_data.email}")
            print(f"Income: {customer_data.annual_income}")
            print(f"Employment: {customer_data.employment_type}")
            return True
        
        # Open the spreadsheet
        sheet = google_sheets_client.open_by_key(GOOGLE_SHEETS_ID)
        
        # Update Customer Data (First sheet - Customer_Data)
        try:
            customer_sheet = sheet.worksheet("Customer_Data")
        except gspread.WorksheetNotFound:
            print("❌ Customer_Data sheet not found. Available sheets:")
            for worksheet in sheet.worksheets():
                print(f"  - {worksheet.title}")
            return False
        
        # Generate unique customer ID if not exists
        if not customer_data.customer_id:
            customer_data.customer_id = f"CUST_{uuid.uuid4().hex[:8].upper()}"
        # Prepare row data according to your sheet structure
        row_data = [
            customer_data.customer_id,
            customer_data.name or "",
            customer_data.phone_number or "",
            customer_data.email or "",
            customer_data.age or "",
            customer_data.city or "",
            customer_data.annual_income or "",
            customer_data.employment_type or "",
            customer_data.company_name or "",
            customer_data.experience_years or "",
            customer_data.credit_score or "",
            customer_data.existing_bob_customer,
            customer_data.current_account_type or "",
            customer_data.existing_credit_cards or "",
            customer_data.monthly_spending or "",
            customer_data.preferred_card_category or "",
            customer_data.interest_areas or "",
            customer_data.lead_status,
            customer_data.eligible_cards or "",
            customer_data.last_interaction_date,
            customer_data.interaction_count,
            customer_data.follow_up_required,
            customer_data.notes or "",
            customer_data.created_date,
            customer_data.assigned_rm
        ]
        
        customer_sheet.append_row(row_data)
        
        # Also log interaction in Interaction_Log sheet
        try:
            interaction_sheet = sheet.worksheet("Interaction_Log")
            interaction_data = [
                customer_data.customer_id,
                now_ist().strftime("%Y-%m-%d %H:%M:%S"),
                "Chat Interaction",
                customer_data.notes[-100:] if customer_data.notes else "",  # Last 100 chars
                "AI Bot",
                customer_data.lead_status
            ]
            interaction_sheet.append_row(interaction_data)
        except gspread.WorksheetNotFound:
            print("⚠️ Interaction_Log sheet not found, skipping interaction log")
        
        print("✅ Google Sheets updated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update Google Sheets: {e}")
        return False

def send_email_summary(customer_data, conversation_summary):
    """Send email summary to sales team"""
    try:
        if not GMAIL_USER or not GMAIL_PASS:
            print("📧 Mock Email Summary:")
            print(f"To: {SALES_EMAIL}")
            print(f"Subject: New Credit Card Lead: {customer_data.name or 'Unknown'}")
            print(f"Customer: {customer_data.name}, Phone: {customer_data.phone_number}")
            return True
        
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = SALES_EMAIL
        msg['Subject'] = f"🎯 New Credit Card Lead: {customer_data.name or 'Potential Customer'}"
        
        body = f"""
        <h2>New Credit Card Inquiry - Bank of Baroda</h2>
        
        <h3>Customer Details:</h3>
        <ul>
            <li><strong>Name:</strong> {customer_data.name or 'Not provided'}</li>
            <li><strong>Phone:</strong> {customer_data.phone_number or 'Not provided'}</li>
            <li><strong>Email:</strong> {customer_data.email or 'Not provided'}</li>
            <li><strong>City:</strong> {customer_data.city or 'Not provided'}</li>
            <li><strong>Annual Income:</strong> ₹{customer_data.annual_income or 'Not provided'}</li>
            <li><strong>Employment Type:</strong> {customer_data.employment_type or 'Not provided'}</li>
            <li><strong>Lead Status:</strong> {customer_data.lead_status}</li>
            <li><strong>Interaction Count:</strong> {customer_data.interaction_count}</li>
            <li><strong>Last Interaction:</strong> {customer_data.last_interaction_date}</li>
        </ul>
        
        <h3>Conversation Summary:</h3>
        <p>{conversation_summary}</p>
        
        <h3>Notes:</h3>
        <p>{customer_data.notes}</p>
        
        <p><strong>Action Required:</strong> Please follow up with this lead within 24 hours.</p>
        
        <hr>
        <p><em>Generated by BoB Credit Card AI Assistant</em></p>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASS)
        text = msg.as_string()
        server.sendmail(GMAIL_USER, SALES_EMAIL, text)
        server.quit()
        
        print("✅ Email summary sent to sales team")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

def initialize_chatbot():
    """Initialize the chatbot with all components"""
    global qa_chain
    
    try:
        # Load knowledge base
        docs = load_knowledge_base()
        
        # Use rule-based responses instead of LLM for now due to HuggingFace issues
        print("⚠️ Using rule-based responses due to model availability issues")
        qa_chain = None
        
        # Setup integrations
        setup_google_sheets()
        
        print("✅ Chatbot components initialized!")
        return True
        
    except Exception as e:
        print(f"❌ Chatbot initialization failed: {e}")
        return False

def get_simple_response(user_message):
    """Enhanced rule-based response system"""
    message_lower = user_message.lower()
    
    # FAQ responses with better matching
    if any(word in message_lower for word in ['apply', 'application', 'how to get']):
        return "To apply for a Bank of Baroda credit card, follow these simple steps:\n\n1️⃣ **Complete the e-application** online at www.bobfinancial.com\n2️⃣ **Aadhaar-based e-signature** for quick verification\n3️⃣ **Confirm with video KYC** from comfort of your home\n\nAlternatively, you can visit any of our nearest Bank of Baroda branches. Would you like me to help check your eligibility?"
    
    elif any(word in message_lower for word in ['benefits', 'advantage', 'perks', 'features']):
        return "🌟 **Bank of Baroda Credit Card Benefits:**\n\n✅ Exciting privileges across dining, travel & entertainment\n✅ Reward points on all spends\n✅ Welcome bonuses & perks\n✅ Complimentary services\n✅ Easy EMI conversion options\n✅ 24/7 customer support\n\nOur cards don't just give you instant credit - they enable you to step up to your dream lifestyle while adding to your savings! What type of benefits interest you most?"
    
    elif any(word in message_lower for word in ['eligibility', 'eligible', 'qualify']):
        return "💳 **Credit Card Eligibility depends on:**\n\n• Credit score & history\n• Monthly/Annual income\n• Employment stability\n• Age (21-65 years)\n• Bank relationship\n\n**Quick Check:** Share your monthly income range and I can suggest the best card for you! You can also visit www.bobfinancial.com for detailed eligibility checker."
    
    elif any(word in message_lower for word in ['types', 'kind', 'categories', 'options']):
        return "🏦 **Bank of Baroda offers 4 main types of credit cards:**\n\n1️⃣ **Retail/Consumer Credit Cards** - For everyday purchases\n2️⃣ **FD-backed/Secured Credit Cards** - Perfect for building credit\n3️⃣ **Co-branded Credit Cards** - Special partnerships with brands\n4️⃣ **Commercial Credit Cards** - For business expenses\n\nEach category has multiple variants based on income and lifestyle. Which type interests you?"
    
    elif any(word in message_lower for word in ['international', 'abroad', 'foreign', 'overseas']):
        return "🌍 **Yes! Use your BoB Credit Card internationally:**\n\n**How to enable:**\n1️⃣ Login to BoB Credit Card app/portal\n2️⃣ Go to Menu → 'Card usage/management'\n3️⃣ Activate international usage instantly\n\n**Benefits abroad:**\n• Accepted worldwide at millions of merchants\n• Contactless payments\n• Emergency assistance\n• Competitive forex rates\n\nPlanning to travel? I can suggest the best international-friendly card!"
    
    elif any(word in message_lower for word in ['cash', 'withdraw', 'atm']):
        return "💰 **Cash Withdrawal from Credit Card:**\n\n• Every BoB credit card has a cash withdrawal sub-limit\n• Use at any ATM with your credit card PIN\n• Check your specific limit by calling customer service\n• Interest charges apply from day 1 on cash advances\n\n📞 Customer service number is printed on your credit card back. Need help with anything else?"
    
    elif any(word in message_lower for word in ['lost', 'theft', 'stolen', 'block']):
        return "🚨 **Immediate Card Blocking Options:**\n\n**Method 1 - SMS:**\nSend: BLOCK XXXX to 9223172141\n(XXXX = last 4 digits of your card)\n\n**Method 2 - App/Portal:**\n1️⃣ Login to BoB Credit Card app\n2️⃣ Go to Menu → 'Card Block'\n3️⃣ Follow instructions to block immediately\n\n⚡ Block your card immediately to prevent misuse. New card will be issued within 3-5 working days."
    
    elif any(word in message_lower for word in ['reward', 'points', 'redeem']):
        return "🎁 **Credit Card Rewards & Redemption:**\n\n• Earn reward points on every purchase\n• Redeem for gift vouchers, cash credits, or products\n• Higher earning rates on specific categories\n• Bonus points on milestone spends\n• Points validity typically 2-3 years\n\nCheck your reward balance in the mobile app or call customer service. Want to know about specific card reward rates?"
    
    elif any(word in message_lower for word in ['fee', 'charges', 'annual', 'cost']):
        return "💳 **Credit Card Fees & Charges:**\n\n**Annual Fee:** Varies by card type (₹500 - ₹5000+)\n**Joining Fee:** Often waived in first year\n**Interest Rate:** 3.5% per month on outstanding balance\n**Late Payment:** ₹100 - ₹1000 based on outstanding\n**Cash Advance:** 2.5% of amount withdrawn\n\n💰 Many fees waived based on annual spends! Which specific card are you interested in?"
    
    else:
        return "👋 Hello! I'm your Bank of Baroda Credit Card Assistant. I can help you with:\n\n🔹 **Card Applications** & Eligibility\n🔹 **Benefits** & Features comparison\n🔹 **International** usage activation\n🔹 **Rewards** & Redemption info\n🔹 **Card blocking** & Security\n🔹 **Personalized** card recommendations\n\nWhat specific information would you like to know about our credit cards?"

# Flask Routes
@app.route('/')
def home():
    """Render the main chat interface"""
    print("🧠 Rendering index.html")
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages with enhanced error handling"""
    try:
        data = request.json
        if not data or 'message' not in data:
            return jsonify({
                "success": False,
                "error": "Invalid request format"
            })
        
        user_message = data['message'].strip()
        session_id = data.get("session_id", "default_session")
        
        if not user_message:
            return jsonify({
                "success": False,
                "error": "Empty message"
            })
        
        print(f"🔤 Received message: {user_message}")
        
        # Extract customer information
        customer_data = extract_customer_info(session_id, user_message)
        
        # Generate bot response using rule-based system
        bot_response = get_simple_response(user_message)
        
        # Generate personalized pitch if we have customer data
        personalized_pitch = None
        if any([customer_data.name, customer_data.annual_income, customer_data.employment_type]):
            personalized_pitch = generate_personalized_pitch_with_flan(customer_data)
        
        # Update integrations (sheets and email) after sufficient interaction
        sheets_updated = False
        email_sent = False
        
        if customer_data.interaction_count >= 2 and (customer_data.name or customer_data.phone_number or customer_data.email):
            sheets_updated = update_google_sheets(customer_data)
            if customer_data.name and (customer_data.phone_number or customer_data.email):
                email_sent = send_email_summary(customer_data, f"Customer inquiry about: {user_message}")
        
        # Prepare customer info for response
        customer_info = {}
        if customer_data.name:
            customer_info['name'] = customer_data.name
        if customer_data.phone_number:
            customer_info['phone'] = customer_data.phone_number
        if customer_data.email:
            customer_info['email'] = customer_data.email
        if customer_data.annual_income:
            customer_info['income'] = customer_data
        if customer_data.annual_income:
            customer_info['income'] = customer_data.annual_income
        
        response_data = {
            "success": True,
            "response": bot_response,
            "customer_info": customer_info,
            "sheets_updated": sheets_updated,
            "email_sent": email_sent
        }
        
        if personalized_pitch:
            response_data["personalized_pitch"] = personalized_pitch
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Chat error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Something went wrong. Please try again.",
            "response": "I apologize, but I'm experiencing technical difficulties. Please try again in a moment."
        })

@app.route('/customer_data/<session_id>')
def get_customer_data(session_id):
    """Get customer data for a session"""
    try:
        if session_id in conversation_logs:
            customer_data = conversation_logs[session_id]
            return jsonify({
                "success": True,
                "customer_data": {
                    "name": customer_data.name,
                    "phone": customer_data.phone_number,
                    "email": customer_data.email,
                    "city": customer_data.city,
                    "income": customer_data.annual_income,
                    "employment": customer_data.employment_type,
                    "interaction_count": customer_data.interaction_count,
                    "last_interaction": customer_data.last_interaction_date
                }
            })
        else:
            return jsonify({
                "success": False,
                "message": "No customer data found for this session"
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": now_ist().isoformat(),
        "components": {
            "google_sheets": google_sheets_client is not None,
            "email_configured": bool(GMAIL_USER and GMAIL_PASS)
        }
    })

if __name__ == '__main__':
    print("🚀 Starting Bank of Baroda Credit Card Chatbot...")
    
    port = int(os.environ.get("PORT", 8000))  # Get port from env or default to 8000

    # Initialize chatbot components
    if initialize_chatbot():
        print("✅ All systems ready!")
        app.run(debug=True, host='0.0.0.0', port=port)
    else:
        print("❌ Failed to initialize chatbot. Please check configuration.")
        print("🔧 Running in basic mode...")
        app.run(debug=True, host='0.0.0.0', port=port)

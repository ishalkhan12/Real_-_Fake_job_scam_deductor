from flask import Flask, render_template, request, session, redirect, flash, send_file, url_for, jsonify
from database.mongodb import users, reports
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import requests
from bs4 import BeautifulSoup
import random
import string
from flask_mail import Mail, Message
import PyPDF2
import urllib.parse
import re

app = Flask(__name__)
app.secret_key = "jobshield_secret_key_123"

# ==========================================
# SMTP EMAIL CONFIGURATION (GMAIL SMTP)
# ==========================================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'khanishal204@gmail.com'
app.config['MAIL_PASSWORD'] = 'fban sfrm jksz ywco'    
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

mail = Mail(app)

# ==========================================
# HUGGING FACE API CONFIGURATION
# ==========================================
HF_MODEL_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
HF_TOKEN = "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"

def query_huggingface_model(text, candidate_labels):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": text,
        "parameters": {"candidate_labels": candidate_labels}
    }
    try:
        response = requests.post(HF_MODEL_URL, headers=headers, json=payload, timeout=10)
        output = response.json()
        if "error" in output:
            print("HF API Error:", output["error"])
            return candidate_labels[0], 50.0
        top_label = output["labels"][0]
        confidence = output["scores"][0] * 100
        return top_label, confidence
    except Exception as e:
        print("Hugging Face Connection Exception:", e)
        return candidate_labels[0], 50.0

def generate_verification_token():
    return ''.join(random.choices(string.digits, k=6))

def get_website_content(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=7)
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string.strip() if soup.title else "Unknown Platform"
        paragraphs = soup.find_all(['p', 'div', 'section'])
        page_text = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20])
        return title, page_text[:1000]
    except Exception as e:
        print("Scraper Warning:", e)
        return "Unverifiable Website Gateway", ""

# ==========================================
# ENHANCED SKILLS DICTIONARY (150+ SKILLS)
# ==========================================
SKILLS_DICTIONARY = [
    # --- Software & Web Development ---
    "python", "javascript", "react", "node.js", "django", "flask", "html", "css", "mongodb",
    "sql", "mysql", "postgresql", "java", "c++", "c#", "php", "laravel", "git", "aws", "docker",
    "web development", "software engineering", "mobile app development", "flutter", "react native",
    "kotlin", "swift", "ruby on rails", "angular", "vue.js", "typescript", "tailwind css",
    "bootstrap", "jquery", "firebase", "azure", "gcp", "kubernetes", "jenkins", "linux", "bash",
    "devops", "ci/cd", "cloud computing", "microservices", "api development", "restful apis",
    "graphql", "redis", "elasticsearch", "nginx", "apache", "serverless", "terraform",

    # --- Marketing & Creative ---
    "digital marketing", "seo", "search engine optimization", "sem", "social media marketing",
    "content marketing", "email marketing", "copywriting", "graphic design", "brand management",
    "market research", "google analytics", "advertising", "public relations", "sales",
    "digital advertising", "paid media", "influencer marketing", "video editing", "animation",
    "ux design", "ui design", "figma", "photoshop", "illustrator", "indesign", "premiere pro",
    "after effects", "motion graphics", "visual design", "creative direction", "art direction",

    # --- Management, HR & Business ---
    "project management", "product management", "business development", "sales strategy",
    "human resources", "hr recruiting", "customer support", "customer relationship management",
    "financial analysis", "accounting", "operations", "strategic planning", "supply chain",
    "logistics", "procurement", "business analysis", "data analysis", "business intelligence",
    "power bi", "tableau", "excel", "vba", "erp", "sap", "oracle", "people management",
    "team leadership", "agile", "scrum", "kanban", "jira", "confluence", "risk management",

    # --- Engineering & Sciences ---
    "mechanical engineering", "civil engineering", "electrical engineering", "chemical engineering",
    "biotechnology", "pharmaceutical", "clinical research", "laboratory", "research & development",
    "quality assurance", "qc", "production", "manufacturing", "lean manufacturing", "six sigma",
    "autocad", "solidworks", "revit", "mep", "hvac", "plumbing", "fire safety", "structural engineering",

    # --- Education & Teaching ---
    "teaching", "lecturer", "professor", "education", "curriculum design", "educational leadership",
    "english language", "training", "facilitation", "classroom management", "lesson planning",

    # --- Healthcare & Medical ---
    "nursing", "medicine", "surgery", "dentistry", "pharmacist", "psychology", "therapy",
    "physiotherapy", "occupational therapy", "speech therapy", "radiology", "medical coding",
    "healthcare management", "public health", "epidemiology", "clinical trials", "pharmacovigilance"
]

def extract_skills_from_text(text):
    text_lower = text.lower()
    found_skills = set()
    for skill in SKILLS_DICTIONARY:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.add(skill)
    return list(found_skills)

# ==========================================
# HOME & CV SCANNER ROUTE
# ==========================================
@app.route("/", methods=["GET", "POST"])
def home():
    skills = None
    linkedin_url = None

    if request.method == "POST":
        # Check if CV file form submitted
        if 'cv_file' in request.files:
            file = request.files['cv_file']
            if file and file.filename != '' and file.filename.endswith('.pdf'):
                try:
                    pdf_reader = PyPDF2.PdfReader(file)
                    cv_text = ""
                    for page in pdf_reader.pages:
                        cv_text += page.extract_text() or ""
                    
                    matched_skills = extract_skills_from_text(cv_text)
                    
                    if not matched_skills:
                        domain_labels = [
                            "Digital Marketing", "Sales Representative", "Human Resources", 
                            "Software Developer", "Graphic Designer", "Project Manager",
                            "Data Analyst", "Financial Analyst", "Teacher", "Nurse",
                            "Mechanical Engineer", "Civil Engineer", "Electrical Engineer"
                        ]
                        predicted_domain, _ = query_huggingface_model(cv_text[:1500], domain_labels)
                        matched_skills = [predicted_domain.lower()]
                    
                    detected_skills = [skill.upper() for skill in matched_skills[:5]]
                    keywords_query = " ".join(detected_skills)
                    encoded_query = urllib.parse.quote(keywords_query)
                    linkedin_url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_query}"
                    
                    session['cv_result'] = {
                        'skills': detected_skills,
                        'linkedin_url': linkedin_url
                    }
                    
                except Exception as e:
                    print("CV Scanning Exception:", e)
                    flash("CV scanning mein error aya. Dobara try karein.")
            else:
                flash("Baraye meherbani valid PDF format ki CV upload karein.")
            
            return redirect("/")

    # GET request handler
    cv_result = session.pop('cv_result', None)
    if cv_result:
        skills = cv_result['skills']
        linkedin_url = cv_result['linkedin_url']

    return render_template("index.html", skills=skills, linkedin_link=linkedin_url)

# ==========================================
# CHECK / DETECT SCAM ROUTE
# ==========================================
@app.route("/check", methods=["GET", "POST"])
def check():
    if request.method == "GET":
        return redirect("/dashboard")

    title = request.form.get("title", "")
    description = request.form.get("description", "")
    salary_input = request.form.get("salary", "").strip()
    try:
        salary = int(salary_input) if salary_input else 0
    except ValueError:
        salary = 0
        
    website = request.form.get("website", "").strip()
    
    if "linkedin.com" in website.lower() or "indeed.com" in website.lower():
        website_title = "Trusted Professional Network"
        website_score = 0
        page_content = "This is an official posting on a verified job platform."
    else:
        website_title, page_content = get_website_content(website)
        website_score = 0
        suspicious_domains = [".xyz", ".top", ".click", ".loan", ".live", ".work"]
        for domain in suspicious_domains:
            if domain in website.lower():
                website_score += 30

    text = title + " " + description + " " + page_content
    prediction, confidence = query_huggingface_model(text[:1000], ["scam", "suspicious", "legitimate"])

    suspicious_keywords = [
        "registration fee", "payment required", "earn instantly", 
        "quick money", "guaranteed income", "investment required", 
        "pay first", "joining fee", "security deposit"
    ]
    
    red_flags = []
    for keyword in suspicious_keywords:
        if keyword in text.lower():
            red_flags.append(f"Detected Vector Phrase: {keyword.title()}")

    if salary > 500000:
        red_flags.append("Unusually High Salary Metric Warning")

    score = sum(25 for keyword in suspicious_keywords if keyword in text.lower())
    if salary > 500000:
        score += 25

    risk_score = min(score + website_score, 100)

    if "linkedin.com" in website.lower() or "indeed.com" in website.lower():
        if len(red_flags) == 0:
            result = "✅ Legitimate Job"
            risk_score = 5
        else:
            result = "⚠ Suspicious Job"
    else:
        if prediction == "scam" or len(red_flags) >= 2 or risk_score >= 40:
            result = "❌ High Scam Risk"
        elif prediction == "suspicious" or len(red_flags) == 1 or risk_score >= 15:
            result = "⚠ Suspicious Job"
        else:
            result = "✅ Legitimate Job"

    if "user" in session:
        reports.insert_one({
            "user": session["user"],
            "email": session["email"],
            "job_title": title,
            "website": website,
            "website_title": website_title,
            "salary": salary,
            "result": result,
            "risk_score": risk_score,
            "red_flags": red_flags,
            "confidence": round(confidence, 2)
        })

    return render_template("result.html", result=result, confidence=round(confidence, 2), 
                           risk_score=risk_score, website=website, website_title=website_title, 
                           red_flags=red_flags)

# ==========================================
# USER & AUTHENTICATION ROUTES
# ==========================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"]
        user = users.find_one({"email": email})
        if user and check_password_hash(user["password"], password):
            if not user.get("is_verified", False):
                session["temp_email"] = email
                flash("Verification Required: Please enter the code sent to your email matrix.")
                return redirect("/verify-email")
            session["user"] = user["name"]
            session["email"] = user["email"]
            return redirect("/dashboard")
        flash("Authorization Failed: Invalid credentials.")
        return redirect("/login")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        existing_user = users.find_one({"email": email})
        if existing_user:
            flash("Identity Collision: This account email is already registered.")
            return redirect("/register")
        hashed_password = generate_password_hash(password)
        verification_token = generate_verification_token()
        
        users.insert_one({
            "name": name,
            "email": email,
            "password": hashed_password,
            "is_verified": False,
            "verification_token": verification_token
        })
        
        print(f"\n🔒 [SECURITY ALERT] OTP FOR USER: {email} -> CODE: {verification_token}\n")
        
        try:
            msg = Message("JobShield Security Activation OTP", recipients=[email])
            msg.body = f"Hello {name},\n\nYour JobShield verification token is: {verification_token}"
            mail.send(msg)
        except Exception as e:
            print("Note: Email delivery skipped/fallback mode active.")
            
        session["temp_email"] = email
        return redirect("/verify-email")
        
    return render_template("register.html")

@app.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    if "temp_email" not in session:
        return redirect("/login")
    if request.method == "POST":
        token_input = request.form["token"].strip()
        email = session["temp_email"]
        user = users.find_one({"email": email})
        if user and user.get("verification_token") == token_input:
            users.update_one({"email": email}, {"$set": {"is_verified": True}, "$unset": {"verification_token": ""}})
            session["user"] = user["name"]
            session["email"] = user["email"]
            session.pop("temp_email", None)
            return redirect("/dashboard")
        flash("Validation Fault: Token mismatch.")
    return render_template("verify.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    total_reports = reports.count_documents({"email": session["email"]})
    scam_reports = reports.count_documents({"email": session["email"], "result": "❌ High Scam Risk"})
    suspicious_reports = reports.count_documents({"email": session["email"], "result": "⚠ Suspicious Job"})
    legit_reports = reports.count_documents({"email": session["email"], "result": "✅ Legitimate Job"})
    recent_reports = reports.find({"email": session["email"]}).sort("_id", -1).limit(5)
    return render_template("dashboard.html", name=session["user"], total_reports=total_reports, scam_reports=scam_reports, suspicious_reports=suspicious_reports, legit_reports=legit_reports, recent_reports=recent_reports)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/history")
def history():
    if "user" not in session:
        return redirect("/login")
    all_reports = reports.find({"email": session["email"]}).sort("_id", -1)
    return render_template("history.html", reports_data=all_reports)

@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect("/login")
    user = users.find_one({"email": session["email"]})
    return render_template("profile.html", user=user)

@app.route("/admin")
def admin():
    if "user" not in session:
        return redirect("/login")
    total_users = users.count_documents({})
    total_reports = reports.count_documents({})
    all_users = users.find().sort("_id", -1)
    return render_template("admin.html", total_users=total_users, total_reports=total_reports, all_users=all_users)

@app.route("/delete-user/<email>")
def delete_user(email):
    if "user" not in session:
        return redirect("/login")
    users.delete_one({"email": email})
    return redirect("/admin")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/features")
def features():
    return render_template("features.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        sender_name = request.form.get("name", "Anonymous User").strip()
        sender_email = request.form.get("email", "No Email").strip()
        user_message = request.form.get("message", "").strip()
        
        try:
            msg = Message(
                subject=f"JobShield Contact: {sender_name}",
                recipients=[app.config['MAIL_USERNAME']]
            )
            msg.body = f"From: {sender_name} ({sender_email})\n\nMessage:\n{user_message}"
            mail.send(msg)
            flash("Thank you! Message delivered successfully.")
        except Exception as e:
            flash("Message logged locally in console.")
            
        return redirect("/contact")
        
    return render_template("contact.html")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"].strip()
        user = users.find_one({"email": email})
        if user:
            token = generate_verification_token()
            users.update_one({"email": email}, {"$set": {"reset_token": token}})
            flash("Reset token generated: " + token)
        else:
            flash("No account associated with this email.")
        return redirect("/forgot-password")
    return render_template("forgot_password.html")

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    token = request.args.get("token") or request.form.get("token")
    if request.method == "POST":
        password = request.form["password"]
        confirm = request.form["confirm_password"]
        if password != confirm:
            flash("Passwords do not match.")
            return redirect("/reset-password?token=" + token)
        user = users.find_one({"reset_token": token})
        if user:
            hashed = generate_password_hash(password)
            users.update_one({"reset_token": token}, {"$set": {"password": hashed}, "$unset": {"reset_token": ""}})
            flash("Password updated successfully! Please login.")
            return redirect("/login")
        else:
            flash("Invalid or expired reset token.")
            return redirect("/forgot-password")
    return render_template("reset_password.html", token=token)

@app.route("/report/<report_id>")
def report_detail(report_id):
    from bson.objectid import ObjectId
    report = reports.find_one({"_id": ObjectId(report_id)})
    if not report or report["email"] != session.get("email"):
        flash("Access denied.")
        return redirect("/history")
    return render_template("report_detail.html", report=report)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if "user" not in session:
        return redirect("/login")
    user = users.find_one({"email": session["email"]})
    if request.method == "POST":
        name = request.form["name"].strip()
        new_password = request.form.get("new_password")
        update_data = {"name": name}
        if new_password:
            update_data["password"] = generate_password_hash(new_password)
        users.update_one({"email": session["email"]}, {"$set": update_data})
        session["user"] = name
        flash("Settings updated successfully.")
        return redirect("/settings")
    return render_template("settings.html", user=user)

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/export-pdf")
def export_pdf():
    if "user" not in session:
        return redirect("/login")
    reports_data = reports.find({"email": session["email"]})
    pdf_file = "jobshield_report.pdf"
    doc = SimpleDocTemplate(pdf_file)
    styles = getSampleStyleSheet()
    content = [Paragraph("JobShield Analysis Report", styles["Title"]), Spacer(1, 20)]
    for report in reports_data:
        text = f"Job Title: {report['job_title']}<br/>Salary: {report['salary']}<br/>Result: {report['result']}<br/><br/>"
        content.append(Paragraph(text, styles["Normal"]))
        content.append(Spacer(1, 10))
    doc.build(content)
    return send_file(pdf_file, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
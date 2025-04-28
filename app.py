from flask import Flask, render_template, request, redirect, session, flash
from supabase_client import supabase
import datetime
from collections import defaultdict

app = Flask(__name__)
app.secret_key = "flask_key1"

@app.route("/")
def login():
    return render_template("login.html")

@app.route("/auth", methods=["POST"])
def auth():
    role = request.form["role"]

    if role == "Teacher":
        email = request.form["email"]
        password = request.form["password"]
        try:
            user = supabase.auth.sign_in_with_password({"email": email, "password": password})
            db_role = supabase.table("teachers").select("role").eq("email", email).execute().data
            session["user"] = user.user.email
            session["role"] = db_role[0].get('role')
            if session.get("role") == "Teacher":
                return redirect("/dashboard")
            else:
                return redirect("/hod_dashboard")
        except Exception as e:
            flash("Login failed. Check credentials.")
            return redirect("/")
    elif role == "Student":
        roll_no = request.form["roll_no"]
        if roll_no:
            student = supabase.table("students").select("*").eq("roll_no", roll_no).execute().data
            if student:
                session["student_roll"] = roll_no
                session["role"] = "Student"
                return redirect("/student_dashboard")
            else:
                flash("Invalid Roll Number")
                return redirect("/")
        else:
            flash("Roll Number not provided")
            return redirect("/")
    else:
        flash("Invalid role selected")
        return redirect("/")
    
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role =request.form["role"]

        try:
            result = supabase.auth.sign_up({"email": email, "password": password})

            supabase.table("teachers").insert({
                "name": name,
                "email": email,
                "role": role
            }).execute()

            flash("Signup successful! You can now log in.", "success")
            return redirect("/")
        except Exception as e:
            flash("Signup failed: " + str(e), "danger")
            return redirect("/signup")

    return render_template("register.html")


@app.route("/student_dashboard")
def student_dashboard():
    if session.get("role") != "Student":
        return redirect("/")

    roll_no = session["student_roll"]
    attendance = supabase.table("attendance").select("*").eq("roll_no", roll_no).execute().data
    name = supabase.table("students").select("name").eq("roll_no", roll_no).execute().data

    subject_summary = {}
    for record in attendance:
        subject = record.get("subject", "Unknown")
        status = record["status"]

        if subject not in subject_summary:
            subject_summary[subject] = {"Present": 0, "Absent": 0, "College Work": 0, "Total": 0}

        subject_summary[subject][status] += 1
        subject_summary[subject]["Total"] += 1

    return render_template("student_dashboard.html", roll_no=roll_no, summary=subject_summary, name=name[0]['name'])

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if session.get("role") != "Teacher":
        return redirect("/")

    class_subject_map = {
        "SE": [
            "Software Engineering", "Data Structures and algorithm", "Microprocessor", 
            "Mathematics 3", "Principles of programming languages", 
            "Project based learning", "Code of conductivity"
        ],
        "TE": [
            "Data Science and Big Data Analytics", "Web Technology", 
            "Artificial Intelligence", "Software Modeling and Architecture", 
            "Statistics and Machine Learning"
        ],
        "BE": [
            "High Performance Computing", "Deep Learning", "Natural Language Processing", 
            "Business Intelligence", "Artificial Intelligence for Big Data Analytics"
        ]
    }

    selected_class = request.form.get("class_name")
    selected_subject = request.form.get("subject")
    selected_type = request.form.get("type")

    students = []
    if selected_class:
        students = supabase.table("students").select("*").eq("class", selected_class).execute().data

    return render_template("dashboard.html",
                           students=students,
                           selected_class=selected_class,
                           selected_subject=selected_subject,
                           selected_type=selected_type,
                           class_subject_map=class_subject_map)

@app.route("/hod_dashboard", methods=["GET", "POST"])
def hod_dashboard():
    if session.get("role") != "HOD":
        return redirect("/")
    class_subject_map = {
        "SE": [
            "Software Engineering", "Data Structures and algorithm", "Microprocessor", 
            "Mathematics 3", "Principles of programming languages", 
            "Project based learning", "Code of conductivity"
        ],
        "TE": [
            "Data Science and Big Data Analytics", "Web Technology", 
            "Artificial Intelligence", "Software Modeling and Architecture", 
            "Statistics and Machine Learning"
        ],
        "BE": [
            "High Performance Computing", "Deep Learning", "Natural Language Processing", 
            "Business Intelligence", "Artificial Intelligence for Big Data Analytics"
        ]
    }

    selected_class = request.form.get("class_name")
    selected_subject = request.form.get("subject")
    
    students = []
    if selected_class:
        students = supabase.table("students").select("*").eq("class", selected_class).execute().data

    return render_template("hod_dashboard.html",
                           students=students,
                           selected_class=selected_class,
                           selected_subject=selected_subject,
                           class_subject_map=class_subject_map)

@app.route("/mark_attendance", methods=["POST"])
def mark_attendance():
    selected_class = request.form.get("class_name")
    selected_subject = request.form.get("subject")
    selected_type = request.form.get("type")
    all_ids = request.form.getlist("all_ids")
    date = request.form.get("attendance_date")
    time = request.form.get("attendance_time")

    if date == '' and time == '':
        date_time = str(datetime.datetime.now())
    else:
        date_time = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M").strftime("%Y-%m-%d %H:%M:%S.%f")

    is_already_marked = supabase.table("attendance").select("*") \
        .eq("date", date_time) \
        .eq("class", selected_class).eq("subject", selected_subject).eq("type", selected_type).execute().data
    
    if not is_already_marked:
        for student_id in all_ids:
            status = request.form.get(f"status_{student_id}")
            student_data = supabase.table("students").select("roll_no").eq("id", int(student_id)).execute().data
            roll_no = student_data[0]["roll_no"] if student_data else "N/A"

            try:
                supabase.table("attendance").insert({
                    "student_id": int(student_id),
                    "roll_no": roll_no,
                    "status": status,
                    "subject": selected_subject,
                    "type": selected_type,
                    "class": selected_class,
                    "date": date_time,
                    "marked_by": session["user"]
                }).execute()
            except Exception as e:
                flash(f"Error for student ID {student_id}: {str(e)}")

        flash("Attendance marked successfully.", "success")
    else:
        flash("Attendance is already marked.", "danger")
    return redirect("/dashboard")


@app.route("/today_attendance", methods=["POST"])
def today_attendance():
    if session.get("role") != "Teacher":
        return redirect("/")
    
    selected_class = request.form.get("class_name")

    today = datetime.date.today()
    today_start = today.strftime("%Y-%m-%d 00:00:00")
    today_end = today.strftime("%Y-%m-%d 23:59:59")

    attendance_data = supabase.table("attendance").select("*") \
        .gte("date", today_start).lte("date", today_end) \
        .eq("marked_by", session["user"]).eq("class", selected_class).execute().data

    students = supabase.table("students").select("roll_no", "name").execute().data
    student_map = {str(s["roll_no"]): s["name"] for s in students}

    return render_template("today_attendance.html", attendance=attendance_data, student_map=student_map)

@app.route("/summary", methods=["POST"])
def summary():
    if session.get("role") != "Teacher":
        return redirect("/")

    selected_class = request.form.get("class_name")
    selected_subject = request.form.get("subject")

    attendance_data = supabase.table("attendance").select("*") \
        .eq("class", selected_class).eq("subject", selected_subject).execute().data

    summary = defaultdict(lambda: defaultdict(lambda: {"Present": 0, "Absent": 0, "College Work": 0}))

    for record in attendance_data:
        roll = record["roll_no"]
        try:
            date_obj = datetime.datetime.fromisoformat(record["date"])
        except:
            date_obj = datetime.datetime.strptime(record["date"], "%Y-%m-%d %H:%M:%S.%f")

        month = date_obj.strftime("%B %Y")
        status = record["status"]
        summary[roll][month][status] += 1

    students = supabase.table("students").select("roll_no", "name").eq("class", selected_class).execute().data
    student_map = {str(s["roll_no"]): s["name"] for s in students}

    return render_template("summary.html", summary=summary, student_map=student_map, subject=selected_subject)

@app.route("/defaulters", methods=["POST"])
def defaulters():
    if session.get("role") != "Teacher":
        return redirect("/")

    selected_class = request.form.get("class_name")
    selected_subject = request.form.get("subject")
    selected_type = request.form.get("type")  # Optional, included for future use

    # Get all students in the selected class
    all_students = supabase.table("students").select("*").eq("class", selected_class).execute().data

    # Initialize attendance summary
    attendance_summary = {
        student["roll_no"]: {
            "name": student["name"],
            "total": 0,
            "present": 0,
        }
        for student in all_students
    }
    
    # Fetch attendance records
    attendance_data = supabase.table("attendance").select("*") \
        .eq("class", selected_class).eq("subject", selected_subject).execute().data

    # Calculate totals and present counts
    for record in attendance_data:
        roll = int(record.get("roll_no"))
        status = record.get("status", "").strip()
        
        if roll in attendance_summary:
            attendance_summary[roll]["total"] += 1
            # print(attendance_summary[roll]["total"])
            if status == "Present":
                attendance_summary[roll]["present"] += 1

    # Build defaulter list (attendance < 75%)
    defaulter_list = []
    for roll, data in attendance_summary.items():
        total = data["total"]
        present = data["present"]
        percentage = (present / total * 100) if total > 0 else 0

        if percentage < 75:
            defaulter_list.append({
                "roll_no": roll,
                "name": data["name"],
                "total": total,
                "present": present,
                "percentage": round(percentage, 2)
            })

    # Sort by lowest percentage
    defaulter_list.sort(key=lambda x: x["percentage"])

    return render_template(
        "defaulters.html",
        defaulters=defaulter_list,
        subject=selected_subject,
        selected_class=selected_class,
        selected_subject=selected_subject,
        selected_type=selected_type
    )

@app.route("/hod_summary", methods=["POST"])
def hod_summary():
    if session.get("role") != "HOD":
        return redirect("/")

    selected_class = request.form.get("class_name")

    attendance_data = supabase.table("attendance").select("*") \
        .eq("class", selected_class).execute().data

    summary = defaultdict(lambda: defaultdict(lambda: {"Present": 0, "Absent": 0, "College Work": 0}))

    for record in attendance_data:
        roll = record["roll_no"]
        try:
            date_obj = datetime.datetime.fromisoformat(record["date"])
        except:
            date_obj = datetime.datetime.strptime(record["date"], "%Y-%m-%d %H:%M:%S.%f")

        month = date_obj.strftime("%B %Y")
        status = record["status"]
        summary[roll][month][status] += 1

    students = supabase.table("students").select("roll_no", "name").eq("class", selected_class).execute().data
    student_map = {str(s["roll_no"]): s["name"] for s in students}

    return render_template("summary.html", summary=summary, student_map=student_map)

@app.route("/hod_defaulters", methods=["POST"])
def hod_defaulters():
    if session.get("role") != "HOD":
        return redirect("/")

    selected_class = request.form.get("class_name")

    # Get all students in the selected class
    all_students = supabase.table("students").select("*").eq("class", selected_class).execute().data

    # Initialize attendance summary
    attendance_summary = {
        student["roll_no"]: {
            "name": student["name"],
            "total": 0,
            "present": 0,
        }
        for student in all_students
    }
    
    # Fetch attendance records
    attendance_data = supabase.table("attendance").select("*") \
        .eq("class", selected_class).execute().data

    # Calculate totals and present counts
    for record in attendance_data:
        roll = int(record.get("roll_no"))
        status = record.get("status", "").strip()
        
        if roll in attendance_summary:
            attendance_summary[roll]["total"] += 1
            # print(attendance_summary[roll]["total"])
            if status == "Present":
                attendance_summary[roll]["present"] += 1

    # Build defaulter list (attendance < 75%)
    defaulter_list = []
    for roll, data in attendance_summary.items():
        total = data["total"]
        present = data["present"]
        percentage = (present / total * 100) if total > 0 else 0

        if percentage < 75:
            defaulter_list.append({
                "roll_no": roll,
                "name": data["name"],
                "total": total,
                "present": present,
                "percentage": round(percentage, 2)
            })

    # Sort by lowest percentage
    defaulter_list.sort(key=lambda x: x["percentage"])

    return render_template(
        "defaulters.html",
        defaulters=defaulter_list,
        selected_class=selected_class
    )


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("👋 Logged out successfully.")
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)

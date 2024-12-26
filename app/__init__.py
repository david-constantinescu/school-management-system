from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)

    # Database models
    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(120), unique=True, nullable=False)
        password = db.Column(db.String(200), nullable=False)
        role = db.Column(db.String(50), nullable=False)
        name = db.Column(db.String(100), nullable=False)
        subject = db.Column(db.String(100), nullable=True)  # For teachers
        class_name = db.Column(db.String(100), nullable=True)  # For students
        child_email = db.Column(db.String(120), nullable=True)  # For parents
    
    class Homework(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        class_name = db.Column(db.String(100), nullable=False)
        teacher_name = db.Column(db.String(100), nullable=False)
        subject = db.Column(db.String(100), nullable=False)
        title = db.Column(db.String(200), nullable=False)
        description = db.Column(db.Text, nullable=True)
        link = db.Column(db.String(500), nullable=True)
        due_date = db.Column(db.Date, nullable=False)
        
    class ClassTeacher(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        class_name = db.Column(db.String(100), nullable=False)
        teacher_name = db.Column(db.String(100), nullable=False)
        subject = db.Column(db.String(100), nullable=False)

    class Class(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), unique=True, nullable=False)
        teacher = db.Column(db.String(100), nullable=False)

    class Lesson(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
        lesson_name = db.Column(db.String(100), nullable=False)
        video_url = db.Column(db.String(200), nullable=False)

    class ClassTeacherStudent(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        class_name = db.Column(db.String(100), nullable=False)
        teacher_name = db.Column(db.String(100), nullable=False)
        student_email = db.Column(db.String(120), db.ForeignKey('user.email'), nullable=False)
        subject = db.Column(db.String(100), nullable=False)
        
        #Relationship to User
        student = db.relationship('User', backref='class_teacher_students')

    class StudentGrade(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        class_teacher_student_id = db.Column(db.Integer, db.ForeignKey('class_teacher_student.id'), nullable=False)
        grade = db.Column(db.Float, nullable=False)
        date = db.Column(db.Date, nullable=False)
        subject = db.Column(db.String(100), nullable=False)

    class StudentAbsence(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        class_teacher_student_id = db.Column(db.Integer, db.ForeignKey('class_teacher_student.id'), nullable=False)
        date = db.Column(db.Date, nullable=False)
        is_motivated = db.Column(db.Boolean, default=False)
        reason = db.Column(db.String(200), nullable=True)
        class_teacher_student = db.relationship('ClassTeacherStudent', backref='absences')

    
    class Notification(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        student_email = db.Column(db.String(120), nullable=False)
        student_name = db.Column(db.String(100), nullable=False)  # New field for student name
        message = db.Column(db.String(200), nullable=False)
        date = db.Column(db.DateTime, default=datetime.utcnow)
    
    class Message(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        sender_email = db.Column(db.String(120), nullable=False)
        receiver_email = db.Column(db.String(120), nullable=False)
        content = db.Column(db.Text, nullable=False)
        timestamp = db.Column(db.DateTime, default=datetime.now)
    
    class Grade(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        class_teacher_student_id = db.Column(db.Integer, db.ForeignKey('class_teacher_student.id'), nullable=False)
        value = db.Column(db.Float, nullable=False)  # The actual grade value
        date = db.Column(db.Date, nullable=False)
        subject = db.Column(db.String(100), nullable=False)
        
        #Relationship to ClassTeacherStudent
        class_teacher_student = db.relationship('ClassTeacherStudent', backref='grades')
    # Create the database tables
    with app.app_context():
        db.create_all()
    
    def add_notification(student_email, student_name, message):
        notification = Notification(student_email=student_email, student_name=student_name, message=message)
        db.session.add(notification)
        db.session.commit()

    @app.route('/', methods=['GET', 'POST'])
    def index():
        return render_template('index.html')
    
    @app.route('/dashboard', methods=['GET', 'POST'])
    def dashboard():
        if 'email' not in session:
            return redirect(url_for('index'))

        # Initialize student_subjects to avoid UnboundLocalError
        student_subjects = []

        if session['role'] == 'student':
            # Get current date
            current_date = date.today()

            # Find student's class
            student_class = session['class_name']

            # Get homeworks for the student's class
            homeworks = Homework.query.filter(
                Homework.class_name == student_class,
                Homework.due_date >= current_date  # Only get homework due today or in the future
            ).all()

            # Get unique subjects for the student's class
            class_teacher_students = ClassTeacherStudent.query.filter_by(
                student_email=session['email']
            ).all()

            for cts in class_teacher_students:
                # Get grades for the selected subject
                grades = StudentGrade.query.filter_by(
                    class_teacher_student_id=cts.id
                ).order_by(StudentGrade.date.desc()).all()  # Fetch grades in reverse chronological order

                absences = StudentAbsence.query.filter_by(
                    class_teacher_student_id=cts.id
                ).all()

                subject_info = {
                    'subject': cts.subject,  # This is the subject taught by the teacher
                    'grades': grades,  # Include grades for this subject
                    'absences': absences
                }
                student_subjects.append(subject_info)

            return render_template('dashboard_student.html', 
                                student_subjects=student_subjects,
                                homeworks=homeworks)

        elif session['role'] == 'teacher':
            classes = []
            class_teachers = ClassTeacher.query.filter_by(teacher_name=session['name']).all()
        
            for class_teacher in class_teachers:
                # Find lessons for this class
                class_lessons = Lesson.query.filter_by(class_id=class_teacher.id).all()
            
                # Create a class object with name and lessons
                class_obj = {
                    'name': class_teacher.class_name,
                    'lessons': class_lessons
                }
                classes.append(class_obj)
        
            return render_template('dashboard_teacher.html', classes=classes)

        elif session['role'] == 'parent':
            # Get the child's email from the session
            child_email = session['child_email']

            # Find the child user
            child = User.query.filter_by(email=child_email).first()
            if not child:
                return "Child not found.", 404

            # Get unique subjects for the child's class
            student_subjects = []  # Initialize for parent role
            class_teacher_students = ClassTeacherStudent.query.filter_by(
                student_email=child_email
            ).all()

            for cts in class_teacher_students:
                subject_info = {
                    'subject': cts.subject,  # This is the subject taught by the teacher
                    'student_email': child_email #Store student email for linking
                }
                student_subjects.append(subject_info)

            return render_template('dashboard_parent.html', 
                                student_subjects=student_subjects)
        
        elif session['role'] == 'form_teacher':
            # Logic for form teacher role
            form_teacher = User.query.filter_by(email=session['email']).first()
            class_name = form_teacher.class_name

            # Get all students in the form teacher's class
            students = User.query.filter_by(class_name=class_name, role='student').all()

            return render_template('form_teacher_dashboard.html', students=students)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            name = request.form['name']
            role = request.form['role']
            child_email = request.form.get('child_email', '')
            subject = request.form.get('subject', '')
            class_name = request.form.get('class_name', '')

            existing_user = User.query.filter_by(email=email).first()

            if existing_user:
                # Allow registration if one is a teacher and the other is a form teacher
                if (existing_user.role == 'teacher' and role == 'form_teacher') or (existing_user.role == 'form_teacher' and role == 'teacher'):
                    pass  # Allow registration; form teacher can also be a regular teacher
                else:
                    return "User  with this email already exists.", 400
                
            # Create a new user with the provided information
            new_user = User(
                email=email, 
                password=password, 
                role=role, 
                name=name, 
                subject=subject, 
                class_name=class_name,
                child_email=child_email  # Store child's email for parents
            )
            db.session.add(new_user)
            db.session.commit()

            # If the user is a student, create a ClassTeacherStudent entry for each teacher of the class
            if role == 'student' and class_name:
                # Find all teachers for this class
                class_teachers = ClassTeacher.query.filter_by(class_name=class_name).all()
                
                for class_teacher in class_teachers:
                    new_class_teacher_student = ClassTeacherStudent(
                        class_name=class_name,
                        teacher_name=class_teacher.teacher_name,
                        student_email=email,
                        subject=class_teacher.subject
                    )
                    db.session.add(new_class_teacher_student)
                
                db.session.commit()

            return redirect(url_for('index'))

        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET':
            # Simply render the login page for GET requests
            return render_template('login.html')
        
        # POST request handling remains the same
        try:
            email = request.form['email']
            password = request.form['password']
            
            # Check for admin credentials
            if email == 'admin' and password == 'catalog-scolar':
                session['email'] = email
                session['role'] = 'admin'
                session['name'] = 'Administrator'
                return redirect(url_for('admin_dashboard'))

            # Check for other users in the database
            user = User.query.filter_by(email=email).first()
            
            if user and user.password == password:
                session['email'] = email
                session['role'] = user.role
                session['name'] = user.name
                
                # Role-based redirects
                if user.role == 'student':
                    session['class_name'] = user.class_name
                    return redirect(url_for('dashboard'))
                
                elif user.role == 'teacher':
                    return redirect(url_for('dashboard'))
                
                elif user.role == 'form_teacher':
                    return redirect(url_for('dashboard_form_teacher'))
                
                elif user.role == 'parent':
                    session['child_email'] = user.child_email
                    return redirect(url_for('dashboard'))
            
            # In case of invalid credentials
            flash('Invalid email or password.')
            return redirect(url_for('login'))
        
        except KeyError:
            # Handle cases where form data is missing
            flash('Please fill in all login fields.')
            return redirect(url_for('login'))
        
    @app.route('/admin-dashboard')
    def admin_dashboard():
        if 'email' not in session or session['role'] != 'admin':
            return redirect(url_for('index'))

        # Fetch all teachers from the database
        teachers = User.query.filter_by(role='teacher').all()
        students = User.query.filter_by(role='student').all()
        parents = User.query.filter_by(role='parent').all()
        form_teachers = User.query.filter_by(role='form_teacher').all()

        return render_template('admin_dashboard.html', 
                            teachers=teachers, 
                            students=students, 
                            parents=parents, 
                            form_teachers=form_teachers)

    # New routes for resetting passwords
    @app.route('/reset-student-password/<student_email>', methods=['GET', 'POST'])
    def reset_student_password(student_email):
        if 'email' not in session or session['role'] != 'admin':
            return redirect(url_for('index'))

        student = User.query.filter_by(email=student_email).first()
        if request.method == 'POST':
            new_password = request.form['new_password']
            if student:
                student.password = new_password
                db.session.commit()
                flash('Student password updated successfully!')
                return redirect(url_for('admin_dashboard'))

        return render_template('reset_student_password.html', student=student)

    @app.route('/reset-parent-password/<parent_email>', methods=['GET', 'POST'])
    def reset_parent_password(parent_email):
        if 'email' not in session or session['role'] != 'admin':
            return redirect(url_for('index'))

        parent = User.query.filter_by(email=parent_email).first()
        if request.method == 'POST':
            new_password = request.form['new_password']
            if parent:
                parent.password = new_password
                db.session.commit()
                flash('Parent password updated successfully!')
                return redirect(url_for('admin_dashboard'))

        return render_template('reset_parent_password.html', parent=parent)

    @app.route('/reset-form-teacher-password/<form_teacher_email>', methods=['GET', 'POST'])
    def reset_form_teacher_password(form_teacher_email):
        if 'email' not in session or session['role'] != 'admin':
            return redirect(url_for('index'))

        form_teacher = User.query.filter_by(email=form_teacher_email).first()
        if request.method == 'POST':
            new_password = request.form['new_password']
            if form_teacher:
                form_teacher.password = new_password
                db.session.commit()
                flash('Form Teacher password updated successfully!')
                return redirect(url_for('admin_dashboard'))

        return render_template('reset_form_teacher_password.html', form_teacher=form_teacher)
    
    @app.route('/add-student-to-class', methods=[' POST'])
    def add_student_to_class():
        student_email = request.form['student_email']
        class_name = request.form['class_name']
        teacher_name = session['name']
        subject = request.form['subject']

        # Create a new ClassTeacherStudent entry
        new_entry = ClassTeacherStudent(
            class_name=class_name,
            teacher_name=teacher_name,
            student_email=student_email,
            subject=subject
        )
        db.session.add(new_entry)
        db.session.commit()

        return redirect(url_for('manage_class', class_name=class_name))
    

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('index'))

    @app.route('/add-class', methods=['POST'])
    def add_class():
        class_name = request.form['class_name']
    
        # Find the current user to get their subject
        user = User.query.filter_by(email=session['email']).first()
        subject = user.subject if user and user.subject else 'Unknown'

        # Check if the class-teacher combination already exists
        existing_class_teacher = ClassTeacher.query.filter_by(
            class_name=class_name, 
            teacher_name=session['name']
        ).first()

        if not existing_class_teacher:
            # Create a new class-teacher relationship
            new_class_teacher = ClassTeacher(
                class_name=class_name, 
                teacher_name=session['name'],
                subject=subject
            )
            db.session.add(new_class_teacher)
            db.session.commit()

        return redirect(url_for('dashboard'))

    @app.route('/add-lesson', methods=['POST'])
    def add_lesson():
        class_name = request.form['class_name']
        lesson_name = request.form['lesson_name']
        video_url = request.form['video_url']

        # Find the ClassTeacher entry for this class and teacher
        class_teacher = ClassTeacher.query.filter_by(
            class_name=class_name, 
            teacher_name=session['name']
        ).first()

        if class_teacher:
            # Create a new lesson associated with this class
            new_lesson = Lesson(
                class_id=class_teacher.id, 
                lesson_name=lesson_name, 
                video_url=video_url
            )
            db.session.add(new_lesson)
            db.session.commit()

        return redirect(url_for('dashboard'))
    
    @app.route('/view-class-lessons/<class_name>')
    def view_class_lessons(class_name):
        if 'email' not in session or session['role'] != 'teacher':
            return redirect(url_for('index'))

        # Find the ClassTeacher entry for this class and teacher
        class_teacher = ClassTeacher.query.filter_by(
        class_name=class_name, 
        teacher_name=session['name']
        ).first()

        # Get lessons for this specific class
        lessons = []
        if class_teacher:
            lessons = Lesson.query.filter_by(class_id=class_teacher.id).all()

        return render_template('class_lessons.html', class_name=class_name, lessons=lessons)
    
    @app.route('/subject/<subject>/teacher/<teacher>')
    def view_subject_lessons(subject, teacher):
        # Find all ClassTeacher entries for this subject and teacher
        class_teachers = ClassTeacher.query.filter_by(
            subject=subject, 
            teacher_name=teacher
        ).all()
    
        lessons = []
        for class_teacher in class_teachers:
            # Get lessons for each class
            class_lessons = Lesson.query.filter_by(class_id=class_teacher.id).all()
            lessons.extend(class_lessons)
    
        return render_template('subject_lessons.html', 
                            subject=subject, 
                            teacher=teacher, 
                            lessons=lessons)

    @app.route('/class/<class_name>')
    def view_class(class_name):
        # Get all teachers for this class
        class_teachers = ClassTeacher.query.filter_by(class_name=class_name).all()
    
        lessons = []
        for class_teacher in class_teachers:
            class_lessons = Lesson.query.filter_by(class_id=class_teacher.id).all()
            lessons.extend(class_lessons)
    
        return render_template('class_view.html', class_name=class_name, class_data={'lessons': lessons})
   
    
    @app.route('/student-management/<class_name>/<student_email>')
    def student_management(class_name, student_email):
        if 'email' not in session or session['role'] != 'teacher':
            return redirect(url_for('index'))

        # Find the specific class-teacher-student relationship
        class_teacher_student = ClassTeacherStudent.query.filter_by(
            class_name=class_name,
            teacher_name=session['name'],
            student_email=student_email
        ).first()

        if not class_teacher_student:
            return "Student not found in this class", 404

        # Get student's grades
        grades = StudentGrade.query.filter_by(
            class_teacher_student_id=class_teacher_student.id
        ).order_by(StudentGrade.date).all()

        # Get student's absences
        absences = StudentAbsence.query.filter_by(
            class_teacher_student_id=class_teacher_student.id
        ).order_by(StudentAbsence.date).all()

        # Prepare grade data for graph
        grades_data = {
            'dates': [str(grade.date) for grade in grades],
            'values': [grade.grade for grade in grades]
        }

        # Get student name
        student = User.query.filter_by(email=student_email).first()

        return render_template('student_management.html', 
                            student_name=student.name,
                            student_email=student_email,
                            class_name=class_name,
                            grades=grades,
                            absences=absences,
                            grades_data=grades_data,
                            current_date=datetime.now().strftime('%Y-%m-%d'))
        
    @app.route('/send_message', methods=['POST'])
    def send_message():
        teacher_email = request.form['teacher_email']
        message_content = request.form['message']
        parent_email = session['email']  # Get the parent's email from the session

        # Create a new message object
        new_message = Message(
            sender_email=parent_email,
            receiver_email=teacher_email,
            content=message_content,
            timestamp=datetime.now()
        )

        # Save the message to the database
        db.session.add(new_message)
        db.session.commit()

        return redirect(url_for('dashboard'))
    
    @app.route('/add-grade', methods=['POST'])
    def add_grade():
        student_email = request.form['student_email']
        class_name = request.form['class_name']
        grade = float(request.form['grade'])
        date = request.form['date']

        # Find the specific class-teacher relationship
        class_teacher = ClassTeacher.query.filter_by(
            class_name=class_name,
            teacher_name=session['name']
        ).first()

        if not class_teacher:
            return "Invalid class or teacher", 400

        subject = class_teacher.subject  # Get the subject from the class teacher

        # Find the specific class-teacher-student relationship
        class_teacher_student = ClassTeacherStudent.query.filter_by(
            class_name=class_name,
            teacher_name=session['name'],
            student_email=student_email
        ).first()

        if not class_teacher_student:
            return "Invalid student or class", 400

        # Create new grade
        new_grade = StudentGrade(
            class_teacher_student_id=class_teacher_student.id,
            grade=grade,
            date=datetime.strptime(date, '%Y-%m-%d').date(),
            subject=subject  # Use the subject from the class teacher
        )
        db.session.add(new_grade)
        db.session.commit()
        
        student = User.query.filter_by(email=student_email).first()  # Get student details
        add_notification(student_email, student.name, "You have received a new grade!")

        return redirect(url_for('student_management', 
                                class_name=class_name, 
                                student_email=student_email))
        
    @app.route('/add-absence', methods=['POST'])
    def add_absence():
        student_email = request.form['student_email']
        class_name = request.form['class_name']
        date = request.form['date']
        reason = request.form.get('reason', '')
        is_motivated = 'is_motivated' in request.form

        # Find the specific class-teacher-student relationship
        class_teacher_student = ClassTeacherStudent.query.filter_by(
            class_name=class_name,
            teacher_name=session['name'],
            student_email=student_email
        ).first()

        if not class_teacher_student:
            return "Invalid student or class", 400

        # Create new absence with is_motivated set to False
        new_absence = StudentAbsence(
            class_teacher_student_id=class_teacher_student.id,
            date=datetime.strptime(date, '%Y-%m-%d').date(),
            reason=reason,
            is_motivated=False  # Set to unmotivated by default
            # No subject field included
        )
        
        db.session.add(new_absence)
        db.session.commit()
        
        student = User.query.filter_by(email=student_email).first()  # Get student details
        add_notification(student_email, student.name, "You have a new absence recorded.")

        return redirect(url_for('student_management', 
                                class_name=class_name, 
                                student_email=student_email))
    
    @app.route('/remove-grade', methods=['POST'])
    def remove_grade():
        grade_id = request.form['grade_id']
        grade = StudentGrade.query.get(grade_id)
        
        if grade:
            db.session.delete(grade)
            db.session.commit()

        return redirect(url_for('student_management', 
                                class_name=grade.class_teacher_student.class_name, 
                                student_email=grade.class_teacher_student.student_email))
        
    @app.route('/motivate-absence', methods=['POST'])
    def motivate_absence():
        absence_id = request.form['absence_id']
        absence = StudentAbsence.query.get(absence_id)
        
        if absence:
            absence.is_motivated = True  # Set the absence as motivated
            db.session.commit()

            # Access the class_teacher_student to get class_name and student_email
            class_teacher_student = absence.class_teacher_student
            return redirect(url_for('student_management', 
                                    class_name=class_teacher_student.class_name, 
                                    student_email=class_teacher_student.student_email))
        
        return "Absence not found", 404

    @app.route('/remove-absence', methods=['POST'])
    def remove_absence():
        absence_id = request.form['absence_id']
        absence = StudentAbsence.query.get(absence_id)
        
        if absence:
            db.session.delete(absence)
            db.session.commit()

        return redirect(url_for('student_management', 
                                class_name=absence.class_teacher_student.class_name, 
                                student_email=absence.class_teacher_student.student_email))
    
    @app.route('/view-subject-grades', methods=['POST'])
    def view_subject_grades():
        if 'email' not in session:
            return redirect(url_for('index'))

        selected_subject = request.form['subject']
        student_email = session['email']

        # Get the class teacher student relationship
        class_teacher_students = ClassTeacherStudent.query.filter_by(student_email=student_email).all()
        subject_grades = []

        for cts in class_teacher_students:
            if cts.subject == selected_subject:
                grades = StudentGrade.query.filter_by(class_teacher_student_id=cts.id).order_by(StudentGrade.date.desc()).all()
                subject_grades.extend(grades)

        return render_template('dashboard_student.html', 
                            student_subjects=class_teacher_students,
                            subject_grades=subject_grades,
                            selected_subject=selected_subject)
        
    @app.route('/add-homework', methods=['POST'])
    def add_homework():
        if 'email' not in session or session['role'] != 'teacher':
            return redirect(url_for('index'))

        class_name = request.form['class_name']
        title = request.form['title']
        description = request.form.get('description', '')
        link = request.form.get('link', '')
        due_date = request.form['due_date']

        # Find the teacher's subject for this class
        class_teacher = ClassTeacher.query.filter_by(
            class_name=class_name, 
            teacher_name=session['name']
        ).first()

        if not class_teacher:
            return "Invalid class or teacher", 400

        # Create new homework
        new_homework = Homework(
            class_name=class_name,
            teacher_name=session['name'],
            subject=class_teacher.subject,
            title=title,
            description=description,
            link=link,
            due_date=date.fromisoformat(due_date)
        )
        db.session.add(new_homework)
        db.session.commit()
        
        students = User.query.filter_by(class_name=class_name).all()  # Get all students in the class
        for student in students:
            add_notification(student.email, student.name, f"New homework assigned: {title}.")

        return redirect(url_for('manage_class', class_name=class_name))

    @app.route('/remove-homework', methods=['POST'])
    def remove_homework():
        if 'email' not in session or session['role'] != 'teacher':
            return redirect(url_for('index'))

        homework_id = request.form['homework_id']
        homework = Homework.query.get(homework_id)

        if homework and homework.teacher_name == session['name']:
            db.session.delete(homework)
            db.session.commit()

        return redirect(url_for('manage_class', class_name=homework.class_name))

    @app.route('/manage-class/<class_name>')
    def manage_class(class_name):
        if 'email' not in session or session['role'] != 'teacher':
            return redirect(url_for('index'))

        # Find all students in this class
        students = User.query.filter_by(
            role='student', 
            class_name=class_name
        ).all()

        # Get lessons for this class
        class_teacher = ClassTeacher.query.filter_by(
            class_name=class_name, 
            teacher_name=session['name']
        ).first()

        lessons = []
        if class_teacher:
            lessons = Lesson.query.filter_by(class_id=class_teacher.id).all()

        # Get current and future homeworks for this class
        current_date = date.today()
        input_date = current_date.strftime('%Y-%m-%d')
        display_date = current_date.strftime('%d.%m.%Y')
        homeworks = Homework.query.filter_by(
            class_name=class_name, 
            teacher_name=session['name']
        ).filter(Homework.due_date >= current_date).all()

        return render_template('class_view.html', 
                            class_name=class_name, 
                            students=students, 
                            lessons=lessons,
                            homeworks=homeworks,
                            input_date=input_date,)
        
    @app.route('/remove-lesson', methods=['POST'])
    def remove_lesson():
        lesson_id = request.form['lesson_id']
        lesson = Lesson.query.get(lesson_id)
        
        if lesson:
            db.session.delete(lesson)
            db.session.commit()

        return redirect(url_for('manage_class', class_name=lesson.class_name))
    
    @app.route('/subject/<subject>/<student_email>', methods=['GET'])
    def subject_details(subject, student_email):
        # Get the class teacher student entry for the selected subject
        class_teacher_students = ClassTeacherStudent.query.filter_by(
            student_email=student_email,
            subject=subject
        ).first()

        if not class_teacher_students:
            return "No data found for this subject.", 404

        # Initialize grades and absences
        grades = StudentGrade.query.filter_by(
            class_teacher_student_id=class_teacher_students.id
        ).order_by(StudentGrade.date.desc()).all()

        absences = StudentAbsence.query.filter_by(
            class_teacher_student_id=class_teacher_students.id
        ).all()

        return render_template('subject_details.html', 
                            subject=subject, 
                            grades=grades, 
                            absences=absences, 
                            student_email=student_email)
    @app.route('/dashboard_form_teacher', methods=['GET'])
    def dashboard_form_teacher():
        if 'email' not in session or session['role'] != 'form_teacher':
            return redirect(url_for('index'))

        # Get the form teacher's class
        form_teacher = User.query.filter_by(email=session['email']).first()
        class_name = form_teacher.class_name

        # Get all students in the form teacher's class
        students = User.query.filter_by(class_name=class_name, role='student').all()

        return render_template('form_teacher_dashboard.html', students=students)   
    
    @app.route('/form_teacher_student_subjects/<student_email>', methods=['GET'])
    def form_teacher_student_subjects(student_email):
        # Get the student's subjects
        class_teacher_students = ClassTeacherStudent.query.filter_by(student_email=student_email).all()

        subjects = []
        for cts in class_teacher_students:
            subjects.append(cts.subject)

        return render_template('form_teacher_student_subjects.html', student_email=student_email, subjects=subjects)
    
    @app.route('/form_teacher_subject_details/<student_email>/<subject_name>', methods=['GET'])
    def form_teacher_subject_details(student_email, subject_name):
        # Fetch the class teacher student entry for the specified student
        class_teacher_student = ClassTeacherStudent.query.filter_by(student_email=student_email, subject=subject_name).first()

        if not class_teacher_student:
            return "No class teacher student entry found.", 404

        # Get the student's name from db
        student = User.query.filter_by(email=student_email).first()
        student_name = student.name if student else student_email
        
        # Fetch grades and absences for the student in the specified subject
        grades = StudentGrade.query.filter_by(class_teacher_student_id=class_teacher_student.id).all()
        absences = StudentAbsence.query.filter_by(class_teacher_student_id=class_teacher_student.id).all()

        return render_template('form_teacher_subject_details.html', 
                            student_email=student_email, 
                            student_name=student_name,
                            subject_name=subject_name, 
                            grades=grades, 
                            absences=absences)
        
    @app.route('/reset-teacher-password/<teacher_email>', methods=['GET', 'POST'])
    def reset_teacher_password(teacher_email):
        if 'email' not in session or session['role'] != 'admin':
            return redirect(url_for('index'))

        teacher = User.query.filter_by(email=teacher_email).first()
        if request.method == 'POST':
            new_password = request.form['new_password']
            if teacher:
                teacher.password = new_password  # Update the password
                db.session.commit()  # Commit the changes to the database
                flash('Password updated successfully!')
                return redirect(url_for('admin_dashboard'))

        return render_template('reset_teacher_password.html', teacher=teacher)
    
    return app
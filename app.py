import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tour.db' 

# --- CẤU HÌNH THƯ MỤC UPLOAD ---
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# --- CẤU HÌNH LOGIN MANAGER ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ĐỊNH NGHĨA CÁC CLASS (MODEL) ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    bookings = db.relationship('Booking', backref='customer', lazy=True)

class Tour(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)  # Cột này sẽ chứa nội dung chi tiết

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tour_id = db.Column(db.Integer, db.ForeignKey('tour.id'), nullable=False)
    departure_date = db.Column(db.String(20))
    guests = db.Column(db.Integer)
    tour_info = db.relationship('Tour', backref='booked_by_users')

# --- KHỞI TẠO DATABASE ---
with app.app_context():
    db.create_all()
    if Tour.query.count() == 0:
        sample_tours = [
            Tour(name="Vịnh Hạ Long", price="2.000.000đ", image="halong.jpg", description="Khám phá kỳ quan thiên nhiên thế giới."),
            Tour(name="Đà Lạt", price="1.500.000đ", image="dalat.jpg", description="Thành phố ngàn hoa thơ mộng."),
            Tour(name="Phú Quốc", price="3.500.000đ", image="phuquoc.jpg", description="Thiên đường đảo ngọc."),
            Tour(name="Sa Pa", price="2.800.000đ", image="sapa.jpg", description="Trải nghiệm sương mù đỉnh Fansipan.")
        ]
        db.session.bulk_save_objects(sample_tours)
        db.session.commit()

# --- CÁC ROUTE XỬ LÝ ---

@app.route('/')
def index():
    search_query = request.args.get('search')
    if search_query:
        all_tours = Tour.query.filter(Tour.name.contains(search_query)).all()
    else:
        all_tours = Tour.query.all()
    return render_template('index.html', tours=all_tours, search_query=search_query)

@app.route('/tour/<int:tour_id>')
def tour_detail(tour_id):
    tour = Tour.query.get_or_404(tour_id)
    return render_template('tour_detail.html', tour=tour)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            login_user(user)
            flash('Đăng nhập thành công!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Email hoặc mật khẩu không chính xác.', 'danger') 
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('Email này đã được sử dụng!', 'danger')
            return redirect(url_for('register'))
        new_user = User(email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Đăng ký thành công! Mời bạn đăng nhập.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    user_bookings = Booking.query.filter_by(user_id=current_user.id).all()
    return render_template('profile.html', bookings=user_bookings)

@app.route('/book/<int:tour_id>', methods=['GET', 'POST'])
@login_required
def booking(tour_id):
    tour = Tour.query.get_or_404(tour_id)
    if request.method == 'POST':
        departure_date = request.form.get('departure_date')
        guests = request.form.get('guests')
        new_booking = Booking(
            user_id=current_user.id,
            tour_id=tour.id,
            departure_date=departure_date,
            guests=guests
        )
        db.session.add(new_booking)
        db.session.commit()
        flash('Đặt tour thành công!', 'success')
        return redirect(url_for('profile'))
    return render_template('booking.html', tour=tour)

# --- QUẢN TRỊ VIÊN (ADMIN) ---

@app.route('/admin/add', methods=['GET', 'POST'])
@login_required
def add_tour():
    if current_user.email != 'admin@gmail.com': 
        flash('Bạn không có quyền truy cập trang này!', 'danger') 
        return redirect(url_for('index')) 
    
    if request.method == 'POST':
        name = request.form.get('name') 
        price = request.form.get('price') 
        description = request.form.get('description') 
        
        file = request.files.get('image_file') 
        filename = "default.jpg" 
        
        if file and file.filename != '':
            filename = file.filename
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        new_tour = Tour(name=name, price=price, image=filename, description=description) 
        
        try:
            db.session.add(new_tour) 
            db.session.commit() 
            flash('Thêm tour thành công!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback() 
            flash(f'Có lỗi xảy ra: {str(e)}', 'danger') 

    return render_template('add_tour.html') 

@app.route('/admin/edit/<int:tour_id>', methods=['GET', 'POST'])
@login_required
def edit_tour(tour_id):
    if current_user.email != 'admin@gmail.com':
        flash('Bạn không có quyền truy cập trang này!', 'danger')
        return redirect(url_for('index'))

    tour = Tour.query.get_or_404(tour_id)
    if request.method == 'POST':
        tour.name = request.form.get('name')
        tour.price = request.form.get('price')
        file = request.files.get('image_file')
        if file and file.filename != '':
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            tour.image = filename
        
        tour.description = request.form.get('description')
        
        try:
            db.session.commit()
            flash(f'Đã cập nhật tour {tour.name}!', 'success')
            return redirect(url_for('index'))
        except:
            db.session.rollback()
            flash('Có lỗi xảy ra khi cập nhật.', 'danger')
            
    return render_template('edit_tour.html', tour=tour)

@app.route('/admin/delete/<int:tour_id>', methods=['POST'])
@login_required
def delete_tour(tour_id):
    if current_user.email != 'admin@gmail.com':
        flash('Hành động bị từ chối!', 'danger')
        return redirect(url_for('index'))
        
    tour = Tour.query.get_or_404(tour_id)
    try:
        db.session.delete(tour)
        db.session.commit()
        flash(f'Đã xóa tour {tour.name}!', 'success')
    except:
        db.session.rollback()
        flash('Không thể xóa tour này.', 'danger')
    return redirect(url_for('index'))

@app.route('/delete_booking/<int:booking_id>', methods=['POST'])
@login_required
def delete_booking(booking_id):
    booking_to_delete = Booking.query.filter_by(id=booking_id, user_id=current_user.id).first_or_404()
    try:
        db.session.delete(booking_to_delete)
        db.session.commit()
        flash('Đã hủy tour thành công!', 'success')
    except:
        db.session.rollback()
        flash('Có lỗi xảy ra, không thể hủy.', 'danger')
    return redirect(url_for('profile'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
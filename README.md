# Portfolio Application

Portfolio web application dengan FastAPI dan Jinja2 templates.

## Features
- Portfolio display dengan dark theme dan animasi
- Admin dashboard untuk mengelola profil
- Upload foto profil (max 5MB)
- Authentication dengan JWT
- Database PostgreSQL

## Local Development

### Requirements
- Python 3.12+
- PostgreSQL

### Setup
1. Clone repository
2. Create virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create `.env` file:
   ```env
   DATABASE_HOSTNAME=localhost
   DATABASE_PORT=5432
   DATABASE_PASSWORD=your_password
   DATABASE_NAME=portfolio_db
   DATABASE_USERNAME=postgres
   SECRET_KEY=your_secret_key_here
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   ```

5. Run application:
   ```bash
   uvicorn app.main:app --reload
   ```

6. Access:
   - Home: http://localhost:8000
   - Portfolio: http://localhost:8000/portofolio/
   - Admin: http://localhost:8000/admin/login

## Deployment ke Render

### Setup Database
1. Buat PostgreSQL database di Render
2. Simpan connection string

### Setup Web Service
1. Buat Web Service baru
2. Connect repository
3. Settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: Python 3

4. Environment Variables (tambahkan di Render dashboard):
   - `DATABASE_HOSTNAME`: [dari Render PostgreSQL]
   - `DATABASE_PORT`: 5432
   - `DATABASE_PASSWORD`: [dari Render PostgreSQL]
   - `DATABASE_NAME`: [dari Render PostgreSQL]
   - `DATABASE_USERNAME`: [dari Render PostgreSQL]
   - `SECRET_KEY`: [generate dengan: openssl rand -hex 32]
   - `ALGORITHM`: HS256
   - `ACCESS_TOKEN_EXPIRE_MINUTES`: 1440

### Persistent File Storage (Optional)
Render menggunakan ephemeral filesystem. Untuk file uploads yang persistent:

**Option 1: Render Disk (Recommended untuk start)**
- Tambah Disk di Render dashboard
- Mount path: `/opt/render/project/src/app/static/uploads`
- Disk akan persist antara deploys

**Option 2: Cloud Storage (Production)**
- Upgrade ke AWS S3 / Cloudinary untuk production
- Ubah `save_uploaded_file` function di `app/routers/admin.py`

### First Deploy
1. Push code ke repository
2. Render akan auto-deploy
3. Buat user pertama via API:
   ```bash
   curl -X POST https://your-app.onrender.com/auth/create \
   -H "Content-Type: application/json" \
   -d '{"email":"admin@example.com","password":"your_password"}'
   ```

## API Endpoints

### Public
- `GET /` - Home page
- `GET /portofolio/` - Portfolio display
- `GET /portofolio/all` - API: Get all profiles (JSON)

### Authentication
- `POST /auth/create` - Create user
- `POST /auth/login` - Login

### Admin (Protected)
- `GET /admin/login` - Login page
- `GET /admin/dashboard` - Dashboard
- `POST /admin/profile/create` - Create profile dengan upload foto
- `PUT /admin/profile/{id}/edit` - Edit profile
- `DELETE /admin/profile/{id}/delete` - Delete profile

## File Upload Specifications
- **Max size**: 5MB
- **Allowed formats**: JPEG, PNG, WebP
- **Storage**: `/app/static/uploads/`
- **Validation**: Content-type dan size check

## Tech Stack
- FastAPI
- Jinja2 Templates
- SQLAlchemy
- PostgreSQL
- JWT Authentication
- Python Multipart (file uploads)

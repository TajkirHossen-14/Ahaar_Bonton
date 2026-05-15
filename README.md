<div align="center">
<p align="center">
  <img src="Assets/Banner/AhaarBonton Banner.png" alt="Ahaar Bonton Banner" width="100%">
</p>
 
### A Surplus Food Redistribution Platform
 
*Connecting Donors, NGOs, and Volunteers to Reduce Food Waste*
</div>

---
 
## 📖 About the Project
 
**Ahaar Bonton (আহার বণ্টন)** is a web-based surplus food redistribution platform built specifically for the context of Bangladesh. Every day, significant amounts of food go to waste at restaurants, weddings, corporate events, and households, while many people struggle to meet their daily nutritional needs.
This platform provides a structured, community-driven solution to that contradiction. Donors can post surplus food listings, NGOs can claim and coordinate pickups, and volunteers can register to assist with deliveries – all through a single, unified platform designed to work within Bangladesh's existing social and organizational fabric.
 
> *"Ahaar" (আহার) means food, and "Bonton" (বণ্টন) means distribution – together, a name that speaks for itself.*
 
---
 
## ✨ Key Features
 
- 🥘 **Food Donation Listings** – Donors can post surplus food with details like quantity, type, and pickup location
- 🏢 **NGO Dashboard** – NGOs can browse available donations and claim them for redistribution
- 🚴 **Volunteer Management** – Volunteers can register and assist with food pickup and delivery
- 👤 **User Authentication** – Separate registration and profile management for Donors, NGOs, and Volunteers
- 📦 **Delivery Tracking** – Manage and track the status of food deliveries
- 🖼️ **Image Uploads** – Food listings support photo uploads via Pillow
---
 
## 🗂️ Project Structure
 
```
AhaarBonton/
│
├── ahaarbonton/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── core/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   ├── admin.py
│   ├── backends.py
│   ├── migrations/
│   ├── management/
│   │   └── commands/
│   │       └── expire_food.py
│   ├── services/
│   │   ├── matching.py
│   │   └── notification.py
│   └── tests.py
│
├── users/
│   ├── models.py
│   ├── forms.py
│   ├── backends.py
│   ├── services/
│   └── apps.py
│
├── food/
│   ├── models.py
│   ├── forms.py
│   ├── services/
│   │   └── matching.py
│   └── apps.py
│
├── delivery/
│   ├── models.py
│   ├── services/
│   │   └── notification.py
│   └── apps.py
│
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── transparency.html
│   ├── 403.html
│   ├── 404.html
│   ├── auth/
│   │   ├── login.html
│   │   ├── register.html
│   │   └── profile.html
│   ├── donor/
│   │   ├── dashboard.html
│   │   ├── add_food.html
│   │   ├── edit_food.html
│   │   └── requests.html
│   ├── ngo/
│   │   ├── dashboard.html
│   │   ├── my_requests.html
│   │   └── request_confirm.html
│   ├── volunteer/
│   │   └── dashboard.html
│   └── admin_panel/
│       └── dashboard.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   ├── img/
│   └── favicon/
│
├── media/
│   ├── food_posts/
│   └── profiles/
│
├── Assets/
│   ├── Banner/
│   └── Screenshots/
│
├── db.sqlite3
├── manage.py
├── requirements.txt
├── .gitignore
└── README.md
```
 
---
 
## 🛠️ Tech Stack
 
| Layer | Technology |
|-------|-----------|
| Backend Framework | Django 6.0.5 |
| Language | Python 3.13.0 |
| Database | SQLite (default) |
| Frontend | HTML5, CSS3, JavaScript |
| Image Handling | Pillow 12.2.0 |
| Templating | Django Templates |
 
---
 
## 🚀 Getting Started
 
### Prerequisites
 
- Python 3.10 or higher
- pip
### Installation
 
**1. Clone the repository**
```bash
git clone https://github.com/TajkirHossen-14/Ahaar_Bonton.git
cd Ahaar_Bonton
```
 
**2. Create and activate a virtual environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate
 
# Linux / macOS
python -m venv venv
source venv/bin/activate
```
 
**3. Install dependencies**
```bash
pip install -r requirements.txt
```
 
**4. Apply migrations**
```bash
python manage.py migrate
```
 
**5. Create a superuser (optional)**
```bash
python manage.py createsuperuser
```
 
**6. Run the development server**
```bash
python manage.py runserver
```
 
Now open your browser and visit **http://127.0.0.1:8000** 🎉
 
---
 
## 👥 User Roles
 
| Role | Description |
|------|-------------|
| 🧑‍🍳 **Donor** | Individuals, restaurants, or businesses that post surplus food |
| 🏢 **NGO** | Organizations that claim food donations and manage distribution |
| 🚴 **Volunteer** | Individuals who help with pickup and delivery of food |
 
---
 
## 🤝 Contributing
 
Contributions are welcome! If you'd like to improve the platform:
 
1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request
 
---
 
## 🙏 Acknowledgements
 
This project was built with the goal of using technology to address real-world food insecurity and reduce waste. Inspired by grassroots food-sharing movements across Bangladesh and beyond.

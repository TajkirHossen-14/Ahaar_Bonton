<div align="center">
<p align="center">
  <img src="Assets/Banner/AhaarBonton Banner 3.png" alt="Ahaar Bonton Banner" width="100%">
</p>

# AhaarBonton
A Surplus Food Redistribution Platform

*Connecting Donors, NGOs, and Volunteers to Reduce Food Waste*

<p>
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white">
  &nbsp; 
  <img src="https://img.shields.io/badge/Django-6.0-092E20?logo=django&logoColor=white">
  <!-- <img src="https://img.shields.io/badge/License-MIT-green.svg">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen"> -->
</p>

</div>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png" width="100%"/>

## 📌 Table of Contents

- [📑 About the Project](#-about-the-project)
- [✨ Key Features](#-key-features)
- [⚙️ How AhaarBonton Works](#️-how-aharbonton-works)
- [🗂️ Project Structure](#️-project-structure)
- [🛠️ Tech Stack](#️-tech-stack)
- [🚀 Getting Started](#-getting-started)
- [👥 User Roles](#-user-roles)
- [🤝🏼 Contributing](#-contributing)

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png" width="100%"/>

## 📑 About the Project

**AhaarBonton (আহার বণ্টন)** is a web-based surplus food redistribution platform built specifically for the context of Bangladesh. Every day, significant amounts of food go to waste at restaurants, weddings, corporate events, and households, while many people struggle to meet their daily nutritional needs.

This platform provides a structured, community-driven solution to that contradiction. Donors can post surplus food listings, NGOs can claim and coordinate pickups, and volunteers can register to assist with deliveries – all through a single, unified platform designed to work within Bangladesh's existing social and organizational fabric.

> *"Ahaar" (আহার) means food, and "Bonton" (বণ্টন) means distribution – together, a name that speaks for itself.*

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png" width="100%"/>

## ✨ Key Features

- 🥘 **Food Donation Listings** – Donors post surplus food with title, quantity, category, image, and GPS-based pickup location
- 🏢 **Priority-Sorted NGO Dashboard** – NGOs browse available food sorted by expiry urgency, with category filters and live countdowns
- 🚴 **Volunteer Delivery System** – Volunteers accept open delivery jobs and manage pickups/drop-offs from their dashboard
- 👤 **Flexible Authentication** – Register and log in using either **Email or Phone Number**, with full **Forgot Password** support
- 🔐 **Dual OTP Delivery Verification** – Two separate OTPs (Pickup OTP from Donor, Delivery OTP from NGO) ensure food is verifiably picked up *and* delivered — not just claimed
- 📍 **GPS Auto-Location** – One-tap location detection auto-fills addresses using the browser's GPS and OpenStreetMap Nominatim
- 🗺️ **Interactive Food Map & Heatmap** – View all available donations on a live map, or see donation density by area (Leaflet.js + OpenStreetMap)
- ⭐ **Trust Score System** – Both Donors and Volunteers build a 0–100 trust score based on successful, on-time deliveries
- 🏆 **Community Leaderboard** – Dual-view leaderboard ranking top Donors & Volunteers by **Activity** (donations/deliveries) or by **Trust Score**
- 💬 **Ratings & Reviews** – NGOs rate Donors & Volunteers, Donors rate Volunteers — visible on public profiles
- 🚩 **Report System** – Users can report inappropriate food posts or fraudulent accounts for Admin review
- 📊 **Transparency Dashboard** – A public-facing impact page with real-time statistics on food saved, deliveries completed, and communities served
- 🖼️ **Image Uploads** – Food listings and user profiles support photo uploads via Pillow
- 📶 **Basic Offline Support (PWA)** – Service Worker caches key pages for smoother reloads on unstable connections
- 🛠️ **Custom Admin Panel** – A dedicated dashboard for monitoring users, food posts, and platform-wide statistics

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png" width="100%"/>

## ⚙️ How AhaarBonton Works

AhaarBonton follows a simple, transparent, and verified flow from food surplus to final delivery.

<br>

### 👤 Step 1  –  Donor Posts Food

A donor (restaurant, household, or event organizer) logs in and creates a food post with:
- Food title, description, and quantity
- Category (Cooked / Raw / Packaged / Bakery)
- Pickup location (auto-filled via GPS)
- Expiry date and time
- Optional food image

The post immediately becomes visible to all registered NGOs on their dashboard.

### 🏢 Step 2  –  NGO Requests Food

NGOs browse available food sorted by **expiry priority** (soonest expiring first).
They can filter by category and see a live expiry countdown on each card.

When an NGO finds suitable food, they send a **collection request** with an optional message to the donor.

### ✅ Step 3  –  Donor Approves the Request

The donor reviews incoming requests and approves or rejects them.

On **approval**, the system automatically:
- Marks the food post as **Claimed**
- Creates a **Delivery record**
- Generates **two unique 6-digit OTPs**:
  - `Pickup OTP` → visible to the Donor (given to Volunteer at pickup)
  - `Delivery OTP` → sent to the NGO via email (given to Volunteer at delivery)

### 🚚 Step 4  –  Volunteer Accepts the Delivery

Volunteers browse open delivery jobs and accept one.

Each job shows:
- Pickup location (Donor's address)
- Drop-off location (NGO name)
- Food quantity and expiry time

### 🔐 Step 5  –  Pickup Confirmed (OTP 1)

The volunteer visits the donor and collects the food.
The **Donor shares the Pickup OTP** with the volunteer.

The volunteer enters the Pickup OTP in their dashboard:
- ✅ Correct OTP → Pickup confirmed, status updates to **Picked Up**
- ❌ Wrong OTP → Error shown, volunteer must try again

At this point, the NGO receives an email notification:
*"Food is on the way! Your Delivery OTP: XXXXXX"*

### 🏁 Step 6  –  Delivery Confirmed (OTP 2)

The volunteer arrives at the NGO and hands over the food.
The **NGO shares the Delivery OTP** with the volunteer.

The volunteer enters the Delivery OTP in their dashboard:
- ✅ Correct OTP → Delivery confirmed, status updates to **Delivered**
- ❌ Wrong OTP → Error shown

### 🎉 Step 7  –  Completion & Impact

Once delivery is confirmed, the system automatically updates:

| What | Result |
|---|---|
| Food Post Status | `Delivered` |
| Food Request Status | `Completed` |
| Donor & Volunteer Trust Score | `+5 Points` |
| Leaderboard & Transparency Dashboard | Updated With New Delivery |
| Donor Notification | Email Confirmation Sent |

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png" width="100%"/>

## 🗂️ Project Structure

AhaarBonton follows a **multi-app Django architecture** — functionality is split into four focused apps (`core`, `users`, `food`, `delivery`) instead of one monolithic app, keeping models and services organized by domain.

```
Ahaar_Bonton/
│
├── ahaarbonton/                 # Django project package (config)
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── core/                         # Shared models, views & core logic
│   ├── admin.py
│   ├── backends.py
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   ├── views.py
│   ├── migrations/
│   ├── services/
│   │   ├── matching.py
│   │   └── notification.py
│   └── management/
│       └── commands/
│           └── expire_food.py
│
├── users/                        # Authentication & account app
│   ├── backends.py
│   ├── forms.py
│   ├── models.py
│   └── services/
│
├── food/                          # Food listings & donation app
│   ├── forms.py
│   ├── models.py
│   └── services/
│       └── matching.py
│
├── delivery/                      # Delivery & logistics app
│   ├── models.py
│   └── services/
│       └── notification.py
│
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── transparency.html
│   ├── leaderboard.html
│   ├── food_map.html
│   ├── heatmap.html
│   ├── offline.html
│   ├── 403.html
│   ├── 404.html
│   ├── auth/
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── profile.html
│   │   ├── password_reset.html
│   │   ├── password_reset_done.html
│   │   ├── password_reset_confirm.html
│   │   ├── password_reset_complete.html
│   │   ├── password_reset_email.html
│   │   └── password_reset_subject.txt
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
│   ├── admin_panel/
│   │   └── dashboard.html
│   ├── profiles/
│   │   └── user_profile.html
│   ├── reports/
│   │   ├── report_post.html
│   │   └── report_user.html
│   └── partials/
│       └── rating_form.html
│
├── static/
│   ├── manifest.json
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── main.js
│   │   └── service-worker.js
│   ├── img/
│   └── favicon/
│
├── media/                    # User-uploaded files (food images, profile pics)
├── Assets/                   # README banners & screenshots
│
├── db.sqlite3
├── manage.py
├── requirements.txt
├── .gitignore
└── README.md
```

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png" width="100%"/>

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend Framework | Django 6.0.5 |
| Language | Python 3.13.0 |
| Database | SQLite (default) |
| Frontend | HTML5, CSS3, JavaScript |
| Maps | OpenStreetMap + Leaflet.js (Free, no API key) |
| Image Handling | Pillow |
| Templating | Django Templates |
| Offline Support | Service Worker (PWA) |

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png" width="100%"/>

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

**5. Create a superuser (Optional)**
```bash
python manage.py createsuperuser
```

**6. Run the development server**
```bash
python manage.py runserver 127.0.0.1:8500
```

Use this fixed port for local development and QA. Open your browser and visit **http://127.0.0.1:8500** 🎉

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png" width="100%"/>

## 👥 User Roles

| Role | Description |
|------|-------------|
| 👤 **Donor** | Individuals, restaurants, or businesses that post surplus food |
| 🏢 **NGO** | Organizations that claim food donations and manage distribution |
| 🚴 **Volunteer** | Individuals who help with pickup and delivery of food |
| 🛠️ **Admin** | Manages users, monitors food posts, and oversees platform activity |

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png" width="100%"/>


## 🤝🏼 Contributing

Contributions are welcome! If you'd like to improve the platform:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/Your-Feature`)
3. Commit your changes (`git commit -m 'Add Some Feature'`)
4. Push to the branch (`git push origin feature/Your-Feature`)
5. Open a Pull Request

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png" width="100%"/>

## 📜 License

This project is licensed under the [MIT License](LICENSE).

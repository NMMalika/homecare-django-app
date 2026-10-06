# Homecare & Caregiver Management System

A comprehensive Django-based healthcare management platform designed to manage homecare requests, caregiver assignments, consultations, referrals, payments, and staff workflows.

## 🚀 Features

* **Client & Homecare Portal:**
  * Request homecare services and generate service quotations.
  * Schedule consultations and access telemedicine modules.
  * Payment verification and tracking.
* **Caregiver Portal (`/caregivers/`):**
  * Dashboard for caregivers to manage assignments and submit daily reports.
  * Profile management and assignment details.
* **Staff Management (`/staff/`):**
  * Centralized dashboard for managing appointments, caregivers, referrals, payments, and service items.
* **Core Administration:**
  * Custom user roles and middleware via `accounts`.
  * Dynamic site configuration and service catalog management.

---

## 🛠️ Tech Stack

* **Backend:** Python 3.11 / 3.14, Django
* **Frontend:** HTML5, CSS3, JavaScript, Bootstrap
* **Database:** SQLite (Development) / PostgreSQL or MySQL (Production)

---

## 📁 Project Structure

```text
.
├── accounts/       # User management, custom roles, and middleware
├── caregivers/     # Caregiver portal, reports, and assignments
├── config/         # Django project settings and root routing
├── core/           # Core utility models, context processors, and site settings
├── homecare/       # Core business logic (requests, quotations, payments)
├── pages/          # Static/content pages (About, Contact, FAQ, Services)
├── services/       # Service offerings and category definitions
├── staff/          # Internal staff dashboard and management features
├── static/         # CSS, JS, fonts, and assets
├── templates/      # Global HTML templates and layout components
└── manage.py       # Django management script
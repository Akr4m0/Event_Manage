# Event Management Platform

A comprehensive Django-based event management system with ticket sales, payment processing, and social authentication.

## Features

- 🎫 **Event Management**: Create, edit, and manage events
- 🎟️ **Ticketing System**: Multiple ticket types with quantity management
- 💳 **Payment Processing**: Integrated Stripe payments and offline payment options
- 🔐 **Authentication**: Social login via Google and Facebook
- 👥 **User Profiles**: Manage user information and event history
- 📊 **Admin Dashboard**: Comprehensive admin interface for event organizers
- 📱 **Responsive Design**: Mobile-friendly interface
- 🔍 **Search & Filters**: Find events by category, date, and location

## Tech Stack

- **Backend**: Django 5.1.7, Django REST Framework
- **Database**: SQLite (development), PostgreSQL (production)
- **Authentication**: Django-allauth, Python Social Auth
- **Payments**: Stripe API
- **Frontend**: Bootstrap 5, Font Awesome
- **Task Queue**: Celery (optional)

## Prerequisites

- Python 3.13+
- pip
- Virtual environment (recommended)
- Stripe account (for payment processing)
- Google/Facebook OAuth apps (for social login)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/event-management-platform.git
   cd event-management-platform
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and add your actual values
   # IMPORTANT: Never commit your actual .env file!
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files**
   ```bash
   python manage.py collectstatic
   ```

8. **Run the development server**
   ```bash
   python manage.py runserver
   ```

Visit `http://localhost:8000` to see the application.

## Configuration

### Stripe Setup

1. Create a Stripe account at https://stripe.com
2. Get your test API keys from the Stripe Dashboard
3. Add them to your `.env` file:
   ```
   STRIPE_PUBLISHABLE_KEY=pk_test_...
   STRIPE_SECRET_KEY=sk_test_...
   ```
4. Set up webhook endpoint in Stripe Dashboard:
   - Endpoint URL: `https://yourdomain.com/payments/webhook/stripe/`
   - Events: `checkout.session.completed`, `checkout.session.expired`, `payment_intent.payment_failed`

### Social Authentication

#### Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs: `http://localhost:8000/auth/complete/google-oauth2/`

#### Facebook OAuth
1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create a new app
3. Add Facebook Login product
4. Set Valid OAuth Redirect URIs: `http://localhost:8000/auth/complete/facebook/`

## Testing

Run tests with:
```bash
python manage.py test
```

For coverage report:
```bash
coverage run --source='.' manage.py test
coverage report
coverage html  # For HTML report
```

## API Documentation

The API is available at `/api/` with the following endpoints:

- `/api/events/` - Event management
- `/api/tickets/` - Ticket operations
- `/api/payments/` - Payment processing
- `/api/users/` - User management

## Deployment

### Production Checklist

- [ ] Set `DEBUG = False` in settings
- [ ] Use PostgreSQL instead of SQLite
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Set up proper email backend
- [ ] Use environment variables for all secrets
- [ ] Enable HTTPS
- [ ] Set up proper static file serving
- [ ] Configure CORS if needed
- [ ] Set up monitoring and logging

### Heroku Deployment

1. Install Heroku CLI
2. Create `Procfile`:
   ```
   web: gunicorn event_management.wsgi
   ```
3. Add `gunicorn` to requirements.txt
4. Configure database and static files
5. Deploy:
   ```bash
   heroku create your-app-name
   heroku config:set $(cat .env | grep -v '^#' | xargs)
   git push heroku main
   heroku run python manage.py migrate
   ```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Django documentation
- Stripe documentation
- Bootstrap team
- All contributors

## Support

For support, email support@eventhub.com or create an issue in the repository.

## Security

Please report security vulnerabilities to security@eventhub.com

---

Made with ❤️ by Akram
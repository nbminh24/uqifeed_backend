# UQIFeed Backend

UQIFeed is a personalized nutrition tracking application that helps users monitor their food intake, track nutritional goals, and receive personalized advice based on AI analysis.

## Features

- 🍽️ **Food Recognition**: Upload food images and automatically detect ingredients and nutritional information
- 📊 **Nutrition Tracking**: Monitor daily and weekly nutrition intake with detailed reports
- 🎯 **Goal Setting**: Set personalized nutrition goals based on your profile and targets
- 📝 **Smart Analysis**: Get personalized advice and suggestions for improving your diet
- 🔍 **Progress Monitoring**: Track your progress over time with weekly reports and insights

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **AI**: Google Gemini AI for food recognition and nutritional analysis
- **Authentication**: JWT (JSON Web Tokens)

## Setup Instructions

### Prerequisites

- Python 3.8+
- PostgreSQL
- Google API key for Gemini AI

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/uqifeed_backend.git
   cd uqifeed_backend
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory with the following variables:
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/uqifeed_db
   SECRET_KEY=your_secret_key_here
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   GOOGLE_API_KEY=your_google_api_key_here
   HOST=0.0.0.0
   PORT=8000
   DEBUG=True
   ```

5. Create the PostgreSQL database:
   ```
   psql -U postgres
   CREATE DATABASE uqifeed_db;
   CREATE USER uqifeed WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE uqifeed_db TO uqifeed;
   ```

6. Run the application:
   ```
   python -m src.main
   ```

7. Access the API documentation at `http://localhost:8000/docs`

## API Documentation

The UQIFeed API provides the following main endpoints:

### Authentication

- `POST /users/register` - Register a new user
- `POST /users/login` - Login and get access token

### User Profile

- `GET /users/me` - Get current user's information
- `POST /users/profile` - Create user profile
- `PUT /users/profile` - Update user profile
- `GET /users/profile` - Get user profile
- `GET /users/nutrition-target` - Get user's nutrition target

### Food Management

- `POST /dishes/recognize` - Recognize food from an image URL
- `POST /dishes/upload-image` - Upload a food image
- `POST /dishes/analyze-uploaded` - Analyze an uploaded food image
- `POST /dishes` - Create a new food entry manually
- `POST /dishes/save-recognized` - Save recognized food to database
- `GET /dishes/{food_id}` - Get a specific food entry
- `GET /dishes` - List user's food entries with filtering options

### Nutrition Analysis

- `POST /nutrition/compare/{food_id}` - Compare food with user's nutrition target
- `GET /nutrition/compare/{comparison_id}/advice` - Get advice for a nutrition comparison
- `GET /nutrition/compare/{comparison_id}/review` - Get nutritional review for a comparison
- `GET /nutrition/target` - Get user's nutrition target

### Reports

- `GET /nutrition/reports/daily/{report_date}` - Get or generate daily report
- `GET /nutrition/reports/weekly/{week_start_date}` - Get or generate weekly report

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.


# UqiFeed API Endpoints by App Screen

This document organizes all API endpoints by app screen to make frontend integration easier.

## 1. Authentication & Login Screens

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|--------------|
| POST | `/users/register` | Register a new user | No |
| POST | `/users/login` | Login and get access token | No |
| POST | `/users/token-refresh` | Refresh access token | Yes |
| POST | `/auth/google` | Initiate Google OAuth login | No |
| GET | `/auth/google/callback` | Google OAuth callback handler | No |
| POST | `/auth/google/token` | Validate Google OAuth token from mobile | No |
| POST | `/auth/facebook` | Initiate Facebook OAuth login | No |
| GET | `/auth/facebook/callback` | Facebook OAuth callback handler | No |
| POST | `/auth/facebook/token` | Validate Facebook OAuth token from mobile | No |
| GET | `/auth/status` | Check authentication status | Yes |
| POST | `/users/logout` | Logout and invalidate token | Yes |

## 2. Registration & Profile Setup Screens

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|--------------|
| POST | `/users/profile` | Create user profile (basic) | Yes |
| PUT | `/users/profile` | Update user profile | Yes |
| GET | `/users/profile` | Get user profile | Yes |
| PUT | `/users/profile/step1` | Update profile with gender, age, etc. | Yes |
| PUT | `/users/profile/step2` | Update profile with height, weight | Yes |
| PUT | `/users/profile/step3` | Update profile with activity level | Yes |
| PUT | `/users/profile/step4` | Update profile with goals | Yes |
| PUT | `/users/profile/step5` | Update profile with diet preferences | Yes |
| GET | `/nutrition/target` | Get user's nutrition targets | Yes |
| PUT | `/nutrition/target` | Update user's nutrition targets | Yes |

## 3. Home Screen & Dashboard

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|--------------|
| GET | `/dishes/daily/{date_str}` | Get all meals for a specific date | Yes |
| GET | `/nutrition/reports/daily/{report_date}` | Get daily nutrition report | Yes |
| GET | `/nutrition/target` | Get user's nutrition targets | Yes |
| GET | `/notifications/count` | Get count of unread notifications | Yes |
| GET | `/notifications` | Get user notifications | Yes |
| PUT | `/notifications/read-all` | Mark all notifications as read | Yes |

## 4. Meal Logging Screen

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|--------------|
| POST | `/dishes/recognize` | Recognize food from an image URL | Yes |
| POST | `/dishes/upload-image` | Upload a food image | Yes |
| POST | `/dishes/analyze-image` | Analyze an uploaded food image | Yes |
| POST | `/dishes/analyze-text` | Analyze food based on text description | Yes |
| POST | `/dishes/` | Create a new food entry manually | Yes |
| POST | `/dishes/save-recognized` | Save recognized food to database | Yes |
| GET | `/dishes/{food_id}` | Get a specific food entry | Yes |
| GET | `/dishes/` | List user's food entries | Yes |
| GET | `/dishes/ingredient/{ingredient_id}` | Get detailed ingredient information | Yes |
| POST | `/dishes/edit-ingredient/{food_id}` | Edit an ingredient in a food entry | Yes |
| POST | `/dishes/add-ingredient/{food_id}` | Add a new ingredient to a food entry | Yes |
| DELETE | `/dishes/remove-ingredient/{food_id}/{ingredient_id}` | Remove an ingredient | Yes |
| GET | `/measurement-units/` | Get list of measurement units | Yes |

## 5. Food Analysis & Nutrition Screen

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|--------------|
| POST | `/nutrition/compare/{food_id}` | Compare food with nutrition target | Yes |
| GET | `/nutrition/compare/{comparison_id}/advice` | Get advice for nutrition | Yes |
| GET | `/nutrition/compare/{comparison_id}/review` | Get nutritional review | Yes |
| GET | `/calories/calculate_dish_calories` | Calculate dish calories | Yes |

## 6. Statistics Screen

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|--------------|
| GET | `/nutrition/reports/weekly-stats` | Get comprehensive weekly statistics | Yes |
| GET | `/nutrition/reports/weekly/{week_start_date}` | Get weekly nutrition report | Yes |

## 7. Settings Screen

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|--------------|
| GET | `/notifications/settings` | Get user's notification settings | Yes |
| PUT | `/notifications/settings` | Update user's notification settings | Yes |
| GET | `/users/subscriptions` | Get user's subscription status | Yes |
| POST | `/users/subscriptions` | Add or update subscription | Yes |
| PUT | `/users/change-password` | Change user password | Yes |
| PUT | `/users/update-preferences` | Update user preferences | Yes |
| DELETE | `/users/account` | Delete user account | Yes |

## 8. Notifications 

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|--------------|
| GET | `/notifications` | Get user notifications with filtering | Yes |
| PUT | `/{notification_id}/read` | Mark a notification as read | Yes |
| DELETE | `/{notification_id}` | Delete a notification | Yes |
| POST | `/meal-reminder` | Send a meal reminder notification | Yes |
| POST | `/progress-update` | Send a progress update notification | Yes |
| POST | `/weekly-summary` | Send a weekly nutrition summary notification | Yes |
| POST | `/nutrition-tip` | Send a nutrition tip notification | Yes |

## 9. Health & System

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|--------------|
| GET | `/` | Root endpoint | No |
| GET | `/health` | Health check endpoint | No |
| GET | `/docs` | API Documentation (Swagger UI) | No |
| GET | `/redoc` | Alternative API Documentation (ReDoc) | No |
from src.storage.user_db import create_user, get_user

email = 'debug5@example.com'
create_user(email, 29, 'other', 'password123')
print('Created user:', get_user(email))


# github 
commits
mostly working & 2.0

#
https://mental-health-llm.onrender.com

#local server
python -m backend.src.api.s

#run backend
#github 
commits
mostly working & 2.0

#
https://mental-health-llm.onrender.com

#local server
python -m backend.src.api.s

# run backend 
cd backend
.\.venv\Scripts\python.exe -m uvicorn src.api.s:app --host 0.0.0.0 --port 8001 --reload


cd backend; .\.venv\Scripts\python.exe -m src.api.s
.\.venv\Scripts\python.exe -m src.api.s

# github
git add src/api/android_server.py
git commit -m "fix_1"
git push

#
https://play.google.com/apps/testing/com.sarvagya.mentalhealthchat

#testers
abc@gmail.com 
abc
a,b,c

## for production
# 1 SubscriptionTestActivity
Change the Intent in ReliefChatActivity.kt line 72 from SubscriptionTestActivity to SubscriptionActivity
# 2 no reload
you can change it to in s.py
uvicorn.run("src.api.s:app", host="0.0.0.0", port=port, reload=False) 
# 3 unicorn
keep 1 unicorn in docker only
# 4 DB_PATH
#local
DB_PATH = os.path.join(os.path.dirname(__file__), "user_data.db")
#render
DB_PATH = "/var/data/user_data.db"

# current versionCode = 21 
versionName = "sarvagya_1.4"

# privacy policy
https://sarvagyayadav26.github.io/privacy-policy-for-mental-health/
 
Register: 
curl -X POST "https://mental-health-llm.onrender.com/auth/register" -H "Content-Type: application/json" -d "{\"email\":\"sarvagyayadav26@gmail.com\",\"age\":29,\"sex\":\"M\",\"password\":\"Qwerty@123\"}" 
Health Check: 
curl "https://mental-health-llm.onrender.com/health" 
Login: 
curl -X POST "https://mental-health-llm.onrender.com/auth/login" -H "Content-Type: application/json" -d "{\"email\":\"sunny.kalgaon@gmail.com\",\"password\":\"Qwerty@123\"}" 
Chat: 
curl -X POST "https://mental-health-llm.onrender.com/chat" -H "Content-Type: application/json" -d "{\"email\":\"sarvagyayadav26@gmail.com\",\"message\":\"hello\"}"

# kill python task to delete user_data.db
taskkill /F /IM python.exe

# render sever health 
https://health-app-mjt7.onrender.com/healthz


# tester
sunny.kalgaon@gmail.com




.\.venv\Scripts\python.exe -m src.api.s

cd backend
.\.venv\Scripts\python.exe -m uvicorn src.api.s:app --host 0.0.0.0 --port 8001 --log-level debug



#github
git add src/api/android_server.py
git commit -m "fix_1"
git push

#
https://play.google.com/apps/testing/com.sarvagya.mentalhealthchat

#testers
abc@gmail.com 
abc
a,b,c

# for production
1.
Change the Intent in ReliefChatActivity.kt line 72 from SubscriptionTestActivity to SubscriptionActivity
2.
you can change it to in s.py
uvicorn.run("src.api.s:app", host="0.0.0.0", port=port, reload=False) 
3. 
keep 1 unicorn in docker only
4. 
Change path
#local
DB_PATH = os.path.join(os.path.dirname(__file__), "user_data.db")
#render
DB_PATH = "/var/data/user_data.db"

#current versionCode = 21
versionName = "sarvagya_1.4"

#privacy policy
https://sarvagyayadav26.github.io/privacy-policy-for-mental-health/
 
Register: 
curl -X POST "https://mental-health-llm.onrender.com/auth/register" -H "Content-Type: application/json" -d "{\"email\":\"sarvagyayadav26@gmail.com\",\"age\":29,\"sex\":\"M\",\"password\":\"Qwerty@123\"}" 
Health Check: 
curl "https://mental-health-llm.onrender.com/health" 
Login: 
curl -X POST "https://mental-health-llm.onrender.com/auth/login" -H "Content-Type: application/json" -d "{\"email\":\"sunny.kalgaon@gmail.com\",\"password\":\"Qwerty@123\"}" 
Chat: 
curl -X POST "https://mental-health-llm.onrender.com/chat" -H "Content-Type: application/json" -d "{\"email\":\"sarvagyayadav26@gmail.com\",\"message\":\"hello\"}"

# start local server
Production: uvicorn src.api.server:app --reload --host 0.0.0.0 --port 5000
Local server: uvicorn src.api.server:app --reload

#kill python task to delete user_data.db
taskkill /F /IM python.exe

# databse in shell
sqlite3 /var/data/user_data.db

#models
GROQ_MODEL = os.getenv("GROQ_MODEL")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")

#render sever health 
https://health-app-mjt7.onrender.com/healthz

curl -X POST http://localhost:8001/chat/history/get -H "Content-Type: application/json" -d '{"email":"s","session_id":1,"limit":200}'


sunny.kalgaon@gmail.com

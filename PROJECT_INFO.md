# issues
7
give all my previous messages we have discussed is giving topic bubbles not the list 
8
shorter messages in the chat, llm is not  understanding to answer shorty

# local server ###################################################
python -m backend.src.api.s

# run backend ####################################################
cd backend
.\.venv\Scripts\python.exe -m uvicorn src.api.s:app --host 0.0.0.0 --port 8001 --reload


cd backend; .\.venv\Scripts\python.exe -m src.api.s
.\.venv\Scripts\python.exe -m src.api.s

# github ##########################################################
git add src/api/android_server.py
git commit -m "fix_1"
git push

## for production #################################################################
# 1 SubscriptionTestActivity
Change the Intent in ReliefChatActivity.kt line 72 from SubscriptionTestActivity to SubscriptionActivity
# 2 no reload
you can change it to in s.py
uvicorn.run("src.api.s:app", host="0.0.0.0", port=port, reload=False) 
# 3 unicorn
keep 1 unicorn in docker only
# 4 update DB_PATH in user_db.py
#local
DB_PATH = os.path.join(os.path.dirname(__file__), "user_data.db")
#render
DB_PATH = "/var/data/user_data.db"
# 5 remove add_middleware 
remove from s.py: add_middleware around line 134
# 6 Safe production preset
CHAT_HISTORY_WINDOW = 6
top_k = 2
Max prompt tokens: ≤ 1.5k
# 7 logger
logger.setLevel(logging.DEBUG)  # dev
logger.setLevel(logging.INFO)   # prod
# 8 update versionCode in app, build.gradle.kts
# 9 update backend path 

# update response time ############################################
.connectTimeout(30, TimeUnit.SECONDS)
.readTimeout(30, TimeUnit.SECONDS)
.writeTimeout(30, TimeUnit.SECONDS)
.callTimeout(40, TimeUnit.SECONDS)
.retryOnConnectionFailure(true)

# 🧪 Testing (fast feedback)
Connect: 5s – fail fast if backend down
Read: 20s – enough for LLM
Write: 10s
Call: 25s – hard stop
Retry: false – see errors immediately

# 🚀 Production (stable UX)
Connect: 10s – handle slow networks
Read: 30s – LLM + RAG
Write: 15s
Call: 40s – safe upper bound
Retry: true – auto recover once


# current versionCode = 21 ##########################################################
versionName = "sarvagya_1.4"

# privacy policy ######################################################
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


# tester ################################################################
sunny.kalgaon@gmail.com


# IP of local server ##########################################################
ipconfig

# backend run ##########################################################
cd backend
.\.venv\Scripts\python.exe -m uvicorn src.api.s:app --host 0.0.0.0 --port 8001 --reload

.\.venv\Scripts\python.exe -m uvicorn src.api.s:app --host 0.0.0.0 --port 8001


#github
git add src/api/android_server.py
git commit -m "fix_1"
git push

#
https://play.google.com/apps/testing/com.sarvagya.mentalhealthchat

#testers
ww
w

abc
a,b,c

# for production
1. subscriptionactivity
Change the Intent in ReliefChatActivity.kt line 72 from SubscriptionTestActivity to SubscriptionActivity
2. you can change it to in s.py
uvicorn.run("src.api.s:app", host="0.0.0.0", port=port, reload=False) 
3. keep 1 unicorn in docker only
4. Change path in db_congig.py
#local
DB_PATH = os.path.join(os.path.dirname(__file__), "user_data.db")
#render
DB_PATH = "/var/data/user_data.db"
5. for less servver downtime
Step 1 (what does NOT cost extra – detailed):
Using Gunicorn + Uvicorn workers
Adding a /health endpoint
Increasing timeouts
Loading models at startup
Better retry handling in Android
These are code/config changes only.
6. (check) uncomment assert DB_PATH in user_db.py at line 13

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
# llm response
career anxiety
sleep 
tell in short
list all messages

# remove db from render 
rm /var/data/user_data.db




# tst
# register
Email: appp
password : a

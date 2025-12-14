package com.sarvagya.mentalhealthchat.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.ImageButton
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.sarvagya.mentalhealthchat.R
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class ReliefChatActivity : AppCompatActivity() {

    private lateinit var chatBox: TextView
    private lateinit var inputBox: EditText
    private lateinit var sendBtn: Button
    private lateinit var scrollView: ScrollView
    private lateinit var subscribeBtn: Button
    private lateinit var chatsBtn: Button
    private lateinit var addChatsBtn: ImageButton
    private lateinit var chatHistorySpinner: Spinner
    
    // Store current remaining chats to pass to subscription screen
    private var currentRemainingChats: Int = -1
    
    // Store chat sessions for selection
    private var chatSessions: List<ChatSession> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_relief_chat)

        chatBox = findViewById(R.id.chatBox)
        inputBox = findViewById(R.id.inputBox)
        sendBtn = findViewById(R.id.sendBtn)
        scrollView = findViewById(R.id.chatScroll)
        subscribeBtn = findViewById(R.id.subscribeBtn)
        chatsBtn = findViewById(R.id.chatsBtn)
        addChatsBtn = findViewById(R.id.addChatsBtn)
        chatHistorySpinner = findViewById(R.id.chatHistorySpinner)

        val backBtn = findViewById<Button>(R.id.backBtn)
        backBtn.setOnClickListener { finish() }
        
        // Hide subscribe button initially
        subscribeBtn.visibility = View.GONE
        
        // Get email from shared preferences FIRST
        val email = getSharedPreferences("app", MODE_PRIVATE)
            .getString("email", null)

        if (email == null) {
            Toast.makeText(this, "No user email found!", Toast.LENGTH_SHORT).show()
            finish()
            return
        }
        
        subscribeBtn.setOnClickListener {
             openSubscription()
        }

        // Add listener for chats button - fetch real-time chats
        chatsBtn.setOnClickListener {
             fetchRealTimeChatsAndOpenSubscription(email)
        }
        
        // Add listener for Add Chats button
        addChatsBtn.setOnClickListener {
             fetchRealTimeChatsAndOpenSubscription(email)
        }

        // Initialize Chats button - will be updated by fetching user stats
        chatsBtn.text = "Chats: --"
        
        // Fetch initial remaining chats count
        fetchRemainingChats(email)

        // Load available chat history
        loadChatHistory(email)

        val api = RetrofitClient.instance

        sendBtn.setOnClickListener {
            val message = inputBox.text.toString().trim()
            if (message.isEmpty()) return@setOnClickListener

            chatBox.append("\nYou: $message\n")
            scrollView.post { scrollView.fullScroll(ScrollView.FOCUS_DOWN) }
            inputBox.setText("")

            val req = ChatRequest(email, message)

            api.chat(req).enqueue(object : Callback<ChatResponse> {
                override fun onResponse(
                    call: Call<ChatResponse>,
                    response: Response<ChatResponse>
                ) {
                    // Handle non-successful responses (like 429)
                    if (!response.isSuccessful) {
                        android.util.Log.d("ReliefChat", "❌ Response failed: ${response.code()}")
                        chatBox.append("\nBot: You've used all your chats. Buy more chats to feel better!\n")
                        
                        subscribeBtn.visibility = View.VISIBLE
                        chatsBtn.text = "Chats: 0"
                        
                        Toast.makeText(
                            this@ReliefChatActivity,
                            "No chats remaining. Please buy more!",
                            Toast.LENGTH_LONG
                        ).show()
                        
                        scrollView.post { scrollView.fullScroll(ScrollView.FOCUS_DOWN) }
                        return
                    }
                    
                    val res = response.body()
                    val reply = res?.reply
                    val error = res?.error
                    
                    // Check if backend explicitly blocked the request (limit reached)
                    if (res?.allowed == false || error != null) {
                        // User hit the limit
                        chatBox.append("\nBot: You've used all 5 free chats. Buy more chats to continue!\n")
                        
                        // Show Subscribe button
                        subscribeBtn.visibility = View.VISIBLE
                        chatsBtn.text = "Chats: 0"
                        
                        Toast.makeText(
                            this@ReliefChatActivity,
                            "Free limit reached. Buy more chats to continue.",
                            Toast.LENGTH_LONG
                        ).show()
                        
                        scrollView.post { scrollView.fullScroll(ScrollView.FOCUS_DOWN) }
                    } else if (reply != null) {
                        // Chat successful - update remaining count
                        android.util.Log.d("ReliefChat", "📊 Chat response - chats value: ${res?.chats}")
                        
                        val remainingChats = res?.chats ?: 0
                        chatsBtn.text = "Chats: $remainingChats"
                        android.util.Log.d("ReliefChat", "✅ Updated button to: Chats: $remainingChats")
                        
                        // Show purchase button if this was the last chat
                        if (remainingChats == 0) {
                            subscribeBtn.visibility = View.VISIBLE
                            Toast.makeText(
                                this@ReliefChatActivity,
                                "You've used all your chats! Buy more to feel better.",
                                Toast.LENGTH_LONG
                            ).show()
                        } else {
                            subscribeBtn.visibility = View.GONE
                        }
                        
                        chatBox.append("\nBot: $reply\n")
                        scrollView.post { scrollView.fullScroll(ScrollView.FOCUS_DOWN) }
                    }
                }

                override fun onFailure(call: Call<ChatResponse>, t: Throwable) {
                    chatBox.append("\n[Error: ${t.message}]\n")
                }
            })
        }
    }
    
    private fun fetchRealTimeChatsAndOpenSubscription(email: String) {
        val api = RetrofitClient.instance
        val req = UserChatsRequest(email)
        
        api.getUserChats(req).enqueue(object : Callback<ChatsResponse> {
            override fun onResponse(
                call: Call<ChatsResponse>,
                response: Response<ChatsResponse>
            ) {
                if (response.isSuccessful && response.body() != null) {
                    val realChats = response.body()!!.chats ?: 0
                    
                    // Update UI and cache
                    currentRemainingChats = realChats
                    chatsBtn.text = "Chats: $realChats"
                    
                    getSharedPreferences("app", MODE_PRIVATE)
                        .edit()
                        .putInt("chats", realChats)
                        .apply()
                    
                    // Open subscription with real chats
                    openSubscription()
                } else {
                    // Fallback to cached value
                    Toast.makeText(
                        this@ReliefChatActivity,
                        "Could not fetch latest chats",
                        Toast.LENGTH_SHORT
                    ).show()
                    openSubscription()
                }
            }
            
            override fun onFailure(call: Call<ChatsResponse>, t: Throwable) {
                // Fallback to cached value
                Toast.makeText(
                    this@ReliefChatActivity,
                    "Network error: ${t.message}",
                    Toast.LENGTH_SHORT
                ).show()
                openSubscription()
            }
        })
    }
    
    private fun openSubscription() {
        val intent = Intent(this, SubscriptionTestActivity::class.java)
      //  val intent = Intent(this, SubscriptionActivity::class.java)
        intent.putExtra("CHATS", currentRemainingChats)
        startActivity(intent)
    }
    
    override fun onResume() {
        super.onResume()
        
        // Reload remaining chats and chat history when returning to activity
        val email = getSharedPreferences("app", MODE_PRIVATE)
            .getString("email", null)
        if (email != null) {
            fetchRemainingChats(email)
            loadChatHistory(email)
        }
    }
    
    private fun fetchRemainingChats(email: String) {
        val api = RetrofitClient.instance
        
        // First check purchased chats
        api.getUserChats(UserChatsRequest(email)).enqueue(object : Callback<ChatsResponse> {
            override fun onResponse(
                call: Call<ChatsResponse>,
                response: Response<ChatsResponse>
            ) {
                if (response.isSuccessful && response.body() != null) {
                    val purchasedChats = response.body()!!.chats ?: 5
                    android.util.Log.d("ReliefChat", "📊 fetchRemainingChats response - chats: $purchasedChats")
                    chatsBtn.text = "Chats: $purchasedChats"
                } else {
                    // Default to 5 for new users
                    android.util.Log.d("ReliefChat", "⚠️ fetchRemainingChats failed, defaulting to 5")
                    chatsBtn.text = "Chats: 5"
                }
            }
            
            override fun onFailure(call: Call<ChatsResponse>, t: Throwable) {
                // Default to 5 chats for new users
                chatsBtn.text = "Chats: 5"
            }
        })
    }
    
    private fun loadChatHistory(email: String) {
        val api = RetrofitClient.instance
        val request = UserChatsRequest(email)
        
        api.getChatHistoryList(request).enqueue(object : Callback<ChatHistoryListResponse> {
            override fun onResponse(
                call: Call<ChatHistoryListResponse>,
                response: Response<ChatHistoryListResponse>
            ) {
                if (response.isSuccessful && response.body() != null) {
                    chatSessions = response.body()!!.chats
                    
                    // Populate Spinner with chat titles
                    val chatTitles = chatSessions.map { it.title }
                    val adapter = ArrayAdapter(
                        this@ReliefChatActivity,
                        android.R.layout.simple_spinner_item,
                        chatTitles
                    )
                    adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
                    chatHistorySpinner.adapter = adapter
                    
                    // Add listener to handle chat selection
                    chatHistorySpinner.onItemSelectedListener = object : android.widget.AdapterView.OnItemSelectedListener {
                        override fun onItemSelected(parent: android.widget.AdapterView<*>?, view: android.view.View?, position: Int, id: Long) {
                            if (position < chatSessions.size) {
                                val selectedChat = chatSessions[position]
                                // Load messages for this chat
                                loadChatMessages(email)
                            }
                        }
                        
                        override fun onNothingSelected(parent: android.widget.AdapterView<*>?) {
                            // Do nothing
                        }
                    }
                }
            }
            
            override fun onFailure(call: Call<ChatHistoryListResponse>, t: Throwable) {
                // Set default empty state
                val defaultChats = listOf("No chats available")
                val adapter = ArrayAdapter(
                    this@ReliefChatActivity,
                    android.R.layout.simple_spinner_item,
                    defaultChats
                )
                adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
                chatHistorySpinner.adapter = adapter
            }
        })
    }
    
    private fun loadChatMessages(email: String) {
        val api = RetrofitClient.instance
        val request = ChatHistoryMessagesRequest(email = email, limit = 10)
        
        api.getChatHistoryMessages(request).enqueue(object : Callback<ChatHistoryMessagesResponse> {
            override fun onResponse(
                call: Call<ChatHistoryMessagesResponse>,
                response: Response<ChatHistoryMessagesResponse>
            ) {
                if (response.isSuccessful && response.body() != null) {
                    val messagesResponse = response.body()!!
                    
                    // Clear chatbox and load all messages
                    chatBox.text = "Chat output will appear here\n"
                    
                    messagesResponse.messages.forEach { msg ->
                        if (msg.role == "user") {
                            chatBox.append("You: ${msg.content}\n")
                        } else {
                            chatBox.append("Bot: ${msg.content}\n")
                        }
                        chatBox.append("\n")
                    }
                    
                    // Scroll to bottom
                    scrollView.post { scrollView.fullScroll(ScrollView.FOCUS_DOWN) }
                    
                    Toast.makeText(
                        this@ReliefChatActivity,
                        "Loaded ${messagesResponse.count} messages",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }
            
            override fun onFailure(call: Call<ChatHistoryMessagesResponse>, t: Throwable) {
                Toast.makeText(
                    this@ReliefChatActivity,
                    "Failed to load messages: ${t.message}",
                    Toast.LENGTH_SHORT
                ).show()
            }
        })
    }
}

package com.sarvagya.mentalhealthchat.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
// ImageButton removed
import android.widget.ScrollView
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
    private lateinit var buy10Btn: Button
    private lateinit var chatsBtn: Button
    private lateinit var chatsHistoryBtn: Button
    private lateinit var closeHistoryBtn: Button
    
    // Store current remaining chats to pass to subscription screen
    private var currentRemainingChats: Int = -1
    
    // chat sessions removed — app now uses single/default session

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_relief_chat)

        chatBox = findViewById(R.id.chatBox)
        inputBox = findViewById(R.id.inputBox)
        sendBtn = findViewById(R.id.sendBtn)
        scrollView = findViewById(R.id.chatScroll)
        buy10Btn = findViewById(R.id.buy10Btn)
        chatsBtn = findViewById(R.id.chatsBtn)
        chatsHistoryBtn = findViewById(R.id.chatsHistoryBtn)
        closeHistoryBtn = findViewById(R.id.closeHistoryBtn)

        val backBtn = findViewById<Button>(R.id.backBtn)
        backBtn.setOnClickListener { finish() }
        buy10Btn.visibility = View.GONE

        // Get email from shared preferences FIRST
        val email = getSharedPreferences("app", MODE_PRIVATE)
            .getString("email", null)

        if (email == null) {
            Toast.makeText(this, "No user email found!", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        buy10Btn.setOnClickListener {
            openSubscription()
        }

        // Add listener for chats button - fetch real-time chats (shows count)
        chatsBtn.setOnClickListener {
            // Open the subscription screen directly (pass currentRemainingChats)
            openSubscription()
        }

        // Chats history button - show all sessions' messages
        chatsHistoryBtn.setOnClickListener {
            displayAllChats(email)
        }

        closeHistoryBtn.setOnClickListener {
            closeHistoryView()
        }

        // Add Chats button removed from UI

        // Initialize Chats button - will be updated by fetching user stats
        chatsBtn.text = "Chats: --"
        // Fetch initial remaining chats count
        fetchRemainingChats(email)

        // Chat sessions functionality removed; no history loading

        val api = RetrofitClient.instance

        sendBtn.setOnClickListener {
            val message = inputBox.text.toString().trim()
            if (message.isEmpty()) return@setOnClickListener

            chatBox.append("\nYou: $message\n")
            scrollView.post { scrollView.fullScroll(ScrollView.FOCUS_DOWN) }
            inputBox.setText("")

            val sessionId = "default"
            val req = ChatRequest(email, message, sessionId)

            api.chat(req).enqueue(object : Callback<ChatResponse> {
                override fun onResponse(
                    call: Call<ChatResponse>,
                    response: Response<ChatResponse>
                ) {
                    // Handle non-successful responses (like 429)
                    if (!response.isSuccessful) {
                        android.util.Log.d("ReliefChat", "❌ Response failed: ${response.code()}")
                        chatBox.append("\nBot: You've used all your chats. Buy more chats to feel better!\n")
                        
                        buy10Btn.visibility = View.VISIBLE
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
                        chatBox.append("\nBot: You've used all your free chats. Buy more chats to continue!\n")
                        
                        // Show Subscribe button
                        buy10Btn.visibility = View.VISIBLE
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
                            buy10Btn.visibility = View.VISIBLE
                            Toast.makeText(
                                this@ReliefChatActivity,
                                "You've used all your chats! Buy more to feel better.",
                                Toast.LENGTH_LONG
                            ).show()
                        } else {
                            buy10Btn.visibility = View.GONE
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

    private fun displayAllChats(email: String) {
        val api = RetrofitClient.instance

        // Clear existing chat box and show header
        // Disable input while viewing read-only history (hide input and send button)
        inputBox.isEnabled = false
        inputBox.visibility = View.GONE
        sendBtn.visibility = View.GONE
        // Hide other header buttons so only Close history remains
        chatsHistoryBtn.visibility = View.GONE
        chatsBtn.visibility = View.GONE
        buy10Btn.visibility = View.GONE
        try {
            findViewById<Button>(R.id.backBtn).visibility = View.GONE
        } catch (e: Exception) {
            // ignore if backBtn not present
        }
        closeHistoryBtn.visibility = View.VISIBLE

        chatBox.text = "Chat output will appear here\n\n"

        // First fetch list of sessions
        api.getChatHistoryList(UserChatsRequest(email)).enqueue(object : Callback<ChatHistoryListResponse> {
            override fun onResponse(
                call: Call<ChatHistoryListResponse>,
                response: Response<ChatHistoryListResponse>
            ) {
                if (response.isSuccessful && response.body() != null) {
                    val sessions = response.body()!!.chats
                    if (sessions.isEmpty()) {
                        chatBox.append("No chat sessions available\n")
                        return
                    }

                    // For each session, fetch messages
                    sessions.forEach { session ->
                        val request = ChatHistoryMessagesRequest(email = email, limit = 100, session_id = session.id.toString())
                        api.getChatHistoryMessages(request).enqueue(object : Callback<ChatHistoryMessagesResponse> {
                            override fun onResponse(
                                call: Call<ChatHistoryMessagesResponse>,
                                response: Response<ChatHistoryMessagesResponse>
                            ) {
                                if (response.isSuccessful && response.body() != null) {
                                    val messagesResponse = response.body()!!
                                    // Do not show session title headers in history list
                                    // Previously: chatBox.append("=== ${session.title} ===\n")
                                    messagesResponse.messages.forEach { msg ->
                                        if (msg.role == "user") {
                                            chatBox.append("You: ${msg.content}\n\n")
                                        } else if (msg.role == "assistant") {
                                            chatBox.append("Bot: ${msg.content}\n\n")
                                        }
                                    }
                                    scrollView.post { scrollView.fullScroll(ScrollView.FOCUS_DOWN) }
                                } else {
                                    chatBox.append("Failed to load messages for ${session.title}\n\n")
                                }
                            }

                            override fun onFailure(call: Call<ChatHistoryMessagesResponse>, t: Throwable) {
                                chatBox.append("Error loading ${session.title}: ${t.message}\n\n")
                            }
                        })
                    }
                } else {
                    chatBox.append("Could not fetch chat sessions\n")
                }
            }

            override fun onFailure(call: Call<ChatHistoryListResponse>, t: Throwable) {
                chatBox.append("Network error: ${t.message}\n")
            }
        })
    }
    
    private fun closeHistoryView() {
        inputBox.isEnabled = true
        inputBox.visibility = View.VISIBLE
        sendBtn.visibility = View.VISIBLE
        closeHistoryBtn.visibility = View.GONE
        // Restore header buttons
        chatsHistoryBtn.visibility = View.VISIBLE
        chatsBtn.visibility = View.VISIBLE
        // Show Subscribe button only if the user has zero remaining chats.
        var remaining = currentRemainingChats
        if (remaining < 0) {
            // fall back to cached value in shared prefs
            remaining = getSharedPreferences("app", MODE_PRIVATE).getInt("chats", 5)
        }
        buy10Btn.visibility = if (remaining <= 0) View.VISIBLE else View.GONE
        try {
            findViewById<Button>(R.id.backBtn).visibility = View.VISIBLE
        } catch (e: Exception) {
            // ignore
        }
        // Keep history visible; user can scroll back or send new messages
    }
    
    private fun openSubscription() {
                 val intent = Intent(this, SubscriptionTestActivity::class.java)
//                val intent = Intent(this, SubscriptionActivity::class.java)
                intent.putExtra("CHATS", currentRemainingChats)
                startActivity(intent)
    }
    
    override fun onResume() {
        super.onResume()
        
        // Reload remaining chats when returning to activity
        val email = getSharedPreferences("app", MODE_PRIVATE)
            .getString("email", null)
        if (email != null) {
            fetchRemainingChats(email)
        }
        // Always reload chat history after returning from subscription/purchase
        // This ensures new sessions are visible after buying chats
        // (If you want to be more specific, check an intent extra or flag)
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
                        currentRemainingChats = purchasedChats
                        // Update subscribe button visibility based on remaining chats
                        buy10Btn.visibility = if (purchasedChats <= 0) View.VISIBLE else View.GONE
                        // Cache value
                        getSharedPreferences("app", MODE_PRIVATE)
                            .edit()
                            .putInt("chats", purchasedChats)
                            .apply()
                } else {
                    // Default to 5 for new users
                    android.util.Log.d("ReliefChat", "⚠️ fetchRemainingChats failed, defaulting to 5")
                        val defaultChats = 5
                        chatsBtn.text = "Chats: $defaultChats"
                        currentRemainingChats = defaultChats
                        buy10Btn.visibility = View.GONE
                }
            }
            
            override fun onFailure(call: Call<ChatsResponse>, t: Throwable) {
                // Default to 5 chats for new users
                val defaultChats = 5
                chatsBtn.text = "Chats: $defaultChats"
                currentRemainingChats = defaultChats
                buy10Btn.visibility = View.GONE
            }
        })
    }
    
    // Chat history and sessions removed from app
    
    // Message history fetch removed

    
}

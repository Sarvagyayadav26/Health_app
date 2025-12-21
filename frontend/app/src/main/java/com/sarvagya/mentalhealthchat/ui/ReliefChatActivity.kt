//ss
package com.sarvagya.mentalhealthchat.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.*
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

    private var currentRemainingChats: Int = -1
    private var isSubscriptionOpen = false

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

        findViewById<Button>(R.id.backBtn).setOnClickListener { finish() }

        buy10Btn.visibility = View.GONE
        chatsBtn.text = "Chats: --"

        val email = getSharedPreferences("app", MODE_PRIVATE)
            .getString("email", null) ?: run {
            Toast.makeText(this, "No user email", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        buy10Btn.setOnClickListener {
            openSubscription()
        }

        chatsBtn.setOnClickListener {
            openSubscription()
        }

        chatsHistoryBtn.setOnClickListener {
            displayAllChats(email)
        }

        closeHistoryBtn.setOnClickListener {
            closeHistoryView()
        }

        fetchRemainingChats(email)

        sendBtn.setOnClickListener {
            val message = inputBox.text.toString().trim()
            if (message.isEmpty()) return@setOnClickListener

            chatBox.append("\nYou: $message\n")
            inputBox.setText("")
            scrollView.post { scrollView.fullScroll(ScrollView.FOCUS_DOWN) }

            RetrofitClient.instance
                .chat(ChatRequest(email, message, "default"))
                .enqueue(object : Callback<ChatResponse> {

                    override fun onResponse(
                        call: Call<ChatResponse>,
                        response: Response<ChatResponse>
                    ) {
                        val res = response.body()

                        if (!response.isSuccessful || res == null || res.allowed == false) {
                            chatBox.append("\nBot: No chats left. Buy more.\n")
                            buy10Btn.visibility = View.VISIBLE
                            fetchRemainingChats(email)
                            return
                        }

                        chatBox.append("\nBot: ${res.reply}\n")
                        currentRemainingChats = res.chats ?: 0
                        chatsBtn.text = "Chats: $currentRemainingChats"

                        buy10Btn.visibility =
                            if (currentRemainingChats <= 0) View.VISIBLE else View.GONE
                    }

                    override fun onFailure(call: Call<ChatResponse>, t: Throwable) {
                        chatBox.append("\nError: ${t.message}\n")
                    }
                })
        }
    }

    private fun openSubscription() {
        if (isSubscriptionOpen) return
        isSubscriptionOpen = true

        val prefs = getSharedPreferences("app", MODE_PRIVATE)
        val persisted = prefs.getInt("chats", -1)

        val chatsToSend =
            if (currentRemainingChats >= 0) currentRemainingChats
            else if (persisted >= 0) persisted
            else 0

        val intent = Intent(this, SubscriptionActivity::class.java)
        intent.putExtra("CHATS", chatsToSend)
        startActivity(intent)
    }

    // ✅ SINGLE, CORRECT onResume
    override fun onResume() {
        super.onResume()
        isSubscriptionOpen = false

        val email = getSharedPreferences("app", MODE_PRIVATE)
            .getString("email", null)

        if (email != null) {
            fetchRemainingChats(email)
        }
    }

    private fun fetchRemainingChats(email: String) {
        RetrofitClient.instance
            .getUserChats(UserChatsRequest(email))
            .enqueue(object : Callback<ChatsResponse> {

                override fun onResponse(
                    call: Call<ChatsResponse>,
                    response: Response<ChatsResponse>
                ) {
                    val chats = response.body()?.chats ?: 0
                    currentRemainingChats = chats
                    chatsBtn.text = "Chats: $chats"

                    buy10Btn.visibility =
                        if (chats <= 0) View.VISIBLE else View.GONE

                    getSharedPreferences("app", MODE_PRIVATE)
                        .edit()
                        .putInt("chats", chats)
                        .apply()
                }

                override fun onFailure(call: Call<ChatsResponse>, t: Throwable) {
                    currentRemainingChats = 0
                    chatsBtn.text = "Chats: --"
                    buy10Btn.visibility = View.GONE
                }
            })
    }

    private fun displayAllChats(email: String) {
        // Use Retrofit (centralized BASE_URL) to fetch messages and open history
        val req = ChatHistoryMessagesRequest(email = email, limit = 200, session_id = "1")
        RetrofitClient.instance.getChatHistoryMessages(req)
            .enqueue(object : Callback<ChatHistoryMessagesResponse> {
                override fun onResponse(
                    call: Call<ChatHistoryMessagesResponse>,
                    response: Response<ChatHistoryMessagesResponse>
                ) {
                    val msgs = response.body()?.messages
                    val serializableList = ArrayList<java.util.HashMap<String, String>>()
                    if (msgs != null && msgs.isNotEmpty()) {
                        for (m in msgs) {
                            val map = java.util.HashMap<String, String>()
                            map["role"] = m.role ?: ""
                            map["content"] = m.content ?: ""
                            map["timestamp"] = m.timestamp ?: ""
                            serializableList.add(map)
                        }
                    }

                    runOnUiThread {
                        val intent = Intent(this@ReliefChatActivity, ChatHistoryActivity::class.java)
                        intent.putExtra("MESSAGES", serializableList as java.io.Serializable)
                        startActivity(intent)
                    }
                }

                override fun onFailure(call: Call<ChatHistoryMessagesResponse>, t: Throwable) {
                    runOnUiThread {
                        Toast.makeText(this@ReliefChatActivity, "History load failed", Toast.LENGTH_SHORT).show()
                    }
                }
            })
    }

    private fun closeHistoryView() {
        // no-op (kept for compatibility)
    }
}

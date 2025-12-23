package com.sarvagya.mentalhealthchat.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import com.sarvagya.mentalhealthchat.R
import androidx.core.content.ContextCompat
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

        // ✅ Default greeting (frontend-only, no backend call) sss
        chatBox.text = "Bot: Hi 🙂 I’m here with you. What’s been on your mind lately?"

        findViewById<Button>(R.id.backBtn).setOnClickListener { finish() }

        buy10Btn.visibility = View.GONE
        chatsBtn.text = "Chats: --"

        val email = getSharedPreferences("app", MODE_PRIVATE)
            .getString("email", null) ?: run {
            Toast.makeText(this, "No user email", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        buy10Btn.setOnClickListener { openSubscription() }
        chatsBtn.setOnClickListener { openSubscription() }
        chatsHistoryBtn.setOnClickListener { displayAllChats(email) }
        closeHistoryBtn.setOnClickListener { }

        fetchRemainingChats(email)

        sendBtn.setOnClickListener {
            val message = inputBox.text.toString().trim()
            if (message.isEmpty()) return@setOnClickListener

            chatBox.append("\n\nYou: $message")
            inputBox.setText("")
            scrollView.post { scrollView.fullScroll(ScrollView.FOCUS_DOWN) }

            RetrofitClient.instance
                .chat(ChatRequest(email, message))
                .enqueue(object : Callback<ChatResponse> {

                    override fun onResponse(
                        call: Call<ChatResponse>,
                        response: Response<ChatResponse>
                    ) {
                        val res = response.body()

                        if (!response.isSuccessful || res == null || res.allowed == false) {
                            chatBox.append("\n\nBot: No chats left. Buy more.")
                            buy10Btn.visibility = View.VISIBLE
                            fetchRemainingChats(email)
                            return
                        }

                        chatBox.append("\n\nBot: ${res.reply}")

                        // ✅ SHOW TOPIC BUTTONS WHEN BACKEND ASKS
                        if (res.show_topics == true && !res.topics.isNullOrEmpty()) {
                            showTopicButtons(res.topics, email)
                        }

                        currentRemainingChats = res.chats ?: 0
                        chatsBtn.text = "Chats: $currentRemainingChats"
                        buy10Btn.visibility =
                            if (currentRemainingChats <= 0) View.VISIBLE else View.GONE
                    }

                    override fun onFailure(call: Call<ChatResponse>, t: Throwable) {
                        chatBox.append("\n\nBot: Service unavailable. Please try later.")
                    }
                })
        }
    }

    // --------------------------------------------------
    // ✅ TOPIC BUTTONS (UNCLEAR ISSUE HANDLING)
    // --------------------------------------------------
    private fun showTopicButtons(topics: List<String>, email: String) {
        // Create a vertical container for topic chips so they appear stacked on screen
        val chipContainer = LinearLayout(this)
        chipContainer.orientation = LinearLayout.VERTICAL
        chipContainer.setPadding(8, 8, 8, 8)

        val containerParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        )
        containerParams.setMargins(12, 8, 12, 8)
        chipContainer.layoutParams = containerParams

        // Add a cancel button so users can dismiss topic chips and return to normal chat
        val cancelBtn = com.google.android.material.button.MaterialButton(this)
        cancelBtn.text = "Cancel"
        val cancelParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        )
        cancelParams.setMargins(12, 6, 12, 6)
        cancelBtn.layoutParams = cancelParams
        cancelBtn.setOnClickListener {
            (chipContainer.parent as? ViewGroup)?.removeView(chipContainer)
        }
        chipContainer.addView(cancelBtn)

        for (topic in topics) {
            val chip = Button(this)
            chip.text = topic
            chip.textSize = 13f
            chip.setPadding(24, 12, 24, 12)
            chip.setBackgroundResource(R.drawable.topic_chip_bg)
            // Ensure chip text is readable on the topic background
            chip.setTextColor(ContextCompat.getColor(this, R.color.textDark))
            chip.isAllCaps = false

            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
            params.setMargins(12, 8, 12, 8)
            chip.layoutParams = params

            chip.setOnClickListener {
                val topicMessage = "__TOPIC_SELECTED__:$topic"

                chatBox.append("\n\nYou: $topic")
                sendTopicToBackend(email, topicMessage)

                // remove the vertical chips container after selection
                (chipContainer.parent as? ViewGroup)?.removeView(chipContainer)
            }

            chipContainer.addView(chip)
        }

        // Add the vertical stack into the chat content so it appears lower
        // (inside the ScrollView content, after existing messages)
        val chatContainer = findViewById<LinearLayout>(R.id.chatContainer)
        chatContainer.addView(chipContainer)

        // Also remove chips if user taps into the input box to type
        inputBox.setOnTouchListener { _, _ ->
            (chipContainer.parent as? ViewGroup)?.removeView(chipContainer)
            // allow normal processing of the touch
            false
        }

        // Scroll down so the newly added chips are visible
        scrollView.post { scrollView.fullScroll(ScrollView.FOCUS_DOWN) }
    }

    private fun sendTopicToBackend(email: String, message: String) {
        RetrofitClient.instance
            .chat(ChatRequest(email, message))
            .enqueue(object : Callback<ChatResponse> {

                override fun onResponse(
                    call: Call<ChatResponse>,
                    response: Response<ChatResponse>
                ) {
                    val res = response.body() ?: return
                    chatBox.append("\n\nBot: ${res.reply}")
                }

                override fun onFailure(call: Call<ChatResponse>, t: Throwable) {
                    chatBox.append("\n\nBot: Something went wrong. Try again.")
                }
            })
    }

    // --------------------------------------------------
    // ✅ EXISTING CODE (UNCHANGED)
    // --------------------------------------------------
    private fun openSubscription() {
        if (isSubscriptionOpen) return
        isSubscriptionOpen = true

        // Do not pass a potentially stale `CHATS` extra; SubscriptionActivity
        // will fetch the authoritative remaining chats from the backend on resume.
        val intent = Intent(this, SubscriptionActivity::class.java)
        startActivity(intent)
    }

    override fun onResume() {
        super.onResume()
        isSubscriptionOpen = false
        getSharedPreferences("app", MODE_PRIVATE)
            .getString("email", null)
            ?.let { fetchRemainingChats(it) }
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
                    buy10Btn.visibility = if (chats <= 0) View.VISIBLE else View.GONE
                }

                override fun onFailure(call: Call<ChatsResponse>, t: Throwable) {
                    chatsBtn.text = "Chats: --"
                }
            })
    }

    private fun displayAllChats(email: String) {
        val req = ChatHistoryMessagesRequest(email, limit = 200, session_id = "1")
        RetrofitClient.instance.getChatHistoryMessages(req)
            .enqueue(object : Callback<ChatHistoryMessagesResponse> {
                override fun onResponse(
                    call: Call<ChatHistoryMessagesResponse>,
                    response: Response<ChatHistoryMessagesResponse>
                ) {
                    val msgs = response.body()?.messages ?: return
                    val list = ArrayList<HashMap<String, String>>()
                    for (m in msgs) {
                        val map = HashMap<String, String>()
                        map["role"] = m.role ?: ""
                        map["content"] = m.content ?: ""
                        map["timestamp"] = m.timestamp ?: ""
                        list.add(map)
                    }
                    startActivity(
                        Intent(this@ReliefChatActivity, ChatHistoryActivity::class.java)
                            .putExtra("MESSAGES", list)
                    )
                }

                override fun onFailure(call: Call<ChatHistoryMessagesResponse>, t: Throwable) {
                    Toast.makeText(this@ReliefChatActivity, "History load failed", Toast.LENGTH_SHORT).show()
                }
            })
    }
}

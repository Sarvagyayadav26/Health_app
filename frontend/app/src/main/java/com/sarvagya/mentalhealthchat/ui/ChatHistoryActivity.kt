package com.sarvagya.mentalhealthchat.ui

import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.sarvagya.mentalhealthchat.R

class ChatHistoryActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_chat_history)

        findViewById<Button>(R.id.backBtn).setOnClickListener { finish() }

        val recycler = findViewById<RecyclerView>(R.id.historyRecycler)
        recycler.layoutManager = LinearLayoutManager(this)

        val serial = intent.getSerializableExtra("MESSAGES")
        val items = ArrayList<LocalChatMessage>()
        if (serial is ArrayList<*>) {
            for (o in serial) {
                if (o is java.util.HashMap<*, *>) {
                    val role = o["role"] as? String ?: ""
                    val content = o["content"] as? String ?: ""
                    val timestamp = o["timestamp"] as? String ?: ""
                    items.add(LocalChatMessage(role, content, timestamp))
                }
            }
        }

        val adapter = ChatHistoryAdapter(items)
        recycler.adapter = adapter

        val emptyText = findViewById<TextView>(R.id.emptyText)
        if (items.isEmpty()) {
            emptyText.visibility = View.VISIBLE
            recycler.visibility = View.GONE
        } else {
            emptyText.visibility = View.GONE
            recycler.visibility = View.VISIBLE
        }

        // Delete history button: hide history on the backend (UI-only) and clear UI
        val deleteBtn = findViewById<Button>(R.id.deleteHistoryBtn)
        deleteBtn.setOnClickListener {
            val prefs = getSharedPreferences("app", MODE_PRIVATE)
            val email = prefs.getString("email", null)
            if (email == null) {
                android.widget.Toast.makeText(this, "No user email", android.widget.Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            // Call hide API
            RetrofitClient.instance.hideHistory(UserChatsRequest(email))
                .enqueue(object : retrofit2.Callback<BasicResponse> {
                    override fun onResponse(call: retrofit2.Call<BasicResponse>, response: retrofit2.Response<BasicResponse>) {
                        // Clear UI only
                        adapter.clearAll()
                        emptyText.visibility = View.VISIBLE
                        recycler.visibility = View.GONE
                        android.widget.Toast.makeText(this@ChatHistoryActivity, "History deleted", android.widget.Toast.LENGTH_SHORT).show()
                    }

                    override fun onFailure(call: retrofit2.Call<BasicResponse>, t: Throwable) {
                        android.widget.Toast.makeText(this@ChatHistoryActivity, "Failed to hide history", android.widget.Toast.LENGTH_SHORT).show()
                    }
                })
        }
    }
}

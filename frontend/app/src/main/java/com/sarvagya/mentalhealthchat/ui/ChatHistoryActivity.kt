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
    }
}

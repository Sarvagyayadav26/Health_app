package com.sarvagya.mentalhealthchat.ui

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.sarvagya.mentalhealthchat.R

class ArticleDetailActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_article_detail)

        val title = intent.getStringExtra("title") ?: "No Title"
        val content = intent.getStringExtra("content") ?: "No Content"

        findViewById<TextView>(R.id.tvTitle).text = title
        findViewById<TextView>(R.id.tvContent).text = content
        
        findViewById<Button>(R.id.btnBack).setOnClickListener {
            finish()
        }
    }
}
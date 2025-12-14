package com.sarvagya.mentalhealthchat.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import androidx.appcompat.app.AppCompatActivity
import com.sarvagya.mentalhealthchat.R

class MentalHealthTopicsActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_mental_health_topics)

        val backBtn = findViewById<Button>(R.id.btnBack)
        backBtn.setOnClickListener {
            finish()
        }

        setupButton(R.id.btnAnxiety, "Anxiety Management Tips", 
            "1. Practice deep breathing.\n2. Limit caffeine intake.\n3. Maintain a regular sleep schedule.\n4. Challenge negative thoughts.\n5. Stay active.")
            
        setupButton(R.id.btnDepression, "Coping with Depression",
            "1. Reach out to friends or family.\n2. Set small, manageable goals.\n3. Engage in activities you used to enjoy.\n4. Exercise regularly.\n5. Avoid alcohol and drugs.")
            
        setupButton(R.id.btnStress, "Stress Relief Tips",
            "1. Take breaks often.\n2. Connect with others.\n3. Eat healthy meals.\n4. Get plenty of sleep.\n5. Recognize when you need more help.")
            
        setupButton(R.id.btnPanic, "Handling Panic Attacks",
            "1. Use deep breathing.\n2. Recognize that you are having a panic attack.\n3. Close your eyes.\n4. Practice mindfulness.\n5. Focus on an object.")
    }

    private fun setupButton(btnId: Int, title: String, content: String) {
        findViewById<Button>(btnId).setOnClickListener {
            val intent = Intent(this, ArticleDetailActivity::class.java)
            intent.putExtra("title", title)
            intent.putExtra("content", content)
            startActivity(intent)
        }
    }
}
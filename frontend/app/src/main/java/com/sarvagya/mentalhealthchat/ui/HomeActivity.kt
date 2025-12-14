package com.sarvagya.mentalhealthchat.ui

import android.content.Intent
import android.os.Bundle
import android.view.HapticFeedbackConstants
import android.view.View
import android.view.animation.DecelerateInterpolator
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.sarvagya.mentalhealthchat.R
import java.util.Calendar

class HomeActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_home)

        // Find Views
        val calmSpaceCard = findViewById<View>(R.id.calmSpaceCard)
        val reliefChatCard = findViewById<View>(R.id.reliefChatCard)
        val miniGameCard = findViewById<View>(R.id.miniGameCard)
        val articleCard = findViewById<View>(R.id.articleCard)
        val logoutBtn = findViewById<Button>(R.id.logoutBtn)
        val welcomeText = findViewById<TextView>(R.id.welcomeText)
        val subText = findViewById<TextView>(R.id.subText)

        // ✅ Personalization: Set Greeting & Daily Goal
        val prefs = getSharedPreferences("app", MODE_PRIVATE)
        val name = prefs.getString("username", "Friend") ?: "Friend"
        
        welcomeText.text = "Hi $name \uD83D\uDC4B\nHope you're doing well." // Waving hand emoji

        // Random Daily Goal
        val goals = listOf(
            "Be kinder to yourself today.",
            "Take 5 deep breaths if you feel stressed.",
            "Write down one thing you are grateful for.",
            "Step outside and look at the sky for a minute.",
            "Drink a glass of water and stretch.",
            "It’s okay to take a break today."
        )
        // Use day of year to pick a goal so it stays same for the day
        val dayOfYear = Calendar.getInstance().get(Calendar.DAY_OF_YEAR)
        val goal = goals[dayOfYear % goals.size]
        subText.text = "Daily Goal: $goal"


        // ✅ Fade-In Animation on Start
        animateEntry(calmSpaceCard, 100)
        animateEntry(reliefChatCard, 200)
        animateEntry(miniGameCard, 300)
        animateEntry(articleCard, 400)
        animateEntry(logoutBtn, 500)

        // Calm Space Card (New)
        calmSpaceCard.setOnClickListener { view ->
            performHaptic(view)
            startActivity(Intent(this, CalmSpaceActivity::class.java))
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        }

        // Relief Chat Card
        reliefChatCard.setOnClickListener { view ->
            performHaptic(view)
            startActivity(Intent(this, ReliefChatActivity::class.java))
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        }

        // Mini Game Card
        miniGameCard.setOnClickListener { view ->
            performHaptic(view)
            startActivity(Intent(this, BubbleGameActivity::class.java))
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        }

        // Mental Health Articles Card
        articleCard.setOnClickListener { view ->
            performHaptic(view)
            startActivity(Intent(this, MentalHealthTopicsActivity::class.java))
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        }

        // Logout Button
        logoutBtn.setOnClickListener { view ->
            performHaptic(view)
            
            // Clear ALL stored login data
            val prefs = getSharedPreferences("app", MODE_PRIVATE)
            prefs.edit().clear().apply()

            // Start LoginActivity and clear activity history
            val intent = Intent(this, LoginActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            startActivity(intent)
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)

            finish()
        }
    }

    // Helper for Smooth Fade-In + Slide-Up Animation
    private fun animateEntry(view: View, delay: Long) {
        view.alpha = 0f
        view.translationY = 50f
        view.animate()
            .alpha(1f)
            .translationY(0f)
            .setDuration(500)
            .setStartDelay(delay)
            .setInterpolator(DecelerateInterpolator())
            .start()
    }

    // Helper for Tiny Vibration (Haptic Feedback)
    private fun performHaptic(view: View) {
        view.performHapticFeedback(HapticFeedbackConstants.CONTEXT_CLICK)
    }
}

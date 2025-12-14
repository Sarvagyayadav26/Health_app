package com.sarvagya.mentalhealthchat.ui

import android.animation.Animator
import android.animation.AnimatorListenerAdapter
import android.animation.ValueAnimator
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.animation.AccelerateDecelerateInterpolator
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.sarvagya.mentalhealthchat.R

class CalmSpaceActivity : AppCompatActivity() {

    private lateinit var breathingCircleOuter: View
    private lateinit var breathingCircleInner: View
    private lateinit var breathInstruction: TextView
    private lateinit var quoteText: TextView
    private lateinit var closeBtn: Button
    
    private var breathAnimator: ValueAnimator? = null
    private val handler = Handler(Looper.getMainLooper())
    private var isBreathing = true

    private val quotes = listOf(
        "\"Peace comes from within. Do not seek it without.\"",
        "\"Breath is the bridge which connects life to consciousness.\"",
        "\"Feelings come and go like clouds in a windy sky. Conscious breathing is my anchor.\"",
        "\"You are enough just as you are.\"",
        "\"Inhale the future, exhale the past.\"",
        "\"This too shall pass.\""
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_calm_space)

        breathingCircleOuter = findViewById(R.id.breathingCircleOuter)
        breathingCircleInner = findViewById(R.id.breathingCircleInner)
        breathInstruction = findViewById(R.id.breathInstruction)
        quoteText = findViewById(R.id.quoteText)
        closeBtn = findViewById(R.id.closeBtn)

        // Set random quote
        quoteText.text = quotes.random()

        closeBtn.setOnClickListener {
            finish()
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        }

        startBreathingAnimation()
    }

    private fun startBreathingAnimation() {
        // 4 seconds Inhale, 4 seconds Exhale = 8 seconds total cycle
        breathAnimator = ValueAnimator.ofFloat(1f, 1.5f)
        breathAnimator?.duration = 4000
        breathAnimator?.repeatCount = ValueAnimator.INFINITE
        breathAnimator?.repeatMode = ValueAnimator.REVERSE
        breathAnimator?.interpolator = AccelerateDecelerateInterpolator()

        breathAnimator?.addUpdateListener { animation ->
            val scale = animation.animatedValue as Float
            breathingCircleOuter.scaleX = scale
            breathingCircleOuter.scaleY = scale
            
            // Inner circle moves slightly less for parallax effect
            val innerScale = 1f + (scale - 1f) * 0.5f
            breathingCircleInner.scaleX = innerScale
            breathingCircleInner.scaleY = innerScale
        }

        breathAnimator?.addListener(object : AnimatorListenerAdapter() {
            override fun onAnimationRepeat(animation: Animator) {
                // Check if we are expanding or contracting based on current fraction or handle logic
                // Actually simpler: toggle text based on a separate runnable or check phase
            }
        })

        breathAnimator?.start()
        
        // Sync text with animation loop
        runTextLoop()
    }

    private fun runTextLoop() {
        if (!isBreathing) return
        
        breathInstruction.text = "Inhale..."
        
        // Switch to Exhale after 4 seconds
        handler.postDelayed({
            if (isBreathing) breathInstruction.text = "Exhale..."
        }, 4000)
        
        // Loop again after 8 seconds
        handler.postDelayed({
            if (isBreathing) runTextLoop()
        }, 8000)
    }

    override fun onDestroy() {
        super.onDestroy()
        isBreathing = false
        breathAnimator?.cancel()
        handler.removeCallbacksAndMessages(null)
    }
}

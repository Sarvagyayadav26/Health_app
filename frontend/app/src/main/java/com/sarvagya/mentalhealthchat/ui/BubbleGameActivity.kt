package com.sarvagya.mentalhealthchat.ui

import android.animation.Animator
import android.animation.AnimatorListenerAdapter
import android.animation.ObjectAnimator
import android.content.Context
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.view.animation.LinearInterpolator
import android.widget.Button
import android.widget.FrameLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.sarvagya.mentalhealthchat.R
import java.util.Collections
import java.util.Random

class BubbleGameActivity : AppCompatActivity() {

    private lateinit var gameContainer: FrameLayout
    private lateinit var scoreText: TextView
    private lateinit var statsText: TextView
    private lateinit var pauseStatsText: TextView
    private lateinit var topLine: View
    private lateinit var bottomLine: View
    private lateinit var pauseOverlay: FrameLayout
    private lateinit var pauseBtn: Button
    private lateinit var resumeBtn: Button
    
    private val handler = Handler(Looper.getMainLooper())
    private var score = 0
    private var isPlaying = false
    private var isPaused = false
    private val random = Random()

    // Includes duplicates to increase frequency of certain items as requested
    private val bubbleLabels = listOf(
        "Caring Others", "Caring Self", "Healing Self", "Nourishing Body",
        "Nourishing Mind", "Helping Family", "Growing Spiritually", "Having Fun",
        "Caring Others", "Caring Self", "Healing Self", "Nourishing Body",
        "Nourishing Mind", "Helping Family", "Growing Spiritually", "Having Fun",
        "Strengthening Relationships", "Building Discipline", "Managing Emotions",
        "Improving Sleep", "Growing Financially", "Creating Balance",
        "Learning Daily", "Staying Present", "Connecting Deeply"
    )

    private val bubbleCounts = mutableMapOf<String, Int>()
    // Keep track of active animators to pause/resume them
    private val activeAnimators = Collections.synchronizedList(mutableListOf<Animator>())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_bubble_game)

        gameContainer = findViewById(R.id.gameContainer)
        scoreText = findViewById(R.id.scoreText)
        statsText = findViewById(R.id.statsText)
        pauseStatsText = findViewById(R.id.pauseStatsText)
        topLine = findViewById(R.id.topLine)
        bottomLine = findViewById(R.id.bottomLine)
        pauseOverlay = findViewById(R.id.pauseOverlay)
        pauseBtn = findViewById(R.id.pauseBtn)
        resumeBtn = findViewById(R.id.resumeBtn)
        val backBtn = findViewById<Button>(R.id.backBtn)

        // Load saved score
        val prefs = getSharedPreferences("game_prefs", Context.MODE_PRIVATE)
        score = prefs.getInt("high_score", 0)
        
        // Load bubble counts
        bubbleLabels.distinct().forEach { label ->
            val count = prefs.getInt("bubble_count_$label", 0)
            bubbleCounts[label] = count
        }
        
        updateScore()
        updateLiveStats()

        backBtn.setOnClickListener {
            finish()
        }

        pauseBtn.setOnClickListener {
            pauseGame()
        }

        resumeBtn.setOnClickListener {
            resumeGame()
        }
    }

    override fun onResume() {
        super.onResume()
        if (!isPaused && !isPlaying) {
            isPlaying = true
            startGameLoop()
        }
    }

    override fun onPause() {
        super.onPause()
        isPlaying = false
        handler.removeCallbacksAndMessages(null)
    }

    private fun updateScore() {
        scoreText.text = "Score: $score"
        getSharedPreferences("game_prefs", Context.MODE_PRIVATE)
            .edit()
            .putInt("high_score", score)
            .apply()
    }
    
    private fun updateLiveStats() {
        val total = bubbleCounts.values.sum()
        if (total == 0) {
            statsText.text = "Start popping bubbles!"
            return
        }

        val sb = StringBuilder()
        // Show top 3 or all? Let's show all horizontally.
        bubbleCounts.entries.sortedByDescending { it.value }.forEach { entry ->
            if (entry.value > 0) {
                val percentage = (entry.value.toFloat() / total.toFloat()) * 100
                sb.append("${entry.key}: ${"%.1f".format(percentage)}%   ")
            }
        }
        statsText.text = sb.toString()
    }

    private fun saveBubbleCount(label: String) {
        val currentCount = bubbleCounts.getOrDefault(label, 0) + 1
        bubbleCounts[label] = currentCount
        
        getSharedPreferences("game_prefs", Context.MODE_PRIVATE)
            .edit()
            .putInt("bubble_count_$label", currentCount)
            .apply()
            
        updateLiveStats()
    }

    private fun pauseGame() {
        isPaused = true
        pauseOverlay.visibility = View.VISIBLE
        handler.removeCallbacksAndMessages(null) // Stop generating new bubbles

        // Pause all active animations and hide bubbles
        // Create a copy to avoid ConcurrentModificationException
        val animatorsCopy = synchronized(activeAnimators) {
             ArrayList(activeAnimators)
        }
        animatorsCopy.forEach { animator -> 
            animator.pause()
            if (animator is ObjectAnimator) {
                (animator.target as? View)?.visibility = View.INVISIBLE
            }
        }

        // Show stats
        val sb = StringBuilder()
        val sorted = bubbleCounts.entries.sortedByDescending { it.value }
        val total = bubbleCounts.values.sum()
        
        sorted.forEach { entry ->
            if (entry.value > 0) {
                val percentage = if (total > 0) (entry.value.toFloat() / total.toFloat()) * 100 else 0f
                sb.append("${entry.key}: ${"%.1f".format(percentage)}%\n")
            }
        }
        if (sb.isEmpty()) sb.append("No data yet.")
        pauseStatsText.text = sb.toString()
    }

    private fun resumeGame() {
        isPaused = false
        pauseOverlay.visibility = View.GONE
        
        // Resume animations and show bubbles
        // Create a copy just in case
        val animatorsCopy = synchronized(activeAnimators) {
             ArrayList(activeAnimators)
        }
        animatorsCopy.forEach { animator ->
            animator.resume()
            if (animator is ObjectAnimator) {
                (animator.target as? View)?.visibility = View.VISIBLE
            }
        }
        
        startGameLoop()
    }

    private fun startGameLoop() {
        if (!isPlaying || isPaused) return

        // Create a bubble every 800ms
        handler.postDelayed({
            if (isPlaying && !isPaused) {
                createBubble()
                startGameLoop()
            }
        }, 800)
    }

    private fun createBubble() {
        if (!isPlaying || isPaused) return

        try {
            val bubble = TextView(this)
            val label = bubbleLabels[random.nextInt(bubbleLabels.size)]
            bubble.text = label
            bubble.gravity = Gravity.CENTER
            bubble.setTextColor(Color.WHITE) 
            bubble.textSize = 14f 
            bubble.textAlignment = View.TEXT_ALIGNMENT_CENTER
            bubble.setPadding(10, 0, 10, 0)
            
            // Make it a horizontal oval
            val width = 350
            val height = 180
            
            // Use ContextCompat to avoid crash on older APIs
            bubble.background = ContextCompat.getDrawable(this, R.drawable.bubble_shape)
            
            val params = FrameLayout.LayoutParams(width, height)
            
            val screenWidth = resources.displayMetrics.widthPixels
            params.leftMargin = random.nextInt(screenWidth - width)
            
            val startFromTop = random.nextBoolean()
            
            val startY = if (startFromTop) -height.toFloat() else resources.displayMetrics.heightPixels.toFloat()
            val endY = if (startFromTop) resources.displayMetrics.heightPixels.toFloat() else -height.toFloat()

            bubble.layoutParams = params
            bubble.translationY = startY
            
            gameContainer.addView(bubble)

            val duration = 8000L
            val animator = ObjectAnimator.ofFloat(bubble, "translationY", startY, endY)
            animator.duration = duration
            animator.interpolator = LinearInterpolator()
            
            animator.addListener(object : AnimatorListenerAdapter() {
                override fun onAnimationEnd(animation: Animator) {
                    gameContainer.removeView(bubble)
                    activeAnimators.remove(animation)
                }
                override fun onAnimationStart(animation: Animator) {
                    activeAnimators.add(animation)
                }
            })

            animator.start()

            // Click Listener
            bubble.setOnClickListener {
                if (isBubbleInZone(bubble) && !isPaused) {
                    score++
                    updateScore()
                    saveBubbleCount(label)
                    
                    // Visual feedback instead of removing
                    bubble.animate()
                        .scaleX(1.1f)
                        .scaleY(1.1f)
                        .setDuration(100)
                        .withEndAction {
                            bubble.animate().scaleX(1f).scaleY(1f).setDuration(100).start()
                        }
                        .start()
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun isBubbleInZone(bubble: View): Boolean {
        val bubbleLoc = IntArray(2)
        bubble.getLocationOnScreen(bubbleLoc)
        val bubbleCenterY = bubbleLoc[1] + (bubble.height / 2)

        val topLoc = IntArray(2)
        topLine.getLocationOnScreen(topLoc)
        val topY = topLoc[1]

        val bottomLoc = IntArray(2)
        bottomLine.getLocationOnScreen(bottomLoc)
        val bottomY = bottomLoc[1]

        return bubbleCenterY > topY && bubbleCenterY < bottomY
    }

    override fun onDestroy() {
        super.onDestroy()
        isPlaying = false
        handler.removeCallbacksAndMessages(null)
        
        // Prevent ConcurrentModificationException by iterating a copy
        val animatorsCopy = synchronized(activeAnimators) {
             ArrayList(activeAnimators)
        }
        animatorsCopy.forEach { it.cancel() }
    }
}

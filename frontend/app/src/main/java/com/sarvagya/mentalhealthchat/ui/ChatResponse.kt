package com.sarvagya.mentalhealthchat.ui

data class ChatResponse(
    val allowed: Boolean?,  // Nullable - testing mode doesn't return this
    val reply: String?,
    val usage_now: Int?,
    val limit: Any?,  // Can be Int or "unlimited" string
    val chats: Int?,
    val processing_time: Double?,
    val error: String?,
    val show_topics: Boolean?,
    val topics: List<String>?
)

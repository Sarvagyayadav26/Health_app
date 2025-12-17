package com.sarvagya.mentalhealthchat.ui

data class ChatRequest(
    val email: String,
    val message: String,
    val session_id: String
)

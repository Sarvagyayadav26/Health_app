package com.sarvagya.mentalhealthchat.ui

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.sarvagya.mentalhealthchat.R

data class LocalChatMessage(
    val role: String,
    val content: String,
    val timestamp: String
)

class ChatHistoryAdapter(private val items: List<LocalChatMessage>) :
    RecyclerView.Adapter<ChatHistoryAdapter.VH>() {

    class VH(view: View) : RecyclerView.ViewHolder(view) {
        val roleText: TextView = view.findViewById(R.id.roleText)
        val contentText: TextView = view.findViewById(R.id.contentText)
        val timestampText: TextView = view.findViewById(R.id.timestampText)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val v = LayoutInflater.from(parent.context).inflate(R.layout.item_chat_message, parent, false)
        return VH(v)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val it = items[position]
        holder.roleText.text = when (it.role) {
            "user" -> "You"
            "assistant" -> "Bot"
            else -> it.role
        }
        holder.contentText.text = it.content
        holder.timestampText.text = it.timestamp
        holder.itemView.setOnLongClickListener {
            try {
                val clipboard = it.context.getSystemService(android.content.Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
                val clip = android.content.ClipData.newPlainText("chat_message", holder.contentText.text)
                clipboard.setPrimaryClip(clip)
                android.widget.Toast.makeText(it.context, "Copied to clipboard", android.widget.Toast.LENGTH_SHORT).show()
            } catch (e: Exception) {
                // ignore
            }
            true
        }
    }

    override fun getItemCount(): Int = items.size
}

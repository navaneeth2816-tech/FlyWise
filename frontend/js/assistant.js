/**
 * FlyWise - Gemini Conversational Assistant Module
 */

let activeConversationId = null;
let isAiResponding = false;

function toggleAiDrawer() {
  const drawer = document.getElementById('ai-chat-drawer');
  if (!drawer) return;
  drawer.classList.toggle('open');
  if (drawer.classList.contains('open')) {
    const input = document.getElementById('ai-chat-input');
    if (input) input.focus();
  }
}

function clearAiChat() {
  activeConversationId = null;
  const container = document.getElementById('ai-chat-messages-container');
  if (container) {
    container.innerHTML = `
      <div class="chat-bubble assistant">
        Hello! I am your <strong>FlyWise AI Assistant</strong> powered by Gemini.<br><br>
        You can ask me <strong>ANY question</strong> — whether general inquiries (science, facts, everyday topics) or specific travel planning (flight discovery, transparent journey costs, connection risks, baggage rules). How can I assist you today?
      </div>
    `;
  }
  showToast('Started a new conversation with FlyWise AI.', 'info');
}

function sendSuggestedPrompt(promptText) {
  const drawer = document.getElementById('ai-chat-drawer');
  if (!drawer.classList.contains('open')) {
    drawer.classList.add('open');
  }
  const input = document.getElementById('ai-chat-input');
  if (input) {
    input.value = promptText;
    handleAssistantSubmit();
  }
}

async function handleAssistantSubmit(e) {
  if (e) e.preventDefault();
  if (isAiResponding) return;

  const input = document.getElementById('ai-chat-input');
  const sendBtn = document.getElementById('ai-chat-send-btn');
  if (!input) return;
  const message = input.value.trim();
  if (!message) return;

  input.value = '';
  appendChatMessage('user', message);

  // Set loading state
  isAiResponding = true;
  if (input) input.disabled = true;
  if (sendBtn) {
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i>';
  }

  // Show typing bubble
  const typingId = appendTypingIndicator();

  try {
    const data = await api.post('/assistant/chat', {
      message,
      conversation_id: activeConversationId
    });

    removeTypingIndicator(typingId);
    activeConversationId = data.conversation_id;
    appendChatMessage('assistant', data.reply, data.itineraries);
  } catch (err) {
    removeTypingIndicator(typingId);
    console.warn('AI Assistant query error:', err);
    appendChatMessage('assistant', `I could not complete your request at this moment (${err.message || 'Connection issue'}). Please try again or ask another question.`);
  } finally {
    isAiResponding = false;
    if (input) {
      input.disabled = false;
      input.focus();
    }
    if (sendBtn) {
      sendBtn.disabled = false;
      sendBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i>';
    }
  }
}

function appendChatMessage(sender, text, itineraries = []) {
  const container = document.getElementById('ai-chat-messages-container');
  if (!container) return;

  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${sender}`;

  // Parse markdown bold, italic, and bullet points
  let formatted = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n\s*-\s+(.*?)(?=\n|$)/g, '<br>• $1')
    .replace(/\n\s*###\s+(.*?)(?=\n|$)/g, '<br><strong style="color: var(--primary);">$1</strong>')
    .replace(/\n/g, '<br>');

  bubble.innerHTML = formatted;

  // If matching itineraries exist, append compact flight cards
  if (itineraries && itineraries.length > 0) {
    const cardWrap = document.createElement('div');
    cardWrap.style.marginTop = '0.75rem';
    cardWrap.style.display = 'flex';
    cardWrap.style.flexDirection = 'column';
    cardWrap.style.gap = '0.5rem';

    cardWrap.innerHTML = itineraries.map(it => {
      const durHrs = Math.floor(it.duration_minutes / 60);
      const durMins = it.duration_minutes % 60;
      return `
        <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 0.65rem; font-size: 0.8rem; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong style="color: var(--primary);">${it.airline_name} (${it.segments[0].flight_number})</strong>
            <div style="color: var(--text-muted);">${durHrs}h ${durMins}m • Score: ${it.recommendation_score}/100</div>
          </div>
          <div style="text-align: right;">
            <div style="font-weight: 800;">₹${Number(it.total_fare).toLocaleString('en-IN')}</div>
            <button style="background: var(--primary); color: white; border: none; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; cursor: pointer; margin-top: 2px;" onclick="toggleAiDrawer(); startBookingFlow('${it.itinerary_id}')">
              Book
            </button>
          </div>
        </div>
      `;
    }).join('');

    bubble.appendChild(cardWrap);
  }

  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

function appendTypingIndicator() {
  const container = document.getElementById('ai-chat-messages-container');
  if (!container) return null;

  const id = `typing-${Date.now()}`;
  const typing = document.createElement('div');
  typing.id = id;
  typing.className = 'chat-bubble assistant';
  typing.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin" style="color: var(--primary);"></i> FlyWise AI is thinking...`;
  container.appendChild(typing);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeTypingIndicator(id) {
  if (!id) return;
  const el = document.getElementById(id);
  if (el) el.remove();
}

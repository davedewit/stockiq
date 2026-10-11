// AI Stock Chat Widget
(function() {
    const LAMBDA_URL = 'https://qkxnxpxsk5dxin7pagolehsqyy0iigpe.lambda-url.us-east-1.on.aws/';
    
    // Create chat widget HTML
    const chatHTML = `
        <style>
        @media (min-width: 769px) {
            #ai-chat-widget { right: 20px !important; }
            #ai-chat-window { right: 0 !important; height: 600px !important; width: 380px !important; }
        }
        /* The right-hand news panel only exists on some pages and only shows from 1401px wide:
           move the chat clear of it there, and nowhere else */
        @media (min-width: 1401px) {
            body.has-news-panel #ai-chat-widget { right: 370px !important; }
        }
        @media (max-width: 768px) {
            #ai-chat-widget { right: 20px !important; }
            #ai-chat-window { right: 0 !important; width: calc(100vw - 40px) !important; max-width: 350px !important; height: 500px !important; }
        }
        </style>
        <div id="ai-chat-widget" style="position: fixed; bottom: 20px; right: 20px; z-index: 10000; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <!-- Chat Button -->
            <button id="ai-chat-btn" style="width: 60px; height: 60px; border-radius: 50%; background: #007bff; border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.3); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: transform 0.2s;">
                <svg id="ai-chat-icon" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <svg id="ai-chat-close-icon" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" style="display: none;">
                    <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
            </button>
            
            <!-- Chat Window -->
            <div id="ai-chat-window" style="display: none; position: absolute; bottom: 80px; right: 0; width: 380px; height: 600px; background: var(--bg-primary, #fff); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.3); flex-direction: column; overflow: hidden;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); color: white; padding: 14px 16px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div style="width: 36px; height: 36px; background: rgba(255,255,255,0.2); border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                            </svg>
                        </div>
                        <div>
                            <div style="font-weight: 600; font-size: 15px; line-height: 1.2;">AI Stock Assistant</div>
                            <div style="font-size: 11px; opacity: 0.85; line-height: 1.2; margin-top: 2px;">Always online</div>
                        </div>
                    </div>
                    <button id="ai-chat-close" style="background: rgba(255,255,255,0.15); border: none; color: white; font-size: 20px; cursor: pointer; padding: 0; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; transition: background 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.25)'" onmouseout="this.style.background='rgba(255,255,255,0.15)'">&times;</button>
                </div>
                
                <!-- Messages -->
                <div id="ai-chat-messages" style="flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; background: var(--bg-secondary, #f8f9fa);">
                    <div style="background: var(--bg-primary, #fff); padding: 12px 14px; border-radius: 10px; font-size: 14px; color: var(--text-primary, #333); box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                        👋 Hi! I'm your AI stock assistant. Ask me questions like:
                        <ul style="margin: 8px 0 0 0; padding-left: 20px; font-size: 13px; line-height: 1.6;">
                            <li>What does the data say about AAPL?</li>
                            <li>How does your S&P 500 screener work?</li>
                            <li>Where can I analyze crypto?</li>
                        </ul>
                    </div>
                </div>
                
                <!-- Input -->
                <div style="padding: 14px 16px; border-top: 1px solid var(--border-color, #e0e0e0); background: var(--bg-primary, #fff);">
                    <div style="display: flex; gap: 8px;">
                        <input id="ai-chat-input" type="text" placeholder="Ask about stocks..." style="flex: 1; padding: 11px 14px; border: 1px solid var(--border-color, #ddd); border-radius: 8px; font-size: 16px; background: var(--bg-primary, #fff); color: var(--text-primary, #333); transition: border-color 0.2s;" onfocus="this.style.borderColor='#007bff'" onblur="this.style.borderColor='var(--border-color, #ddd)'">
                        <button id="ai-chat-send" style="padding: 11px 18px; background: #007bff; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; font-size: 14px; transition: background 0.2s; white-space: nowrap;" onmouseover="this.style.background='#0056b3'" onmouseout="this.style.background='#007bff'">Send</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Insert widget into page
    document.addEventListener('DOMContentLoaded', function() {
        document.body.insertAdjacentHTML('beforeend', chatHTML);
        // Pages with the right-hand news panel (home page) get the chat moved clear of it on wide screens
        if (document.getElementById('news-panel')) {
            document.body.classList.add('has-news-panel');
        }
        
        const chatBtn = document.getElementById('ai-chat-btn');
        const chatWindow = document.getElementById('ai-chat-window');
        const chatClose = document.getElementById('ai-chat-close');
        const chatInput = document.getElementById('ai-chat-input');
        const chatSend = document.getElementById('ai-chat-send');
        const chatMessages = document.getElementById('ai-chat-messages');
        
        // Check if rate limited from previous session
        const currentUserId = localStorage.getItem('userId') || 'anonymous';
        const rateLimitedUserId = sessionStorage.getItem('aiChatRateLimitedUser');
        const rateLimited = sessionStorage.getItem('aiChatRateLimited');
        
        // Clear rate limit if user changed (logged in/out)
        if (rateLimited === 'true' && rateLimitedUserId !== currentUserId) {
            sessionStorage.removeItem('aiChatRateLimited');
            sessionStorage.removeItem('aiChatRateLimitedUser');
        } else if (rateLimited === 'true') {
            chatInput.disabled = true;
            chatSend.disabled = true;
            chatInput.placeholder = 'Chat limit reached';
            chatInput.style.opacity = '0.5';
            chatSend.style.opacity = '0.5';
            chatSend.style.cursor = 'not-allowed';
        }
        
        // Clear chat history if user changed (logged in/out)
        const lastChatUserId = sessionStorage.getItem('lastChatUserId');
        if (lastChatUserId && lastChatUserId !== currentUserId) {
            // User changed - clear old chat history
            sessionStorage.removeItem('aiChatHistory_' + lastChatUserId);
        }
        sessionStorage.setItem('lastChatUserId', currentUserId);
        
        // Load chat history from sessionStorage (per user)
        const userId = localStorage.getItem('userId') || 'anonymous';
        const savedHistory = sessionStorage.getItem('aiChatHistory_' + userId);
        if (savedHistory) {
            try {
                const messages = JSON.parse(savedHistory);
                messages.forEach(msg => {
                    const msgId = 'msg-' + Date.now() + Math.random();
                    const isUser = msg.sender === 'user';
                    
                    // Convert URLs to clickable links for AI messages
                    let displayText = msg.text;
                    if (!isUser) {
                        // Decode ALL HTML entities
                        displayText = msg.text.replace(/&amp;/g, '&')
                                             .replace(/&#39;/g, "'")
                                             .replace(/&quot;/g, '"')
                                             .replace(/&lt;/g, '<')
                                             .replace(/&gt;/g, '>');
                        // Handle markdown links [text](url) or [text]url
                        displayText = displayText.replace(/\[([^\]]+)\]\(?(https?:\/\/[^\s)]+)\)?/g, '<a href="$2" style="color: #007bff; text-decoration: underline;">$1</a>');
                        // Handle plain URLs (not already in links)
                        displayText = displayText.replace(/(?<!href=")(?<!>)(https?:\/\/[^\s<]+)(?![^<]*<\/a>)/g, '<a href="$1" style="color: #007bff; text-decoration: underline;">$1</a>');
                    }
                    
                    const msgHTML = `
                        <div id="${msgId}" style="display: flex; ${isUser ? 'justify-content: flex-end;' : ''}">
                            <div style="max-width: 80%; padding: 10px 14px; border-radius: ${isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px'}; font-size: 14px; line-height: 1.5; ${isUser ? 'background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); color: white; box-shadow: 0 2px 8px rgba(0, 123, 255, 0.3);' : 'background: var(--bg-primary, #fff); color: var(--text-primary, #333); box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid var(--border-color, #e8e8e8);'}">
                                ${displayText}
                            </div>
                        </div>
                    `;
                    chatMessages.insertAdjacentHTML('beforeend', msgHTML);
                });
                chatMessages.scrollTop = chatMessages.scrollHeight;
            } catch (e) {
                console.error('Failed to load chat history:', e);
            }
        }
        
        // Detect current page context to give AI relevant information
        function getPageContext() {
            const path = window.location.pathname;
            const stockMatch = path.match(/\/stocks\/([^/]+)\.html/);
            if (stockMatch) {
                const symbol = stockMatch[1];
                const companyEl = document.querySelector('h1');
                const company = companyEl ? companyEl.textContent.replace(/\s*Stock Analysis.*/, '').trim() : symbol;
                return { page: 'stock', symbol, company };
            }
            if (path.includes('analysis.html')) return { page: 'analysis' };
            if (path.includes('dashboard.html')) {
                // what the dashboard shows right now, in a few plain lines, so questions about it can be answered from the user's own figures
                let shown = '';
                try {
                    shown = [window.practicePortfolio && window.practicePortfolio.summary && window.practicePortfolio.summary(),
                             window.practiceAutopilot && window.practiceAutopilot.summary && window.practiceAutopilot.summary()].filter(Boolean).join('\n').slice(0, 2500);
                } catch (e) { shown = ''; }
                return { page: 'dashboard', dashboard: shown };
            }
            if (path.includes('index.html') || path === '/') return { page: 'home' };
            return { page: 'other' };
        }

        // Update suggested questions based on current page
        function updateSuggestedQuestions() {
            const ctx = getPageContext();
            const welcomeEl = document.querySelector('#ai-chat-messages div');
            if (!welcomeEl) return;
            let questions = [];
            if (ctx.page === 'stock') {
                questions = [
                    `What does the data say about ${ctx.symbol}?`,
                    `What's the outlook for ${ctx.symbol}?`,
                    `Give me other stocks like ${ctx.symbol}`
                ];
            } else if (ctx.page === 'analysis') {
                questions = ['How does the screener work?', 'Which screener should I use?', 'What do the scores mean?'];
            } else if (ctx.page === 'dashboard') {
                questions = ['What is my autopilot going to do next?', 'What does the risk level change?', 'How do I set how much goes into each market?'];
            } else {
                questions = ['What does the data say about Apple stock?', 'How does the S&P 500 screener work?', 'What can you help me with?'];
            }
            welcomeEl.innerHTML = `👋 Hey! I can help with stocks and investing. Try asking:<ul style="margin: 8px 0 0 0; padding-left: 20px; font-size: 13px; line-height: 1.6;">${questions.map(q => `<li>${q}</li>`).join('')}</ul>`;
        }

        // Toggle chat window
        chatBtn.addEventListener('click', function() {
            const isVisible = chatWindow.style.display === 'flex';
            chatWindow.style.display = isVisible ? 'none' : 'flex';
            document.getElementById('ai-chat-icon').style.display = isVisible ? 'block' : 'none';
            document.getElementById('ai-chat-close-icon').style.display = isVisible ? 'none' : 'block';
            if (!isVisible) {
                updateSuggestedQuestions();
                // Track chat opened
                if (typeof gtag !== 'undefined') {
                    gtag('event', 'chat_opened', {
                        'event_category': 'AI Chat',
                        'event_label': 'Chat Widget Opened'
                    });
                }
                // Don't auto-focus on mobile to prevent keyboard popup
                // Scroll to bottom after window is visible
                setTimeout(() => {
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }, 0);
            }
        });
        
        chatClose.addEventListener('click', function() {
            chatWindow.style.display = 'none';
            document.getElementById('ai-chat-icon').style.display = 'block';
            document.getElementById('ai-chat-close-icon').style.display = 'none';
        });
        
        // Close chat when clicking outside
        document.addEventListener('click', function(e) {
            if (chatWindow.style.display === 'flex' && 
                !chatWindow.contains(e.target) && 
                !chatBtn.contains(e.target)) {
                chatWindow.style.display = 'none';
                document.getElementById('ai-chat-icon').style.display = 'block';
                document.getElementById('ai-chat-close-icon').style.display = 'none';
            }
        });
        
        // Send message
        function sendMessage() {
            const message = chatInput.value.trim();
            if (!message) return;
            
            // Get user ID first
            let userId = localStorage.getItem('userId');
            const isLoggedIn = userId && userId.includes('@');
            
            if (!isLoggedIn) {
                // Not logged in - use/generate anonymous ID
                userId = localStorage.getItem('anonymousId');
                if (!userId) {
                    userId = 'anon_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                    localStorage.setItem('anonymousId', userId);
                }
            }
            
            // Get conversation history BEFORE adding new message (get previous context)
            const history = JSON.parse(sessionStorage.getItem('aiChatHistory_' + userId) || '[]');
            const recentHistory = history.slice(-6); // Last 3 exchanges (6 messages: 3 user + 3 AI)
            
            // Clear input immediately
            chatInput.value = '';
            
            // Add user message
            addMessage(message, 'user');
            
            // Show typing indicator after a tiny delay to ensure unique ID
            setTimeout(() => {
                const typingId = addMessage('Thinking...', 'ai', true);
                
                // Call Lambda with history
                fetch(LAMBDA_URL, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message,
                        userId,
                        pageContext: getPageContext(),
                        conversationHistory: recentHistory
                    })
                })
                .then(res => {
                    if (res.status === 429) {
                        // Rate limit hit - disable chat
                        return res.json().then(data => ({rateLimited: true, data}));
                    }
                    return res.json().then(data => ({rateLimited: false, data}));
                })
                .then(result => {
                    // Remove typing indicator
                    const typingEl = document.getElementById(typingId);
                    if (typingEl) typingEl.remove();
                    
                    if (result.rateLimited) {
                        // Show rate limit message and disable input
                        addMessage(result.data.response, 'ai');
                        chatInput.disabled = true;
                        chatSend.disabled = true;
                        chatInput.placeholder = 'Chat limit reached';
                        chatInput.style.opacity = '0.5';
                        chatSend.style.opacity = '0.5';
                        chatSend.style.cursor = 'not-allowed';
                        sessionStorage.setItem('aiChatRateLimited', 'true');
                        sessionStorage.setItem('aiChatRateLimitedUser', userId);
                        // Track rate limit hit
                        if (typeof gtag !== 'undefined') {
                            gtag('event', 'chat_rate_limited', {
                                'event_category': 'AI Chat',
                                'event_label': isLoggedIn ? 'Logged In' : 'Anonymous'
                            });
                        }
                    } else if (result.data.response) {
                        addMessage(result.data.response, 'ai');
                        
                        // Track message sent
                        if (typeof gtag !== 'undefined') {
                            const history = JSON.parse(sessionStorage.getItem('aiChatHistory_' + userId) || '[]');
                            const messageCount = history.filter(m => m.sender === 'user').length + 1;
                            gtag('event', 'chat_message_sent', {
                                'event_category': 'AI Chat',
                                'event_label': isLoggedIn ? 'Logged In' : 'Anonymous',
                                'value': messageCount
                            });
                        }
                        
                        // Check if this was the 10th message (warning message)
                        if (result.data.response.includes('⚠️')) {
                            // Disable input after showing warning
                            chatInput.disabled = true;
                            chatSend.disabled = true;
                            chatInput.placeholder = 'Chat limit reached';
                            chatInput.style.opacity = '0.5';
                            chatSend.style.opacity = '0.5';
                            chatSend.style.cursor = 'not-allowed';
                            sessionStorage.setItem('aiChatRateLimited', 'true');
                            sessionStorage.setItem('aiChatRateLimitedUser', userId);
                        }
                    } else {
                        addMessage('Sorry, I encountered an error. Please try again.', 'ai');
                    }
                })
                .catch(err => {
                    const typingEl = document.getElementById(typingId);
                    if (typingEl) typingEl.remove();
                    addMessage('Sorry, I\'m having trouble connecting. Please try again.', 'ai');
                });
            }, 10);
        }
        
        chatSend.addEventListener('click', sendMessage);
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendMessage();
        });
        
        // Add message to chat
        function addMessage(text, sender, isTyping = false) {
            const msgId = 'msg-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
            const isUser = sender === 'user';
            
            // Convert URLs to clickable links for AI messages
            let displayText = text;
            if (!isUser) {
                // Decode ALL HTML entities
                displayText = text.replace(/&amp;/g, '&')
                                 .replace(/&#39;/g, "'")
                                 .replace(/&quot;/g, '"')
                                 .replace(/&lt;/g, '<')
                                 .replace(/&gt;/g, '>');
                // Handle markdown links [text](url) or [text]url
                displayText = displayText.replace(/\[([^\]]+)\]\(?(https?:\/\/[^\s)]+)\)?/g, '<a href="$2" style="color: #007bff; text-decoration: underline;">$1</a>');
                // Handle plain URLs (not already in links)
                displayText = displayText.replace(/(?<!href=")(?<!>)(https?:\/\/[^\s<]+)(?![^<]*<\/a>)/g, '<a href="$1" style="color: #007bff; text-decoration: underline;">$1</a>');
            }
            
            const msgHTML = `
                <div id="${msgId}" style="display: flex; ${isUser ? 'justify-content: flex-end;' : ''} animation: slideIn 0.2s ease-out;">
                    <div style="max-width: 80%; padding: 10px 14px; border-radius: ${isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px'}; font-size: 14px; line-height: 1.5; ${isUser ? 'background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); color: white; box-shadow: 0 2px 8px rgba(0, 123, 255, 0.3);' : 'background: var(--bg-primary, #fff); color: var(--text-primary, #333); box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid var(--border-color, #e8e8e8);'} ${isTyping ? 'opacity: 0.7; font-style: italic;' : ''}">
                        ${displayText}
                    </div>
                </div>
            `;
            chatMessages.insertAdjacentHTML('beforeend', msgHTML);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            // Save to sessionStorage (skip typing indicators) - per user
            if (!isTyping) {
                const userId = localStorage.getItem('userId') || 'anonymous';
                const history = JSON.parse(sessionStorage.getItem('aiChatHistory_' + userId) || '[]');
                history.push({text, sender});
                sessionStorage.setItem('aiChatHistory_' + userId, JSON.stringify(history));
            }
            
            return msgId;
        }
        
        // Hover effect on button
        chatBtn.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.1)';
        });
        chatBtn.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
})();

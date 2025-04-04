const FullInvestor = defineComponent({
    template: "#full-investor-template",
    props: { slug: String, rendercontacts: Boolean },
    emits: ["close-investor", "bookmarked"],
    delimiters: ["[[", "]]"],
    mounted() {
        window.addEventListener("keydown", this.handleKeyDown);
        document.addEventListener("click", this.handleClickOutside);
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleKeyDown);
        this.deleteInvestorParam();
        document.removeEventListener("click", this.handleClickOutside);
        const script_element = document.getElementById("twitter-script");
        if (script_element) script_element.remove();
    },
    async created() {
        await this.fetchInvestor();
        window.removeEventListener("popstate", this.checkUrlParams);
    },
    methods: {
        async fetchInvestor() {
            try {
                const response = await fetch(`/investor/${this.slug}/get`);
                if (response.ok) {
                    const data = await response.json();
                    this.investor = data.investor;
                    this.isBookmarked = data.isBookmarked;
                    this.unpaid = data.unpaid;
                    if (data.investments && data.n_of_investments) {
                        this.investments = data.investments;
                        this.n_of_investments = data.n_of_investments;
                    }
                    await this.loadTwitterTimeline();
                } else {
                    this.closeInvestor();
                    return;
                }
            } catch (error) {
                console.error("Error fetching investor:", error);
                this.closeInvestor();
            } finally {
                this.isLoading = false;
            }
        },
        async loadTwitterTimeline() {
            if (!this.investor?.twitter) return;
            this.loadingTwitter = true;
            this.ensureTwitterScriptLoaded(() => {
                const timeline = document.querySelector(".twitter-timeline");
                if (timeline) {
                    timeline.innerHTML = "";
                    timeline.setAttribute("href", this.investor.twitter);
                    window.twttr?.widgets.load();

                    const observer = new MutationObserver((mutations) => {
                        mutations.forEach((mutation) => {
                            const twitterWidget = document.querySelector("[id^='twitter-widget-']");
                            if (twitterWidget && twitterWidget.offsetHeight > 0) {
                                this.loadingTwitter = false;
                                observer.disconnect();
                            }
                        });
                    });

                    observer.observe(document.body, { childList: true, subtree: true });
                }
            });
        },
        async toggleBookmark(investorId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/investor/${investorId}/bookmark`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.ok) {
                    if (response.url.includes("/onboarding/")) {
                        window.location.href = response.url;
                    }
                    const data = await response.json();
                    if (data[0].bookmarked) {
                        this.$emit("bookmarked", { investorId: investorId, status: true });
                        this.isBookmarked = !this.isBookmarked;
                    } else {
                        this.$emit("bookmarked", { investorId: investorId, status: false });
                        this.isBookmarked = !this.isBookmarked;
                    }
                }
            } catch (error) {
                console.error(error);
            }
        },
        async sortInvestments(sortType) {
            const compareDates = (a, b) => {
                const dateA = new Date(a.announced_date);
                const dateB = new Date(b.announced_date);
                return sortType === "asc" ? dateA - dateB : dateB - dateA;
            };

            this.investments.sort(compareDates);

            // Force re-render
            this.investments = [...this.investments];
            this.sortOrder = sortType;
            this.sortDropdownOpened = false;
        },
        ensureTwitterScriptLoaded(callback) {
            const script_element = document.getElementById("twitter-script");
            if (script_element) script_element.remove();

            if (!this.twitterScriptLoaded) {
                const script = document.createElement("script");
                script.src = "https://platform.twitter.com/widgets.js";
                script.id = "twitter-script";
                script.async = true;
                script.onload = () => {
                    this.twitterScriptLoaded = true;
                    callback();
                };
                document.body.appendChild(script);
            } else {
                callback();
            }
        },
        deleteInvestorParam() {
            const url = new URL(window.location.href);
            url.searchParams.delete("investor");
            window.history.replaceState({}, "", url);
        },
        checkUrlParams() {
            const urlParams = new URLSearchParams(window.location.search);
            const investorSlug = urlParams.get("investor");
            if (!investorSlug) {
                this.$emit("close-investor");
            }
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.$emit("close-investor");
            }
        },
        toggleExpansion() {
            this.isExpanded = !this.isExpanded;
        },
        closeInvestor() {
            this.$emit("close-investor");
        },
        getTwitterHandle(url) {
            return url.split("/").pop();
        },
        handleClickOutside(event) {
            const dropdownContainer = this.$refs.dropdownContainer;
            if (dropdownContainer && !dropdownContainer.contains(event.target)) {
                this.dropdownOpened = false;
            }
        },
    },
    data() {
        return {
            showPopover: false,
            isExpanded: false,
            isLoading: true,
            isBookmarked: false,
            investor: null,
            unpaid: false,
            sortDropdownOpened: false,
            sortOrder: null,
            investments: [],
            dropdownOpened: false,
            twitterScriptLoaded: false,
            loadingTwitter: false,
        };
    },
});

const GeminiComponent = defineComponent({
    template: "#gemini-template",
    emits: ["close-gemini"],
    props: ["userId"],
    watch: {
        response() {
            if (this.isScrolledToBottom) {
                this.scrollToBottom();
            }
        },
    },
    components: {
        FullInvestor,
    },
    async created() {
        await this.loadAllChats();
        this.loadChatById(this.selectedChatId);
        window.addEventListener("popstate", this.handlePopState);
        this.checkAndSelectUrlParam("investor", this.selectInvestorSlug);
    },
    computed: {
        currentChatName() {
            if (!this.selectedChatId) return "";
            for (const [date, chats] of this.userChats) {
                const chat = chats.find((chat) => chat.id === this.selectedChatId);
                if (chat) return chat.name;
            }
            return "";
        },
    },
    mounted() {
        document.addEventListener("click", this.handleHistorySidebarClickOutside);
        document.addEventListener("click", this.handleClickOutside);
        document.body.addEventListener("click", this.handleInvestorButtonClick);
        this.handleScroll();
    },
    beforeUnmount() {
        document.removeEventListener("click", this.handleHistorySidebarClickOutside);
        document.removeEventListener("click", this.handleClickOutside);
        document.body.removeEventListener("click", this.handleInvestorButtonClick);
        window.removeEventListener("popstate", this.handlePopState);
        this.stopSSEStream();
    },
    methods: {
        async getChatById(chatId) {
            try {
                const response = await fetch(`/message/chat/${chatId}/details`, {
                    method: "GET",
                    headers: { "Content-Type": "application/json" },
                });

                const data = await response.json();

                if (data.error) {
                    console.error("Error loading chat:", data.error);
                    return;
                }

                this.chats = [data, ...this.chats];
            } catch (error) {
                console.error("Error loading chat:", error);
            }
        },
        async createChat() {
            this.response = [];
            this.selectedChatId = null;
        },
        async loadChatById(chatId) {
            if (chatId === null || chatId === undefined) {
                console.warn("Invalid chatId, nothing to load.");
                return;
            }
            try {
                const response = await fetch(`/message/chat/${chatId}/details`, {
                    method: "GET",
                    headers: { "Content-Type": "application/json" },
                });
                const data = await response.json();

                if (data.error) {
                    console.error("Error loading chat:", data.error);
                    return;
                }
                this.response = data.messages.map((msg) => ({
                    content: this.processMarkdown(msg.message),
                    type: msg.type,
                    isHTML: true,
                }));
                this.scrollToBottom();
            } catch (error) {
                console.error("Error loading chat:", error);
            }
        },
        async loadAllChats() {
            try {
                const response = await fetch(`/message/chats/${this.userId}`, {
                    method: "GET",
                    headers: { "Content-Type": "application/json" },
                });

                if (!response.ok) {
                    const data = await response.json();
                    console.error("Error loading chats:", data.error || "Unknown error");
                    this.isHistoryVisible = false;
                    this.hasChats = false;
                    return;
                }

                const data = await response.json();

                if (!data || data.length === 0) {
                    this.isHistoryVisible = false;
                    this.hasChats = false;
                    return;
                }

                this.hasChats = true;
                this.isHistoryVisible = true;
                this.selectedChatId = data[0].id;

                // Group chats by date category
                const grouped = this.groupChatsByDate(data);
                this.userChats = grouped;
            } catch (error) {
                console.error("Error loading chats:", error);
                this.isHistoryVisible = false;
                this.hasChats = false;
            }
        },

        groupChatsByDate(chats) {
            const grouped = new Map();

            for (const chat of chats) {
                const category = this.formatDate(chat.created);

                if (!grouped.has(category)) {
                    grouped.set(category, []);
                }
                grouped.get(category).push({ ...chat, isNew: false });
            }

            // Sort by date category
            return new Map(
                [...grouped.entries()]
                    .map(([key, value]) => [key, value])
                    .sort((a, b) => {
                        const order = [
                            "Recently",
                            "Yesterday",
                            "1 Week",
                            "2 Weeks",
                            "3 Weeks",
                            "1 Month",
                            "Few months",
                            "Long ago",
                        ];

                        const indexA = order.indexOf(a[0]);
                        const indexB = order.indexOf(b[0]);
                        return (indexA === -1 ? order.length : indexA) - (indexB === -1 ? order.length : indexB);
                    }),
            );
        },

        formatDate(created) {
            const date = new Date(created);
            const today = new Date();
            today.setHours(0, 0, 0, 0);

            const chatDate = new Date(date);
            chatDate.setHours(0, 0, 0, 0);

            const diffTime = today - chatDate;
            const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

            if (diffDays === 0) return "Recently";
            if (diffDays === 1) return "Yesterday";
            if (diffDays <= 7) return "1 Week";
            if (diffDays <= 14) return "2 Weeks";
            if (diffDays <= 21) return "3 Weeks";
            if (diffDays <= 31) return "1 Month";
            if (diffDays <= 60) return "Few months";
            return "Long ago";
        },
        async selectChat(chatId) {
            this.selectedChatId = chatId;
            this.loadChatById(chatId);
            this.stopSSEStream();
        },
        async deleteChat(chatId) {
            const csrf_token = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/message/chat/${chatId}/delete`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf_token },
                });
                if (response.ok)
                    for (const [date, chats] of this.userChats) {
                        const index = chats.findIndex((c) => c.id === chatId);
                        if (index > -1) {
                            const chat = chats[index];
                            chat.isDeleting = true;

                            await new Promise((resolve) => setTimeout(resolve, 200));

                            chats.splice(index, 1);

                            if (chats.length === 0) {
                                this.userChats.delete(date);
                            }
                            break;
                        }
                    }

                if (this.selectedChatId === chatId) {
                    this.selectedChatId = null;
                }
            } catch (error) {
                console.error("Failed to delete chat:", error);
            }
        },
        async saveChatName(chat) {
            if (!this.newChatName.trim() || this.newChatName.trim() === chat.name) {
                this.cancelEditing();
                return;
            }

            const csrf_token = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`message/chat/${chat.id}/rename`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrf_token,
                    },
                    body: JSON.stringify({
                        name: this.newChatName.trim(),
                    }),
                    credentials: "same-origin",
                });

                if (!response.ok) {
                    throw new Error("Something went wrong");
                }

                const data = await response.json();

                const targetChat = this.findChatById(chat.id);
                if (targetChat) {
                    targetChat.name = data.chat.name || this.newChatName.trim();
                }
            } catch (error) {
                console.error("Error renaming chat:", error);
                const targetChat = this.findChatById(chat.id);
                if (targetChat) {
                    targetChat.name = chat.name;
                }
            } finally {
                this.cancelEditing();
            }
        },
        async getTwitterAvatar(slug) {
            try {
                const response = await fetch(`/investor/${slug}/twitter`);
                if (!response.ok) {
                    console.error(`Error loading avatar for ${slug}: ${response.status} ${response.statusText}`);
                    return "https://unavatar.io/x/default";
                }
                const data = await response.json();
                const twitter = data.split("/").pop();
                return `https://unavatar.io/x/${twitter}`;
            } catch (error) {
                console.error("Error loading avatar:", error);
            }
        },
        async loadAvatar(slug) {
            if (this.avatarCache.has(slug)) {
                return;
            }
            try {
                const avatarUrl = await this.getTwitterAvatar(slug);
                this.avatarCache.set(slug, avatarUrl);
                this.updateAvatarImages(slug, avatarUrl);
            } catch (error) {
                console.error("Error in loadAvatar:", error);
            }
        },
        async fetchChat(chatId) {
            const csrf_token = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/message/chat/${chatId}`, {
                    method: "GET",
                    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf_token },
                });

                const data = await response.json();

                if (data.error) {
                    console.error("Error loading chat:", data.error);
                    return;
                }

                const category = "Recently";
                const newChat = { ...JSON.parse(data), isNew: true };
                if (this.userChats.has(category)) {
                    this.userChats.get(category).unshift(newChat);
                } else {
                    this.userChats.set(category, [newChat]);
                }
            } catch (error) {
                console.error("Error loading chat:", error);
            }
        },
        async cancelGeneration() {
            this.$nextTick(() => {
                this.scrollToBottom();
            });

            this.stopSSEStream();
            this.isGenerating = false;
            this.isAborted[this.selectedChatId] = true;
            this.saveAbortedState();
            const csrf_token = document.getElementById("csrf_token").value;
            const userMessages = this.response.filter((message) => message.type === "user");
            const lastUserMessage = userMessages.length > 0 ? userMessages[userMessages.length - 1] : null;

            try {
                const response = await fetch(`/message/chat/${this.selectedChatId}/save-messages`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf_token },
                    body: JSON.stringify({
                        chat_id: this.selectedChatId,
                        user_message: lastUserMessage.content,
                    }),
                });

                const data = await response.json();
                if (data.error) {
                    console.error("Error saving chat:", data.error);
                    return;
                }
            } catch (error) {
                console.error("Error saving chat:", error);
                return;
            }
        },
        async startSSEStream(chatId, retry = false) {
            this.scrollToBottom();
            this.isGenerating = true;
            this.stopSSEStream();

            // Use null check with default value
            const useChatId = chatId !== null ? chatId : 0;

            const csrf_token = document.getElementById("csrf_token").value;
            this.isThinking = true;
            this.currentMessage = null;
            const promptDiv = this.$refs.prompt;

            let promptText = "";

            if (promptDiv === null) {
                const userMessages = this.response.filter((message) => message.type === "user");
                const lastUserMessage = userMessages.length > 0 ? userMessages[userMessages.length - 1] : null;
                promptText = lastUserMessage ? lastUserMessage.content : "";
                if (!promptText) {
                    this.isGenerating = false;
                    this.isThinking = false;
                    return;
                }
            } else {
                promptText = promptDiv.textContent.trim();
                if (!promptText) {
                    this.isGenerating = false;
                    this.isThinking = false;
                    return;
                }
                this.response.push({ content: promptText, type: "user" });
                promptDiv.textContent = "";
            }

            const url = `/message/stream?prompt=${encodeURIComponent(promptText)}&chat_id=${useChatId}`;
            console.log(`Connecting to SSE stream at: ${url}`);

            try {
                this.eventSource = new EventSource(url);
                let accumulatedText = "";
                let hasError = false;

                this.eventSource.onopen = () => {
                    console.log("SSE connection opened");
                    this.queue = [];
                    this.isTyping = false;
                };

                this.eventSource.onmessage = async (event) => {
                    const text = event.data;

                    // Handle error messages
                    if (text.startsWith('{"error":')) {
                        try {
                            const errorObj = JSON.parse(text);
                            console.error("Stream error:", errorObj.error);
                            if (!this.currentMessage) {
                                this.currentMessage = {
                                    content: `Sorry, an error occurred: ${errorObj.error}`,
                                    type: "gemini",
                                    isHTML: true,
                                    isError: true,
                                };
                                this.response.push(this.currentMessage);
                            }
                            hasError = true;
                            this.stopSSEStream();
                            this.isGenerating = false;
                            this.isAborted[useChatId] = true;
                            this.saveAbortedState();
                            return;
                        } catch (e) {
                            // If it's not valid JSON, treat as normal text
                        }
                    }

                    if (text === "[DONE]") {
                        console.log("All messages received");
                        this.stopSSEStream();
                        this.isGenerating = false;

                        if (hasError) return;

                        if (useChatId) {
                            try {
                                const url = retry
                                    ? `/message/chat/${useChatId}/add-bot-message`
                                    : `/message/chat/${useChatId}/save-messages`;
                                const response = await fetch(url, {
                                    method: "POST",
                                    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf_token },
                                    body: JSON.stringify({
                                        bot_message: accumulatedText.trim(),
                                        chat_id: useChatId,
                                        user_message: promptText,
                                    }),
                                });

                                if (!response.ok) {
                                    const data = await response.json();
                                    console.error("Error saving chat:", data.error || "Unknown error");
                                    return;
                                }
                            } catch (error) {
                                console.error("Error saving chat:", error);
                                return;
                            }
                        } else {
                            try {
                                const response = await fetch(`/message/chat/create`, {
                                    method: "POST",
                                    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf_token },
                                    body: JSON.stringify({
                                        bot_message: accumulatedText,
                                        user_message: promptText,
                                    }),
                                });

                                if (!response.ok) {
                                    const data = await response.json();
                                    console.error("Error creating chat:", data.error || "Unknown error");
                                    return;
                                }

                                const data = await response.json();
                                this.hasChats = true;
                                this.isHistoryVisible = true;

                                const chat = JSON.parse(data.chat);
                                this.selectedChatId = chat.id;

                                const category = "Recently";
                                const newChat = { ...JSON.parse(data.chat), isNew: true };
                                if (this.userChats.has(category)) {
                                    this.userChats.get(category).unshift(newChat);
                                } else {
                                    this.userChats.set(category, [newChat]);
                                }
                            } catch (error) {
                                console.error("Error creating chat:", error);
                                return;
                            }
                        }

                        return;
                    }

                    accumulatedText += text;

                    if (!this.currentMessage) {
                        this.currentMessage = { content: "", type: "gemini", isHTML: true };
                        this.response.push(this.currentMessage);
                    }

                    // Add to the queue and ensure processing starts
                    this.queue.push(text);
                    if (!this.isTyping) {
                        this.processQueue();
                    }
                };

                this.eventSource.onerror = (error) => {
                    console.error("SSE error:", error);
                    this.stopSSEStream();
                    this.isGenerating = false;
                    this.isAborted[useChatId] = true;
                    this.saveAbortedState();

                    if (!this.currentMessage) {
                        this.currentMessage = {
                            content: "Sorry, an error occurred while generating the response. Please try again.",
                            type: "gemini",
                            isHTML: true,
                            isError: true,
                        };
                        this.response.push(this.currentMessage);
                    }
                };
            } catch (error) {
                console.error("Error setting up SSE:", error);
                this.isGenerating = false;
                this.isThinking = false;
                this.isAborted[useChatId] = true;
                this.saveAbortedState();
            }
        },

        stopSSEStream() {
            if (this.eventSource) {
                this.eventSource.close();
                this.eventSource = null;
            }
            if (this.interval) {
                clearInterval(this.interval);
                this.interval = null;
            }
            this.isThinking = false;
        },
        retryGeneration(chatId) {
            this.isAborted[chatId] = false;
            this.saveAbortedState();
            this.startSSEStream(chatId, true);
        },
        saveAbortedState() {
            localStorage.setItem("isAborted", JSON.stringify(this.isAborted));
        },
        handleAnimationEnd(chat) {
            if (chat.isNew) {
                chat.isNew = false;
            }
        },
        checkAndSelectUrlParam(paramName, selectFunction) {
            const urlParams = new URLSearchParams(window.location.search);
            const paramSlug = urlParams.get(paramName);
            if (paramSlug) {
                selectFunction(paramSlug);
            }
        },
        processQueue() {
            if (!this.queue.length) {
                this.isTyping = false;
                return;
            }

            this.isTyping = true;
            const text = this.queue.shift();

            // Immediately append the text to the current message
            if (this.currentMessage) {
                this.currentMessage.content += text;

                // Scroll to bottom if needed
                if (this.isScrolledToBottom) {
                    this.scrollToBottom();
                }
            }

            // Process the next item in the queue after a very short delay
            setTimeout(() => {
                this.processQueue();
            }, 10);
        },
        handleScroll() {
            const chatContainer = this.$refs.chatContainer;
            if (chatContainer);
            this.isScrolledToBottom =
                chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight <= 20;
        },
        scrollToBottom() {
            this.$nextTick(() => {
                const chatContainer = this.$refs.chatContainer;
                if (chatContainer) {
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }
            });
        },
        displayMessage(message) {
            const fullMessage = message.message;
            let currentIndex = 0;

            const interval = setInterval(() => {
                if (currentIndex < fullMessage.length) {
                    const currentContent = fullMessage.slice(0, currentIndex);
                    const currentMessage = this.response.find(
                        (msg) => msg.type === message.type && msg.content === currentContent,
                    );
                    if (currentMessage) {
                        currentMessage.content = fullMessage.slice(0, currentIndex + 1);
                    } else {
                        this.response.push({
                            content: fullMessage.slice(0, currentIndex + 1),
                            type: message.type,
                            isHTML: message.type === "gemini",
                        });
                    }
                    currentIndex++;
                } else {
                    clearInterval(interval);
                }
            }, 0);
        },
        processMarkdown(text) {
            if (!text) return "";

            try {
                const lines = text.split("\n");
                let html = "";
                let inUl = false;
                let needLineBreak = false;

                const processText = (text) => {
                    return text
                        .replace(/\*\*([\s\S]*?)\*\*/g, "<strong>$1</strong>")
                        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, buttonText, slug) => {
                            const cachedAvatar = this.avatarCache.get(slug);
                            const avatarImg = `<img src="${cachedAvatar || "https://unavatar.io/x/default"}" data-slug="${slug}" class="h-5 w-5 mr-1 avatar-placeholder">`;
                            const buttonHTML = `<button data-slug="${slug}" class="investor-btn inline-flex items-center justify-center px-2 border border-gray-300 rounded-lg shadow-sm bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-sky-500">${avatarImg}${buttonText}</button>`;

                            if (!this.avatarCache.has(slug)) {
                                this.loadAvatar(slug);
                            }
                            return buttonHTML;
                        });
                };

                for (const line of lines) {
                    const trimmedLine = line.trim();
                    const listItemMatch = line.match(/^(\s*)(\*|\d+\.)\s+(.*)/);

                    if (listItemMatch) {
                        const indent = listItemMatch[1].length;
                        const content = processText(listItemMatch[3]);

                        if (indent >= 4) {
                            if (!inUl) {
                                html += "<ul>";
                                inUl = true;
                            }
                            html += `<li>${content}</li>`;
                        } else {
                            if (inUl) {
                                html += "</ul>";
                                inUl = false;
                            }
                            html += `<li>${content}</li>`;
                        }
                        needLineBreak = false;
                    } else {
                        if (inUl) {
                            html += "</ul>";
                            inUl = false;
                        }

                        if (trimmedLine === "") {
                            if (needLineBreak) html += "<br>";
                            needLineBreak = false;
                        } else {
                            const processedLine = processText(trimmedLine);

                            if (needLineBreak) html += "<br>";
                            html += processedLine;
                            needLineBreak = true;
                        }
                    }
                }
                if (inUl) {
                    html += "</ul>";
                }
                return html;
            } catch (error) {
                console.error("Error processing markdown:", error);
                return text;
            }
        },
        updateAvatarImages(slug, avatarUrl) {
            const images = document.querySelectorAll(`img[data-slug="${slug}"]`);
            images.forEach((img) => {
                img.src = avatarUrl;
            });
        },
        toggleDropdown(chatId) {
            this.openedDropdownChatId = this.openedDropdownChatId === chatId ? null : chatId;
        },
        toggleHistory() {
            this.isHistoryVisible = !this.isHistoryVisible;
        },
        toggleExpansion() {
            this.isExpanded = !this.isExpanded;
        },
        closeGemini() {
            this.$emit("close-gemini");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.$emit("close-gemini");
            }
        },
        handleClickOutside(event) {
            const isDropdown = event.target.closest(".dropdown-content");
            const isButton = event.target.closest("[data-dropdown-button]");
            const isRenameButton = event.target.closest("[data-rename-button]");
            const isEditingInput = event.target.closest('input[ref^="nameInput-"]');

            if (!isDropdown && !isButton && !isRenameButton && !isEditingInput) {
                this.openedDropdownChatId = null;
            }

            if (this.editingChatId !== null && !isEditingInput && !isRenameButton) {
                const currentChat = this.findChatById(this.editingChatId);
                if (currentChat) {
                    this.saveChatName(currentChat);
                }
            }
        },
        handleHistorySidebarClickOutside(event) {
            const historyContainer = this.$refs.historyContainer;
            if (historyContainer && !historyContainer.contains(event.target)) {
                this.isHistoryVisible = false;
            }
        },
        startEditing(chat) {
            this.editingChatId = chat.id;
            this.newChatName = chat.name;
            this.openedDropdownChatId = null;

            this.$nextTick(() => {
                const inputRef = this.$refs[`nameInput-${chat.id}`];
                if (inputRef) {
                    inputRef[0].focus();
                }
            });
        },
        cancelEditing() {
            this.editingChatId = null;
            this.newChatName = "";
        },
        findChatById(chatId) {
            for (const [, chats] of this.userChats) {
                const found = chats.find((c) => c.id === chatId);
                if (found) return found;
            }
            return null;
        },
        selectInvestorSlug(investorSlug) {
            if (!investorSlug) {
                this.handleCloseInvestor();
                return;
            }
            this.selectedInvestorSlug = investorSlug;
        },
        handleCloseInvestor() {
            this.selectedInvestorSlug = null;
            const url = new URL(window.location);
            url.searchParams.delete("investor");
            window.history.replaceState({}, "", url);
        },
        handleInvestorButtonClick(event) {
            const investorBtn = event.target.closest(".investor-btn");
            if (investorBtn) {
                const slug = investorBtn.dataset.slug;
                this.selectInvestorSlug(slug);
                event.stopPropagation();
            }
        },
    },
    data() {
        return {
            response: [],
            messages: {},
            selectedChatId: null,
            userChats: new Map(),
            avatarCache: new Map(),
            chats: [],
            isExpanded: false,
            isGeminiOpened: true,
            isHistoryVisible: true,
            isScrolledToBottom: true,
            dropdownOpened: false,
            openedDropdownChatId: null,
            queue: [],
            editingChatId: null,
            eventSource: null,
            newChatName: "",
            currentMessage: null,
            interval: null,
            selectedInvestorSlug: null,
            isTyping: false,
            isThinking: false,
            isGenerating: false,
            isAborted: JSON.parse(localStorage.getItem("isAborted")) || {},
            hasChats: false,
        };
    },
});

const SearchHistory = defineComponent({
    template: "#search-history-template",
    delimiters: ["[[", "]]"],
    props: ["type"],
    async mounted() {
        try {
            const response = await fetch(`/search-history?type=${this.type}&page=1&limit=5`);
            if (response.ok) {
                const data = await response.json();
                for (let item of data) {
                    this.searchHistoryData.push(...item.histories);
                }
            } else {
                console.error("An error occurred while fetching the search history.");
            }
        } catch (error) {
            console.error(error);
        }
    },
    data() {
        return {
            searchHistoryData: [],
        };
    },
});

const FullInvestmentFirm = defineComponent({
    template: "#full-investment-firm-template",
    props: { slug: String },
    emits: ["close-investment-firm", "bookmarked"],
    mounted() {
        window.addEventListener("keydown", this.handleKeyDown);
        document.addEventListener("click", this.handleClickOutside);
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleKeyDown);
        this.deleteInvestmentFirmParam();
        document.removeEventListener("click", this.handleClickOutside);
    },
    async created() {
        await this.fetchInvestmentFirm();
        window.removeEventListener("popstate", this.checkUrlParams);
    },
    methods: {
        async fetchInvestmentFirm() {
            this.isLoading = true;
            try {
                const response = await fetch(`/investment-firm/${this.slug}/get`);
                if (response.ok) {
                    const data = await response.json();
                    this.investmentFirm = data.investment_firm;
                    this.unpaid = data.unpaid;
                    this.isBookmarked = data.isBookmarked;
                    if (data.investments) {
                        this.investments = data.investments;
                    }
                } else {
                    this.closeInvestmentFirm();
                    return;
                }
            } catch (error) {
                console.error("Error fetching investment firm:", error);
            } finally {
                this.isLoading = false;
            }
        },
        async toggleBookmark(firmId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/investment-firm/${firmId}/bookmark`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.ok) {
                    if (response.url.includes("/onboarding/")) {
                        window.location.href = response.url;
                    }
                    const data = await response.json();
                    if (data[0].bookmarked) {
                        this.$emit("bookmarked", { firmId: firmId, status: true });
                        this.isBookmarked = !this.isBookmarked;
                    } else {
                        this.$emit("bookmarked", { firmId: firmId, status: false });
                        this.isBookmarked = !this.isBookmarked;
                    }
                }
            } catch (error) {
                console.error(error);
            }
        },
        async sortInvestments(sortType) {
            const compareDates = (a, b) => {
                const dateA = new Date(a.announced_date);
                const dateB = new Date(b.announced_date);
                return sortType === "asc" ? dateA - dateB : dateB - dateA;
            };

            this.investments.sort(compareDates);

            // Force re-render
            this.investments = [...this.investments];
            this.sortOrder = sortType;
            this.sortDropdownOpened = false;
        },
        getTwitterHandle(url) {
            if (!url) return;
            return url.split("/").pop();
        },
        deleteInvestmentFirmParam() {
            const url = new URL(window.location.href);
            url.searchParams.delete("investment-firm");
            window.history.replaceState({}, "", url);
        },
        checkUrlParams() {
            const urlParams = new URLSearchParams(window.location.search);
            const investorSlug = urlParams.get("investment-firm");
            if (!investorSlug) {
                this.$emit("close-investment-firm");
            }
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.$emit("close-investment-firm");
            }
        },
        toggleExpansion() {
            this.isExpanded = !this.isExpanded;
        },
        сloseInvestmentFirm() {
            this.$emit("close-investment-firm");
        },
        handleClickOutside(event) {
            const dropdownContainer = this.$refs.dropdownContainer;
            if (dropdownContainer && !dropdownContainer.contains(event.target)) {
                this.dropdownOpened = false;
            }
        },
    },
    data() {
        return {
            isExpanded: false,
            isLoading: false,
            investmentFirm: null,
            isBookmarked: false,
            unpaid: false,
            sortDropdownOpened: false,
            sortOrder: null,
            investments: [],
            dropdownOpened: false,
        };
    },
});

const FullCompany = defineComponent({
    template: "#full-company-template",
    props: { slug: String },
    emits: ["close-company", "bookmarked"],
    delimiters: ["[[", "]]"],
    mounted() {
        window.addEventListener("keydown", this.handleKeyDown);
        document.addEventListener("click", this.handleClickOutside);
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleKeyDown);
        this.deleteCompanyParam();
        document.removeEventListener("click", this.handleClickOutside);
    },
    async created() {
        await this.fetchCompany();
        window.removeEventListener("popstate", this.checkUrlParams);
    },
    methods: {
        async fetchCompany() {
            this.isLoading = true;
            try {
                const response = await fetch(`/company/${this.slug}/get`);
                if (response.ok) {
                    const data = await response.json();
                    this.company = data.company;
                    this.unpaid = data.unpaid;
                    this.isBookmarked = data.isBookmarked;
                    if (data.investments) {
                        this.investments = data.investments;
                    }
                } else {
                    this.closeCompany();
                    return;
                }
            } catch (error) {
                console.error("Error fetching company:", error);
            } finally {
                this.isLoading = false;
            }
        },
        async toggleBookmark(companyId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/company/${companyId}/bookmark`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.ok) {
                    if (response.url.includes("/onboarding/")) {
                        window.location.href = response.url;
                    }
                    const data = await response.json();
                    if (data[0].bookmarked) {
                        this.$emit("bookmarked", { companyId: companyId, status: true });
                        this.isBookmarked = !this.isBookmarked;
                    } else {
                        this.$emit("bookmarked", { companyId: companyId, status: false });
                        this.isBookmarked = !this.isBookmarked;
                    }
                }
            } catch (error) {
                console.error(error);
            }
        },

        async sortInvestments(sortType) {
            const compareDates = (a, b) => {
                const dateA = new Date(a.announced_date);
                const dateB = new Date(b.announced_date);
                return sortType === "asc" ? dateA - dateB : dateB - dateA;
            };

            this.investments.sort(compareDates);

            // Force re-render
            this.investments = [...this.investments];
            this.sortOrder = sortType;
            this.sortDropdownOpened = false;
        },
        deleteCompanyParam() {
            const url = new URL(window.location.href);
            url.searchParams.delete("company");
            window.history.replaceState({}, "", url);
        },
        checkUrlParams() {
            const urlParams = new URLSearchParams(window.location.search);
            const investorSlug = urlParams.get("company");
            if (!investorSlug) {
                this.$emit("close-company");
            }
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.$emit("close-company");
            }
        },
        getTwitterHandle(url) {
            if (!url) return;
            return url.split("/").pop();
        },
        toggleExpansion() {
            this.isExpanded = !this.isExpanded;
        },
        closeCompany() {
            this.$emit("close-company");
        },
        handleClickOutside(event) {
            const dropdownContainer = this.$refs.dropdownContainer;
            if (dropdownContainer && !dropdownContainer.contains(event.target)) {
                this.dropdownOpened = false;
            }
        },
    },
    data() {
        return {
            isExpanded: false,
            isLoading: false,
            isBookmarked: false,
            company: null,
            unpaid: false,
            sortDropdownOpened: false,
            sortOrder: null,
            investments: [],
            dropdownOpened: false,
        };
    },
});

const app = createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
        FullInvestor,
        FullInvestmentFirm,
        FullCompany,
        SearchHistory,
        GeminiComponent,
    },
    watch: {
        asideMinified(value) {
            localStorage.setItem("asideMinified", value);
        },
        isGeminiOpened() {
            this.updateOverflow();
        },
        selectedInvestorSlug() {
            this.updateOverflow();
        },
        selectedInvestmentFirmId() {
            this.updateOverflow();
        },
    },
    created() {
        // posthog.capture("App Loaded");
        this.asideMinified = localStorage.getItem("asideMinified") === "true";
        window.addEventListener("popstate", this.checkUrlParams("investor", this.selectInvestorSlug, "close-investor"));
        window.addEventListener(
            "popstate",
            this.checkUrlParams("investment-firm", this.selectInvestmentFirmSlug, "close-investment-firm"),
        );
        window.addEventListener("popstate", this.checkUrlParams("company", this.selectCompanySlug, "close-company"));
        this.checkAndSelectUrlParam("investor", this.selectInvestorSlug);
        this.checkAndSelectUrlParam("investment-firm", this.selectInvestmentFirmSlug);
        this.checkAndSelectUrlParam("company", this.selectCompanySlug);
    },
    mounted() {
        const lowerSlider = document.getElementById("min_investment");
        const upperSlider = document.getElementById("max_investment");

        if (lowerSlider) {
            lowerSlider.oninput = this.handleLowerSliderInput;
        }

        if (upperSlider) {
            upperSlider.oninput = this.handleUpperSliderInput;
        }

        const searchBtn = document.getElementById("search-btn");
        if (searchBtn) {
            searchBtn.addEventListener("click", this.search);
        }

        this.updateOverflow();
        this.setupMenuToggle();
        this.initializeValuesFromParams();
        this.updateLinksWithQueryParams();
        window.addEventListener("popstate", this.checkUrlParams("investor", this.selectInvestorSlug, "close-investor"));
        window.addEventListener(
            "popstate",
            this.checkUrlParams("investment-firm", this.selectInvestmentFirmSlug, "close-investment-firm"),
        );
        window.addEventListener("popstate", this.checkUrlParams("company", this.selectCompanySlug, "close-company"));
        window.addEventListener("click", this.closeSortDropdownOutside);
        window.addEventListener("scroll", this.handleScroll);
    },
    updated() {
        window.addEventListener("popstate", this.checkUrlParams("investor", this.selectInvestorSlug, "close-investor"));
        window.addEventListener(
            "popstate",
            this.checkUrlParams("investment-firm", this.selectInvestmentFirmSlug, "close-investment-firm"),
        );
        window.addEventListener("popstate", this.checkUrlParams("company", this.selectCompanySlug, "close-company"));
    },

    methods: {
        async handleInvestorBookmark(data) {
            try {
                if (data.status) {
                    this.investorBookmakrIds.push(data.investorId); // Corrected typo
                    document.getElementById(`bookmark-svg-investor-${data.investorId}`).style.fill = "#FFC9FC";
                } else {
                    this.investorBookmakrIds = this.investorBookmakrIds.filter((id) => id !== data.investorId); // Corrected typo
                    document.getElementById(`bookmark-svg-investor-${data.investorId}`).style.fill = "none";
                }
            } catch (error) {
                console.error("Error handling investor bookmark:", error);
            }
        },
        async handleInvestmentFirmBookmark(data) {
            if (data.status) {
                this.investmentFirmBookmakrIds.push(data.firmId);
                document.getElementById(`bookmark-svg-firm-${data.firmId}`).style.fill = "#FFC9FC";
            } else {
                this.investmentFirmBookmakrIds = this.investmentFirmBookmakrIds.filter((id) => id !== data.firmId);
                document.getElementById(`bookmark-svg-firm-${data.firmId}`).style.fill = "none";
            }
        },
        async handleCompanyBookmark(data) {
            try {
                if (data.status) {
                    this.companyBookmarkIds.push(data.companyId);
                    document.getElementById(`bookmark-svg-company-${data.companyId}`).style.fill = "#FFC9FC";
                } else {
                    this.companyBookmarkIds = this.companyBookmarkIds.filter((id) => id !== data.companyId);
                    document.getElementById(`bookmark-svg-company-${data.companyId}`).style.fill = "none";
                }
            } catch (error) {
                console.error("Error handling company bookmark:", error);
            }
        },
        async getCountryList(searchInput) {
            let country_list = this.$refs.countryListElement;
            for (let i = 0; i < country_list.children.length; i++) {
                if (country_list.children[i].textContent.toUpperCase().includes(searchInput.toUpperCase())) {
                    country_list.children[i].classList.remove("hidden");
                } else {
                    country_list.children[i].classList.add("hidden");
                }
            }
        },
        async getIndustryList(searchInput) {
            let industry_list = this.$refs.industryListElement;
            for (let i = 0; i < industry_list.children.length; i++) {
                if (industry_list.children[i].textContent.toUpperCase().includes(searchInput.toUpperCase())) {
                    industry_list.children[i].classList.remove("hidden");
                } else {
                    industry_list.children[i].classList.add("hidden");
                }
            }
        },
        async toggleInvestorBookmark(investorId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/investor/${investorId}/bookmark`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.ok) {
                    if (response.url.includes("/onboarding/")) {
                        window.location.href = response.url;
                    }
                    const data = await response.json();
                    if (data[0].bookmarked) {
                        this.investorBookmakrIds.push(investorId);
                        document.getElementById(`bookmark-svg-investor-${investorId}`).style.fill = "#FFC9FC";
                    } else {
                        this.investorBookmakrIds = this.investorBookmakrIds.filter((id) => id !== investorId);
                        document.getElementById(`bookmark-svg-investor-${investorId}`).style.fill = "none";
                    }
                }
            } catch (error) {
                console.error(error);
            }
        },
        async toggleInvestmentFirmBookmark(firmId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/investment-firm/${firmId}/bookmark`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.ok) {
                    if (response.url.includes("/onboarding/")) {
                        window.location.href = response.url;
                    }
                    const data = await response.json();

                    if (data[0].bookmarked) {
                        this.investmentFirmBookmakrIds.push(firmId);
                        document.getElementById(`bookmark-svg-firm-${firmId}`).style.fill = "#FFC9FC";
                    } else {
                        this.investmentFirmBookmakrIds = this.investmentFirmBookmakrIds.filter((id) => id !== firmId);
                        document.getElementById(`bookmark-svg-firm-${firmId}`).style.fill = "none";
                    }
                }
            } catch (error) {
                console.error(error);
            }
        },
        async toggleCompanyBookmark(companyId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/company/${companyId}/bookmark`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.ok) {
                    if (response.url.includes("/onboarding/")) {
                        window.location.href = response.url;
                    }
                    const data = await response.json();
                    if (data[0].bookmarked) {
                        this.companyBookmarkIds.push(companyId);
                        document.getElementById(`bookmark-svg-company-${companyId}`).style.fill = "#FFC9FC";
                    } else {
                        this.companyBookmarkIds = this.companyBookmarkIds.filter((id) => id !== companyId);
                        document.getElementById(`bookmark-svg-company-${companyId}`).style.fill = "none";
                    }
                }
            } catch (error) {
                console.error(error);
            }
        },
        async markAsRead(notificationId) {
            try {
                const csrfToken = document.getElementById("csrf_token").value;
                const response = await fetch(`/notification/mark-read/${notificationId}`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.redirected) {
                    window.location.href = response.url;
                } else if (!response.ok) {
                    console.error("An error occurred while marking the notification as read.");
                }
            } catch (error) {
                console.error(error);
            }
        },
        checkAndSelectUrlParam(paramName, selectFunction) {
            const urlParams = new URLSearchParams(window.location.search);
            const paramSlug = urlParams.get(paramName);
            if (paramSlug) {
                selectFunction(paramSlug);
            }
        },
        checkUrlParams(paramName, selectFunction, closeEvent) {
            const urlParams = new URLSearchParams(window.location.search);
            let paramSlug = urlParams.get(paramName);
            if (paramSlug) {
                if (typeof paramSlug === "object" && paramSlug !== null) {
                    paramSlug = paramSlug;
                }
                selectFunction(paramSlug);
            } else {
                this.$emit(closeEvent);
            }
        },
        updateUrlParam(paramName, paramValue, stateKey) {
            const url = new URL(window.location.href);
            if (url.searchParams.get(paramName) !== paramValue) {
                url.searchParams.set(paramName, paramValue);
                window.history.pushState({}, "", url);
            }
            this[stateKey] = paramValue;
        },
        updateOverflow() {
            if (this.isGeminiOpened || this.selectedInvestorSlug || this.selectedInvestmentFirmId) {
                document.body.classList.add("overflow-hidden");
            } else {
                document.body.classList.remove("overflow-hidden");
            }
        },
        selectInvestorSlug(investorSlug) {
            this.updateUrlParam("investor", investorSlug, "selectedInvestorSlug");
        },
        selectInvestmentFirmSlug(investmentFirmSlug) {
            this.updateUrlParam("investment-firm", investmentFirmSlug, "selectedInvestmentFirmSlug");
        },
        selectCompanySlug(companySlug) {
            this.updateUrlParam("company", companySlug, "selectedCompanySlug");
        },
        openMenu() {
            document.getElementById("menu").classList.remove("hidden");
        },
        closeMenu() {
            document.getElementById("menu").classList.add("hidden");
        },
        initializeValuesFromParams() {
            const urlParams = new URLSearchParams(window.location.search);

            const paramsArray = [
                "filter_field",
                "round",
                "industry",
                "sort_field",
                "descending",
                "rounds_exclusive",
                "industries_exclusive",
                "country",
            ];
            paramsArray.forEach((inputName) => {
                const values = urlParams.getAll(inputName);
                values.forEach((value) => {
                    this.openAdvanced = true;
                    const checkbox = document.querySelector(`input[name="${inputName}"][value="${value}"]`);
                    if (checkbox) checkbox.checked = true;
                });
            });

            const value = urlParams.get("search");
            if (value !== null) {
                this.openAdvanced = true;
                document.getElementById("search").value = value;
            }

            this.setSliderValuesFromParams("min_investment");
            this.setSliderValuesFromParams("max_investment");
            if (this.openAdvanced) this.toggleAdvanced();
        },
        setSliderValuesFromParams(sliderId) {
            const urlParams = new URLSearchParams(window.location.search);
            const value = urlParams.get(sliderId);

            if (value !== null) {
                this.openAdvanced = true;
                const percentage = (value / 50000000) * 100;
                document.getElementById(sliderId).value = percentage;
            }
        },
        toggleAdvanced() {
            const advancedMenu = document.getElementById("advanced-menu");

            const openedAdvanced = document.getElementById("opened-advanced");
            const closedAdvanced = document.getElementById("closed-advanced");

            if (advancedMenu.classList.contains("hidden")) {
                advancedMenu.classList.remove("hidden");
                advancedMenu.classList.add("flex");

                openedAdvanced.classList.remove("hidden");
                closedAdvanced.classList.add("hidden");
            } else {
                advancedMenu.classList.add("hidden");
                advancedMenu.classList.remove("flex");

                openedAdvanced.classList.add("hidden");
                closedAdvanced.classList.remove("hidden");
            }
        },
        search(query = "") {
            const roundValues = this.getCheckedValues("round");
            const industryValues = this.getCheckedValues("industry");
            const countryValues = this.getCheckedValues("country");
            const sortValues = this.getCheckedValues("sort_field");
            const filterValues = this.getCheckedValues("filter_field");

            let searchQuery = document.getElementById("search").value;
            if (!searchQuery && typeof query == "string") {
                searchQuery = query;
            }

            const minValueElement = document.getElementById("min_investment");
            const minValue = minValueElement ? minValueElement.value : 0;

            const maxValueElement = document.getElementById("max_investment");
            const maxValue = maxValueElement ? maxValueElement.value : 100;

            const descendingElement = document.getElementById("descending");
            const descending = descendingElement ? descendingElement.checked : false;

            const roundsExclusiveElement = document.getElementById("rounds_exclusive");
            const roundsExclusive = roundsExclusiveElement ? roundsExclusiveElement.checked : false;

            const industriesExclusiveElement = document.getElementById("industries_exclusive");
            const industriesExclusive = industriesExclusiveElement ? industriesExclusiveElement.checked : false;

            const paramsArray = this.getExistingParams([
                "search",
                "filter_field",
                "rounds_exclusive",
                "industries_exclusive",
                "round",
                "industry",
                "country",
                "sort_field",
                "descending",
                "page",
                "min_investment",
                "max_investment",
            ]);

            this.handleLists(roundValues, "round", paramsArray);
            this.handleLists(industryValues, "industry", paramsArray);
            this.handleLists(countryValues, "country", paramsArray);
            this.handleLists(sortValues, "sort_field", paramsArray);
            this.handleLists(filterValues, "filter_field", paramsArray);

            this.handleInvestmentRange(minValue, "min_investment", paramsArray);
            this.handleInvestmentRange(maxValue, "max_investment", paramsArray);

            this.handleBooleans(roundsExclusive, "rounds_exclusive", paramsArray);
            this.handleBooleans(industriesExclusive, "industries_exclusive", paramsArray);
            this.handleBooleans(descending, "descending", paramsArray);

            if (searchQuery !== "") paramsArray.unshift(`search=${encodeURIComponent(searchQuery)}`);

            const paramsString = paramsArray.length > 0 ? "?" + paramsArray.join("&") : "";
            const baseUrl = window.location.href.split("?")[0];
            const newUrl = baseUrl + paramsString;

            window.location.href = newUrl;
        },
        getCheckedValues(inputName) {
            const checkboxes = document.querySelectorAll(`input[name="${inputName}"]:checked`);
            return Array.from(checkboxes).map((checkbox) => checkbox.value);
        },
        getExistingParams(excludedParams) {
            const urlParams = new URLSearchParams(window.location.search);
            let paramsArray = [];

            for (let param of urlParams) {
                if (!excludedParams.includes(param[0])) {
                    paramsArray.push(`${param[0]}=${encodeURIComponent(param[1])}`);
                }
            }

            return paramsArray;
        },
        handleLists(values, paramName, paramsArray) {
            values.forEach((value) => paramsArray.push(`${paramName}=${encodeURIComponent(value)}`));
        },
        handleInvestmentRange(value, paramName, paramsArray) {
            if (value == 0 || value == 100) return;
            if (value !== "") {
                const actualValue = Math.floor((value / 100) * 50000000);
                paramsArray.push(`${paramName}=${encodeURIComponent(actualValue)}`);
            }
        },
        handleBooleans(value, paramName, paramsArray) {
            if (value) {
                paramsArray.push(`${paramName}=${value ? 1 : ""}`);
            }
        },
        handleLowerSliderInput() {
            const lowerSlider = document.getElementById("min_investment");
            const upperSlider = document.getElementById("max_investment");

            if (parseInt(lowerSlider.value) >= parseInt(upperSlider.value)) {
                lowerSlider.value = parseInt(upperSlider.value) - 9;
            }
        },
        handleUpperSliderInput() {
            const lowerSlider = document.getElementById("min_investment");
            const upperSlider = document.getElementById("max_investment");

            if (parseInt(upperSlider.value) <= parseInt(lowerSlider.value)) {
                upperSlider.value = parseInt(lowerSlider.value) + 9;
            }
        },
        setupMenuToggle() {
            this.menus.forEach(({ menu, button }) => {
                const menuElement = document.getElementById(menu);
                const buttonElement = document.getElementById(button);

                if (!menuElement || !buttonElement) return;

                document.addEventListener("click", (event) => {
                    if (!menuElement.contains(event.target) && !buttonElement.contains(event.target)) {
                        menuElement.classList.remove(...this.showClasses);
                        menuElement.classList.add(...this.hideClasses);
                    }
                });

                buttonElement.onclick = () => {
                    if (menuElement.classList.contains(this.hideClasses[0])) {
                        menuElement.classList.add(...this.showClasses);
                        menuElement.classList.remove(...this.hideClasses);
                    } else {
                        menuElement.classList.remove(...this.showClasses);
                        menuElement.classList.add(...this.hideClasses);
                    }
                };
            });
        },
        applyQueryParams(url) {
            const params = new URLSearchParams(window.location.search);
            params.delete("page");
            params.delete("investor");
            params.delete("company");

            if (params.toString()) {
                return `${url}${url.includes("?") ? "&" : "?"}${params.toString()}`;
            }
            return url;
        },
        updateLinksWithQueryParams() {
            document.querySelectorAll('a[href^="/"]:not([href^="//"])').forEach((link) => {
                if (!link.getAttribute("href").includes("search")) return;
                link.setAttribute("href", this.applyQueryParams(link.getAttribute("href")));
            });
        },

        closeSortDropdownOutside() {
            this.sortDropdownOpened = false;
        },
        showSearchHistory() {
            this.isSearchHistoryVisible = true;
        },
        hideSearchHistory() {
            // Delay hiding to allow click event to be registered
            setTimeout(() => {
                this.isSearchHistoryVisible = false;
            }, 200);
        },
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            openAdvanced: false,
            isSearchHistoryVisible: false,
            isGeminiOpened: false,
            showPopover: false,
            selectedInvestorSlug: null,
            selectedInvestmentFirmSlug: null,
            selectedCompanySlug: null,
            bookmarkedInvestorId: null,
            investmentInvestorId: null,
            n_of_investments: 0,
            investorBookmakrIds: [],
            investmentFirmBookmakrIds: [],
            companyBookmarkIds: [],
            selectedIndustry: "",
            selectedCountry: "",
            menus: [
                { menu: "industry-options-menu", button: "industry-options" },
                { menu: "country-options-menu", button: "country-options" },
                { menu: "sorting-options-menu", button: "sorting-options" },
                { menu: "filter-options-menu", button: "filter-options" },
                { menu: "round-options-menu", button: "round-options" },
            ],
            showClasses: ["transform", "opacity-100", "scale-100"],
            hideClasses: ["opacity-0", "scale-95", "pointer-events-none"],
        };
    },
});

// app.use(posthogPlugin);

app.mount("#app");

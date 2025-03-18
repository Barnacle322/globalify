// const UploadFileComponent = defineComponent({
//     template: "#upload-file-template",
//     emits: ["close-upload-file"],
//     delimiters: ["[[", "]]"],
//
//     methods: {
//
//     }
//
//
//
//
// })


createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
        // UploadFileComponent,
    },
    delimiters: ["[[", "]]"],
    watch: {
        asideMinified(value) {
            localStorage.setItem("asideMinified", value);
        },
    },
    mounted() {
        document.addEventListener("click", this.handleClickOutside);
        this.asideMinified = localStorage.getItem("asideMinified") == "true";
    },
    methods: {
        handleFileUpload(event) {
            this.file = event.target.files[0];
            this.filename = this.file ? this.file.name : null;
            console.log("File:", this.file);

            this.showResults = false;
            this.deck = null;
            this.scores = null;
        },
        async analyzeFile() {
            if (!this.file) {
                this.uploadStatus = "Please select a file first";
                return;
            }
            this.uploadStatus = "Analyzing...";

            const formData = new FormData();
            formData.append("file", this.file);

            try {
                console.log("Before fetch");
                const response = await fetch("/deck/analysis", {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": document.getElementById("csrf_token").value,
                    },
                    body: formData,
                });

                console.log("After fetch");
                console.log("Response status:", response.status);

                if (!response.ok) {
                    throw new Error("Analysis failed");
                }

                const data = await response.json();
                console.log("Analysis result:", data);

                if (data.redirect_url) {
                    console.log("Redirect URL detected:", data.redirect_url);
                    // Directly redirect to the new URL
                    window.location.href = data.redirect_url;
                    return; // Exit function after redirect
                }
            } catch (error) {
                console.error("Error in analyzeFile:", error.message, error.stack);
                this.uploadStatus = error.message;
            }
        },
        async fetchDeck(deckId) {
            try {
                console.log("Fetching deck data for deckId:", deckId);
                const response = await fetch(`/deck/deck_results/${deckId}`);
                console.log("Fetch response status:", response.status);
                if (!response.ok) {
                    throw new Error(`Failed to fetch deck data: ${response.status}`);
                }
                const data = await response.json();
                console.log("Deck data:", data);
                this.deck = data.deck;
                this.scores = data.scores;
                this.showResults = true;
                this.printState();
            } catch (error) {
                console.error("Error fetching deck data:", error.message, error.stack);
                this.uploadStatus = error.message;
            }
        },

        async loadPageContent(url) {
            try {
                console.log("Fetching page content from:", url);
                const response = await fetch(url);
                console.log("Page fetch status:", response.status);
                if (!response.ok) {
                    throw new Error(`Failed to fetch page content: ${response.status}`);
                }
                const html = await response.text();
                console.log("Page content loaded:", html.substring(0, 100) + "..."); // Log snippet
                this.currentPage = html; // Inject HTML into the DOM
                // Update browser URL without reloading
                window.history.pushState({ deckId: this.getDeckIdFromUrl(url) }, "", url);
            } catch (error) {
                console.error("Error loading page content:", error.message, error.stack);
                this.uploadStatus = error.message;
            }
        },

        selectFeedback(feedback) {
            console.log("Selected Feedback:", feedback);
            this.selectedFeedback = feedback;
        },

        moveToPreviousCard() {
            const currentIndex = this.deckData.findIndex(deck => deck.id === this.selectedDeck.id);
            if (currentIndex > 0) {
                this.selectedDeck = this.deckData[currentIndex - 1];
                this.updateFeedback();
            }
        },
        moveToNextCard() {
            const currentIndex = this.deckData.findIndex(deck => deck.id === this.selectedDeck.id);
            if (currentIndex < this.deckData.length - 1) {
                this.selectedDeck = this.deckData[currentIndex + 1];
                this.updateFeedback();
            }
        },
        updateFeedback() {
            // This updates the feedback section based on the selected deck
            this.selectedFeedback = this.selectedDeck.feedback;
        },

    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            openAdvanced: false,
            showResults: false,
            file: null,
            filename: null,
            uploadStatus: null,
            deck: null,
            scores: null,
            selectedFeedback: null,
            currentPage: null,
            uploadFileComponent: false,
        };
    },
}).mount("#app");

    createApp({
        components: {
            AsideComponent,
            AsideMobileComponent,
            NavbarComponent,
            // AnalysisResultComponent,
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
            const currentPath = window.location.pathname;

            // Check if the path is /deck/page
            if (currentPath.startsWith('/deck/page')) {
                const parts = currentPath.split('/');
                const deckId = parts[parts.length - 1];

                // If deckId exists, fetch deck data
                if (deckId) {
                    this.fetchDeck(deckId).then(() => {
                        if (this.deck && this.deck.json_feedback && this.deck.json_feedback.length > 0) {
                            this.selectedFeedback = this.deck.json_feedback[0]; // Set first feedback as default
                        }
                        console.log("Scores after fetch:", this.scores); // Log after fetch completes
                    });
                } else {
                    console.log("No deckId found in URL");
                }
            } else {
                console.log("Not on a /deck/page URL");
            }
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
                    const response = await fetch("/deck/analysis", {
                        method: "POST",
                        headers: {
                            "X-CSRFToken": document.getElementById("csrf_token").value,
                        },
                        body: formData,
                    });

                    const data = await response.json();

                    if (!response.ok) {
                        throw new Error(data.error || "Analysis failed");
                    }

                    window.location.href = data.redirect_url;
                } catch (error) {
                    console.error("Error:", error);
                    this.uploadStatus = error.message;
                }
            },
            async fetchDeck(deckId) {
                try {
                    const response = await fetch(`/deck/deck_results/${deckId}`);
                    if (!response.ok) {
                        throw new Error("Failed to fetch deck data");
                    }
                    const data = await response.json();
                    this.deck = data.deck;

                    this.scores = data.scores;
                    console.log(this.deck)
                    this.showResults = true;
                } catch (error) {
                    console.error("Error fetching deck data:", error);
                    this.uploadStatus = error.message;
                }
            },

            selectFeedback(feedback) {
                console.log("Selected Feedback:", feedback);
                this.selectedFeedback = feedback;
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
            };
        },
    }).mount("#app");

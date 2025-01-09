const { defineComponent, createApp } = Vue;

createApp({
    methods: {
        startStream() {
            console.log("Starting stream...");
            this.response = [];
            this.queue = [];
            if (this.intervalId) {
                clearInterval(this.intervalId);
            }
            const eventSource = new EventSource(`/stream/${this.prompt}`);
            eventSource.onmessage = (event) => {
                this.queue.push(...event.data.split(""));
            };
            eventSource.onerror = () => {
                eventSource.close();
            };
            this.intervalId = setInterval(() => {
                if (this.queue.length > 0) {
                    const char = this.queue.shift();
                    if (char === "." || char === "," || char === "!" || char === "?") {
                        this.response.push(char);
                    } else if (
                        this.response.length > 0 &&
                        this.response[this.response.length - 1] !== " " &&
                        char !== " " &&
                        ![".", ",", "!", "?"].includes(this.response[this.response.length - 1])
                    ) {
                        this.response.push(" ", char);
                    } else {
                        this.response.push(char);
                    }
                }
            }, 1); // Adjust the interval time as needed
        },
    },
    data() {
        return {
            prompt: "",
            response: [],
            queue: [],
            intervalId: null,
        };
    },
}).mount("#app");

const FirstStageComponent = defineComponent({
    template: "#first-stage-template",
    delimiters: ["[[", "]]"],
    props: ['formData'],
    data() {
        return {};
    },
    methods: {
        nextPage() {
            this.$emit("change-page", 1); // Emit to move forward
        },
        previousPage() {
            this.$emit("change-page", -1); // Emit to move back
        }
    }
});

const SecondStageComponent = defineComponent({
    template: "#second-stage-template",
    delimiters: ["[[", "]]"],
    props: ['formData'],
    data() {
        return {};
    },
    methods: {
        previousPage() {
            this.$emit("change-page", -1); // Emit to move back
        },
        submit() {  // Change this method
            this.$emit("submit-form"); // Emit event to parent
    }
    }
});

createApp({
    components: {
        FirstStageComponent,
        SecondStageComponent,
    },
    data() {
        return {
            currentPage: parseInt(localStorage.getItem("currentPage")) || 1,
            enterClass: "slide-fade-in-left",
            leaveClass: "slide-fade-out-left",
            company_id: "",
            formData: {
                mission_statement: '',
                target_market: '',
                key_products: '',
                description: '',
                assets: '',
                awards: '',
                partnerships: '',
                team_description: '',
                customer_testimonials: '',
                founder_bio: ''
            },
        };
    },
    mounted() {
        this.company_id = document.getElementById('company_id')?.value || ""; // Fetch value after DOM is ready
    },
    computed: {
        currentComponent() {
            switch (this.currentPage) {
                case 1:
                    return FirstStageComponent;
                case 2:
                    return SecondStageComponent;
                default:
                    return FirstStageComponent;
            }
        },
    },
    methods: {
        changePage(pageNumber) {
            const newPage = this.currentPage + pageNumber;
            if (newPage >= 1 && newPage <= 2) {
                this.enterClass = pageNumber > 0 ? "slide-fade-in-left" : "slide-fade-in-right";
                this.leaveClass = pageNumber > 0 ? "slide-fade-out-left" : "slide-fade-out-right";
                this.currentPage = newPage;
                localStorage.setItem("currentPage", this.currentPage);
            }
        },
    async submitForm() {
        try {
            const csrfToken = document.getElementById('csrf_token').value;
            const dataToSend = { ...this.formData };

            const response = await fetch(`/microwebpage/create/${this.company_id}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': csrfToken // Include CSRF token if required by your backend
                },
                body: JSON.stringify(dataToSend)
            });

            if (!response.ok) {
                throw new Error('Submission failed');
            }

            const result = await response.json();
            console.log('Success:', result);
            if (result.redirect_url) {
                window.location.href = result.redirect_url;
            }
            this.resetForm();
        } catch (error) {
            console.error('Error submitting form:', error);
            alert('An error occurred while submitting the form. Please try again.');
        }
    },
    resetForm() {
        this.currentStage = 1;
        Object.keys(this.formData).forEach(key => {
            this.formData[key] = '';
        });
    }
    },
}).mount("#app");

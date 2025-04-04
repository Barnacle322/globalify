const FirstStageComponent = defineComponent({
    template: "#first-stage-template",
    delimiters: ["[[", "]]"],
    props: ['formData'],
    data() {
        return {
            errors: {}
        };
    },
    methods: {
        validateFields() {
            const isValid = this.formData.mission_statement.trim() !== '' &&
                         this.formData.target_market.trim() !== '' &&
                         this.formData.key_products.trim() !== '';

            this.$emit('first-stage-valid', isValid);
            return isValid;
        },
        nextPage() {
            if (this.validateFields()) {
                this.$emit("change-page", 1);
            }
        },
        previousPage() {
            this.$emit("change-page", -1);
        },
        goBack() {
            window.history.back();
        },
    },
    watch: {
        "formData.mission_statement": function() {
            this.validateFields();
        },
        "formData.target_market": function() {
            this.validateFields();
        },
        "formData.key_products": function() {
            this.validateFields();
        },
    },
});

const SecondStageComponent = defineComponent({
    template: "#second-stage-template",
    delimiters: ["[[", "]]"],
    props: ['formData', 'isFirstStageValid'],
    data() {
        return {};
    },
    methods: {
        previousPage() {
            this.$emit("change-page", -1);
        },
        submit() {
            this.$emit("submit-form");
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
            currentPage: 1,
            enterClass: "slide-fade-in-left",
            leaveClass: "slide-fade-out-left",
            company_id: "",
            storageKey: "microwebpage_form_data",
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
    computed: {
        currentComponent() {
            switch (this.currentPage) {
                case 1: return FirstStageComponent;
                case 2: return SecondStageComponent;
                default: return FirstStageComponent;
            }
        },
        isFirstStageValid() {
            return this.formData.mission_statement.trim() !== '' &&
                   this.formData.target_market.trim() !== '' &&
                   this.formData.key_products.trim() !== '';
        }
    },
    mounted() {
        this.company_id = document.getElementById('company_id')?.value || "";
        this.storageKey = `microwebpage_form_${this.company_id || 'new'}`;
        this.loadFormData();
    },
    methods: {
        changePage(pageNumber) {
            const newPage = this.currentPage + pageNumber;
            if (newPage >= 1 && newPage <= 2) {
                this.enterClass = pageNumber > 0 ? "slide-fade-in-left" : "slide-fade-in-right";
                this.leaveClass = pageNumber > 0 ? "slide-fade-out-left" : "slide-fade-out-right";
                this.currentPage = newPage;
                this.saveFormData();
            }
        },
        saveFormData() {
            localStorage.setItem(this.storageKey, JSON.stringify({
                formData: this.formData,
                currentPage: this.currentPage
            }));
        },
        loadFormData() {
            const savedData = localStorage.getItem(this.storageKey);
            if (savedData) {
                try {
                    const parsedData = JSON.parse(savedData);
                    this.formData = { ...this.formData, ...parsedData.formData };
                    this.currentPage = parsedData.currentPage || 1;
                } catch (e) {
                    console.error('Failed to parse saved form data', e);
                }
            }
        },
        clearFormData() {
            localStorage.removeItem(this.storageKey);
        },
        async submitForm() {
            try {
                const csrfToken = document.getElementById('csrf_token').value;
                const dataToSend = { ...this.formData };

                const response = await fetch(`/microwebpage/create/${this.company_id}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken
                    },
                    body: JSON.stringify(dataToSend)
                });

                if (!response.ok) {
                    throw new Error('Submission failed');
                }

                const result = await response.json();
                if (result.redirect_url) {
                    window.location.href = result.redirect_url;
                }
            } catch (error) {
                console.error('Error submitting form:', error);
                alert('An error occurred while submitting the form. Please try again.');
            }
        },
        resetForm() {
            Object.keys(this.formData).forEach(key => {
                this.formData[key] = '';
            });
            this.currentPage = 1;
            this.clearFormData();
        }
    },
    watch: {
        formData: {
            handler() {
                this.saveFormData();
            },
            deep: true
        }
    }
}).mount("#app");
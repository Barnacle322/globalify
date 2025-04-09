const FirstStageComponent = defineComponent({
    template: "#first-stage-template",
    delimiters: ["[[", "]]"],
    props: ['formData'],
    data() {
        return {
            errors: {
                hero_title: '',
                hero_subtitle: '',
                mission_title: '',
                mission_statement: '',
                leadership_title: '',
                leadership_subtitle: '',
                customer_testimonials_title: '',
                customer_testimonials_subtitle: '',
                images: ''
            }
        };
    },
    methods: {
        validateFields() {
            let isValid = true;

            // Reset errors
            this.errors = {
                hero_title: '',
                hero_subtitle: '',
                mission_title: '',
                mission_statement: '',
                leadership_title: '',
                leadership_subtitle: '',
                customer_testimonials_title: '',
                customer_testimonials_subtitle: '',
                images: ''
            };

            // Validate required fields
            if (!this.formData.hero_title?.trim()) {
                this.errors.hero_title = 'Hero title is required';
                isValid = false;
            }

            if (!this.formData.hero_subtitle?.trim()) {
                this.errors.hero_subtitle = 'Hero subtitle is required';
                isValid = false;
            }

            if (!this.formData.mission_title?.trim()) {
                this.errors.mission_title = 'Mission title is required';
                isValid = false;
            }

            if (!this.formData.mission_statement?.trim()) {
                this.errors.mission_statement = 'Mission statement is required';
                isValid = false;
            }

            if (!this.formData.leadership_title?.trim()) {
                this.errors.leadership_title = 'Leadership title is required';
                isValid = false;
            }

            if (!this.formData.leadership_subtitle?.trim()) {
                this.errors.leadership_subtitle = 'Leadership subtitle is required';
                isValid = false;
            }

            if (!this.formData.customer_testimonials_title?.trim()) {
                this.errors.customer_testimonials_title = 'Testimonials title is required';
                isValid = false;
            }

            if (!this.formData.customer_testimonials_subtitle?.trim()) {
                this.errors.customer_testimonials_subtitle = 'Testimonials subtitle is required';
                isValid = false;
            }

            if (this.formData.images.length === 0) {
                this.errors.images = 'At least one company photo is required';
                isValid = false;
            }

            this.$emit('first-stage-valid', isValid);
            return isValid;
        },
        nextPage() {
            if (this.validateFields()) {
                this.$emit("change-page", 1);
            }
        },
        goBack() {
            window.history.back();
        },
        handleLogoUpload(event) {
            const file = event.target.files[0];
            if (!file) return;

            if (!file.type.match('image.*')) {
                alert('Please upload an image file (PNG, JPG, etc.)');
                event.target.value = '';
                return;
            }

            this.formData.logoFile = file;

            // Create preview
            const reader = new FileReader();
            reader.onload = (e) => {
                this.formData.logoPreview = e.target.result;
            };
            reader.readAsDataURL(file);
        },
        handleImageUpload(event) {
            const files = event.target.files;
            if (!files.length) return;

            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                        if (!file.type.match('image.*')) continue;

                        const reader = new FileReader();
                        reader.onload = (e) => {
                            this.formData.images.push({
                                file: file,  // Ensure the original File object is stored
                                preview: e.target.result
                            });
                            console.log('Added image:', file); // Debug here
                        };
                        reader.readAsDataURL(file);
                    }

            event.target.value = '';
            // Clear images error if we now have images
            if (this.formData.images.length > 0) {
                this.errors.images = '';
            }
        },
        removeImage(index) {
            this.formData.images.splice(index, 1);
            // If no images left, set error
            if (this.formData.images.length === 0) {
                this.errors.images = 'At least one company photo is required';
            }
        }
    },
    watch: {
        "formData.hero_title": function() {
            if (this.formData.hero_title?.trim()) {
                this.errors.hero_title = '';
            }
        },
        "formData.hero_subtitle": function() {
            if (this.formData.hero_subtitle?.trim()) {
                this.errors.hero_subtitle = '';
            }
        },
        "formData.mission_title": function() {
            if (this.formData.mission_title?.trim()) {
                this.errors.mission_title = '';
            }
        },
        "formData.mission_statement": function() {
            if (this.formData.mission_statement?.trim()) {
                this.errors.mission_statement = '';
            }
        },
        "formData.leadership_title": function() {
            if (this.formData.leadership_title?.trim()) {
                this.errors.leadership_title = '';
            }
        },
        "formData.leadership_subtitle": function() {
            if (this.formData.leadership_subtitle?.trim()) {
                this.errors.leadership_subtitle = '';
            }
        },
        "formData.customer_testimonials_title": function() {
            if (this.formData.customer_testimonials_title?.trim()) {
                this.errors.customer_testimonials_title = '';
            }
        },
        "formData.customer_testimonials_subtitle": function() {
            if (this.formData.customer_testimonials_subtitle?.trim()) {
                this.errors.customer_testimonials_subtitle = '';
            }
        },
        "formData.images": {
            handler: function(newVal) {
                if (newVal.length > 0) {
                    this.errors.images = '';
                }
            },
            deep: true
        }
    },
});

const SecondStageComponent = defineComponent({
    template: "#second-stage-template",
    delimiters: ["[[", "]]"],
    props: ['formData', 'isFirstStageValid'],
    data() {
        return {
            tech_stack_input: '',
            new_faq_question: '',
            new_faq_answer: '',
            new_award_title: '',
            new_award_description: '',
            new_partnership_name: '',
            new_partnership_details: '',
            new_growth_metric: '',
            new_growth_value: ''
        };
    },
    methods: {
        previousPage() {
            this.$emit("change-page", -1);
        },
        submit() {
            this.$emit("submit-form");
        },
        addTechStackItem() {
            if (this.tech_stack_input.trim()) {
                if (!this.formData.tech_stack) {
                    this.formData.tech_stack = [];
                }
                this.formData.tech_stack.push(this.tech_stack_input.trim());
                this.tech_stack_input = '';
            }
        },
        removeTechStackItem(index) {
            this.formData.tech_stack.splice(index, 1);
        },
        addKeyProduct() {
            if (!this.formData.key_products) {
                this.formData.key_products = [];
            }
            this.formData.key_products.push({ name: '', description: '' });
        },
        removeKeyProduct(index) {
            this.formData.key_products.splice(index, 1);
        },
        addFaqItem() {
            if (this.new_faq_question.trim() && this.new_faq_answer.trim()) {
                if (!this.formData.faq) {
                    this.formData.faq = [];
                }
                this.formData.faq.push({
                    question: this.new_faq_question.trim(),
                    answer: this.new_faq_answer.trim()
                });
                this.new_faq_question = '';
                this.new_faq_answer = '';
            }
        },
        removeFaqItem(index) {
            this.formData.faq.splice(index, 1);
        },
        addAwardItem() {
            if (this.new_award_title.trim()) {
                if (!this.formData.awards) {
                    this.formData.awards = [];
                }
                this.formData.awards.push({
                    title: this.new_award_title.trim(),
                    description: this.new_award_description.trim()
                });
                this.new_award_title = '';
                this.new_award_description = '';
            }
        },
        removeAwardItem(index) {
            this.formData.awards.splice(index, 1);
        },
        addPartnershipItem() {
            if (this.new_partnership_name.trim()) {
                if (!this.formData.partnerships) {
                    this.formData.partnerships = [];
                }
                this.formData.partnerships.push({
                    name: this.new_partnership_name.trim(),
                    details: this.new_partnership_details.trim()
                });
                this.new_partnership_name = '';
                this.new_partnership_details = '';
            }
        },
        removePartnershipItem(index) {
            this.formData.partnerships.splice(index, 1);
        },
        addGrowthItem() {
            if (this.new_growth_metric.trim() && this.new_growth_value.trim()) {
                if (!this.formData.user_growth) {
                    this.formData.user_growth = [];
                }
                this.formData.user_growth.push({
                    metric: this.new_growth_metric.trim(),
                    value: this.new_growth_value.trim()
                });
                this.new_growth_metric = '';
                this.new_growth_value = '';
            }
        },
        removeGrowthItem(index) {
            this.formData.user_growth.splice(index, 1);
        }
    },
    mounted() {
        // Initialize arrays if they don't exist
        if (!this.formData.tech_stack) {
            this.$set(this.formData, 'tech_stack', []);
        }
        if (!this.formData.key_products) {
            this.$set(this.formData, 'key_products', [{}]);
        }
        if (!this.formData.faq) {
            this.$set(this.formData, 'faq', []);
        }
        if (!this.formData.awards) {
            this.$set(this.formData, 'awards', []);
        }
        if (!this.formData.partnerships) {
            this.$set(this.formData, 'partnerships', []);
        }
        if (!this.formData.user_growth) {
            this.$set(this.formData, 'user_growth', []);
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
                // First stage fields
                images: [],
                logoFile: null,
                logoPreview: null,
                hero_title: '',
                hero_subtitle: '',
                mission_title: '',
                mission_statement: '',
                leadership_title: '',
                leadership_subtitle: '',
                customer_testimonials_title: '',
                customer_testimonials_subtitle: '',

                // Second stage fields
                team_title: '',
                team_subtitle: '',
                legal_structure: '',
                year_founded: null,
                business_model: '',
                target_market: '',
                market_positioning: '',
                revenue_streams: '',
                intellectual_property: '',
                sustainability_initiatives: '',
                founder_bio: '',
                tech_stack: [],
                key_products: [],
                faq: [],
                awards: [],
                partnerships: [],
                user_growth: []
            },
        };
    },
    computed: {
        currentComponent() {
            return this.currentPage === 1 ? 'FirstStageComponent' : 'SecondStageComponent';
        },
        isFirstStageValid() {
            return this.formData.hero_title.trim() !== '' &&
                   this.formData.hero_subtitle.trim() !== '' &&
                   this.formData.mission_title.trim() !== '' &&
                   this.formData.mission_statement.trim() !== '' &&
                   this.formData.leadership_title.trim() !== '' &&
                   this.formData.leadership_subtitle.trim() !== '' &&
                   this.formData.customer_testimonials_title.trim() !== '' &&
                   this.formData.customer_testimonials_subtitle.trim() !== '' &&
                   this.formData.images.length > 0;
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
            const dataToSave = {...this.formData};
            // Remove file objects that can't be serialized
            delete dataToSave.logoFile;
            // Convert images array to serializable format
            dataToSave.images = dataToSave.images.map(img => ({
                preview: img.preview
                // file object is not saved
            }));

            localStorage.setItem(this.storageKey, JSON.stringify({
                formData: dataToSave,
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
                const formData = new FormData();

                // Append all simple fields
                Object.keys(this.formData).forEach(key => {
                    if (key !== 'logoFile' && key !== 'images' &&
                        key !== 'tech_stack' && key !== 'key_products' &&
                        key !== 'faq' && key !== 'awards' &&
                        key !== 'partnerships' && key !== 'user_growth' &&
                        this.formData[key] !== null) {
                        formData.append(key, this.formData[key]);
                    }
                });

                // Append arrays as JSON strings
                ['tech_stack', 'key_products', 'faq', 'awards', 'partnerships', 'user_growth'].forEach(arrayField => {
                    if (this.formData[arrayField] && this.formData[arrayField].length > 0) {
                        formData.append(arrayField, JSON.stringify(this.formData[arrayField]));
                    }
                });

                // Append logo file if exists
                if (this.formData.logoFile) {
                    formData.append('logo', this.formData.logoFile);
                }

                // Append images
                this.formData.images.forEach((img, index) => {
                    if (img.file) {
                        console.log(`Appending image ${index}:`, img.file); // Debug each image
                        formData.append("images[]", img.file);
                    }
                });

                const response = await fetch(`/microwebpage/create/${this.company_id}`, {
                    method: 'POST',
                    headers: {
                        'X-CSRF-Token': csrfToken
                    },
                    body: formData
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
            this.formData = {
                images: [],
                logoFile: null,
                logoPreview: null,
                hero_title: '',
                hero_subtitle: '',
                mission_title: '',
                mission_statement: '',
                leadership_title: '',
                leadership_subtitle: '',
                customer_testimonials_title: '',
                customer_testimonials_subtitle: '',
                team_title: '',
                team_subtitle: '',
                legal_structure: '',
                year_founded: null,
                business_model: '',
                target_market: '',
                market_positioning: '',
                revenue_streams: '',
                intellectual_property: '',
                sustainability_initiatives: '',
                founder_bio: '',
                tech_stack: [],
                key_products: [],
                faq: [],
                awards: [],
                partnerships: [],
                user_growth: []
            };
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
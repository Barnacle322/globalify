createApp({


    methods: {
        submitForm() {
            console.log('Form submitted:', this.form)
        }
    },


    data(){
        return {
                asideExpanded: false,
                asideMinified: false,
                form: {
                    name: '',
                    description: '',
                    logo_url: '',
                    website_url: '',
                    contact_email: '',
                    employee_number: 0
                }
            }
        }



}).mount("app")
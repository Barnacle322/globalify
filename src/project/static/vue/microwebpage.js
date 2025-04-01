createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
    },

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
    },


    data(){
        return {
            asideExpanded: false,
            asideMinified: false,
            openAdvanced: false,

            form: {
                name: '',
                description: '',
                logo_url: '',
                website_url: '',
                contact_email: '',
                employee_number: 0
            }
        }
    },
}).mount("app")

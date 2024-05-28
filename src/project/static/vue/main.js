createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
        Bookmark,
    },
    watch: {
        asideMinified(value) {
            localStorage.setItem("asideMinified", value);
        },
    },
    created() {
        this.asideMinified = localStorage.getItem("asideMinified") === "true";
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
        };
    },
}).mount("#app");

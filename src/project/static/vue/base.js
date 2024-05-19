const { defineComponent, createApp } = Vue;

const AsideComponent = defineComponent({
    props: ["place", "minified"],
    template: "#aside-template",
    data() {
        return {
            currentPath: null,
        };
    },
    mounted() {
        this.currentPath = window.location.pathname.split("/")[1];
        if (["suggestions", "investor"].includes(this.currentPath)) {
            this.currentPath = "search";
        }
    },
});

const AsideMobileComponent = defineComponent({
    template: "#aside-mobile-template",
    methods: {
        closeAside() {
            this.$emit("close-aside");
        },
    },
    data() {
        return {
            currentPath: null,
        };
    },
    mounted() {
        this.currentPath = window.location.pathname.split("/")[1];
    },
});

const NavbarComponent = defineComponent({
    template: "#navbar-template",
    emits: ["open-aside"],
    methods: {
        expandAside() {
            this.$emit("open-aside");
        },
        handleAllNotificationsRead() {
            this.notifications.forEach((notification) => {
                notification.is_read = true;
            });
        },
    },
});

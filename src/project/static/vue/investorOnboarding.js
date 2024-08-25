const { defineComponent, createApp } = Vue;

createApp({
    components: {},

    data() {
        return {
            varr: "hello",
        };
    },
    methods: {
        hello() {
            console.log(this.varr);
        },
    },
}).mount("#app");

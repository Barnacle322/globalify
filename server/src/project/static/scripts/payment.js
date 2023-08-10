document.addEventListener("DOMContentLoaded", async () => {
    const { publishableKey } = await fetch("/payment/config").then((r) => r.json());
    const stripe = Stripe(publishableKey);

    const { clientSecret } = await fetch("/payment/create-payment-intent", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
    }).then((r) => r.json());

    const appearance = {
        theme: 'night',
        variables: {
            borderRadius: '4px',
            colorBackground: '#000000',
            colorPrimary: '#36B7FF',
            colorPrimaryText: '#1A1B25',
            colorText: 'white',
            colorTextSecondary: 'white',
            colorTextPlaceholder: '#727F96',
            colorIconTab: 'white',
            colorLogo: 'dark'
          },
        rules: {
            '.Input': {
              border: '2px solid'
            }
        }
    };
    const elements = stripe.elements({ clientSecret, appearance });

    const paymentElement = elements.create("payment");
    paymentElement.mount("#payment-element");

    const form = document.getElementById('payment-form');
    let submitted = false;
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
  
      // Disable double submission of the form
      if(submitted) { return; }
      submitted = true;
      form.querySelector('button').disabled = true;
  
      const nameInput = document.querySelector('#name');
  
      // Confirm the payment given the clientSecret
      // from the payment intent that was just created on
      // the server.
      const {error: stripeError} = await stripe.confirmPayment({
        elements,
        confirmParams: {
          return_url: `${window.location.origin}/payment/complete`,
        }
      });
  
      if (stripeError) {
        const messages = document.getElementById('error-messages');
        messages.innerText = stripeError.message;
        addMessage(stripeError.message);
        submitted = false;
        form.querySelector('button').disabled = false;
        return;
      }
    });
});

#! /usr/bin/env python3.6
# Python 3.6 or newer required.
import stripe

# This is your real test secret API key.
stripe.api_key = (
    "sk_test_51NZyTUDsBtpSnIdQ0GUJud2HlXGnHweQ21dtrZWmZJ4PehZVd4TmramS1TizgD3vpZxLLuusrNgRLSB4yrZfHrqf00yZFxTlcg"
)
# You probably have a database to keep track of preexisting customers
# But to keep things simple, we'll use an Object to store Stripe object IDs in this example.
CUSTOMERS = [{"stripe_id": "cus_RTEE83PgiGeVrx", "email": "imamidinov.agahan09@gmail.com"}]
# Prices in Stripe model the pricing scheme of your business.
# Create Prices in the Dashboard or with the API before accepting payments
# and store the IDs in your database.
PRICES = {"basic": "price_1RUPAYDsBtpSnIdQpcbp2Fdk", "professional": "price_1RUPAYDsBtpSnIdQpcbp2Fdk"}


def send_invoice(email):
    # Look up a customer in your database
    customers = [c for c in CUSTOMERS if c["email"] == email]
    if customers:
        customer_id = customers[0]["stripe_id"]
    else:
        # Create a new Customer
        customer = stripe.Customer.create(
            email=email,  # Use your email address for testing purposes
            description="Customer to invoice",
        )
        # Store the customer ID in your database for future purchases
        CUSTOMERS.append({"stripe_id": customer.id, "email": email})
        # Read the Customer ID from your database
        customer_id = customer.id

    # Create an Invoice
    invoice = stripe.Invoice.create(
        customer=customer_id,
        collection_method="send_invoice",
        days_until_due=30,
    )

    # Create an Invoice Item with the Price and Customer you want to charge
    stripe.InvoiceItem.create(customer=customer_id, price=PRICES["basic"], invoice=invoice.id)

    # Send the Invoice
    invoice = stripe.Invoice.finalize_invoice(invoice.id)
    stripe.Invoice.send_invoice(invoice.id)
    return

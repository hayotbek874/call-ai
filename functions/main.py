
import os
from flask import Flask, request, jsonify
from firebase_functions import https_fn
from firebase_admin import initialize_app

# Assuming crm_client.py is in the same directory
from crm_client import CRMClient

initialize_app()

app = Flask(__name__)

# Initialize CRM Client
# IMPORTANT: Store these in environment variables in a real application
CRM_URL = os.environ.get("RETAILCRM_URL", "https://your-crm-domain.retailcrm.pro")
CRM_API_KEY = os.environ.get("RETAILCRM_API_KEY", "your-api-key")
crm = CRMClient(CRM_URL, CRM_API_KEY)

@app.route("/orders", methods=["POST"])
def process_order():
    try:
        data = request.get_json()

        # 1. Extract data from the frontend request
        call_id = data.get("callId")
        phone_number = data.get("phoneNumber")
        analysis = data.get("analysis", {})
        customer_info = analysis.get("customer", {})
        items = analysis.get("items", [])
        transcript = data.get("transcript", "")
        recording_url = data.get("recordingUrl", "")

        if not call_id or not phone_number or not customer_info.get("name"):
            return jsonify({"error": "Missing required fields"}), 400

        # 2. Check if customer exists, otherwise create it
        site_code = "default" # Or determine dynamically if you have multiple sites
        customer_resp = crm.customers(filters={"name": phone_number})
        customer_id = None

        if customer_resp.is_successful() and customer_resp["customers"]:
            customer_id = customer_resp["customers"][0]["id"]
            print(f"Found existing customer with ID: {customer_id}")
        else:
            new_customer = {
                "firstName": customer_info.get("name"),
                "phones": [{"number": phone_number}],
                "address": {"text": customer_info.get("address")}
            }
            create_customer_resp = crm.customer_create(new_customer, site=site_code)
            if create_customer_resp.is_successful():
                customer_id = create_customer_resp["id"]
                print(f"Created new customer with ID: {customer_id}")
            else:
                 return jsonify({"error": "Failed to create customer", "details": create_customer_resp.get_errors()}), 500


        # 3. Create the order
        if customer_id and items:
            order = {
                "customer": {"id": customer_id},
                "items": items,
                "status": "new", # Or a different default status
                "orderMethod": "phone-call", # Or a different method
                "managerComment": f"Order created via AI Call Center.\n\nTranscript:\n{transcript}"
            }
            create_order_resp = crm.order_create(order, site=site_code)
            if not create_order_resp.is_successful():
                 return jsonify({"error": "Failed to create order", "details": create_order_resp.get_errors()}), 500
            print(f"Successfully created order with ID: {create_order_resp['id']}")

        # 4. Log the call event to CRM
        call_event = {
            "phone": phone_number,
            "type": "in", # Assuming incoming call
            "hangupStatus": "answered",
            "externalId": call_id,
            "recordUrl": recording_url
        }
        crm.telephony_call_event(call_event)

        return jsonify({"status": "success", "customerId": customer_id}), 201

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

# Expose the Flask app as a single Cloud Function
@https_fn.on_request()
def api(req: https_fn.Request) -> https_fn.Response:
    with app.request_context(req.environ):
        return app.full_dispatch_request()


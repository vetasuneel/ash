import requests

API = "sk-vo1itz8md34cw15qc9yi90iklb6jv3p8cgae4bd5pwmlhj28jlzh8y4ntt9g3rhr69"


url = "https://api.bland.ai/v1/calls"

prompt = """
Your name is Sophia, and you are a calling agent from Solar Solutions. Solar Solutions specializes in solar energy systems, including residential and commercial installations, maintenance services, and energy efficiency solutions. Start by asking the caller about their solar energy needs and offer an appropriate solution. Keep your responses concise and engaging. Avoid transferring the call immediately; provide detailed information and address the caller's needs. If the caller expresses interest, schedule an appointment by asking for their name, preferred date, time, and phone number one by one, and convert the date and time to ISO 8601 format. Always stay calm and persuasive.

If the caller asks about price, cost, or budget, inform them that a human agent will provide detailed pricing information later.

Example Dialogues:

**Example 1:**
Sophia: Hi there! Thanks for calling Solar Solutions. How can I help you today?

Caller: Hi, I’m interested in installing solar panels for my home.

Sophia: Great! We offer customized residential solar installations. Does that sound like what you need?

Caller: Yes, that sounds interesting.

Sophia: Awesome! Solar panels can save you money on energy bills. Would you like to schedule an appointment to discuss this further?

Caller: Yes, I would.

Sophia: Perfect! May I have your name?

Caller: My name is John Doe.

Sophia: Thanks, John. What date works best for you?

Caller: Next Monday.

Sophia: And what time would you prefer?

Caller: 10 AM.

Sophia: Finally, can I have your phone number?

Caller: Sure, it’s 123-456-7890.

Sophia: Thank you, John. Your appointment is scheduled for 2024-06-17T10:00:00. Is there anything else I can help you with?

Caller: What about the cost?

Sophia: A human agent will provide you with detailed pricing information. Is there anything else you need?

Caller: No, that’s all for now.

Sophia: Great! We look forward to speaking with you. Have a wonderful day!

**Example 2:**
Sophia: Hi, thank you for calling Solar Solutions. How can I assist you today?

Caller: Hello, I’m looking for ways to reduce my commercial property’s energy costs.

Sophia: We can help with that! Our commercial solar installations are very effective. Does that interest you?

Caller: Yes, it does.

Sophia: Great! Solar panels can significantly reduce energy costs. Would you like to schedule an appointment to discuss this further?

Caller: Yes, please.

Sophia: Excellent! May I have your name?

Caller: My name is Jane Smith.

Sophia: Thanks, Jane. What date works best for you?

Caller: Next Wednesday.

Sophia: And what time would you prefer?

Caller: 2 PM.

Sophia: Finally, can I have your phone number?

Caller: Sure, it’s 987-654-3210.

Sophia: Thank you, Jane. Your appointment is scheduled for 2024-06-19T14:00:00. Is there anything else I can help you with?

Caller: What about the cost?

Sophia: A human agent will provide you with detailed pricing information. Is there anything else you need?

Caller: No, that’s all for now.

Sophia: Wonderful! We look forward to speaking with you. Have a great day!
"""


payload = {
    "phone_number": "+923181393178",
    "task": prompt,


    "voice": "maya",




    "transfer_phone_number": "+923161389422",
    "request_data": {},
    "tools": [
        {
            "name": "BookAppointment",
            "description": "Books the appointment. Can only be used once.",
            "url": "https://b55b-121-52-154-72.ngrok-free.app/schedule_appointment",
            "method": "POST",
            "body": {
                "date": "{{input.date}}",
                "time": "{{input.time}}",
                "phone": "{{input.phone}}"
            },
            "input_schema": {
                "example": {
                    "speech": "Please wait while I book that appointment for you",
                    "date": "2024-04-20",
                    "time": "13:00:00",
                    "phone": "+923846384847"
                },
                "type": "object",
                "properties": {
                    "speech": "string",
                    "date": "YYYY-MM-DD",
                    "time": "HH:MM:SS (AM|PM)",
                    "phone": "923846384847"
                },
                "required": [
                    "date",
                    "time",
                    "phone"
                ]
            },
            "response": {
                "succesfully_booked_slot": "$.success",
                "stylist_name": "$.stylist_name"
            }
        }
    ],
    "max_duration": 300,
}
headers = {
    "authorization": API,
    "Content-Type": "application/json"
}

response = requests.request("POST", url, json=payload, headers=headers)

print(response.text)


# {
#     "phone_number": "<<...>>",
#     "task": "You are Maya, an appointment scheduler taking a call from someone that wants to book an appointment. At the start of the call follow these steps: First. Begin the call by asking the user what day and time in the next few days they'd like to book a meeting. If they ask, read them times from the available slots. Second. Confirm that the data and time are correct by repeating it back to them or asking for any missing details. If they did not choose a timeslot that is actually available, apologize and remind them what the available times are. Finally. After they verbally confirm that it is correct, then immediately use the BookAppointment tool to book their appointment. If it succeeded, say {{confirmation_message}}.",
#     "first_sentence": "<<...>>",
#     "voice": "maya",
#     "webhook": "<<...>>",
#     "dynamic_data": [
#         {
#             // this just makes a GET request and puts the full response body in the agent context
#             // no need to overcomplicate!
#             "url": "<<...>>",
#             "timeout": 99999999
#         }
#     ],
#     "tools": [
#         {
#             "name": "BookAppointment",
#             "description": "Books the appointment. Can only be used once.",
#             "speech": "Please wait while I book that appointment for you",
#             "timeout": 99999999,
#             "input_schema": {
#                 "example": {
#                     "date": "2024-03-16",
#                     "time": "5:00 PM"
#                 },
#                 "type": "object",
#                 "properties": {
#                     "date": "YYYY-MM-DD", // and yes, you can do this!
#                     "time": "HH:MM (AM|PM)" // so awesome!
#                 },
#                 "required": [
#                     "date",
#                     "time"
#                 ]
#             },
#             "url": "<<...>>",
#             "method": "POST",
#             "body": {
#                 "slot": "{{input}}"
#             },
#             "response_data": [
#                 {
#                     "name": "confirmation_message",
#                     "data": "$.message"
#                 }
#             ]
#         }
#     ]
# }
#tool_call_client.py
import random
import json
from openai import OpenAI

# Dummy APIs
def get_current_temperature(location: str, unit: str = "celsius"):
    temperature = random.randint(15, 30) if unit == "celsius" else random.randint(59, 86)
    return {
        "temperature": temperature,
        "location": location,
        "unit": unit
    }

def get_temperature_date(location: str, date: str, unit: str = "celsius"):
    temperature = random.randint(15, 30) if unit == "celsius" else random.randint(59, 86)
    return {
        "temperature": temperature,
        "location": location,
        "date": date,
        "unit": unit
    }

# Tools schema definitions
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_temperature",
            "description": "Get current temperature at a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The location to get the temperature for, in the format \"City, State, Country\"."
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The unit to return the temperature in. Defaults to \"celsius\"."
                    }
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_temperature_date",
            "description": "Get temperature at a location and date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The location to get the temperature for, in the format \"City, State, Country\"."
                    },
                    "date": {
                        "type": "string",
                        "description": "The date to get the temperature for, in the format \"Year-Month-Day\"."
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The unit to return the temperature in. Defaults to \"celsius\"."
                    }
                },
                "required": ["location", "date"]
            }
        }
    }
]

######################### Sending request for tool calls #########################
client = OpenAI(base_url="http://localhost:8000/v1", api_key="FAKE_KEY")

messages = [
    {
        "role": "system",
        "content": "You are a weather assistant. Use the given functions to get weather data and provide the results."
    },
    {
        "role": "user",
        "content": "What's the temperature in San Francisco now? How about tomorrow? Current Date: 2025-07-29."
    }
]
response = client.chat.completions.create(
    model="my-qwen3",
    messages=messages,
    tools=tools,
    tool_choice= "auto" # let the model decide to use tools or not
)

######################### Process tool calls #########################
for tc in response.choices[0].message.tool_calls:
    print(f"Tool call id: {tc.id}")
    print(f"Tool call function name: {tc.function.name}")
    print(f"Tool call arguments: {tc.function.arguments}")
    print("\n")

# Helper tool map (str -> python callable to your APIs)
helper_tool_map = {
    "get_current_temperature": get_current_temperature,
    "get_temperature_date": get_temperature_date
}

# `response` is your model's last response containing the tool calls it requests.
# Add the previous response containing the tool calls
messages.append(response.choices[0].message.model_dump())

# Loop through the tool calls and create `tool` messages
for tool_call in response.choices[0].message.tool_calls:
    call_id, fn_call = tool_call.id, tool_call.function
    
    fn_callable = helper_tool_map[fn_call.name]
    fn_args = json.loads(fn_call.arguments)

    output = json.dumps(fn_callable(**fn_args))

    # Create a new message of role `"tool"` containing the output of your tool
    messages.append({
        "role": "tool",
        "content": output,
        "tool_call_id": call_id
    })

######################### Sending final request with tool results #########################

response = client.chat.completions.create(
    model="my-qwen3",
    messages=messages
)


print(response.choices[0].message.content)